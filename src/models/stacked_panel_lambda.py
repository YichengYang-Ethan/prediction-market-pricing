#!/usr/bin/env python3
"""
Stacked Panel Time-Varying λ with Natural Cubic Spline
=======================================================
Estimates: Pr(y_i = 1 | p_it) = Φ(z_it - f(τ_it) - X_iβ)
where f(τ) is a natural cubic spline with K interior knots.

Author: Yicheng Yang (UIUC)
"""

import os, sys, json, logging, time, warnings
import numpy as np
import pandas as pd
from scipy import stats, optimize, interpolate
from datetime import datetime

np.random.seed(42)
warnings.filterwarnings('ignore')

# ─── Paths ──────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(ROOT, 'data')
OUT_TABLES = os.path.join(ROOT, 'outputs/tables')
OUT_FIGS = os.path.join(ROOT, 'outputs/figures')
OUT_LOGS = os.path.join(ROOT, 'outputs/logs')

for d in [OUT_TABLES, OUT_FIGS, OUT_LOGS]:
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUT_LOGS, 'stacked_panel_lambda.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# NATURAL CUBIC SPLINE BASIS
# ═══════════════════════════════════════════════════════════════════

def poly_basis(tau, degree=2):
    """Polynomial basis for f(τ) with f(0)=0 constraint.

    f(τ) = γ₁τ + γ₂τ² + ... + γ_d τ^d
    No intercept → f(0)=0 by construction.

    Returns: B (N x degree), names
    """
    tau = np.asarray(tau, dtype=np.float64)
    cols = []
    names = []
    for d in range(1, degree + 1):
        cols.append(tau ** d)
        names.append(f'τ^{d}' if d > 1 else 'τ')
    return np.column_stack(cols), names


def horizon_fe_basis(tau):
    """Horizon fixed effects basis with f(τ=0.05)=0 constraint.

    One dummy per horizon except the reference (τ=0.05).
    Returns: B (N x (H-1)), names
    """
    tau = np.asarray(tau, dtype=np.float64)
    unique_taus = np.sort(np.unique(tau))
    ref = unique_taus[0]  # reference: τ=0.05
    cols = []
    names = []
    for t in unique_taus[1:]:
        cols.append((tau == t).astype(np.float64))
        names.append(f'τ={t:.2f}')
    return np.column_stack(cols), names


# ═══════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════

def load_and_stack(price_lo=0.05, price_hi=0.95, subsample_ids=None):
    """Load data and create stacked panel.

    Args:
        subsample_ids: if provided, restrict to these contract IDs only.
    """
    df = pd.read_parquet(os.path.join(DATA_DIR, 'combined_analysis_dataset.parquet'))
    log.info(f"Loaded: {len(df)} contracts")

    # Merge spread
    markets = pd.read_parquet(os.path.join(DATA_DIR, 'combined_markets.parquet'))
    if 'spread' in markets.columns:
        df = df.merge(markets[['id', 'spread']], on='id', how='left')

    # Subsample filter
    if subsample_ids is not None:
        df = df[df['id'].isin(subsample_ids)].copy()
        log.info(f"Subsample filter: {len(df)} contracts retained")

    # Define horizons from existing columns
    horizons = [
        ('p_open', 0.05),
        ('p_10pct', 0.10),
        ('p_20pct', 0.20),
        ('p_30pct', 0.30),
        ('p_40pct', 0.40),
        ('p_mid', 0.50),
        ('p_60pct', 0.60),
        ('p_70pct', 0.70),
        ('p_80pct', 0.80),
    ]

    # Stack
    rows = []
    for idx, contract in df.iterrows():
        y = contract['resolved_yes']
        vol = contract.get('volume', np.nan)
        dur = contract.get('duration_hours', np.nan)
        spread = contract.get('spread', 0) or 0
        cid = contract['id']

        if pd.isna(vol) or pd.isna(dur):
            continue

        for col, tau in horizons:
            p = contract.get(col)
            if p is None or pd.isna(p):
                continue
            if p <= price_lo or p >= price_hi:
                continue
            rows.append({
                'contract_id': cid,
                'resolved_yes': int(y),
                'p_it': float(p),
                'tau': tau,
                'volume': float(vol),
                'duration_hours': float(dur),
                'spread': float(spread),
            })

    panel = pd.DataFrame(rows)
    n_contracts = panel['contract_id'].nunique()
    log.info(f"Stacked panel: {len(panel)} obs from {n_contracts} contracts, "
             f"mean obs/contract = {len(panel)/n_contracts:.1f}")
    log.info(f"Tau distribution: {panel.groupby('tau').size().to_dict()}")

    return panel, df


# ═══════════════════════════════════════════════════════════════════
# MODEL
# ═══════════════════════════════════════════════════════════════════

def build_model_matrices(panel, basis_type='poly2', include_covariates=True):
    """Build z, design matrix [B(τ), X], y for the stacked panel.

    basis_type: 'poly1', 'poly2', 'poly3', 'horizon_fe'
    Returns: z_it, W (combined design), y, col_names, contract_ids, n_basis
    """
    p = np.clip(panel['p_it'].values, 1e-6, 1 - 1e-6)
    z = stats.norm.ppf(p)
    y = panel['resolved_yes'].values.astype(np.float64)
    tau = panel['tau'].values

    # Build f(τ) basis
    if basis_type.startswith('poly'):
        degree = int(basis_type.replace('poly', ''))
        B, basis_names = poly_basis(tau, degree=degree)
    elif basis_type == 'horizon_fe':
        B, basis_names = horizon_fe_basis(tau)
    else:
        raise ValueError(f"Unknown basis_type: {basis_type}")

    n_basis = B.shape[1]

    if include_covariates:
        log_vol = np.log1p(panel['volume'].values)
        log_dur = np.log1p(panel['duration_hours'].values)
        extremity = np.abs(panel['p_it'].values - 0.5)
        spread = panel['spread'].values

        X = np.column_stack([np.ones(len(panel)), log_vol, log_dur, extremity, spread])
        cov_names = ['Constant (β₀)', 'ln(Volume)', 'ln(Duration)', '|p - 0.5|', 'Spread']

        W = np.column_stack([B, X])
        col_names = basis_names + cov_names
    else:
        W = np.column_stack([B, np.ones(len(panel))])
        col_names = basis_names + ['Constant (β₀)']

    contract_ids = panel['contract_id'].values

    return z, W, y, col_names, contract_ids, n_basis


