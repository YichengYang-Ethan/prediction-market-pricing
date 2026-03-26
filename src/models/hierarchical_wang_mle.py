#!/usr/bin/env python3
"""
Hierarchical One-Stage Wang MLE
================================
Replaces two-step OLS in Section 5.3 with joint MLE:
    Pr(y_i = 1 | p_i, X_i) = Φ(z_i - X_iβ)
where z_i = Φ⁻¹(p_mkt_i) is a known offset.

Author: Yicheng Yang (UIUC)
"""

import os, sys, json, logging, time
import numpy as np
import pandas as pd
from scipy import stats, optimize
from datetime import datetime

np.random.seed(42)

# ─── Paths ──────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(ROOT, 'data')
OUT_TABLES = os.path.join(ROOT, 'outputs/tables')
OUT_LOGS = os.path.join(ROOT, 'outputs/logs')

os.makedirs(OUT_TABLES, exist_ok=True)
os.makedirs(OUT_LOGS, exist_ok=True)

# ─── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUT_LOGS, 'hierarchical_wang_mle.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════

def load_data():
    """Load combined analysis dataset + merge spread from combined_markets."""
    df = pd.read_parquet(os.path.join(DATA_DIR, 'combined_analysis_dataset.parquet'))
    log.info(f"Loaded combined_analysis_dataset: {len(df)} rows")

    # Merge spread + liquidity from combined_markets
    markets = pd.read_parquet(os.path.join(DATA_DIR, 'combined_markets.parquet'))
    merge_cols = ['id']
    for col in ['spread', 'liquidity', 'question']:
        if col in markets.columns:
            merge_cols.append(col)
    df = df.merge(markets[merge_cols], on='id', how='left')
    log.info(f"After merge: spread notna={df['spread'].notna().sum()}, "
             f"liquidity notna={df.get('liquidity', pd.Series()).notna().sum()}")

    # Identify 12-day subsample (original expanded data IDs)
    exp = pd.read_parquet(os.path.join(DATA_DIR, 'expanded_analysis_dataset.parquet'))
    exp_ids = set(exp['id'])
    df['is_12day'] = df['id'].isin(exp_ids)
    log.info(f"12-day subsample: {df['is_12day'].sum()} rows")

    return df


def prepare_sample(df, price_lo=0.05, price_hi=0.95, subset=None):
    """Filter and build design matrix.

    Returns: z (probit offset), X (design matrix), y (outcomes), feature_names
    """
    sub = df.copy()
    if subset == '12day':
        sub = sub[sub['is_12day']].copy()

    mask = (
        (sub['p_open'] > price_lo) & (sub['p_open'] < price_hi)
        & sub['p_open'].notna() & sub['resolved_yes'].notna()
        & sub['volume'].notna() & sub['duration_hours'].notna()
    )
    sub = sub[mask].reset_index(drop=True)

    # Outcome
    y = sub['resolved_yes'].values.astype(np.float64)

    # Probit offset
    p = np.clip(sub['p_open'].values.astype(np.float64), 1e-6, 1 - 1e-6)
    z = stats.norm.ppf(p)

    # Covariates
    log_vol = np.log1p(sub['volume'].values.astype(np.float64))
    log_dur = np.log1p(sub['duration_hours'].values.astype(np.float64))
    extremity = np.abs(sub['p_open'].values - 0.5)
    spread = sub['spread'].fillna(0).values.astype(np.float64)

    # Design matrix: [1, ln(Vol), ln(Dur), |p-0.5|, Spread]
    X = np.column_stack([np.ones(len(sub)), log_vol, log_dur, extremity, spread])
    feature_names = ['Constant', 'ln(Volume)', 'ln(Duration)', '|p - 0.5|', 'Spread']

    log.info(f"Sample: N={len(y)}, resolution_rate={y.mean():.3f}, "
             f"price_range=[{p.min():.3f}, {p.max():.3f}]")
    return z, X, y, feature_names, sub


# ═══════════════════════════════════════════════════════════════════
# MODEL
# ═══════════════════════════════════════════════════════════════════

