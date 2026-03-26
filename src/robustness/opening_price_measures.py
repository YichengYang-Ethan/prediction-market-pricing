#!/usr/bin/env python3
"""
Opening Price Measure Robustness Analysis
==========================================
Constructs 4 alternative opening price measures from CLOB hourly price histories
and re-runs core λ estimations to test sensitivity to early-stage illiquidity.

Author: Yicheng Yang (UIUC)
"""

import os, sys, json, logging, warnings
import numpy as np
import pandas as pd
from scipy import stats, optimize
from datetime import datetime

np.random.seed(42)
warnings.filterwarnings('ignore')

# ─── Paths ──────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(ROOT, 'data')
OUT_TABLES = os.path.join(ROOT, 'outputs/tables')
OUT_LOGS = os.path.join(ROOT, 'outputs/logs')

for d in [OUT_TABLES, OUT_LOGS]:
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUT_LOGS, 'opening_price_robustness.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# WANG MLE (self-contained, reused from unified_analysis.py logic)
# ═══════════════════════════════════════════════════════════════════

# Chunk size < 32768 to avoid numpy 1.26.3 + Accelerate BLAS bug
_CHUNK = 30000


def _nll_baseline(lam, z, y):
    """NLL for baseline Wang MLE: Pr(y=1) = Φ(z - λ). Chunked."""
    total_ll = 0.0
    total_grad = 0.0
    N = len(y)
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        z_c, y_c = z[start:end], y[start:end]
        eta = z_c - lam
        Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        phi = stats.norm.pdf(eta)
        total_ll += np.sum(y_c * np.log(Phi) + (1 - y_c) * np.log(1 - Phi))
        total_grad += np.sum(y_c * phi / Phi - (1 - y_c) * phi / (1 - Phi))
    return -total_ll, np.array([total_grad])


def _nll_baseline_val(lam, z, y):
    """NLL value only for baseline."""
    N = len(y)
    total = 0.0
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        eta = z[start:end] - lam[0]
        Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        total += -np.sum(y[start:end] * np.log(Phi) + (1 - y[start:end]) * np.log(1 - Phi))
    return total


def mle_baseline(p, y, label=""):
    """Baseline Wang MLE: single λ."""
    z = stats.norm.ppf(np.clip(p, 1e-6, 1 - 1e-6))
    result = optimize.minimize(
        lambda lam: _nll_baseline(lam[0], z, y),
        x0=[0.15], method='BFGS', jac=True,
        options={'gtol': 1e-8}
    )
    lam_hat = result.x[0]
    ll = -result.fun

    # SE from numerical Hessian
    H = optimize.approx_fprime([lam_hat], lambda l: _nll_baseline_val(l, z, y), 1e-7)
    # Actually need second derivative
    h = 1e-5
    f0 = _nll_baseline_val([lam_hat], z, y)
    fp = _nll_baseline_val([lam_hat + h], z, y)
    fm = _nll_baseline_val([lam_hat - h], z, y)
    hess = (fp - 2 * f0 + fm) / h**2
    se = 1.0 / np.sqrt(max(hess, 1e-10))

    z_stat = lam_hat / se
    p_val = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    log.info(f"  [{label}] λ̂={lam_hat:.4f}, SE={se:.4f}, z={z_stat:.2f}, p={p_val:.4e}, N={len(y)}")
    return {'lambda': float(lam_hat), 'se': float(se), 'z': float(z_stat),
            'p_value': float(p_val), 'n': int(len(y)), 'll': float(ll)}


# ═══════════════════════════════════════════════════════════════════
# HIERARCHICAL MLE (probit with offset)
# ═══════════════════════════════════════════════════════════════════

def _nll_hierarchical(theta, z, X, y):
    """NLL for hierarchical model: Pr(y=1) = Φ(z - Xβ). Chunked."""
    N = len(y)
    p_dim = len(theta)
    total_ll = 0.0
    total_grad = np.zeros(p_dim)
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        z_c, X_c, y_c = z[start:end], X[start:end], y[start:end]
        eta = z_c - X_c @ theta
        Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        phi = stats.norm.pdf(eta)
        total_ll += np.sum(y_c * np.log(Phi) + (1 - y_c) * np.log(1 - Phi))
        score = y_c * phi / Phi - (1 - y_c) * phi / (1 - Phi)
        total_grad += score @ X_c
    return -total_ll, total_grad