# Chunk size < 32768 to avoid numpy 1.26.3 + Accelerate BLAS bug
_CHUNK = 30000


def neg_log_likelihood_panel(theta, z, W, y):
    """NLL with analytic gradient for the panel model.

    Model: Pr(y=1) = Φ(z - W @ θ)
    Chunked to avoid numpy/BLAS bug at N >= 32768.
    """
    N = len(y)
    p = len(theta)
    total_ll = 0.0
    total_grad = np.zeros(p)

    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        z_c, W_c, y_c = z[start:end], W[start:end], y[start:end]

        eta_c = z_c - W_c @ theta
        Phi_c = np.clip(stats.norm.cdf(eta_c), 1e-12, 1 - 1e-12)
        phi_c = stats.norm.pdf(eta_c)

        total_ll += np.sum(y_c * np.log(Phi_c) + (1 - y_c) * np.log(1 - Phi_c))

        score_c = y_c * phi_c / Phi_c - (1 - y_c) * phi_c / (1 - Phi_c)
        total_grad += score_c @ W_c

    return -total_ll, total_grad


def nll_only_panel(theta, z, W, y):
    N = len(y)
    total_nll = 0.0
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        eta_c = z[start:end] - W[start:end] @ theta
        Phi_c = np.clip(stats.norm.cdf(eta_c), 1e-12, 1 - 1e-12)
        total_nll += -np.sum(y[start:end] * np.log(Phi_c) + (1 - y[start:end]) * np.log(1 - Phi_c))
    return total_nll


def clustered_se(theta, z, W, y, contract_ids):
    """Liang-Zeger clustered sandwich SE.

    V_cluster = H⁻¹ (Σ_i s̄_i s̄_i') H⁻¹
    with finite-sample correction.

    Uses analytic Fisher information for H (guaranteed PSD).
    """
    p_dim = len(theta)
    N = len(y)

    # Analytic Fisher information (guaranteed PSD), chunked for BLAS bug
    H = np.zeros((p_dim, p_dim))
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        eta_c = z[start:end] - W[start:end] @ theta
        Phi_c = np.clip(stats.norm.cdf(eta_c), 1e-12, 1 - 1e-12)
        phi_c = stats.norm.pdf(eta_c)
        w_c = phi_c**2 / (Phi_c * (1 - Phi_c))
        Ww_c = W[start:end] * np.sqrt(w_c)[:, None]
        H += Ww_c.T @ Ww_c

    eigvals = np.linalg.eigvalsh(H)
    log.info(f"Fisher info: min eigenvalue = {eigvals.min():.4f}, "
             f"max = {eigvals.max():.4f}, cond = {eigvals.max()/max(eigvals.min(), 1e-15):.1f}")

    if eigvals.min() <= 0:
        log.warning(f"Fisher info not PD (min eig = {eigvals.min():.6f}), adding ridge")
        H += np.eye(p_dim) * max(-eigvals.min() + 1e-6, 1e-6)

    H_inv = np.linalg.inv(H)

    # Per-observation scores (chunked for BLAS bug)
    S = np.zeros((N, p_dim))
    for start in range(0, N, _CHUNK):
        end = min(start + _CHUNK, N)
        eta_c = z[start:end] - W[start:end] @ theta
        Phi_c = np.clip(stats.norm.cdf(eta_c), 1e-12, 1 - 1e-12)
        phi_c = stats.norm.pdf(eta_c)
        score_c = y[start:end] * phi_c / Phi_c - (1 - y[start:end]) * phi_c / (1 - Phi_c)
        S[start:end] = -score_c[:, None] * W[start:end]

    # Cluster-sum scores
    unique_ids = np.unique(contract_ids)
    G = len(unique_ids)
    meat = np.zeros((p_dim, p_dim))
    id_to_idx = {}
    for i, uid in enumerate(contract_ids):
        if uid not in id_to_idx:
            id_to_idx[uid] = []
        id_to_idx[uid].append(i)

    for uid, indices in id_to_idx.items():
        s_bar = S[indices].sum(axis=0)  # cluster-level score
        meat += np.outer(s_bar, s_bar)

    # Finite-sample correction: (G / (G-1)) * (N / (N-1))
    correction = (G / (G - 1)) * (N / (N - 1)) if G > 1 else 1.0

    V_cluster = correction * H_inv @ meat @ H_inv
    se_cluster = np.sqrt(np.diag(V_cluster))

    # Also compute Fisher SE for comparison
    se_fisher = np.sqrt(np.diag(H_inv))

    log.info(f"Clustered SE: G={G} clusters, N={N} obs, correction={correction:.4f}")

    return se_fisher, se_cluster, V_cluster, H_inv


