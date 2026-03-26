#!/usr/bin/env python3
"""
Kalshi Hierarchical One-Stage Wang MLE + Category-Level Comparison
==================================================================
Runs the same probit-offset model as Section 5.3 on Kalshi data:
    Pr(y_i = 1 | p_i, X_i) = Φ(Φ⁻¹(p_mkt_i) - X_i β)

Also estimates category-level λ for cross-platform comparison with Polymarket Table 14.

Author: Yicheng Yang (UIUC)
"""

import os, sys, json, logging, time, re
import numpy as np
import pandas as pd
from scipy import stats, optimize
from datetime import datetime

np.random.seed(42)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(ROOT, 'data')
OUT_TABLES = os.path.join(ROOT, 'outputs/tables')
OUT_LOGS = os.path.join(ROOT, 'outputs/logs')
os.makedirs(OUT_TABLES, exist_ok=True)
os.makedirs(OUT_LOGS, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUT_LOGS, 'kalshi_hierarchical.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

_CHUNK = 30000  # BLAS bug workaround


# ═══════════════════════════════════════════════════════════════════
#  CORE MLE
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


def nll_only(beta, z, X, y):
    """NLL without gradient."""
    eta = z - X @ beta
    Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
    return -np.sum(y * np.log(Phi) + (1 - y) * np.log(1 - Phi))


def scalar_mle(z, y):
    """Estimate constant-only λ (pooled MLE)."""
    def nll(lam):
        eta = z - lam
        Phi = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        return -np.sum(y * np.log(Phi) + (1 - y) * np.log(1 - Phi))

    result = optimize.minimize_scalar(nll, bounds=(-2, 2), method='bounded')
    lam = result.x
    ll = -result.fun

    eps = 1e-4
    h = (nll(lam + eps) - 2 * nll(lam) + nll(lam - eps)) / eps**2
    se = 1 / np.sqrt(h) if h > 0 else np.nan

    # LR test vs λ=0
    ll_null = -nll(0.0)
    lr = 2 * (ll - ll_null)
    p_val = 1 - stats.chi2.cdf(max(lr, 0), df=1)

    # 95% CI
    ci_lo = lam - 1.96 * se
    ci_hi = lam + 1.96 * se

    return {
        'lambda': float(lam), 'se': float(se), 'll': float(ll),
        'lr': float(lr), 'p_value': float(p_val),
        'ci_lo': float(ci_lo), 'ci_hi': float(ci_hi),
    }


def estimate_mle(z, X, y, feature_names, label=""):
    """Full MLE with Fisher and sandwich SEs."""
    n, p = X.shape
    log.info(f"[{label}] N={n}, p={p}")

    beta0 = np.zeros(p)
    beta0[0] = 0.187  # Kalshi pooled estimate
    bounds = [(-2, 2)] + [(-10, 10)] * (p - 1)

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
        neg_log_likelihood, np.array([0.187]), args=(z, X[:, :1], y),
        method='L-BFGS-B', jac=True, bounds=[(-2, 2)],
        options={'maxiter': 5000, 'ftol': 1e-12}
    )
    ll_restricted = -result_r.fun
    lr_cov = 2 * (ll_full - ll_restricted)
    p_cov = 1 - stats.chi2.cdf(max(lr_cov, 0), df=p - 1)

    # LR test: λ=0
    ll_null = -nll_only(np.zeros(p), z, X, y)
    lr_null = 2 * (ll_full - ll_null)
    p_null = 1 - stats.chi2.cdf(max(lr_null, 0), df=p)

    aic = 2 * p - 2 * ll_full
    bic = p * np.log(n) - 2 * ll_full
    pseudo_r2 = 1 - (-ll_full) / (-ll_null) if ll_null != 0 else np.nan

    results = {
        'label': label, 'n': n, 'n_params': p,
        'll_full': float(ll_full), 'll_restricted': float(ll_restricted),
        'll_null': float(ll_null),
        'lr_covariates': float(lr_cov), 'p_covariates': float(p_cov),
        'lr_null': float(lr_null), 'p_null': float(p_null),
        'aic': float(aic), 'bic': float(bic), 'pseudo_r2': float(pseudo_r2),
        'coefficients': [],
    }

    log.info(f"[{label}] Results:")
    log.info(f"  {'Variable':<20} {'β̂':>8} {'SE(F)':>8} {'SE(R)':>8} {'z(F)':>8} {'p(F)':>8}")
    for i, name in enumerate(feature_names):
        z_f = beta_hat[i] / se_fisher[i] if se_fisher[i] > 0 else np.nan
        z_r = beta_hat[i] / se_robust[i] if se_robust[i] > 0 else np.nan
        p_f = float(2 * (1 - stats.norm.cdf(abs(z_f))))
        p_r = float(2 * (1 - stats.norm.cdf(abs(z_r))))
        sig = '***' if p_f < 0.001 else '**' if p_f < 0.01 else '*' if p_f < 0.05 else ''
        log.info(f"  {name:<20} {beta_hat[i]:>8.4f} {se_fisher[i]:>8.4f} "
                 f"{se_robust[i]:>8.4f} {z_f:>8.2f} {p_f:>8.4f} {sig}")
        results['coefficients'].append({
            'name': name, 'beta': float(beta_hat[i]),
            'se_fisher': float(se_fisher[i]), 'se_robust': float(se_robust[i]),
            'z_fisher': float(z_f), 'z_robust': float(z_r),
            'p_fisher': p_f, 'p_robust': p_r,
        })

    log.info(f"  LL={ll_full:.2f}, AIC={aic:.2f}, BIC={bic:.2f}")
    log.info(f"  LR(covariates): χ²={lr_cov:.1f}, df={p-1}, p={p_cov:.2e}")
    log.info(f"  LR(null): χ²={lr_null:.1f}, df={p}, p={p_null:.2e}")

    return results