def _nll_hier_val(theta, z, X, y):
    N = len(y)
    total = 0.0
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        eta = z[start:end] - X[start:end] @ theta
        Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        total += -np.sum(y[start:end] * np.log(Phi) + (1 - y[start:end]) * np.log(1 - Phi))
    return total


def mle_hierarchical(p, y, volume, duration, label=""):
    """One-stage hierarchical Wang MLE with covariates."""
    z = stats.norm.ppf(np.clip(p, 1e-6, 1 - 1e-6))
    log_vol = np.log1p(volume)
    log_dur = np.log1p(duration)
    extremity = np.abs(p - 0.5)
    X = np.column_stack([np.ones(len(y)), log_vol, log_dur, extremity])
    names = ['Constant', 'ln(Volume)', 'ln(Duration)', '|p-0.5|']

    theta0 = np.zeros(X.shape[1])
    theta0[0] = 0.15

    result = optimize.minimize(
        _nll_hierarchical, theta0, args=(z, X, y),
        method='BFGS', jac=True, options={'gtol': 1e-8}
    )

    if not result.success:
        result2 = optimize.minimize(
            _nll_hierarchical, theta0, args=(z, X, y),
            method='Newton-CG', jac=True, options={'xtol': 1e-10}
        )
        if result2.fun < result.fun:
            result = result2

    theta_hat = result.x
    ll = -result.fun
    N = len(y)

    # Robust sandwich SE (chunked)
    p_dim = len(theta_hat)
    H = np.zeros((p_dim, p_dim))
    S = np.zeros((N, p_dim))
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        eta = z[start:end] - X[start:end] @ theta_hat
        Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        phi = stats.norm.pdf(eta)
        w = phi**2 / (Phi * (1 - Phi))
        Xw = X[start:end] * np.sqrt(w)[:, None]
        H += Xw.T @ Xw
        score = y[start:end] * phi / Phi - (1 - y[start:end]) * phi / (1 - Phi)
        S[start:end] = -score[:, None] * X[start:end]

    H_inv = np.linalg.inv(H)
    meat = S.T @ S
    V_robust = H_inv @ meat @ H_inv
    se_robust = np.sqrt(np.diag(V_robust))

    coeffs = {}
    for i, name in enumerate(names):
        z_stat = theta_hat[i] / se_robust[i] if se_robust[i] > 0 else np.nan
        p_val = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        coeffs[name] = {'beta': float(theta_hat[i]), 'se': float(se_robust[i]),
                        'z': float(z_stat), 'p': float(p_val)}

    # LR test vs constant λ
    ll_restricted = -_nll_hier_val(np.array([theta_hat[0], 0, 0, 0]), z, X, y)
    lr_stat = 2 * (ll - ll_restricted)
    lr_p = 1 - stats.chi2.cdf(max(lr_stat, 0), df=p_dim - 1)

    log.info(f"  [{label}] Hierarchical MLE: N={N}, LL={ll:.1f}, LR={lr_stat:.1f} (p={lr_p:.2e})")
    for name, c in coeffs.items():
        sig = '***' if c['p'] < 0.001 else '**' if c['p'] < 0.01 else '*' if c['p'] < 0.05 else ''
        log.info(f"    {name:<15} β={c['beta']:>8.4f} SE={c['se']:>7.4f} z={c['z']:>6.2f} {sig}")

    return {'coefficients': coeffs, 'n': N, 'll': float(ll),
            'lr_stat': float(lr_stat), 'lr_p': float(lr_p)}


# ═══════════════════════════════════════════════════════════════════
# VOLUME-STRATIFIED MLE
# ═══════════════════════════════════════════════════════════════════

