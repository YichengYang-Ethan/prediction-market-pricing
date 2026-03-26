#!/usr/bin/env python3
"""
Timing Harmonization: Polymarket Price Ladder vs Kalshi
========================================================
Quantifies how much of the Kalshi-vs-Polymarket covariate reversal
is explained by price timing alone.

Task A: Polymarket timing ladder (5%, 20%, 50%, 80%)
Task B: Distance-to-Kalshi diagnostic (L1, L2)
Task C: Harmonized interpretation memo

Author: Yicheng Yang (UIUC)
"""

import os, json, logging
import numpy as np
import pandas as pd
from scipy import stats, optimize
from datetime import datetime

np.random.seed(42)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(ROOT, 'data')
OUT_TABLES = os.path.join(ROOT, 'outputs/tables')
OUT_LOGS = os.path.join(ROOT, 'outputs/logs')
OUT_DOCS = os.path.join(ROOT, 'docs')
os.makedirs(OUT_TABLES, exist_ok=True)
os.makedirs(OUT_LOGS, exist_ok=True)
os.makedirs(OUT_DOCS, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUT_LOGS, 'timing_harmonization.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  CORE MLE (identical to hierarchical_wang_mle.py)
# ═══════════════════════════════════════════════════════════════════

def neg_log_likelihood(beta, z, X, y):
    """Negative Bernoulli log-likelihood with analytic gradient."""
    eta = z - X @ beta
    Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
    phi = stats.norm.pdf(eta)
    ll = np.sum(y * np.log(Phi) + (1 - y) * np.log(1 - Phi))
    score_i = y * phi / Phi - (1 - y) * phi / (1 - Phi)
    grad_ll = -score_i @ X
    return -ll, -grad_ll


def estimate_hierarchical(z, X, y, feature_names, label=""):
    """Full hierarchical MLE with Fisher + sandwich SEs."""
    n, p = X.shape

    beta0 = np.zeros(p)
    beta0[0] = 0.18
    bounds = [(-3, 3)] + [(-10, 10)] * (p - 1)

    result = optimize.minimize(
        neg_log_likelihood, beta0, args=(z, X, y),
        method='L-BFGS-B', jac=True, bounds=bounds,
        options={'maxiter': 5000, 'ftol': 1e-12, 'gtol': 1e-10}
    )
    if not result.success:
        log.warning(f"[{label}] Optimizer: {result.message}")

    beta_hat = result.x
    ll_full = -result.fun

    # Fisher SE (numerical Hessian)
    eps = 1e-5
    H = np.zeros((p, p))
    for i in range(p):
        e_i = np.zeros(p)
        e_i[i] = eps
        _, g_plus = neg_log_likelihood(beta_hat + e_i, z, X, y)
        _, g_minus = neg_log_likelihood(beta_hat - e_i, z, X, y)
        H[i, :] = (g_plus - g_minus) / (2 * eps)
    H = (H + H.T) / 2
    eigvals = np.linalg.eigvalsh(H)
    if eigvals.min() <= 0:
        H += np.eye(p) * max(-eigvals.min() + 1e-6, 1e-6)
    V_fisher = np.linalg.inv(H)
    se_fisher = np.sqrt(np.diag(V_fisher))

    # Sandwich SE
    eta = z - X @ beta_hat
    Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
    phi = stats.norm.pdf(eta)
    score_i = y * phi / Phi - (1 - y) * phi / (1 - Phi)
    S = (-score_i[:, None] * X)
    meat = S.T @ S
    V_robust = V_fisher @ meat @ V_fisher
    se_robust = np.sqrt(np.diag(V_robust))

    # LR test: restricted (intercept only) vs full
    result_r = optimize.minimize(
        neg_log_likelihood, np.array([0.18]), args=(z, X[:, :1], y),
        method='L-BFGS-B', jac=True, bounds=[(-3, 3)],
        options={'maxiter': 5000, 'ftol': 1e-12}
    )
    ll_restricted = -result_r.fun
    lr_cov = 2 * (ll_full - ll_restricted)

    coefficients = {}
    log.info(f"[{label}] N={n}")
    log.info(f"  {'Variable':<20} {'β̂':>8} {'SE(R)':>8} {'z':>8} {'p':>8}")
    for i, name in enumerate(feature_names):
        z_val = beta_hat[i] / se_robust[i] if se_robust[i] > 0 else np.nan
        p_val = float(2 * (1 - stats.norm.cdf(abs(z_val))))
        sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else ''
        log.info(f"  {name:<20} {beta_hat[i]:>8.4f} {se_robust[i]:>8.4f} "
                 f"{z_val:>8.2f} {p_val:>8.4f} {sig}")
        coefficients[name] = {
            'beta': float(beta_hat[i]),
            'se_fisher': float(se_fisher[i]),
            'se_robust': float(se_robust[i]),
            'z_robust': float(z_val),
            'p_robust': float(p_val),
        }
    log.info(f"  LR(cov): χ²={lr_cov:.1f}")

    return {
        'label': label, 'n': n,
        'll_full': float(ll_full), 'lr_covariates': float(lr_cov),
        'coefficients': coefficients,
    }


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info("TIMING HARMONIZATION: POLYMARKET LADDER vs KALSHI")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # ─── Load Polymarket data ───
    pm = pd.read_parquet(os.path.join(DATA_DIR, 'combined_analysis_dataset.parquet'))
    log.info(f"Polymarket loaded: {len(pm)} rows")

    # ─── Load Kalshi coefficients from stored results ───
    with open(os.path.join(OUT_TABLES, 'kalshi_hierarchical_results.json')) as f:
        kalshi_results = json.load(f)
    kalshi_coefs = {c['name']: c for c in kalshi_results['hierarchical_main']['coefficients']}
    kalshi_n = kalshi_results['hierarchical_main']['n']
    kalshi_beta = {
        'Constant': kalshi_coefs['Constant']['beta'],
        'ln(Volume)': kalshi_coefs['ln(Volume)']['beta'],
        'ln(Duration)': kalshi_coefs['ln(Duration)']['beta'],
        '|p - 0.5|': kalshi_coefs['|p - 0.5|']['beta'],
    }
    kalshi_se = {
        'Constant': kalshi_coefs['Constant']['se_robust'],
        'ln(Volume)': kalshi_coefs['ln(Volume)']['se_robust'],
        'ln(Duration)': kalshi_coefs['ln(Duration)']['se_robust'],
        '|p - 0.5|': kalshi_coefs['|p - 0.5|']['se_robust'],
    }
    log.info(f"Kalshi reference (N={kalshi_n}): β_vol={kalshi_beta['ln(Volume)']:+.4f}, "
             f"β_dur={kalshi_beta['ln(Duration)']:+.4f}, β_ext={kalshi_beta['|p - 0.5|']:+.4f}")

    # ─── Define timing points ───
    timing_points = [
        ('PM 5\\% (opening)', 'p_open'),
        ('PM 20\\%', 'p_20pct'),
        ('PM 50\\% (mid-life)', 'p_mid'),
        ('PM 80\\% (late-life)', 'p_80pct'),
    ]

    feat_names = ['Constant', 'ln(Volume)', 'ln(Duration)', '|p - 0.5|']
    slope_names = ['ln(Volume)', 'ln(Duration)', '|p - 0.5|']

    # ═══════════════════════════════════════════════════════════════
    #  TASK A: POLYMARKET TIMING LADDER
    # ═══════════════════════════════════════════════════════════════
    log.info("")
    log.info("=" * 70)
    log.info("TASK A: POLYMARKET TIMING LADDER")
    log.info("=" * 70)

    ladder_results = []

    for label, price_col in timing_points:
        log.info(f"\n--- {label} ({price_col}) ---")

        # Filter: valid price, volume, duration
        mask = (
            pm[price_col].notna()
            & (pm[price_col] > 0.05) & (pm[price_col] < 0.95)
            & pm['resolved_yes'].notna()
            & pm['volume'].notna() & (pm['volume'] > 0)
            & pm['duration_hours'].notna() & (pm['duration_hours'] > 0)
        )
        sub = pm[mask].reset_index(drop=True)

        y = sub['resolved_yes'].values.astype(np.float64)
        p_mkt = np.clip(sub[price_col].values.astype(np.float64), 1e-6, 1 - 1e-6)
        z = stats.norm.ppf(p_mkt)

        log_vol = np.log1p(sub['volume'].values.astype(np.float64))
        log_dur = np.log1p(sub['duration_hours'].values.astype(np.float64))
        extremity = np.abs(sub[price_col].values - 0.5)

        X = np.column_stack([np.ones(len(sub)), log_vol, log_dur, extremity])

        res = estimate_hierarchical(z, X, y, feat_names, label=label.replace('\\%', '%'))
        ladder_results.append({
            'label': label,
            'price_col': price_col,
            **res,
        })

    # ─── Generate Task A LaTeX table ───
    def sig_tex(pv):
        if pv < 0.001: return '$^{***}$'
        if pv < 0.01: return '$^{**}$'
        if pv < 0.05: return '$^{*}$'
        return ''

    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Polymarket timing ladder: one-stage hierarchical Wang MLE estimated at '
        r'different lifecycle pricing points. The Kalshi pooled estimate (using near-settlement '
        r'prices) is shown in the last row for comparison. Robust (sandwich) standard errors '
        r'in parentheses.}',
        r'\label{tab:polymarket_timing_ladder}',
        r'\begin{tabular}{lrcccc}',
        r'\toprule',
        r'Timing point & $N$ & $\hat{\beta}_0$ & $\hat{\beta}_{\text{vol}}$ '
        r'& $\hat{\beta}_{\text{dur}}$ & $\hat{\beta}_{\text{ext}}$ \\',
        r'\midrule',
    ]

    for lr in ladder_results:
        coefs = lr['coefficients']
        row_parts = [lr['label'], f"{lr['n']:,}"]
        for fname in feat_names:
            c = coefs[fname]
            row_parts.append(
                f"{c['beta']:.4f}{sig_tex(c['p_robust'])} ({c['se_robust']:.4f})"
            )
        lines.append(' & '.join(row_parts) + r' \\')

    # Kalshi row
    lines.append(r'\midrule')
    kalshi_parts = [r'Kalshi (near-settle.)', f"{kalshi_n:,}"]
    for fname in feat_names:
        c = kalshi_coefs[fname]
        kalshi_parts.append(
            f"{c['beta']:.4f}{sig_tex(c['p_robust'])} ({c['se_robust']:.4f})"
        )
    lines.append(' & '.join(kalshi_parts) + r' \\')

    # Sign comparison row
    lines.append(r'\midrule')
    lines.append(r'\multicolumn{6}{l}{\textit{Sign comparison (Polymarket opening $\to$ Kalshi):}} \\')
    sign_parts = ['', '']
    for fname in feat_names:
        pm_sign = '+' if ladder_results[0]['coefficients'][fname]['beta'] > 0 else '$-$'
        k_sign = '+' if kalshi_beta[fname] > 0 else '$-$'
        match = r'\checkmark' if (pm_sign == '+') == (k_sign == '+') else r'$\times$'
        sign_parts.append(f"{pm_sign} $\\to$ {k_sign} {match}")
    lines.append(' & '.join(sign_parts) + r' \\')

    lines += [
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ]

    tex_a = '\n'.join(lines)
    path_a = os.path.join(OUT_TABLES, 'polymarket_timing_ladder.tex')
    with open(path_a, 'w') as f:
        f.write(tex_a)
    log.info(f"\nSaved: {path_a}")

    # ═══════════════════════════════════════════════════════════════
    #  TASK B: DISTANCE-TO-KALSHI DIAGNOSTIC
    # ═══════════════════════════════════════════════════════════════
    log.info("")
    log.info("=" * 70)
    log.info("TASK B: DISTANCE-TO-KALSHI DIAGNOSTIC")
    log.info("=" * 70)

    distance_rows = []
    for lr in ladder_results:
        coefs = lr['coefficients']
        diffs = {}
        abs_diffs = []
        sq_diffs = []
        for fname in slope_names:
            d = coefs[fname]['beta'] - kalshi_beta[fname]
            diffs[fname] = d
            abs_diffs.append(abs(d))
            sq_diffs.append(d ** 2)

        l1 = sum(abs_diffs)
        l2 = np.sqrt(sum(sq_diffs))

        log.info(f"  {lr['label'].replace(chr(92)+'%','%')}: "
                 f"Δvol={diffs['ln(Volume)']:+.4f}, "
                 f"Δdur={diffs['ln(Duration)']:+.4f}, "
                 f"Δext={diffs['|p - 0.5|']:+.4f}, "
                 f"L1={l1:.4f}, L2={l2:.4f}")

        distance_rows.append({
            'label': lr['label'],
            'n': lr['n'],
            'diffs': diffs,
            'abs_diffs': {k: abs(v) for k, v in diffs.items()},
            'l1': l1,
            'l2': l2,
        })

    # Check monotonicity
    l1_values = [r['l1'] for r in distance_rows]
    l2_values = [r['l2'] for r in distance_rows]
    l1_monotone = all(l1_values[i] >= l1_values[i+1] for i in range(len(l1_values)-1))
    l2_monotone = all(l2_values[i] >= l2_values[i+1] for i in range(len(l2_values)-1))
    log.info(f"\n  L1 monotonically decreasing? {l1_monotone}")
    log.info(f"  L2 monotonically decreasing? {l2_monotone}")

    # Percentage reduction from opening to late-life
    l1_reduction = (l1_values[0] - l1_values[-1]) / l1_values[0] * 100
    l2_reduction = (l2_values[0] - l2_values[-1]) / l2_values[0] * 100
    log.info(f"  L1 reduction (5% → 80%): {l1_reduction:.1f}%")
    log.info(f"  L2 reduction (5% → 80%): {l2_reduction:.1f}%")

    # Per-coefficient monotonicity
    for fname in slope_names:
        vals = [abs(r['diffs'][fname]) for r in distance_rows]
        mono = all(vals[i] >= vals[i+1] for i in range(len(vals)-1))
        reduction = (vals[0] - vals[-1]) / vals[0] * 100 if vals[0] != 0 else 0
        log.info(f"  {fname}: |Δ| from {vals[0]:.4f} → {vals[-1]:.4f} "
                 f"(reduction {reduction:.1f}%, monotone={mono})")

    # ─── Generate Task B LaTeX table ───
    lines_b = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Distance between Polymarket and Kalshi slope coefficients at each '
        r'timing point. $\Delta\beta_j = \hat{\beta}^{\text{PM}}_j - \hat{\beta}^{\text{Kalshi}}_j$ '
        r'for each covariate $j$. Decreasing distances indicate convergence toward the '
        r'Kalshi coefficient pattern.}',
        r'\label{tab:polymarket_vs_kalshi_distance}',
        r'\begin{tabular}{lcccccc}',
        r'\toprule',
        r' & \multicolumn{3}{c}{Signed difference $\Delta\beta$} '
        r'& \multicolumn{2}{c}{Distance} & \\',
        r'\cmidrule(lr){2-4} \cmidrule(lr){5-6}',
        r'Timing & $\Delta\beta_{\text{vol}}$ & $\Delta\beta_{\text{dur}}$ '
        r'& $\Delta\beta_{\text{ext}}$ & $L_1$ & $L_2$ & Reduction \\',
        r'\midrule',
    ]

    for i, dr in enumerate(distance_rows):
        d = dr['diffs']
        reduction_str = '---' if i == 0 else f"{(1 - dr['l1']/distance_rows[0]['l1'])*100:.0f}\\%"
        lines_b.append(
            f"{dr['label']} & {d['ln(Volume)']:+.4f} & {d['ln(Duration)']:+.4f} "
            f"& {d['|p - 0.5|']:+.4f} & {dr['l1']:.4f} & {dr['l2']:.4f} "
            f"& {reduction_str} \\\\"
        )

    lines_b += [
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ]

    tex_b = '\n'.join(lines_b)
    path_b = os.path.join(OUT_TABLES, 'polymarket_vs_kalshi_timing_distance.tex')
    with open(path_b, 'w') as f:
        f.write(tex_b)
    log.info(f"\nSaved: {path_b}")

    # ═══════════════════════════════════════════════════════════════
    #  TASK C: HARMONIZED INTERPRETATION MEMO
    # ═══════════════════════════════════════════════════════════════
    log.info("")
    log.info("=" * 70)
    log.info("TASK C: INTERPRETATION MEMO")
    log.info("=" * 70)

    # Determine which coefficients flip sign
    sign_flips = {}
    for fname in slope_names:
        pm_open = ladder_results[0]['coefficients'][fname]['beta']
        pm_late = ladder_results[-1]['coefficients'][fname]['beta']
        k_val = kalshi_beta[fname]
        same_sign_open = (pm_open > 0) == (k_val > 0)
        same_sign_late = (pm_late > 0) == (k_val > 0)
        sign_flips[fname] = {
            'pm_open': pm_open,
            'pm_late': pm_late,
            'kalshi': k_val,
            'matches_open': same_sign_open,
            'matches_late': same_sign_late,
            'flipped_to_match': not same_sign_open and same_sign_late,
        }

    # Prepare summary data for memo
    vol_vals = [lr['coefficients']['ln(Volume)']['beta'] for lr in ladder_results]
    dur_vals = [lr['coefficients']['ln(Duration)']['beta'] for lr in ladder_results]
    ext_vals = [lr['coefficients']['|p - 0.5|']['beta'] for lr in ladder_results]

    vol_range = max(vol_vals) - min(vol_vals)
    dur_range = max(dur_vals) - min(dur_vals)
    ext_range = max(ext_vals) - min(ext_vals)

    # How much of the gap does timing close?
    gap_closed = {}
    for fname in slope_names:
        pm_open = ladder_results[0]['coefficients'][fname]['beta']
        pm_late = ladder_results[-1]['coefficients'][fname]['beta']
        k_val = kalshi_beta[fname]
        total_gap = abs(pm_open - k_val)
        remaining_gap = abs(pm_late - k_val)
        closed_pct = (1 - remaining_gap / total_gap) * 100 if total_gap > 0 else 0
        gap_closed[fname] = {
            'total': total_gap,
            'remaining': remaining_gap,
            'closed_pct': closed_pct,
        }
        log.info(f"  {fname}: gap {total_gap:.4f} → {remaining_gap:.4f} "
                 f"({closed_pct:.1f}% closed by timing)")

    # Any sign flips?
    n_flips = sum(1 for v in sign_flips.values() if v['flipped_to_match'])
    n_still_opposite = sum(1 for v in sign_flips.values()
                           if not v['matches_open'] and not v['matches_late'])

    memo = f"""# Timing Harmonization Memo

Date: {datetime.now().strftime('%Y-%m-%d')}

---

## Background

The Kalshi hierarchical MLE (N={kalshi_n:,}) shows all three slope coefficients
with reversed signs relative to Polymarket:

| Coefficient | Polymarket (opening) | Kalshi (near-settlement) |
|-------------|---------------------|-------------------------|
| β_volume | {ladder_results[0]['coefficients']['ln(Volume)']['beta']:+.4f} | {kalshi_beta['ln(Volume)']:+.4f} |
| β_duration | {ladder_results[0]['coefficients']['ln(Duration)']['beta']:+.4f} | {kalshi_beta['ln(Duration)']:+.4f} |
| β_extremity | {ladder_results[0]['coefficients']['|p - 0.5|']['beta']:+.4f} | {kalshi_beta['|p - 0.5|']:+.4f} |

This memo assesses how much of this reversal is attributable to price timing
(Polymarket uses early-lifecycle prices; Kalshi uses near-settlement prices).

## Question 1: Monotonic convergence?

"""

    # Check each coefficient
    for fname in slope_names:
        vals = [lr['coefficients'][fname]['beta'] for lr in ladder_results]
        abs_diffs = [abs(v - kalshi_beta[fname]) for v in vals]
        mono = all(abs_diffs[i] >= abs_diffs[i+1] for i in range(len(abs_diffs)-1))
        direction = "toward Kalshi" if abs_diffs[-1] < abs_diffs[0] else "away from Kalshi"
        memo += f"**{fname}**: {vals[0]:+.4f} → {vals[-1]:+.4f} (Kalshi: {kalshi_beta[fname]:+.4f}). "
        memo += f"|Δ| moves {direction}: {abs_diffs[0]:.4f} → {abs_diffs[-1]:.4f}. "
        memo += f"Monotonic: {'Yes' if mono else 'No'}.\n\n"

    memo += f"""**Aggregate L1 distance**: {l1_values[0]:.4f} → {l1_values[-1]:.4f} """
    memo += f"""(reduction: {l1_reduction:.1f}%). """
    memo += f"""Monotonically decreasing: {'Yes' if l1_monotone else 'No'}.\n\n"""

    memo += f"""**Aggregate L2 distance**: {l2_values[0]:.4f} → {l2_values[-1]:.4f} """
    memo += f"""(reduction: {l2_reduction:.1f}%). """
    memo += f"""Monotonically decreasing: {'Yes' if l2_monotone else 'No'}.\n\n"""

    memo += """## Question 2: Which coefficients are most timing-sensitive?

"""
    sensitivities = [
        ('ln(Volume)', vol_range, gap_closed['ln(Volume)']['closed_pct']),
        ('ln(Duration)', dur_range, gap_closed['ln(Duration)']['closed_pct']),
        ('|p - 0.5|', ext_range, gap_closed['|p - 0.5|']['closed_pct']),
    ]
    sensitivities.sort(key=lambda x: x[2], reverse=True)

    for fname, rng, pct in sensitivities:
        memo += f"- **{fname}**: range across timing points = {rng:.4f}, "
        memo += f"gap closed = {pct:.1f}%\n"

    most_sensitive = sensitivities[0][0]
    memo += f"\n**Most timing-sensitive**: {most_sensitive} "
    memo += f"({sensitivities[0][2]:.1f}% of the PM-vs-Kalshi gap closed by moving "
    memo += f"from opening to late-life pricing).\n\n"

    memo += """## Question 3: Does timing fully explain the reversal?

"""
    # Check sign convergence
    for fname in slope_names:
        sf = sign_flips[fname]
        if sf['flipped_to_match']:
            memo += f"- **{fname}**: Sign flips from {sf['pm_open']:+.4f} to {sf['pm_late']:+.4f}, "
            memo += f"matching Kalshi ({sf['kalshi']:+.4f}). **Timing explains the sign reversal.**\n"
        elif not sf['matches_open'] and not sf['matches_late']:
            memo += f"- **{fname}**: Remains opposite ({sf['pm_late']:+.4f} vs Kalshi {sf['kalshi']:+.4f}). "
            memo += f"**Timing narrows the gap but does not flip the sign.**\n"
        else:
            memo += f"- **{fname}**: Signs already match. Timing shifts magnitude only.\n"

    # Overall assessment
    if n_flips == 3:
        timing_verdict = "fully explains"
    elif n_flips >= 2:
        timing_verdict = "substantially explains"
    elif n_flips == 1:
        timing_verdict = "partially explains"
    else:
        if l1_reduction > 50:
            timing_verdict = "substantially narrows but does not fully explain"
        elif l1_reduction > 25:
            timing_verdict = "partially explains"
        else:
            timing_verdict = "plays a limited role in explaining"

    memo += f"""
**Summary**: Price timing {timing_verdict} the cross-platform covariate reversal.
L1 distance reduction from opening to late-life: {l1_reduction:.1f}%.
Sign flips achieved by timing alone: {n_flips}/3.
Signs still reversed after timing adjustment: {n_still_opposite}/3.

"""

    memo += """## Question 4: What remains unexplained?

"""
    remaining_factors = []
    if n_still_opposite > 0:
        reversed_names = [fname for fname, sf in sign_flips.items()
                          if not sf['matches_open'] and not sf['matches_late']]
        memo += f"After timing adjustment, {n_still_opposite} coefficient(s) remain opposite "
        memo += f"in sign ({', '.join(reversed_names)}). "
        remaining_factors.append("coefficient sign persistence")

    memo += """The residual gap likely reflects:

1. **Market composition**: 86.9% of Kalshi contracts are <24h duration (weather daily, crypto daily),
   vs Polymarket's more balanced duration distribution. The duration split analysis (Task 1 of the
   sub-analysis) confirms that Short (<24h) contracts exhibit all three reversed signs even within
   Kalshi, while Medium (24h-7d) contracts show 2/3 signs matching Polymarket.

2. **Contract microstructure**: Kalshi uses order-book with CLOB matching; Polymarket uses AMM-based
   token trading. Liquidity provision, spread dynamics, and price impact differ structurally.

3. **Participant composition**: Kalshi attracts US-regulated retail and institutional participants
   (CFTC-regulated DCME); Polymarket operates offshore with crypto-native participants.
   Risk preferences and information processing may differ systematically.

**Separation of effects**: The timing harmonization closes """
    memo += f"{l1_reduction:.0f}% of the aggregate gap. "
    memo += f"""The remaining {100 - l1_reduction:.0f}% is attributable to composition, microstructure,
and participant effects — which this diagnostic cannot separate without matched-contract data.

---

## Data tables

| Timing | N | β₀ | β_vol | β_dur | β_ext |
|--------|---|-------|-------|-------|-------|
"""

    for lr in ladder_results:
        c = lr['coefficients']
        memo += f"| {lr['label'].replace(chr(92)+'%','%')} | {lr['n']:,} "
        for fname in feat_names:
            memo += f"| {c[fname]['beta']:+.4f} "
        memo += "|\n"
    memo += f"| Kalshi (near-settlement) | {kalshi_n:,} "
    for fname in feat_names:
        memo += f"| {kalshi_beta[fname]:+.4f} "
    memo += "|\n"

    memo += """
| Timing | Δβ_vol | Δβ_dur | Δβ_ext | L1 | L2 | Reduction |
|--------|--------|--------|--------|-----|-----|-----------|
"""
    for i, dr in enumerate(distance_rows):
        d = dr['diffs']
        red = '---' if i == 0 else f"{(1 - dr['l1']/distance_rows[0]['l1'])*100:.0f}%"
        memo += (f"| {dr['label'].replace(chr(92)+'%','%')} | {d['ln(Volume)']:+.4f} "
                 f"| {d['ln(Duration)']:+.4f} | {d['|p - 0.5|']:+.4f} "
                 f"| {dr['l1']:.4f} | {dr['l2']:.4f} | {red} |\n")

    memo_path = os.path.join(OUT_DOCS, 'timing_harmonization_memo.md')
    with open(memo_path, 'w') as f:
        f.write(memo)
    log.info(f"Saved: {memo_path}")

    # ─── Save JSON ───
    all_results = {
        'ladder': [{
            'label': lr['label'],
            'price_col': lr['price_col'],
            'n': lr['n'],
            'coefficients': lr['coefficients'],
        } for lr in ladder_results],
        'kalshi_reference': {
            'n': kalshi_n,
            'beta': kalshi_beta,
            'se_robust': kalshi_se,
        },
        'distances': [{
            'label': dr['label'],
            'diffs': dr['diffs'],
            'l1': dr['l1'],
            'l2': dr['l2'],
        } for dr in distance_rows],
        'summary': {
            'l1_reduction_pct': l1_reduction,
            'l2_reduction_pct': l2_reduction,
            'l1_monotone': l1_monotone,
            'l2_monotone': l2_monotone,
            'sign_flips': n_flips,
            'signs_still_opposite': n_still_opposite,
            'gap_closed_pct': {k: v['closed_pct'] for k, v in gap_closed.items()},
            'timing_verdict': timing_verdict,
        }
    }

    json_path = os.path.join(OUT_TABLES, 'timing_harmonization_results.json')
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    log.info(f"Saved: {json_path}")

    log.info("\nDone.")
    return all_results


if __name__ == '__main__':
    main()