def neg_log_likelihood(beta, z, X, y):
    """Negative Bernoulli log-likelihood with analytic gradient.

    Model: Pr(y=1) = Φ(z - Xβ)
    Returns: (nll, gradient)
    """
    eta = z - X @ beta                          # N-vector
    Phi = stats.norm.cdf(eta)                    # Φ(η)
    phi = stats.norm.pdf(eta)                    # φ(η)

    # Clip for numerical stability
    Phi = np.clip(Phi, 1e-12, 1 - 1e-12)

    # Log-likelihood
    ll = np.sum(y * np.log(Phi) + (1 - y) * np.log(1 - Phi))

    # Gradient: ∂ℓ/∂β = -Σ [(y·φ/Φ - (1-y)·φ/(1-Φ))] · X_i
    score_i = y * phi / Phi - (1 - y) * phi / (1 - Phi)  # N-vector
    grad_ll = -score_i @ X  # negative because offset is z - Xβ

    return -ll, -grad_ll  # return negative for minimization


def nll_only(beta, z, X, y):
    """Negative log-likelihood without gradient."""
    eta = z - X @ beta
    Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
    ll = np.sum(y * np.log(Phi) + (1 - y) * np.log(1 - Phi))
    return -ll


def estimate_mle(z, X, y, feature_names, label=""):
    """Run MLE estimation with Fisher and sandwich SEs.

    Returns dict with estimates, SEs, test statistics.
    """
    n, p = X.shape
    log.info(f"[{label}] Estimating MLE: N={n}, p={p}")

    # Initial values: β₀ = 0.176, rest = 0
    beta0 = np.zeros(p)
    beta0[0] = 0.176

    # Bounds
    bounds = [(-2, 2)] + [(-10, 10)] * (p - 1)

    # Optimize
    t0 = time.time()
    result = optimize.minimize(
        neg_log_likelihood, beta0, args=(z, X, y),
        method='L-BFGS-B', jac=True, bounds=bounds,
        options={'maxiter': 5000, 'ftol': 1e-12, 'gtol': 1e-10}
    )
    elapsed = time.time() - t0

    if not result.success:
        log.warning(f"[{label}] Optimizer warning: {result.message}")

    beta_hat = result.x
    ll_full = -result.fun
    log.info(f"[{label}] Converged in {elapsed:.2f}s, LL={ll_full:.2f}, "
             f"β̂ = {beta_hat}")

    # ── Fisher SE (observed information) ──
    # Numerical Hessian of NLL
    eps = 1e-5
    H = np.zeros((p, p))
    for i in range(p):
        e_i = np.zeros(p)
        e_i[i] = eps
        _, g_plus = neg_log_likelihood(beta_hat + e_i, z, X, y)
        _, g_minus = neg_log_likelihood(beta_hat - e_i, z, X, y)
        H[i, :] = (g_plus - g_minus) / (2 * eps)

    # Symmetrize
    H = (H + H.T) / 2

    # Check positive definiteness
    eigvals = np.linalg.eigvalsh(H)
    if eigvals.min() <= 0:
        log.warning(f"[{label}] Hessian not PD! min eigenvalue = {eigvals.min():.6f}")
        # Add small ridge
        H += np.eye(p) * max(-eigvals.min() + 1e-6, 1e-6)

    V_fisher = np.linalg.inv(H)
    se_fisher = np.sqrt(np.diag(V_fisher))

    # ── Sandwich (robust) SE ──
    eta = z - X @ beta_hat
    Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
    phi = stats.norm.pdf(eta)
    score_i = y * phi / Phi - (1 - y) * phi / (1 - Phi)  # N-vector
    S = (-score_i[:, None] * X)  # N × p score matrix (negative for ∂nll/∂β)

    # Meat: Σ s_i s_i'
    meat = S.T @ S  # p × p

    # Sandwich: H⁻¹ meat H⁻¹
    H_inv = V_fisher
    V_robust = H_inv @ meat @ H_inv
    se_robust = np.sqrt(np.diag(V_robust))

    # ── LR test: restricted model (λ = β₀ only) vs full ──
    beta_restricted = np.zeros(p)
    result_r = optimize.minimize(
        neg_log_likelihood, np.array([0.176]), args=(z, X[:, :1], y),
        method='L-BFGS-B', jac=True, bounds=[(-2, 2)],
        options={'maxiter': 5000, 'ftol': 1e-12}
    )
    ll_restricted = -result_r.fun
    lr_stat_covariates = 2 * (ll_full - ll_restricted)
    df_test = p - 1
    p_value_covariates = 1 - stats.chi2.cdf(max(lr_stat_covariates, 0), df=df_test)

    # ── LR test: λ = 0 (β = 0) ──
    ll_null = -nll_only(np.zeros(p), z, X, y)
    lr_stat_null = 2 * (ll_full - ll_null)
    p_value_null = 1 - stats.chi2.cdf(max(lr_stat_null, 0), df=p)

    # ── AIC / BIC ──
    aic = 2 * p - 2 * ll_full
    bic = p * np.log(n) - 2 * ll_full

    # ── Pseudo R² (McFadden) ──
    pseudo_r2 = 1 - (-ll_full) / (-ll_null) if ll_null != 0 else np.nan

    # Build results
    results = {
        'label': label,
        'n': n,
        'n_params': p,
        'll_full': float(ll_full),
        'll_restricted': float(ll_restricted),
        'll_null': float(ll_null),
        'lr_stat_covariates': float(lr_stat_covariates),
        'lr_df_covariates': df_test,
        'p_value_covariates': float(p_value_covariates),
        'lr_stat_null': float(lr_stat_null),
        'p_value_null': float(p_value_null),
        'aic': float(aic),
        'bic': float(bic),
        'pseudo_r2': float(pseudo_r2),
        'converged': result.success,
        'coefficients': [],
    }

    for i, name in enumerate(feature_names):
        z_fisher = beta_hat[i] / se_fisher[i] if se_fisher[i] > 0 else np.nan
        z_robust = beta_hat[i] / se_robust[i] if se_robust[i] > 0 else np.nan
        results['coefficients'].append({
            'name': name,
            'beta': float(beta_hat[i]),
            'se_fisher': float(se_fisher[i]),
            'se_robust': float(se_robust[i]),
            'z_fisher': float(z_fisher),
            'z_robust': float(z_robust),
            'p_fisher': float(2 * (1 - stats.norm.cdf(abs(z_fisher)))),
            'p_robust': float(2 * (1 - stats.norm.cdf(abs(z_robust)))),
        })

    # Log coefficient summary
    log.info(f"[{label}] Results:")
    log.info(f"  {'Variable':<20} {'β̂':>8} {'SE(F)':>8} {'SE(R)':>8} {'z(F)':>8} {'p(F)':>8}")
    for c in results['coefficients']:
        sig = '***' if c['p_fisher'] < 0.001 else '**' if c['p_fisher'] < 0.01 else '*' if c['p_fisher'] < 0.05 else ''
        log.info(f"  {c['name']:<20} {c['beta']:>8.4f} {c['se_fisher']:>8.4f} "
                 f"{c['se_robust']:>8.4f} {c['z_fisher']:>8.2f} {c['p_fisher']:>8.4f} {sig}")
    log.info(f"  LL={ll_full:.2f}, AIC={aic:.2f}, BIC={bic:.2f}, Pseudo-R²={pseudo_r2:.6f}")
    log.info(f"  LR(covariates): χ²={lr_stat_covariates:.2f}, df={df_test}, p={p_value_covariates:.2e}")

    return results