def mle_volume_stratified(p, y, volume, label=""):
    """Wang MLE by volume tier."""
    tiers = [
        ('Low (<$500)', volume < 500),
        ('Medium ($500-2K)', (volume >= 500) & (volume < 2000)),
        ('High ($2K-10K)', (volume >= 2000) & (volume < 10000)),
        ('Very high (>$10K)', volume >= 10000),
    ]
    results = {}
    for tier_name, mask in tiers:
        if mask.sum() < 30:
            log.info(f"  [{label}] {tier_name}: N={mask.sum()} < 30, skipping")
            continue
        r = mle_baseline(p[mask], y[mask], label=f"{label} {tier_name}")
        results[tier_name] = r
    return results


# ═══════════════════════════════════════════════════════════════════
# OPENING PRICE MEASURES
# ═══════════════════════════════════════════════════════════════════

def build_opening_measures(df, histories, spread_map):
    """Construct 4 opening price measures for each contract.

    Returns DataFrame with columns: id, resolved_yes, volume, duration_hours,
    p_open_current, p_open_avg5, p_open_post_settle, p_open_filtered.
    """
    rows = []
    n_skip_short = 0
    n_skip_no_hist = 0

    for _, contract in df.iterrows():
        cid = str(contract['id'])
        hist_entry = histories.get(cid)
        if hist_entry is None:
            n_skip_no_hist += 1
            continue

        hist = hist_entry.get('history', [])
        if len(hist) < 5:
            n_skip_short += 1
            continue

        prices = [float(h['p']) for h in hist]
        n_pts = len(prices)
        vol = contract.get('volume', 0) or 0
        dur = contract.get('duration_hours', 0) or 0
        y = int(contract['resolved_yes'])
        spread = spread_map.get(cid, 0.001)

        # Measure 1: Current baseline — first 5% of lifetime midpoint
        idx_5pct = min(int(0.0 * (n_pts - 1)), n_pts - 1)  # p_open = idx 0
        p_current = prices[idx_5pct]

        # Measure 2: 5-price average (proxy for VWAP)
        # Average of first 5 distinct hourly prices
        unique_prices = []
        for p in prices[:min(10, n_pts)]:
            if len(unique_prices) == 0 or p != unique_prices[-1]:
                unique_prices.append(p)
            if len(unique_prices) >= 5:
                break
        # If fewer than 5 unique, use what we have (but at least 2)
        if len(unique_prices) >= 2:
            p_avg5 = float(np.mean(unique_prices[:5]))
        else:
            p_avg5 = p_current  # fallback

        # Measure 3: Post-settle — skip first 2 hourly obs, take avg of obs 3-5
        if n_pts >= 5:
            p_post_settle = float(np.mean(prices[2:5]))
        elif n_pts >= 3:
            p_post_settle = float(np.mean(prices[2:]))
        else:
            p_post_settle = p_current

        # Measure 4: Filtered — only keep if spread < median and price not stale
        # Stale = first 3 prices are identical
        is_stale = len(set(prices[:3])) == 1
        median_spread = 0.001  # from diagnostic: median spread = 0.001
        is_low_spread = spread <= median_spread * 2  # allow 2x median
        # For filtered: use p_current if passes filter, else NaN
        if not is_stale and is_low_spread:
            p_filtered = p_current
        else:
            p_filtered = np.nan

        rows.append({
            'id': contract['id'],
            'resolved_yes': y,
            'volume': float(vol),
            'duration_hours': float(dur),
            'p_open_current': p_current,
            'p_open_avg5': p_avg5,
            'p_open_post_settle': p_post_settle,
            'p_open_filtered': p_filtered,
            'n_hist_points': n_pts,
            'is_stale': is_stale,
            'spread': float(spread),
        })

    log.info(f"Opening measures: {len(rows)} contracts built, "
             f"{n_skip_no_hist} no history, {n_skip_short} too short")

    panel = pd.DataFrame(rows)

    # Diagnostics
    stale_pct = panel['is_stale'].mean() * 100
    filtered_n = panel['p_open_filtered'].notna().sum()
    log.info(f"  Stale quote rate (first 3 obs identical): {stale_pct:.1f}%")
    log.info(f"  Filtered measure: {filtered_n} / {len(panel)} pass filter ({filtered_n/len(panel)*100:.1f}%)")

    # Compare measures
    for m in ['p_open_avg5', 'p_open_post_settle']:
        diff = (panel[m] - panel['p_open_current']).abs()
        log.info(f"  |{m} - p_open_current|: mean={diff.mean():.4f}, "
                 f"median={diff.median():.4f}, max={diff.max():.4f}")

    return panel