def estimate_panel(panel, basis_type='poly2', include_covariates=True, label=""):
    """Full estimation: MLE + clustered SE."""
    log.info(f"[{label}] Building matrices (basis={basis_type}, covariates={include_covariates})")

    z, W, y, col_names, contract_ids, n_basis = build_model_matrices(
        panel, basis_type=basis_type, include_covariates=include_covariates
    )
    p_dim = W.shape[1]
    N = len(y)

    log.info(f"[{label}] N={N}, dim={p_dim}, cols={col_names}")

    # Collinearity diagnostic
    cond = np.linalg.cond(W.T @ W)
    log.info(f"[{label}] Condition number of W'W: {cond:.1f}")
    if cond > 30:
        log.warning(f"[{label}] HIGH CONDITION NUMBER: {cond:.1f} > 30 — potential collinearity")

    # Initial values
    theta0 = np.zeros(p_dim)
    # Set intercept initial value
    for i, name in enumerate(col_names):
        if 'Constant' in name:
            theta0[i] = 0.166

    # Gradient check at initial point
    nll_test, grad_anal = neg_log_likelihood_panel(theta0, z, W, y)
    grad_num = optimize.approx_fprime(theta0, lambda t: nll_only_panel(t, z, W, y), 1e-7)
    grad_err = np.max(np.abs(grad_anal - grad_num) / (1 + np.abs(grad_num)))
    log.info(f"[{label}] Gradient check: max relative error = {grad_err:.2e}")
    if grad_err > 1e-3:
        log.error(f"[{label}] GRADIENT CHECK FAILED: error = {grad_err:.2e}")

    # Optimize with BFGS (more robust than L-BFGS-B for this problem)
    t0 = time.time()
    result = optimize.minimize(
        neg_log_likelihood_panel, theta0, args=(z, W, y),
        method='BFGS', jac=True,
        options={'maxiter': 10000, 'gtol': 1e-8}
    )
    elapsed = time.time() - t0

    if not result.success:
        log.warning(f"[{label}] BFGS: {result.message}, trying Newton-CG...")
        result2 = optimize.minimize(
            neg_log_likelihood_panel, theta0, args=(z, W, y),
            method='Newton-CG', jac=True,
            options={'maxiter': 10000, 'xtol': 1e-10}
        )
        if result2.fun < result.fun or result2.success:
            result = result2
            log.info(f"[{label}] Newton-CG succeeded")
        else:
            log.warning(f"[{label}] Newton-CG also failed: {result2.message}")

    theta_hat = result.x
    ll_full = -result.fun
    log.info(f"[{label}] Converged in {elapsed:.2f}s, LL={ll_full:.2f}")

    # Clustered SE
    se_fisher, se_cluster, V_cluster, H_inv = clustered_se(theta_hat, z, W, y, contract_ids)

    # Null model: θ = 0
    ll_null = -nll_only_panel(np.zeros(p_dim), z, W, y)
    lr_stat = 2 * (ll_full - ll_null)
    p_value = 1 - stats.chi2.cdf(max(lr_stat, 0), df=p_dim)

    # Build results
    results = {
        'label': label,
        'n_obs': N,
        'n_contracts': len(np.unique(contract_ids)),
        'n_params': p_dim,
        'n_basis': n_basis,
        'basis_type': basis_type,
        'll_full': float(ll_full),
        'll_null': float(ll_null),
        'lr_stat': float(lr_stat),
        'p_value': float(p_value),
        'aic': float(2 * p_dim - 2 * ll_full),
        'bic': float(p_dim * np.log(N) - 2 * ll_full),
        'condition_number': float(cond),
        'coefficients': [],
    }

    log.info(f"[{label}] Results:")
    log.info(f"  {'Parameter':<20} {'θ̂':>8} {'SE(F)':>8} {'SE(C)':>8} {'z(C)':>8} {'p(C)':>8}")
    for i, name in enumerate(col_names):
        z_c = theta_hat[i] / se_cluster[i] if se_cluster[i] > 0 else np.nan
        p_c = float(2 * (1 - stats.norm.cdf(abs(z_c))))
        sig = '***' if p_c < 0.001 else '**' if p_c < 0.01 else '*' if p_c < 0.05 else ''
        results['coefficients'].append({
            'name': name,
            'theta': float(theta_hat[i]),
            'se_fisher': float(se_fisher[i]),
            'se_cluster': float(se_cluster[i]),
            'z_cluster': float(z_c),
            'p_cluster': float(p_c),
        })
        log.info(f"  {name:<20} {theta_hat[i]:>8.4f} {se_fisher[i]:>8.4f} "
                 f"{se_cluster[i]:>8.4f} {z_c:>8.2f} {p_c:>8.4f} {sig}")

    log.info(f"  LL={ll_full:.2f}, AIC={results['aic']:.1f}, BIC={results['bic']:.1f}")

    return results, theta_hat, col_names, V_cluster


# ═══════════════════════════════════════════════════════════════════
# f(τ) CURVE EVALUATION
# ═══════════════════════════════════════════════════════════════════