# ═══════════════════════════════════════════════════════════════════
#  CATEGORY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════

CATEGORY_RULES = {
    'Sports': [r'\b(nba|nfl|mlb|nhl|ufc|mma|boxing|tennis|soccer|football|cricket|golf|f1|formula|racing|ncaa|college|premier league|la liga|serie a|bundesliga|champion|playoffs|super bowl|world series|stanley cup|finals|game \d|match|fight|bout|round)\b'],
    'Politics': [r'\b(president|election|congress|senate|house|democrat|republican|trump|biden|governor|mayor|political|vote|ballot|legislation|executive order|impeach|tariff|cabinet|pardon|bill pass|ratif)\b'],
    'Crypto': [r'\b(bitcoin|btc|ethereum|eth|crypto|doge|solana|sol|xrp|bnb|coin|token|defi|nft)\b'],
    'Tech': [r'\b(apple|google|meta|microsoft|amazon|tesla|nvidia|openai|chatgpt|ai\b|artificial intelligence|tech|iphone|android|starship|spacex|launch)\b'],
}


def classify_category(title):
    """Classify Kalshi contract into category by keywords."""
    t = title.lower()
    for cat, patterns in CATEGORY_RULES.items():
        for pat in patterns:
            if re.search(pat, t):
                return cat
    return 'Other'


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info("KALSHI HIERARCHICAL MLE + CATEGORY COMPARISON")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # Load data
    df = pd.read_parquet(os.path.join(DATA_DIR, 'kalshi_analysis_dataset.parquet'))
    log.info(f"Loaded: {len(df)} Kalshi contracts")

    # Filter: valid prices, volume, duration
    mask = (
        (df['p_open'] > 0.05) & (df['p_open'] < 0.95)
        & df['p_open'].notna() & df['resolved_yes'].notna()
        & df['volume'].notna() & (df['volume'] > 0)
        & df['duration_hours'].notna() & (df['duration_hours'] > 0)
    )
    df = df[mask].reset_index(drop=True)
    log.info(f"After filtering: {len(df)}")

    # Build design matrix
    y = df['resolved_yes'].values.astype(np.float64)
    p = np.clip(df['p_open'].values.astype(np.float64), 1e-6, 1 - 1e-6)
    z = stats.norm.ppf(p)

    log_vol = np.log1p(df['volume'].values.astype(np.float64))
    log_dur = np.log1p(df['duration_hours'].values.astype(np.float64))
    extremity = np.abs(df['p_open'].values - 0.5)

    X_main = np.column_stack([np.ones(len(df)), log_vol, log_dur, extremity])
    feat_main = ['Constant', 'ln(Volume)', 'ln(Duration)', '|p - 0.5|']

    # ─── Task 2: Main hierarchical MLE ───
    log.info("")
    log.info("=" * 60)
    log.info("TASK 2: HIERARCHICAL MLE (MAIN SPEC)")
    log.info("=" * 60)

    res_main = estimate_mle(z, X_main, y, feat_main, label="Kalshi Main")

    # ─── Task 2: Year fixed effects robustness ───
    log.info("")
    log.info("=" * 60)
    log.info("TASK 2: WITH YEAR FIXED EFFECTS")
    log.info("=" * 60)

    df['year'] = pd.to_datetime(df['settlement_ts'], format='ISO8601').dt.year
    years = sorted(df['year'].unique())
    log.info(f"Years: {years}")

    # Create year dummies (omit first year as reference)
    year_dummies = []
    year_names = []
    for yr in years[1:]:
        year_dummies.append((df['year'] == yr).values.astype(np.float64))
        year_names.append(f'Year={yr}')

    if year_dummies:
        X_year = np.column_stack([X_main] + year_dummies)
        feat_year = feat_main + year_names
        res_year = estimate_mle(z, X_year, y, feat_year, label="Kalshi Year FE")
    else:
        res_year = None

    # ─── Task 2: Generate LaTeX table ───
    log.info("")
    log.info("Generating LaTeX table...")

    def sig(pv):
        if pv < 0.001: return '$^{***}$'
        if pv < 0.01: return '$^{**}$'
        if pv < 0.05: return '$^{*}$'
        return ''

    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{One-stage hierarchical Wang MLE on Kalshi contracts. '
        r'Dependent variable: binary outcome $y_i$. '
        r'Model: $\Pr(y_i = 1) = \Phi(\Phi^{-1}(p_i^{\text{mkt}}) - X_i\beta)$. '
        r'Fisher standard errors reported; sandwich robust SEs in brackets.}',
        r'\label{tab:kalshi_hierarchical}',
    ]

    n_main = res_main['n']
    cols = r' & \multicolumn{2}{c}{Main spec} '
    cmidrule = r'\cmidrule(lr){2-3}'
    if res_year:
        cols += r'& \multicolumn{2}{c}{Year FE} '
        cmidrule += r' \cmidrule(lr){4-5}'
    cols += r'\\'

    lines += [
        r'\begin{tabular}{l' + 'rr' * (2 if res_year else 1) + '}',
        r'\toprule',
        cols,
        cmidrule,
        r'Variable & Coef. & SE ' + (r'& Coef. & SE ' if res_year else '') + r'\\',
        r'\midrule',
    ]

    # Main spec rows
    for c in res_main['coefficients']:
        name_tex = c['name'].replace('ln(Volume)', r'$\ln(\text{Volume})$')
        name_tex = name_tex.replace('ln(Duration)', r'$\ln(\text{Duration})$')
        name_tex = name_tex.replace('|p - 0.5|', r'$|p - 0.5|$')
        row = f"{name_tex} & {c['beta']:.4f}{sig(c['p_fisher'])} & ({c['se_fisher']:.4f}) "
        if res_year:
            # Find matching coefficient
            match = [cc for cc in res_year['coefficients'] if cc['name'] == c['name']]
            if match:
                cc = match[0]
                row += f"& {cc['beta']:.4f}{sig(cc['p_fisher'])} & ({cc['se_fisher']:.4f}) "
            else:
                row += r'& & '
        row += r'\\'
        lines.append(row)
        # Robust SE in brackets
        row_r = f" & [{c['se_robust']:.4f}] & "
        if res_year:
            match = [cc for cc in res_year['coefficients'] if cc['name'] == c['name']]
            if match:
                row_r += f"& [{match[0]['se_robust']:.4f}] & "
            else:
                row_r += '& & '
        row_r += r'\\'
        lines.append(row_r)

    # Year FE rows (if applicable)
    if res_year:
        for cc in res_year['coefficients']:
            if cc['name'].startswith('Year='):
                name_tex = cc['name']
                row = f"{name_tex} & & & {cc['beta']:.4f}{sig(cc['p_fisher'])} & ({cc['se_fisher']:.4f}) \\\\"
                lines.append(row)
                row_r = f" & & & [{cc['se_robust']:.4f}] & \\\\"
                lines.append(row_r)

    # Footer
    lines += [
        r'\midrule',
        f'$N$ & \\multicolumn{{2}}{{r}}{{{res_main["n"]:,}}} '
        + (f'& \\multicolumn{{2}}{{r}}{{{res_year["n"]:,}}} ' if res_year else '')
        + r'\\',
        f'Log-lik. & \\multicolumn{{2}}{{r}}{{{res_main["ll_full"]:.1f}}} '
        + (f'& \\multicolumn{{2}}{{r}}{{{res_year["ll_full"]:.1f}}} ' if res_year else '')
        + r'\\',
        f'LR $\\chi^2$ (covariates) & \\multicolumn{{2}}{{r}}{{{res_main["lr_covariates"]:.1f}}} '
        + (f'& \\multicolumn{{2}}{{r}}{{{res_year["lr_covariates"]:.1f}}} ' if res_year else '')
        + r'\\',
        f'Pseudo $R^2$ & \\multicolumn{{2}}{{r}}{{{res_main["pseudo_r2"]:.6f}}} '
        + (f'& \\multicolumn{{2}}{{r}}{{{res_year["pseudo_r2"]:.6f}}} ' if res_year else '')
        + r'\\',
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ]

    tex = '\n'.join(lines)
    tex_path = os.path.join(OUT_TABLES, 'kalshi_hierarchical.tex')
    with open(tex_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved: {tex_path}")

    # ─── Task 3: Category-level MLE ───
    log.info("")
    log.info("=" * 60)
    log.info("TASK 3: CATEGORY-LEVEL λ COMPARISON")
    log.info("=" * 60)

    df['category'] = df['title'].fillna('').apply(classify_category)
    cat_counts = df['category'].value_counts()
    log.info(f"Category counts:\n{cat_counts.to_string()}")

    # Polymarket reference values (from Table 14 in paper)
    pm_ref = {
        'Sports': {'lambda': 0.070, 'se': 0.042, 'n': 973},
        'Politics': {'lambda': 0.054, 'se': 0.157, 'n': 71},
        'Crypto': {'lambda': 0.253, 'se': 0.077, 'n': 305},
        'Tech': {'lambda': 0.268, 'se': 0.079, 'n': 414},
        'Other': {'lambda': 0.282, 'se': 0.051, 'n': 692},
    }

    cat_results = []
    for cat in ['Sports', 'Politics', 'Crypto', 'Tech', 'Other']:
        sub = df[df['category'] == cat]
        if len(sub) < 20:
            log.info(f"  {cat}: N={len(sub)}, skipping (< 20)")
            cat_results.append({'category': cat, 'n': len(sub), 'lambda': None})
            continue

        y_c = sub['resolved_yes'].values.astype(np.float64)
        p_c = np.clip(sub['p_open'].values.astype(np.float64), 1e-6, 1 - 1e-6)
        z_c = stats.norm.ppf(p_c)

        res_c = scalar_mle(z_c, y_c)
        pm = pm_ref.get(cat, {})
        delta = res_c['lambda'] - pm.get('lambda', 0) if pm.get('lambda') is not None else None

        sig_str = '***' if res_c['p_value'] < 0.001 else '**' if res_c['p_value'] < 0.01 else '*' if res_c['p_value'] < 0.05 else ''
        log.info(f"  {cat:<12} N={len(sub):>7,}  λ̂={res_c['lambda']:.3f}{sig_str}  "
                 f"SE={res_c['se']:.3f}  "
                 f"PM={pm.get('lambda', '?'):.3f}  Δ={delta:+.3f}" if delta is not None else
                 f"  {cat:<12} N={len(sub):>7,}  λ̂={res_c['lambda']:.3f}{sig_str}  SE={res_c['se']:.3f}")

        cat_results.append({
            'category': cat,
            'n_kalshi': len(sub),
            'lambda_kalshi': res_c['lambda'],
            'se_kalshi': res_c['se'],
            'p_kalshi': res_c['p_value'],
            'n_pm': pm.get('n'),
            'lambda_pm': pm.get('lambda'),
            'se_pm': pm.get('se'),
            'delta': delta,
        })

    # Category comparison LaTeX table
    cat_lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Cross-platform category-level Wang parameter comparison. '
        r'Each cell reports $\hat{\lambda}_{MLE}$ estimated separately by category. '
        r'$\Delta\lambda = \hat{\lambda}_{\text{Kalshi}} - \hat{\lambda}_{\text{Polymarket}}$; '
        r'positive values indicate higher risk loading on the less liquid platform.}',
        r'\label{tab:cross_platform_category}',
        r'\begin{tabular}{lrrrrrrr}',
        r'\toprule',
        r' & \multicolumn{3}{c}{Polymarket} & \multicolumn{3}{c}{Kalshi} & \\',
        r'\cmidrule(lr){2-4} \cmidrule(lr){5-7}',
        r'Category & $N$ & $\hat{\lambda}$ & SE & $N$ & $\hat{\lambda}$ & SE & $\Delta\lambda$ \\',
        r'\midrule',
    ]

    for cr in cat_results:
        cat = cr['category']
        if cr.get('lambda_kalshi') is None:
            continue
        sig_k = sig(cr['p_kalshi'])
        delta_str = f"{cr['delta']:+.3f}" if cr['delta'] is not None else '---'
        cat_lines.append(
            f"{cat} & {cr['n_pm']:,} & {cr['lambda_pm']:.3f} & {cr['se_pm']:.3f} "
            f"& {cr['n_kalshi']:,} & {cr['lambda_kalshi']:.3f}{sig_k} & {cr['se_kalshi']:.3f} "
            f"& {delta_str} \\\\"
        )

    # Pooled row
    pooled_k = scalar_mle(z, y)
    cat_lines.append(r'\midrule')
    sig_pool = sig(pooled_k['p_value'])
    cat_lines.append(
        f"\\textit{{Pooled}} & 2,460 & 0.176 & 0.027 "
        f"& {len(df):,} & {pooled_k['lambda']:.3f}{sig_pool} & {pooled_k['se']:.3f} "
        f"& {pooled_k['lambda'] - 0.176:+.3f} \\\\"
    )

    cat_lines += [
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ]

    cat_tex = '\n'.join(cat_lines)
    cat_path = os.path.join(OUT_TABLES, 'cross_platform_category.tex')
    with open(cat_path, 'w') as f:
        f.write(cat_tex)
    log.info(f"Saved: {cat_path}")

    # Save JSON
    all_results = {
        'hierarchical_main': res_main,
        'hierarchical_year_fe': res_year,
        'category_comparison': cat_results,
        'pooled_kalshi': pooled_k,
    }
    json_path = os.path.join(OUT_TABLES, 'kalshi_hierarchical_results.json')
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    log.info(f"Saved: {json_path}")

    log.info("")
    log.info("Done.")
    return all_results


if __name__ == '__main__':
    main()