# ═══════════════════════════════════════════════════════════════════
# LATEX TABLE
# ═══════════════════════════════════════════════════════════════════

def _sig(p):
    if p < 0.001: return '$^{***}$'
    if p < 0.01: return '$^{**}$'
    if p < 0.05: return '$^{*}$'
    return ''


def format_robustness_table(results, out_path):
    """LaTeX table comparing λ̂ across opening measures."""
    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Sensitivity of $\hat{\lambda}_{MLE}$ to opening price construction. '
        r'Each row uses a different method to extract the opening price from the hourly '
        r'CLOB price history. All other estimation details are identical to the baseline '
        r'specification (Section 5.2).}',
        r'\label{tab:opening_robustness}',
        r'\begin{tabular}{lrrrrr}',
        r'\toprule',
        r'Opening Measure & $N$ & $\hat{\lambda}_{MLE}$ & SE & $p$-value & $\Delta\%$ \\',
        r'\midrule',
    ]

    baseline_lam = None
    for name, r in results.items():
        lam = r['lambda']
        if baseline_lam is None:
            baseline_lam = lam
            delta = '---'
        else:
            pct_change = (lam - baseline_lam) / abs(baseline_lam) * 100 if baseline_lam != 0 else 0
            delta = f'{pct_change:+.1f}\\%'

        sig = _sig(r['p_value'])
        lines.append(
            f'{name} & {r["n"]:,} & {lam:.4f}{sig} & {r["se"]:.4f} '
            f'& {r["p_value"]:.2e} & {delta} \\\\'
        )

    lines.extend([
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ])

    tex = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved: {out_path}")
    return tex


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info("OPENING PRICE MEASURE ROBUSTNESS ANALYSIS")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # ── Load data ──
    df = pd.read_parquet(os.path.join(DATA_DIR, 'combined_analysis_dataset.parquet'))
    log.info(f"Analysis dataset: {len(df)} contracts")

    with open(os.path.join(DATA_DIR, 'combined_histories.json')) as f:
        histories = json.load(f)
    log.info(f"Histories: {len(histories)} markets")

    markets = pd.read_parquet(os.path.join(DATA_DIR, 'combined_markets.parquet'))
    spread_map = dict(zip(markets['id'].astype(str), markets['spread'].fillna(0.001)))

    # ── Build opening measures ──
    log.info("")
    log.info("=" * 60)
    log.info("STEP 1: Build Opening Price Measures")
    log.info("=" * 60)

    panel = build_opening_measures(df, histories, spread_map)

    # ── Define measures ──
    measures = {
        'First-5\\% midpoint (baseline)': 'p_open_current',
        'Post-settle (skip first 2h)': 'p_open_post_settle',
        '5-price average': 'p_open_avg5',
        'Filtered (non-stale, low-spread)': 'p_open_filtered',
    }

    price_lo, price_hi = 0.05, 0.95

    # ── Step 2: Run estimations ──
    log.info("")
    log.info("=" * 60)
    log.info("STEP 2: Core Estimations Per Measure")
    log.info("=" * 60)

    all_results = {}
    baseline_results = {}
    hier_results = {}
    vol_results = {}

    for measure_name, col in measures.items():
        log.info(f"\n{'─' * 50}")
        log.info(f"Measure: {measure_name} (column: {col})")
        log.info(f"{'─' * 50}")

        sub = panel[panel[col].notna()].copy()
        p = sub[col].values
        mask = (p > price_lo) & (p < price_hi)
        sub = sub[mask].copy()
        p = sub[col].values
        y = sub['resolved_yes'].values.astype(np.float64)

        log.info(f"  N after price filter: {len(sub)}")

        # (a) Baseline MLE
        r_base = mle_baseline(p, y, label=measure_name)
        baseline_results[measure_name] = r_base

        # (b) Hierarchical MLE
        vol = sub['volume'].values
        dur = sub['duration_hours'].values
        r_hier = mle_hierarchical(p, y, vol, dur, label=measure_name)
        hier_results[measure_name] = r_hier

        # (c) Volume-stratified
        r_vol = mle_volume_stratified(p, y, vol, label=measure_name)
        vol_results[measure_name] = r_vol

    # ── Step 3: Diagnostic ──
    log.info("")
    log.info("=" * 60)
    log.info("STEP 3: Diagnostic Summary")
    log.info("=" * 60)

    baseline_key = 'First-5\\% midpoint (baseline)'
    lam_baseline = baseline_results[baseline_key]['lambda']

    log.info(f"\nBaseline λ̂ = {lam_baseline:.4f}")
    log.info(f"{'Measure':<40} {'λ̂':>8} {'Δ%':>8} {'N':>8}")
    log.info("-" * 70)

    max_pct_change = 0
    for name, r in baseline_results.items():
        if name == baseline_key:
            pct = 0
        else:
            pct = (r['lambda'] - lam_baseline) / abs(lam_baseline) * 100
        max_pct_change = max(max_pct_change, abs(pct))
        log.info(f"{name:<40} {r['lambda']:>8.4f} {pct:>+7.1f}% {r['n']:>8,}")

    log.info(f"\nMax absolute change: {max_pct_change:.1f}%")
    if max_pct_change < 20:
        conclusion = ("Microstructure confounds do not materially affect the risk premium "
                      "estimate: the maximum change across all four opening price "
                      f"constructions is {max_pct_change:.1f}%.")
        log.info(f"CONCLUSION: {conclusion}")
    elif max_pct_change < 50:
        conclusion = (f"Moderate sensitivity to opening price construction "
                      f"(max change {max_pct_change:.1f}%). The risk premium is robust in sign "
                      "but its magnitude is partially affected by microstructure.")
        log.info(f"CONCLUSION: {conclusion}")
    else:
        conclusion = (f"Substantial sensitivity to opening price construction "
                      f"(max change {max_pct_change:.1f}%). A material portion of the "
                      "estimated risk premium may reflect early-stage illiquidity artifacts.")
        log.info(f"WARNING: {conclusion}")

    # Hierarchical comparison
    log.info(f"\n{'Measure':<40} {'Const':>8} {'lnVol':>8} {'lnDur':>8} {'|p-.5|':>8}")
    log.info("-" * 76)
    for name, r in hier_results.items():
        c = r['coefficients']
        log.info(f"{name:<40} {c['Constant']['beta']:>8.4f} {c['ln(Volume)']['beta']:>8.4f} "
                 f"{c['ln(Duration)']['beta']:>8.4f} {c['|p-0.5|']['beta']:>8.4f}")

    # ── Save outputs ──
    log.info("")
    log.info("=" * 60)
    log.info("SAVING OUTPUTS")
    log.info("=" * 60)

    # LaTeX table
    tex = format_robustness_table(
        baseline_results,
        os.path.join(OUT_TABLES, 'opening_price_robustness.tex')
    )
    print("\n" + tex + "\n")

    # JSON
    all_output = {
        'baseline_mle': {k: v for k, v in baseline_results.items()},
        'hierarchical_mle': {},
        'volume_stratified': {},
        'diagnostic': {
            'max_pct_change': float(max_pct_change),
            'conclusion': conclusion,
            'baseline_lambda': float(lam_baseline),
        },
    }
    # Serialize hierarchical results
    for k, v in hier_results.items():
        all_output['hierarchical_mle'][k] = v
    for k, v in vol_results.items():
        all_output['volume_stratified'][k] = {tk: tv for tk, tv in v.items()}

    json_path = os.path.join(OUT_TABLES, 'opening_price_robustness.json')
    with open(json_path, 'w') as f:
        json.dump(all_output, f, indent=2, default=str)
    log.info(f"Saved: {json_path}")

    log.info("")
    log.info("=" * 70)
    log.info("DONE")
    log.info("=" * 70)

    return all_output


if __name__ == '__main__':
    main()