# ═══════════════════════════════════════════════════════════════════
# SMOKE TEST
# ═══════════════════════════════════════════════════════════════════

def smoke_test(z, X, y):
    """Verify: when β₁=β₂=β₃=β₄=0 constrained, β₀ ≈ 0.166 (pooled MLE on expanded)."""
    log.info("=" * 60)
    log.info("SMOKE TEST: Restricted model (intercept only)")
    log.info("=" * 60)

    # Estimate intercept-only model
    def nll_scalar(lam):
        eta = z - lam
        Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        return -np.sum(y * np.log(Phi) + (1 - y) * np.log(1 - Phi))

    result = optimize.minimize_scalar(nll_scalar, bounds=(-1, 1), method='bounded')
    lam_hat = result.x

    # SE
    eps = 1e-4
    h = (nll_scalar(lam_hat + eps) - 2 * nll_scalar(lam_hat) + nll_scalar(lam_hat - eps)) / eps**2
    se = 1 / np.sqrt(h) if h > 0 else np.nan

    log.info(f"  β₀ (intercept-only) = {lam_hat:.4f} (SE = {se:.4f})")
    log.info(f"  Expected ≈ 0.166 (pooled MLE from unified_results.json)")

    # Check
    target = 0.166
    if abs(lam_hat - target) < 0.02:
        log.info(f"  ✓ PASS: |{lam_hat:.4f} - {target}| = {abs(lam_hat - target):.4f} < 0.02")
        return True
    else:
        log.warning(f"  ✗ FAIL: |{lam_hat:.4f} - {target}| = {abs(lam_hat - target):.4f} >= 0.02")
        return False