def evaluate_f_tau(theta, col_names, n_basis, V_cluster, tau_grid=None,
                   basis_type='poly2'):
    """Evaluate f(τ) + β₀ on a fine grid with CI.

    Returns: tau_grid, f_total (f(τ) + β₀), se_total, ci_lo, ci_hi
    """
    if tau_grid is None:
        tau_grid = np.linspace(0.01, 0.85, 200)

    # Build basis on grid
    if basis_type.startswith('poly'):
        degree = int(basis_type.replace('poly', ''))
        B_grid, _ = poly_basis(tau_grid, degree=degree)
    elif basis_type == 'horizon_fe':
        # For horizon FE, evaluate at the discrete points only
        unique_taus = np.array([0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80])
        tau_grid = np.concatenate([[0.05], unique_taus])
        B_grid = np.zeros((len(tau_grid), len(unique_taus)))
        for j, t in enumerate(unique_taus):
            B_grid[:, j] = (tau_grid == t).astype(np.float64)
    else:
        raise ValueError(f"Unknown basis_type: {basis_type}")

    # f(τ) = B(τ) @ γ
    gamma = theta[:n_basis]
    f_tau = B_grid @ gamma

    # Find β₀ index
    beta0_idx = None
    for i, name in enumerate(col_names):
        if 'Constant' in name:
            beta0_idx = i
            break

    beta0 = theta[beta0_idx] if beta0_idx is not None else 0

    # Total λ(τ) = f(τ) + β₀
    f_total = f_tau + beta0

    # SE via delta method
    se_total = np.zeros(len(tau_grid))
    for i in range(len(tau_grid)):
        g = np.zeros(len(theta))
        g[:n_basis] = B_grid[i]
        if beta0_idx is not None:
            g[beta0_idx] = 1.0
        se_total[i] = np.sqrt(max(g @ V_cluster @ g, 0))

    ci_lo = f_total - 1.96 * se_total
    ci_hi = f_total + 1.96 * se_total

    return tau_grid, f_total, se_total, ci_lo, ci_hi


# ═══════════════════════════════════════════════════════════════════
# DERIVED QUANTITIES
# ═══════════════════════════════════════════════════════════════════

def compute_derived(tau_grid, f_total, ci_lo):
    """Compute half-life and significance horizon."""
    # λ at τ=0.05 (opening)
    idx_open = np.argmin(np.abs(tau_grid - 0.05))
    lambda_open = f_total[idx_open]

    # Half-life: τ* where f_total = lambda_open / 2
    half_target = lambda_open / 2
    if lambda_open > 0:
        crossings = np.where(np.diff(np.sign(f_total - half_target)))[0]
        if len(crossings) > 0:
            idx = crossings[0]
            # Linear interpolation
            t1, t2 = tau_grid[idx], tau_grid[idx + 1]
            f1, f2 = f_total[idx], f_total[idx + 1]
            half_life = t1 + (half_target - f1) / (f2 - f1) * (t2 - t1)
        else:
            half_life = np.nan
    else:
        half_life = np.nan

    # Significance horizon: τ** where lower CI crosses zero
    sig_crossings = np.where(np.diff(np.sign(ci_lo)))[0]
    if len(sig_crossings) > 0:
        idx = sig_crossings[0]
        t1, t2 = tau_grid[idx], tau_grid[idx + 1]
        f1, f2 = ci_lo[idx], ci_lo[idx + 1]
        sig_horizon = t1 + (0 - f1) / (f2 - f1) * (t2 - t1) if (f2 - f1) != 0 else t1
    else:
        # CI never crosses zero — either always significant or never
        if ci_lo[0] > 0:
            sig_horizon = tau_grid[-1]  # always significant in range
        else:
            sig_horizon = 0.0

    # Total decay
    idx_end = np.argmin(np.abs(tau_grid - 0.80))
    total_decay = f_total[idx_end] - f_total[idx_open]

    derived = {
        'lambda_open': float(lambda_open),
        'half_life': float(half_life),
        'significance_horizon': float(sig_horizon),
        'total_decay': float(total_decay),
        'lambda_at_50pct': float(f_total[np.argmin(np.abs(tau_grid - 0.50))]),
        'lambda_at_80pct': float(f_total[np.argmin(np.abs(tau_grid - 0.80))]),
    }

    log.info(f"Derived quantities:")
    log.info(f"  λ(opening) = {derived['lambda_open']:.4f}")
    log.info(f"  Half-life = {derived['half_life']:.2f} of lifetime")
    log.info(f"  Significance horizon = {derived['significance_horizon']:.2f} of lifetime")
    log.info(f"  Total decay (0.05→0.80) = {derived['total_decay']:.4f}")
    log.info(f"  λ(50%) = {derived['lambda_at_50pct']:.4f}")
    log.info(f"  λ(80%) = {derived['lambda_at_80pct']:.4f}")

    return derived


# ═══════════════════════════════════════════════════════════════════
# FIGURES
# ═══════════════════════════════════════════════════════════════════