# ═══════════════════════════════════════════════════════════════════
# LATEX TABLES
# ═══════════════════════════════════════════════════════════════════

def sig_stars(p):
    if p < 0.001: return '$^{***}$'
    if p < 0.01: return '$^{**}$'
    if p < 0.05: return '$^{*}$'
    return ''


def format_main_table(results_full, results_12day, out_path):
    """Generate LaTeX table: one-stage hierarchical MLE results."""

    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{One-stage hierarchical Wang MLE. Dependent variable: binary outcome $y_i$. '
        r'Model: $\Pr(y_i = 1) = \Phi(\Phi^{-1}(p_i^{\text{mkt}}) - X_i\beta)$. '
        r'Fisher and sandwich robust standard errors reported.}',
        r'\label{tab:hierarchical}',
        r'\begin{tabular}{lrrrrrr}',
        r'\toprule',
        r' & \multicolumn{3}{c}{Full sample ($N = ' + str(results_full['n']) + r'$)} '
        r'& \multicolumn{3}{c}{12-day subsample ($N = ' + str(results_12day['n']) + r'$)} \\',
        r'\cmidrule(lr){2-4} \cmidrule(lr){5-7}',
        r'Variable & Coef. & SE (Fisher) & SE (Robust) & Coef. & SE (Fisher) & SE (Robust) \\',
        r'\midrule',
    ]

    for i in range(len(results_full['coefficients'])):
        cf = results_full['coefficients'][i]
        c12 = results_12day['coefficients'][i]
        sig_f = sig_stars(cf['p_fisher'])
        sig_12 = sig_stars(c12['p_fisher'])
        name = cf['name']
        if name == '|p - 0.5|':
            name = r'$|p - 0.5|$ (extremity)'

        lines.append(
            f'{name} & {cf["beta"]:.4f}{sig_f} & ({cf["se_fisher"]:.4f}) & ({cf["se_robust"]:.4f}) '
            f'& {c12["beta"]:.4f}{sig_12} & ({c12["se_fisher"]:.4f}) & ({c12["se_robust"]:.4f}) \\\\'
        )

    lines.extend([
        r'\midrule',
        f'Log-likelihood & \\multicolumn{{3}}{{r}}{{{results_full["ll_full"]:.1f}}} '
        f'& \\multicolumn{{3}}{{r}}{{{results_12day["ll_full"]:.1f}}} \\\\',
        f'LR test ($\\lambda = \\text{{const}}$) & \\multicolumn{{3}}{{r}}{{$\\chi^2 = {results_full["lr_stat_covariates"]:.1f}$, '
        f'$p = {results_full["p_value_covariates"]:.2e}$}} '
        f'& \\multicolumn{{3}}{{r}}{{$\\chi^2 = {results_12day["lr_stat_covariates"]:.1f}$, '
        f'$p = {results_12day["p_value_covariates"]:.2e}$}} \\\\',
        f'AIC & \\multicolumn{{3}}{{r}}{{{results_full["aic"]:.1f}}} '
        f'& \\multicolumn{{3}}{{r}}{{{results_12day["aic"]:.1f}}} \\\\',
        f'$N$ & \\multicolumn{{3}}{{r}}{{{results_full["n"]:,}}} '
        f'& \\multicolumn{{3}}{{r}}{{{results_12day["n"]:,}}} \\\\',
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ])

    tex = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved main table: {out_path}")
    return tex


def format_comparison_table(results_onestage, out_path):
    """Generate comparison table: two-step OLS vs one-stage MLE."""

    # Two-step OLS values from Section 5.3 (paper)
    two_step = {
        'Constant': {'coef': 0.247, 'se': 0.021},
        'ln(Volume)': {'coef': -0.010, 'se': 0.002},
        'ln(Duration)': {'coef': 0.016, 'se': 0.004},
        '|p - 0.5|': {'coef': -0.361, 'se': 0.028},
        'Spread': {'coef': -0.612, 'se': 0.822},
    }

    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Comparison: two-step OLS (Section 5.3 original) vs.\ one-stage hierarchical MLE. '
        r'The one-stage model jointly estimates all parameters, eliminating the generated-regressor problem.}',
        r'\label{tab:twostep_vs_onestage}',
        r'\begin{tabular}{lrrrr}',
        r'\toprule',
        r' & \multicolumn{2}{c}{Two-step OLS} & \multicolumn{2}{c}{One-stage MLE} \\',
        r'\cmidrule(lr){2-3} \cmidrule(lr){4-5}',
        r'Variable & Coef. & HC1 SE & Coef. & Robust SE \\',
        r'\midrule',
    ]

    for c in results_onestage['coefficients']:
        name = c['name']
        ts_name = name
        if name == '|p - 0.5|':
            ts_name = '|p - 0.5|'
            name = r'$|p - 0.5|$ (extremity)'
        ts = two_step.get(ts_name, {'coef': '', 'se': ''})
        sig_ts = sig_stars(0.001) if ts_name in ['Constant', 'ln(Volume)', 'ln(Duration)', '|p - 0.5|'] else ''
        sig_os = sig_stars(c['p_robust'])

        if isinstance(ts['coef'], float):
            lines.append(
                f'{name} & {ts["coef"]:.4f}{sig_ts} & ({ts["se"]:.4f}) '
                f'& {c["beta"]:.4f}{sig_os} & ({c["se_robust"]:.4f}) \\\\'
            )
        else:
            lines.append(
                f'{name} & --- & --- & {c["beta"]:.4f}{sig_os} & ({c["se_robust"]:.4f}) \\\\'
            )

    lines.extend([
        r'\midrule',
        f'$R^2$ / Pseudo-$R^2$ & \\multicolumn{{2}}{{r}}{{0.072}} '
        f'& \\multicolumn{{2}}{{r}}{{{results_onestage["pseudo_r2"]:.4f}}} \\\\',
        f'$N$ & \\multicolumn{{2}}{{r}}{{2,460}} '
        f'& \\multicolumn{{2}}{{r}}{{{results_onestage["n"]:,}}} \\\\',
        r'Generated-regressor problem & \multicolumn{2}{r}{Yes} & \multicolumn{2}{r}{No} \\',
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ])

    tex = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved comparison table: {out_path}")
    return tex


# ═══════════════════════════════════════════════════════════════════
# ROBUSTNESS
# ═══════════════════════════════════════════════════════════════════

def robustness_category_fe(df, z_full, X_full, y_full, feature_names):
    """Add category fixed effects as robustness."""
    log.info("=" * 60)
    log.info("ROBUSTNESS: Category Fixed Effects")
    log.info("=" * 60)

    from deep_analysis import classify_category

    sub = df.copy()
    mask = (sub['p_open'] > 0.05) & (sub['p_open'] < 0.95) & sub['volume'].notna() & sub['duration_hours'].notna()
    sub = sub[mask].reset_index(drop=True)

    if 'question' in sub.columns:
        sub['cat'] = sub['question'].apply(classify_category)
    elif 'category' in sub.columns:
        sub['cat'] = sub['category'].fillna('Other')
    else:
        log.warning("No question/category column, skipping category FE")
        return None

    # Create dummies (drop 'Other' as reference)
    cats = sorted(sub['cat'].unique())
    ref = 'Other'
    cat_dummies = []
    cat_names = []
    for cat in cats:
        if cat == ref:
            continue
        cat_dummies.append((sub['cat'] == cat).values.astype(np.float64))
        cat_names.append(f'FE: {cat}')

    if not cat_dummies:
        log.warning("Only one category, skipping")
        return None

    z = stats.norm.ppf(np.clip(sub['p_open'].values, 1e-6, 1 - 1e-6))
    base_X = np.column_stack([
        np.ones(len(sub)),
        np.log1p(sub['volume'].values.astype(np.float64)),
        np.log1p(sub['duration_hours'].values.astype(np.float64)),
        np.abs(sub['p_open'].values - 0.5),
        sub['spread'].fillna(0).values.astype(np.float64),
    ])
    X_fe = np.column_stack([base_X] + cat_dummies)
    y = sub['resolved_yes'].values.astype(np.float64)
    names_fe = feature_names + cat_names

    results = estimate_mle(z, X_fe, y, names_fe, label="Category FE")
    return results