def plot_f_tau_curve(tau_grid, f_total, ci_lo, ci_hi, derived,
                     old_estimates=None, out_path=None):
    """Publication-quality f(τ) curve with CI band."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))

    # Spline curve
    ax.plot(tau_grid, f_total, 'b-', linewidth=2, label='Spline estimate $f(\\tau) + \\beta_0$')
    ax.fill_between(tau_grid, ci_lo, ci_hi, alpha=0.2, color='blue', label='95% CI (clustered)')

    # Reference line
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

    # Old point estimates (from Table 6)
    if old_estimates is not None:
        taus_old = [e['tau'] for e in old_estimates]
        lams_old = [e['lambda'] for e in old_estimates]
        ses_old = [e['se'] for e in old_estimates]
        ax.errorbar(taus_old, lams_old, yerr=[1.96 * s for s in ses_old],
                     fmt='ro', markersize=6, capsize=4, linewidth=1.5,
                     label='Separate MLEs (Table 6)', zorder=5)

    # Derived markers
    if not np.isnan(derived['half_life']):
        hl = derived['half_life']
        hl_val = derived['lambda_open'] / 2
        ax.plot(hl, hl_val, 'g^', markersize=10, zorder=6)
        ax.annotate(f'Half-life = {hl:.0%}',
                    (hl, hl_val), textcoords='offset points',
                    xytext=(15, 10), fontsize=9, color='green')

    ax.set_xlabel('Fraction of contract lifetime ($\\tau$)', fontsize=12)
    ax.set_ylabel('$\\hat{\\lambda}(\\tau) = f(\\tau) + \\beta_0$', fontsize=12)
    ax.set_title('Time-Varying Risk Premium: Stacked Panel Spline Estimate', fontsize=13)
    ax.legend(fontsize=10, loc='upper right')
    ax.set_xlim(0, 0.85)

    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        log.info(f"Saved figure: {out_path}")
    plt.close()


# ═══════════════════════════════════════════════════════════════════
# LATEX TABLES
# ═══════════════════════════════════════════════════════════════════

def sig_stars(p):
    if p < 0.001: return '$^{***}$'
    if p < 0.01: return '$^{**}$'
    if p < 0.05: return '$^{*}$'
    return ''


def format_parameter_table(results_nocov, results_cov, out_path):
    """LaTeX table with both specifications."""
    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Stacked panel time-varying $\hat{\lambda}$ with natural cubic spline. '
        r'Model: $\Pr(y_i = 1 \mid p_{it}) = \Phi(\Phi^{-1}(p_{it}) - f(\tau_{it}) - X_i\beta)$. '
        r'Contract-clustered standard errors (Liang--Zeger).}',
        r'\label{tab:stacked_panel}',
        r'\begin{tabular}{lrrrr}',
        r'\toprule',
        r' & \multicolumn{2}{c}{(1) $f(\tau)$ only} & \multicolumn{2}{c}{(2) $f(\tau) + X_i\beta$} \\',
        r'\cmidrule(lr){2-3} \cmidrule(lr){4-5}',
        r'Parameter & Estimate & Cluster SE & Estimate & Cluster SE \\',
        r'\midrule',
        r'\textit{Spline parameters} & & & & \\',
    ]

    # Spline params (don't report individually, just note)
    n_spline_nocov = results_nocov['n_basis']
    n_spline_cov = results_cov['n_basis']
    lines.append(f'$f(\\tau)$ basis coefficients & \\multicolumn{{2}}{{c}}{{({n_spline_nocov} params)}} '
                 f'& \\multicolumn{{2}}{{c}}{{({n_spline_cov} params)}} \\\\')
    lines.append(r'\midrule')
    lines.append(r'\textit{Covariates} & & & & \\')

    # Find covariate params in model (2)
    for c in results_cov['coefficients']:
        if c['name'].startswith('f(τ)'):
            continue
        sig = sig_stars(c['p_cluster'])
        # Find corresponding in model (1)
        if 'Constant' in c['name']:
            c1 = [x for x in results_nocov['coefficients'] if 'Constant' in x['name']]
            if c1:
                c1 = c1[0]
                sig1 = sig_stars(c1['p_cluster'])
                lines.append(f'Constant ($\\beta_0$) & {c1["theta"]:.4f}{sig1} & ({c1["se_cluster"]:.4f}) '
                             f'& {c["theta"]:.4f}{sig} & ({c["se_cluster"]:.4f}) \\\\')
            else:
                lines.append(f'Constant ($\\beta_0$) & --- & --- '
                             f'& {c["theta"]:.4f}{sig} & ({c["se_cluster"]:.4f}) \\\\')
        else:
            name = c['name']
            if name == '|p - 0.5|':
                name = '$|p - 0.5|$ (extremity)'
            lines.append(f'{name} & --- & --- '
                         f'& {c["theta"]:.4f}{sig} & ({c["se_cluster"]:.4f}) \\\\')

    lines.extend([
        r'\midrule',
        f'Log-likelihood & \\multicolumn{{2}}{{r}}{{{results_nocov["ll_full"]:.1f}}} '
        f'& \\multicolumn{{2}}{{r}}{{{results_cov["ll_full"]:.1f}}} \\\\',
        f'AIC & \\multicolumn{{2}}{{r}}{{{results_nocov["aic"]:.1f}}} '
        f'& \\multicolumn{{2}}{{r}}{{{results_cov["aic"]:.1f}}} \\\\',
        f'Contracts (clusters) & \\multicolumn{{2}}{{r}}{{{results_nocov["n_contracts"]:,}}} '
        f'& \\multicolumn{{2}}{{r}}{{{results_cov["n_contracts"]:,}}} \\\\',
        f'Total observations & \\multicolumn{{2}}{{r}}{{{results_nocov["n_obs"]:,}}} '
        f'& \\multicolumn{{2}}{{r}}{{{results_cov["n_obs"]:,}}} \\\\',
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ])

    tex = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved parameter table: {out_path}")
    return tex


def format_derived_table(derived, out_path):
    """LaTeX table for derived quantities."""
    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Derived quantities from the stacked panel spline model.}',
        r'\label{tab:derived}',
        r'\begin{tabular}{lr}',
        r'\toprule',
        r'Quantity & Estimate \\',
        r'\midrule',
        f'$\\hat{{\\lambda}}$ at opening ($\\tau = 0.05$) & {derived["lambda_open"]:.4f} \\\\',
        f'$\\hat{{\\lambda}}$ at mid-life ($\\tau = 0.50$) & {derived["lambda_at_50pct"]:.4f} \\\\',
        f'$\\hat{{\\lambda}}$ at $\\tau = 0.80$ & {derived["lambda_at_80pct"]:.4f} \\\\',
        f'Half-life ($\\tau^*$) & {derived["half_life"]:.0%} of lifetime \\\\',
        f'Significance horizon ($\\tau^{{**}}$) & {derived["significance_horizon"]:.0%} of lifetime \\\\',
        f'Total decay ($\\tau: 0.05 \\to 0.80$) & {derived["total_decay"]:.4f} \\\\',
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ]
    tex = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved derived table: {out_path}")
    return tex


# ═══════════════════════════════════════════════════════════════════
# ROBUSTNESS
# ═══════════════════════════════════════════════════════════════════

def robustness_basis_comparison(panel):
    """Compare polynomial degrees and horizon FE."""
    log.info("=" * 60)
    log.info("ROBUSTNESS: Basis Comparison")
    log.info("=" * 60)

    results = []
    for bt in ['poly1', 'poly2', 'poly3', 'horizon_fe']:
        r, _, _, _ = estimate_panel(panel, basis_type=bt, include_covariates=False,
                                    label=f"Basis={bt}")
        results.append({'basis': bt, 'aic': r['aic'], 'bic': r['bic'],
                        'll': r['ll_full'], 'n_params': r['n_params'],
                        'cond': r['condition_number']})
        log.info(f"  {bt}: AIC={r['aic']:.1f}, BIC={r['bic']:.1f}, "
                 f"cond={r['condition_number']:.1f}, p={r['n_params']}")

    return results


def robustness_duration_quintile(panel, basis_type='poly2'):
    """Leave-one-duration-quintile-out: check f(τ) stability."""
    log.info("=" * 60)
    log.info("ROBUSTNESS: Leave-one-duration-quintile-out")
    log.info("=" * 60)

    panel = panel.copy()
    panel['dur_quintile'] = pd.qcut(panel['duration_hours'], 5, labels=False, duplicates='drop')
    results = []

    for q in sorted(panel['dur_quintile'].unique()):
        sub = panel[panel['dur_quintile'] != q].copy()
        dur_range = panel[panel['dur_quintile'] == q]['duration_hours']
        log.info(f"  Dropping quintile {q} (duration {dur_range.min():.0f}-{dur_range.max():.0f}h, "
                 f"N dropped = {len(panel) - len(sub)})")

        r, theta, col_names, V = estimate_panel(sub, basis_type=basis_type,
                                                 include_covariates=False,
                                                 label=f"Drop Q{q}")
        n_basis = r['n_basis']
        tau_grid, f_total, _, _, _ = evaluate_f_tau(theta, col_names, n_basis, V,
                                                     basis_type=basis_type)

        # Check monotonicity
        diffs = np.diff(f_total)
        monotone = np.all(diffs <= 0.01)
        results.append({
            'dropped_quintile': int(q),
            'n_obs': r['n_obs'],
            'monotone': bool(monotone),
            'lambda_open': float(f_total[np.argmin(np.abs(tau_grid - 0.05))]),
            'lambda_50pct': float(f_total[np.argmin(np.abs(tau_grid - 0.50))]),
        })
        log.info(f"    Monotone: {monotone}, λ(open)={results[-1]['lambda_open']:.4f}, "
                 f"λ(50%)={results[-1]['lambda_50pct']:.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════
# 12-DAY SUBSAMPLE
# ═══════════════════════════════════════════════════════════════════

def run_12day_subsample():
    """Re-run stacked panel on the 12-day subsample (expanded_analysis_dataset IDs).

    Outputs files with _12day suffix for comparison with full-sample results.
    """
    log.info("")
    log.info("=" * 70)
    log.info("12-DAY SUBSAMPLE STACKED PANEL")
    log.info("=" * 70)

    # Get 12-day IDs
    exp = pd.read_parquet(os.path.join(DATA_DIR, 'expanded_analysis_dataset.parquet'))
    exp_ids = set(exp['id'])
    log.info(f"12-day subsample IDs: {len(exp_ids)}")

    # Load and stack with subsample filter
    panel, _ = load_and_stack(subsample_ids=exp_ids)

    # ── Model (1): f(τ) only ──
    log.info("")
    log.info("=" * 60)
    log.info("12-DAY: Model (1) — f(τ) = γ₁τ + γ₂τ² (no covariates)")
    log.info("=" * 60)

    results_nocov, theta_nocov, names_nocov, V_nocov = estimate_panel(
        panel, basis_type='poly2', include_covariates=False, label="12-day Model (1)"
    )
    n_basis_nocov = results_nocov['n_basis']

    tau_grid, f_total_nocov, se_nocov, ci_lo_nocov, ci_hi_nocov = evaluate_f_tau(
        theta_nocov, names_nocov, n_basis_nocov, V_nocov, basis_type='poly2'
    )

    derived_nocov = compute_derived(tau_grid, f_total_nocov, ci_lo_nocov)

    # ── Model (2): f(τ) + X_iβ ──
    log.info("")
    log.info("=" * 60)
    log.info("12-DAY: Model (2) — f(τ) + X_iβ (with covariates)")
    log.info("=" * 60)

    results_cov, theta_cov, names_cov, V_cov = estimate_panel(
        panel, basis_type='poly2', include_covariates=True, label="12-day Model (2)"
    )
    n_basis_cov = results_cov['n_basis']

    tau_grid_cov, f_total_cov, se_cov, ci_lo_cov, ci_hi_cov = evaluate_f_tau(
        theta_cov, names_cov, n_basis_cov, V_cov, basis_type='poly2'
    )

    derived_cov = compute_derived(tau_grid_cov, f_total_cov, ci_lo_cov)

    # ── Old Table 6 estimates (from 12-day sample) ──
    old_estimates = [
        {'tau': 0.05, 'lambda': 0.176, 'se': 0.027},
        {'tau': 0.10, 'lambda': 0.158, 'se': 0.027},
        {'tau': 0.20, 'lambda': 0.110, 'se': 0.028},
        {'tau': 0.30, 'lambda': 0.082, 'se': 0.029},
        {'tau': 0.40, 'lambda': 0.080, 'se': 0.030},
        {'tau': 0.50, 'lambda': 0.050, 'se': 0.030},
        {'tau': 0.60, 'lambda': 0.052, 'se': 0.031},
        {'tau': 0.70, 'lambda': 0.040, 'se': 0.032},
        {'tau': 0.80, 'lambda': 0.031, 'se': 0.033},
    ]

    # ── Figures ──
    plot_f_tau_curve(
        tau_grid, f_total_nocov, ci_lo_nocov, ci_hi_nocov,
        derived_nocov, old_estimates=old_estimates,
        out_path=os.path.join(OUT_FIGS, 'fig_stacked_panel_f_tau_12day.png')
    )

    plot_f_tau_curve(
        tau_grid_cov, f_total_cov, ci_lo_cov, ci_hi_cov,
        derived_cov, old_estimates=old_estimates,
        out_path=os.path.join(OUT_FIGS, 'fig_stacked_panel_f_tau_covariates_12day.png')
    )

    # ── LaTeX tables ──
    format_parameter_table(
        results_nocov, results_cov,
        os.path.join(OUT_TABLES, 'stacked_panel_params_12day.tex')
    )

    format_derived_table(
        derived_nocov,
        os.path.join(OUT_TABLES, 'stacked_panel_derived_12day.tex')
    )

    # ── JSON ──
    all_12day = {
        'model_nocov': results_nocov,
        'model_cov': results_cov,
        'derived_nocov': derived_nocov,
        'derived_cov': derived_cov,
    }
    json_path = os.path.join(OUT_TABLES, 'stacked_panel_results_12day.json')
    with open(json_path, 'w') as f:
        json.dump(all_12day, f, indent=2, default=str)
    log.info(f"Saved 12-day JSON: {json_path}")

    # ── Summary ──
    log.info("")
    log.info("=" * 60)
    log.info("12-DAY SUBSAMPLE SUMMARY")
    log.info("=" * 60)
    log.info(f"N contracts: {results_nocov['n_contracts']}")
    log.info(f"N stacked obs: {results_nocov['n_obs']}")
    log.info(f"Model (1) — λ(open) = {derived_nocov['lambda_open']:.4f}, "
             f"half-life = {derived_nocov['half_life']:.4f}")
    log.info(f"Model (2) — λ(open) = {derived_cov['lambda_open']:.4f}, "
             f"half-life = {derived_cov['half_life']:.4f}")

    return all_12day


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info("STACKED PANEL TIME-VARYING λ")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # Load and stack
    panel, df_raw = load_and_stack()

    # ── Collinearity diagnostic ──
    log.info("")
    log.info("=" * 60)
    log.info("COLLINEARITY DIAGNOSTIC")
    log.info("=" * 60)

    z_diag = stats.norm.ppf(np.clip(panel['p_it'].values, 1e-6, 1 - 1e-6))
    B_poly2, _ = poly_basis(panel['tau'].values, degree=2)
    ZB = np.column_stack([z_diag, B_poly2])
    cond_zb = np.linalg.cond(ZB)
    log.info(f"Condition number of [z_it, τ, τ²]: {cond_zb:.1f}")
    corrs = [np.corrcoef(z_diag, B_poly2[:, j])[0, 1] for j in range(B_poly2.shape[1])]
    log.info(f"Correlation z_it vs [τ, τ²]: {[f'{c:.3f}' for c in corrs]}")
    if cond_zb > 30:
        log.warning(f"Condition number {cond_zb:.1f} > 30, but low correlation — proceeding")

    # ── Model (1): f(τ) only, quadratic ──
    log.info("")
    log.info("=" * 60)
    log.info("MODEL (1): f(τ) = γ₁τ + γ₂τ² (no covariates)")
    log.info("=" * 60)

    results_nocov, theta_nocov, names_nocov, V_nocov = estimate_panel(
        panel, basis_type='poly2', include_covariates=False, label="Model (1)"
    )
    n_basis_nocov = results_nocov['n_basis']

    tau_grid, f_total_nocov, se_nocov, ci_lo_nocov, ci_hi_nocov = evaluate_f_tau(
        theta_nocov, names_nocov, n_basis_nocov, V_nocov, basis_type='poly2'
    )

    # Check monotonicity
    diffs = np.diff(f_total_nocov)
    monotone = np.all(diffs <= 0.005)
    log.info(f"f(τ)+β₀ monotone decreasing: {monotone}")

    derived_nocov = compute_derived(tau_grid, f_total_nocov, ci_lo_nocov)

    # ── Model (2): f(τ) + X_iβ ──
    log.info("")
    log.info("=" * 60)
    log.info("MODEL (2): f(τ) + X_iβ (with covariates)")
    log.info("=" * 60)

    results_cov, theta_cov, names_cov, V_cov = estimate_panel(
        panel, basis_type='poly2', include_covariates=True, label="Model (2)"
    )
    n_basis_cov = results_cov['n_basis']

    tau_grid_cov, f_total_cov, se_cov, ci_lo_cov, ci_hi_cov = evaluate_f_tau(
        theta_cov, names_cov, n_basis_cov, V_cov, basis_type='poly2'
    )

    derived_cov = compute_derived(tau_grid_cov, f_total_cov, ci_lo_cov)

    # Check signs
    for c in results_cov['coefficients']:
        if c['name'] == 'ln(Volume)' and c['theta'] > 0:
            log.error(f"SIGN CHECK FAIL: ln(Volume) = {c['theta']:.4f} (expected negative)")
        if c['name'] == 'ln(Duration)' and c['theta'] < 0:
            log.error(f"SIGN CHECK FAIL: ln(Duration) = {c['theta']:.4f} (expected positive)")
        if c['name'] == '|p - 0.5|' and c['theta'] > 0:
            log.error(f"SIGN CHECK FAIL: |p - 0.5| = {c['theta']:.4f} (expected negative)")

    # ── Model (3): Horizon FE (validation) ──
    log.info("")
    log.info("=" * 60)
    log.info("MODEL (3): Horizon Fixed Effects (validation)")
    log.info("=" * 60)

    results_fe, theta_fe, names_fe, V_fe = estimate_panel(
        panel, basis_type='horizon_fe', include_covariates=False, label="Horizon FE"
    )
    n_basis_fe = results_fe['n_basis']

    tau_grid_fe, f_total_fe, se_fe, ci_lo_fe, ci_hi_fe = evaluate_f_tau(
        theta_fe, names_fe, n_basis_fe, V_fe, basis_type='horizon_fe'
    )

    # ── Old Table 6 estimates ──
    old_estimates = [
        {'tau': 0.05, 'lambda': 0.176, 'se': 0.027},
        {'tau': 0.10, 'lambda': 0.158, 'se': 0.027},
        {'tau': 0.20, 'lambda': 0.110, 'se': 0.028},
        {'tau': 0.30, 'lambda': 0.082, 'se': 0.029},
        {'tau': 0.40, 'lambda': 0.080, 'se': 0.030},
        {'tau': 0.50, 'lambda': 0.050, 'se': 0.030},
        {'tau': 0.60, 'lambda': 0.052, 'se': 0.031},
        {'tau': 0.70, 'lambda': 0.040, 'se': 0.032},
        {'tau': 0.80, 'lambda': 0.031, 'se': 0.033},
    ]

    # ── Figures ──
    log.info("")
    log.info("=" * 60)
    log.info("GENERATING FIGURES AND TABLES")
    log.info("=" * 60)

    plot_f_tau_curve(
        tau_grid, f_total_nocov, ci_lo_nocov, ci_hi_nocov,
        derived_nocov, old_estimates=old_estimates,
        out_path=os.path.join(OUT_FIGS, 'fig_stacked_panel_f_tau.png')
    )

    plot_f_tau_curve(
        tau_grid_cov, f_total_cov, ci_lo_cov, ci_hi_cov,
        derived_cov, old_estimates=old_estimates,
        out_path=os.path.join(OUT_FIGS, 'fig_stacked_panel_f_tau_covariates.png')
    )

    # LaTeX tables
    tex_params = format_parameter_table(
        results_nocov, results_cov,
        os.path.join(OUT_TABLES, 'stacked_panel_params.tex')
    )
    print("\n" + tex_params + "\n")

    tex_derived = format_derived_table(
        derived_nocov,
        os.path.join(OUT_TABLES, 'stacked_panel_derived.tex')
    )
    print("\n" + tex_derived + "\n")

    # ── Robustness: basis comparison ──
    log.info("")
    rob_basis = robustness_basis_comparison(panel)

    # ── Robustness: duration quintile ──
    log.info("")
    rob_dur = robustness_duration_quintile(panel, basis_type='poly2')

    # ── 12-day subsample ──
    results_12day = run_12day_subsample()

    # ── Save all results ──
    all_results = {
        'model_nocov': results_nocov,
        'model_cov': results_cov,
        'model_horizon_fe': results_fe,
        'derived_nocov': derived_nocov,
        'derived_cov': derived_cov,
        'robustness_basis': rob_basis,
        'robustness_duration': rob_dur,
        'collinearity_condition': float(cond_zb),
        'subsample_12day': results_12day,
    }
    json_path = os.path.join(OUT_TABLES, 'stacked_panel_results.json')
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    log.info(f"Saved JSON: {json_path}")

    # ── Final summary ──
    log.info("")
    log.info("=" * 70)
    log.info("SUMMARY")
    log.info("=" * 70)
    log.info(f"Model (1) — f(τ) = γ₁τ + γ₂τ² (no covariates):")
    log.info(f"  λ(open) = {derived_nocov['lambda_open']:.4f}")
    log.info(f"  Half-life = {derived_nocov['half_life']:.2f}")
    log.info(f"  Significance horizon = {derived_nocov['significance_horizon']:.2f}")
    log.info(f"  Monotone: {monotone}")
    log.info(f"Model (2) — f(τ) + Xβ:")
    log.info(f"  λ(open) = {derived_cov['lambda_open']:.4f}")
    log.info(f"  Half-life = {derived_cov['half_life']:.2f}")
    log.info(f"Model (3) — Horizon FE:")
    for c in results_fe['coefficients']:
        if 'Constant' in c['name']:
            log.info(f"  β₀ (=λ at τ=0.05) = {c['theta']:.4f}")
        elif c['name'].startswith('τ='):
            log.info(f"  {c['name']}: Δλ = {c['theta']:.4f} (cluster SE = {c['se_cluster']:.4f})")
    log.info(f"12-day subsample:")
    d12_nocov = results_12day.get('derived_nocov', {})
    d12_cov = results_12day.get('derived_cov', {})
    log.info(f"  Model (1) — λ(open) = {d12_nocov.get('lambda_open', float('nan')):.4f}, "
             f"half-life = {d12_nocov.get('half_life', float('nan')):.4f}")
    log.info(f"  Model (2) — λ(open) = {d12_cov.get('lambda_open', float('nan')):.4f}, "
             f"half-life = {d12_cov.get('half_life', float('nan')):.4f}")
    log.info("Done.")


if __name__ == '__main__':
    main()