def robustness_price_range(df, ranges=None):
    """Sensitivity to price range filter."""
    if ranges is None:
        ranges = [(0.02, 0.98), (0.05, 0.95), (0.10, 0.90), (0.15, 0.85)]

    log.info("=" * 60)
    log.info("ROBUSTNESS: Price Range Sensitivity")
    log.info("=" * 60)

    results = []
    for lo, hi in ranges:
        z, X, y, names, _ = prepare_sample(df, price_lo=lo, price_hi=hi)
        r = estimate_mle(z, X, y, names, label=f"Range [{lo:.2f}, {hi:.2f}]")
        r['price_range'] = f'[{lo:.2f}, {hi:.2f}]'
        results.append(r)
    return results


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info("HIERARCHICAL ONE-STAGE WANG MLE")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # Load data
    df = load_data()

    # ── Smoke test ──
    z_full, X_full, y_full, names, sub_full = prepare_sample(df)
    passed = smoke_test(z_full, X_full, y_full)
    if not passed:
        log.error("SMOKE TEST FAILED — aborting")
        sys.exit(1)
    log.info("")

    # ── Main estimation: Full sample (28-day) ──
    log.info("=" * 60)
    log.info("MAIN ESTIMATION: Full sample (28-day)")
    log.info("=" * 60)
    results_full = estimate_mle(z_full, X_full, y_full, names, label="Full (28-day)")

    # Check coefficient signs
    signs_expected = {
        'ln(Volume)': 'negative',
        'ln(Duration)': 'positive',
        '|p - 0.5|': 'negative',
    }
    for c in results_full['coefficients']:
        expected = signs_expected.get(c['name'])
        if expected:
            actual = 'negative' if c['beta'] < 0 else 'positive'
            if actual != expected:
                log.error(f"SIGN CHECK FAILED: {c['name']} = {c['beta']:.4f} "
                          f"(expected {expected}, got {actual})")
                log.error("PAUSING — unexpected coefficient sign. Review before continuing.")
                # Don't exit, just warn prominently
                print(f"\n{'!'*60}")
                print(f"WARNING: {c['name']} has unexpected sign!")
                print(f"  Expected: {expected}, Got: {actual} ({c['beta']:.4f})")
                print(f"{'!'*60}\n")
            else:
                log.info(f"  ✓ {c['name']}: {actual} as expected ({c['beta']:.4f})")

    # ── 12-day subsample ──
    log.info("")
    log.info("=" * 60)
    log.info("ESTIMATION: 12-day subsample")
    log.info("=" * 60)
    z_12, X_12, y_12, names_12, _ = prepare_sample(df, subset='12day')
    results_12day = estimate_mle(z_12, X_12, y_12, names_12, label="12-day subsample")

    # ── Output LaTeX tables ──
    log.info("")
    log.info("=" * 60)
    log.info("GENERATING LATEX TABLES")
    log.info("=" * 60)

    tex_main = format_main_table(
        results_full, results_12day,
        os.path.join(OUT_TABLES, 'hierarchical_wang_main.tex')
    )
    print("\n" + tex_main + "\n")

    tex_comp = format_comparison_table(
        results_full,
        os.path.join(OUT_TABLES, 'hierarchical_wang_comparison.tex')
    )
    print("\n" + tex_comp + "\n")

    # ── Robustness: price range ──
    log.info("")
    rob_price = robustness_price_range(df)

    # ── Robustness: category FE ──
    log.info("")
    sys.path.insert(0, ROOT)
    try:
        rob_cat = robustness_category_fe(df, z_full, X_full, y_full, names)
    except Exception as e:
        log.warning(f"Category FE robustness skipped: {e}")
        rob_cat = None

    # ── Save all results as JSON ──
    all_results = {
        'full_sample': results_full,
        '12day_subsample': results_12day,
        'robustness_price_range': [
            {k: v for k, v in r.items() if k != 'coefficients'}
            for r in rob_price
        ] if rob_price else None,
        'robustness_category_fe': (
            {k: v for k, v in rob_cat.items()} if rob_cat else None
        ),
    }
    json_path = os.path.join(OUT_TABLES, 'hierarchical_wang_results.json')
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    log.info(f"Saved JSON results: {json_path}")

    # ── Summary ──
    log.info("")
    log.info("=" * 70)
    log.info("SUMMARY")
    log.info("=" * 70)
    for c in results_full['coefficients']:
        log.info(f"  {c['name']:<20} β̂ = {c['beta']:>8.4f}  "
                 f"SE(F) = {c['se_fisher']:.4f}  SE(R) = {c['se_robust']:.4f}")
    log.info(f"  LR test (covariates): χ² = {results_full['lr_stat_covariates']:.1f}, "
             f"p = {results_full['p_value_covariates']:.2e}")
    log.info(f"  N = {results_full['n']}")
    log.info("Done.")


if __name__ == '__main__':
    main()
