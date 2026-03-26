#!/usr/bin/env python3
"""
EIV Empirical Analysis
======================
Computes rolling realized event volatility across all contracts with
sufficient price history, reports summary statistics, and tests for
volatility clustering (ARCH effects).

Author: Yicheng Yang (UIUC)
"""

import os, json, logging, warnings
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime

np.random.seed(42)
warnings.filterwarnings('ignore')

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
        logging.FileHandler(os.path.join(OUT_LOGS, 'eiv_empirical.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# ─── Classification helper ──────────────────────────────────────
def classify_category(q):
    q = q.lower()
    for kw in ['nba', 'nfl', 'nhl', 'mlb', 'ufc', 'soccer', 'tennis',
               'boxing', 'cricket', 'f1 ', 'grand prix', 'league', 'championship',
               'match', 'game ', 'score', ' vs ', 'series', 'tournament',
               'premier league', 'la liga', 'bundesliga']:
        if kw in q: return 'Sports'
    for kw in ['trump', 'biden', 'election', 'president', 'congress', 'senate',
               'governor', 'vote', 'democrat', 'republican', 'political', 'cabinet',
               'supreme court', 'impeach', 'executive order']:
        if kw in q: return 'Politics'
    for kw in ['bitcoin', 'ethereum', 'crypto', 'solana', 'token', 'defi',
               'nft', 'blockchain', 'btc', 'eth']:
        if kw in q: return 'Crypto'
    for kw in ['ai ', 'gpt', 'openai', 'spacex', 'nasa', 'apple', 'google',
               'tesla', 'meta ', 'microsoft', 'amazon']:
        if kw in q: return 'Tech'
    return 'Other'


def main():
    log.info("=" * 70)
    log.info("EIV EMPIRICAL ANALYSIS")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # Load data
    with open(os.path.join(DATA_DIR, 'combined_histories.json')) as f:
        histories = json.load(f)

    df = pd.read_parquet(os.path.join(DATA_DIR, 'combined_analysis_dataset.parquet'))
    markets = pd.read_parquet(os.path.join(DATA_DIR, 'combined_markets.parquet'))
    question_map = dict(zip(markets['id'].astype(str), markets['question'].fillna('')))
    volume_map = dict(zip(df['id'].astype(str), df['volume']))

    log.info(f"Histories: {len(histories)}, Analysis contracts: {len(df)}")

    # ── Compute realized EIV for each contract ──
    MIN_OBS = 20
    WINDOW = 10  # rolling window for realized vol

    results = []
    arch_rejections = 0
    arch_tested = 0

    for cid_str, entry in histories.items():
        hist = entry.get('history', [])
        if len(hist) < MIN_OBS:
            continue

        prices = np.array([float(h['p']) for h in hist])

        # Clip to avoid log-odds infinities
        prices = np.clip(prices, 0.01, 0.99)

        # Log-odds transformation
        logodds = np.log(prices / (1 - prices))

        # Increments
        dlogodds = np.diff(logodds)
        if len(dlogodds) < WINDOW:
            continue

        # Rolling realized volatility (std of log-odds increments)
        # Use rolling window of WINDOW observations
        rolling_std = pd.Series(dlogodds).rolling(window=WINDOW, min_periods=WINDOW).std()
        rolling_std = rolling_std.dropna().values

        if len(rolling_std) < 5:
            continue

        # Annualize: hourly data → multiply by sqrt(24*365) ≈ sqrt(8760)
        ann_factor = np.sqrt(8760)
        sigma_realized = float(np.median(rolling_std)) * ann_factor
        sigma_mean = float(np.mean(rolling_std)) * ann_factor
        sigma_iqr = float(np.percentile(rolling_std, 75) - np.percentile(rolling_std, 25)) * ann_factor

        # ARCH(1) LM test on squared increments
        sq = dlogodds**2
        if len(sq) > 10:
            arch_tested += 1
            # Regress sq[t] on sq[t-1]
            y = sq[1:]
            x = sq[:-1]
            x_with_const = np.column_stack([np.ones(len(x)), x])
            try:
                beta = np.linalg.lstsq(x_with_const, y, rcond=None)[0]
                resid = y - x_with_const @ beta
                ss_res = np.sum(resid**2)
                ss_tot = np.sum((y - np.mean(y))**2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                lm_stat = len(y) * r2
                lm_p = 1 - stats.chi2.cdf(lm_stat, df=1)
                arch_reject = lm_p < 0.05
                if arch_reject:
                    arch_rejections += 1
            except:
                arch_reject = False
                lm_p = 1.0
        else:
            arch_reject = False
            lm_p = 1.0

        vol = volume_map.get(cid_str, 0)
        question = question_map.get(cid_str, '')
        cat = classify_category(question)

        results.append({
            'id': cid_str,
            'n_obs': len(hist),
            'sigma_realized': sigma_realized,
            'sigma_mean': sigma_mean,
            'sigma_iqr': sigma_iqr,
            'arch_reject': arch_reject,
            'arch_lm_p': float(lm_p),
            'volume': float(vol),
            'category': cat,
        })

    rdf = pd.DataFrame(results)
    log.info(f"Computed EIV for {len(rdf)} contracts (≥{MIN_OBS} hourly obs)")

    # ── Summary statistics ──
    log.info("")
    log.info("=" * 60)
    log.info("SUMMARY STATISTICS: Realized Event Volatility")
    log.info("=" * 60)

    log.info(f"Overall (N={len(rdf)}):")
    log.info(f"  Median σ_realized = {rdf['sigma_realized'].median():.2f}")
    log.info(f"  IQR = [{rdf['sigma_realized'].quantile(0.25):.2f}, {rdf['sigma_realized'].quantile(0.75):.2f}]")
    log.info(f"  Mean = {rdf['sigma_realized'].mean():.2f}, SD = {rdf['sigma_realized'].std():.2f}")

    log.info(f"\nBy Category:")
    cat_stats = rdf.groupby('category')['sigma_realized'].agg(['count', 'median', 'mean',
        lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)])
    cat_stats.columns = ['N', 'Median', 'Mean', 'Q25', 'Q75']
    for cat, row in cat_stats.iterrows():
        log.info(f"  {cat:<10} N={row['N']:>5.0f}  median={row['Median']:.2f}  "
                 f"IQR=[{row['Q25']:.2f}, {row['Q75']:.2f}]")

    # Volume tiers
    rdf['vol_tier'] = pd.cut(rdf['volume'],
        bins=[-1, 500, 2000, 10000, np.inf],
        labels=['Low (<$500)', 'Med ($500-2K)', 'High ($2K-10K)', 'Very high (>$10K)'])

    log.info(f"\nBy Volume Tier:")
    vol_stats = rdf.groupby('vol_tier', observed=True)['sigma_realized'].agg(
        ['count', 'median', 'mean'])
    for tier, row in vol_stats.iterrows():
        log.info(f"  {tier:<20} N={row['count']:>5.0f}  median={row['median']:.2f}  mean={row['mean']:.2f}")

    # ARCH test
    rejection_rate = arch_rejections / arch_tested if arch_tested > 0 else 0
    log.info(f"\nARCH(1) LM Test:")
    log.info(f"  Tested: {arch_tested} contracts")
    log.info(f"  Rejections (p < 0.05): {arch_rejections} ({rejection_rate:.1%})")

    # ── Scatter plot: σ_realized vs ln(volume) ──
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Panel (a): Scatter
    ax = axes[0]
    mask = rdf['volume'] > 0
    rdf_plot = rdf[mask].copy()
    rdf_plot['ln_vol'] = np.log(rdf_plot['volume'])

    # Winsorize sigma for plotting
    p99 = rdf_plot['sigma_realized'].quantile(0.99)
    rdf_plot['sigma_plot'] = rdf_plot['sigma_realized'].clip(upper=p99)

    colors = {'Sports': '#1f77b4', 'Politics': '#d62728', 'Crypto': '#ff7f0e',
              'Tech': '#2ca02c', 'Other': '#7f7f7f'}

    for cat in ['Sports', 'Politics', 'Crypto', 'Tech', 'Other']:
        sub = rdf_plot[rdf_plot['category'] == cat]
        if len(sub) > 0:
            ax.scatter(sub['ln_vol'], sub['sigma_plot'], alpha=0.3, s=8,
                       color=colors[cat], label=f'{cat} (N={len(sub)})')

    # Regression line
    from numpy.polynomial import polynomial as P
    x_all = rdf_plot['ln_vol'].values
    y_all = rdf_plot['sigma_plot'].values
    coef = np.polyfit(x_all, y_all, 1)
    x_line = np.linspace(x_all.min(), x_all.max(), 100)
    ax.plot(x_line, np.polyval(coef, x_line), 'k--', linewidth=1.5,
            label=f'OLS: slope={coef[0]:.2f}')

    # Correlation
    rho, p_rho = stats.spearmanr(x_all, y_all)
    ax.set_xlabel('$\\ln(\\text{Volume})$', fontsize=11)
    ax.set_ylabel('Realized event volatility $\\hat{\\sigma}_{\\text{realized}}$', fontsize=11)
    ax.set_title(f'(a) Realized EIV vs Volume (Spearman $\\rho={rho:.3f}$, $p={p_rho:.1e}$)',
                 fontsize=11)
    ax.legend(fontsize=8, loc='upper right')

    # Panel (b): Distribution by category (box plot)
    ax = axes[1]
    cat_order = ['Sports', 'Politics', 'Crypto', 'Tech', 'Other']
    data_for_box = [rdf[rdf['category'] == c]['sigma_realized'].clip(upper=p99).values
                    for c in cat_order]
    bp = ax.boxplot(data_for_box, labels=cat_order, patch_artist=True, showfliers=False)
    for patch, cat in zip(bp['boxes'], cat_order):
        patch.set_facecolor(colors[cat])
        patch.set_alpha(0.6)
    ax.set_ylabel('Realized event volatility $\\hat{\\sigma}_{\\text{realized}}$', fontsize=11)
    ax.set_title('(b) Distribution by Category', fontsize=11)

    plt.tight_layout()
    fig_path = os.path.join(OUT_FIGS, 'fig_eiv_distribution.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    log.info(f"Saved figure: {fig_path}")

    # ── LaTeX summary table ──
    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Cross-contract distribution of realized event volatility '
        r'$\hat{\sigma}_{\text{realized}}$, computed as the median rolling standard deviation '
        r'of hourly log-odds increments (annualized, window $= 10$). '
        r'Contracts with $\geq 20$ hourly observations.}',
        r'\label{tab:eiv_summary}',
        r'\begin{tabular}{lrrrrr}',
        r'\toprule',
        r'Group & $N$ & Median & IQR & Mean & ARCH(1) rej.\ rate \\',
        r'\midrule',
    ]

    # Overall
    overall_rej = f'{rejection_rate:.0%}'
    lines.append(
        f'All contracts & {len(rdf):,} & {rdf["sigma_realized"].median():.2f} '
        f'& [{rdf["sigma_realized"].quantile(0.25):.2f}, {rdf["sigma_realized"].quantile(0.75):.2f}] '
        f'& {rdf["sigma_realized"].mean():.2f} & {overall_rej} \\\\'
    )
    lines.append(r'\midrule')
    lines.append(r'\textit{By category} & & & & & \\')

    for cat in cat_order:
        sub = rdf[rdf['category'] == cat]
        if len(sub) > 0:
            arch_sub = sub['arch_reject'].sum() / len(sub) if len(sub) > 0 else 0
            lines.append(
                f'{cat} & {len(sub):,} & {sub["sigma_realized"].median():.2f} '
                f'& [{sub["sigma_realized"].quantile(0.25):.2f}, {sub["sigma_realized"].quantile(0.75):.2f}] '
                f'& {sub["sigma_realized"].mean():.2f} & {arch_sub:.0%} \\\\'
            )

    lines.append(r'\midrule')
    lines.append(r'\textit{By volume tier} & & & & & \\')
    for tier in ['Low (<$500)', 'Med ($500-2K)', 'High ($2K-10K)', 'Very high (>$10K)']:
        sub = rdf[rdf['vol_tier'] == tier]
        if len(sub) > 0:
            arch_sub = sub['arch_reject'].sum() / len(sub) if len(sub) > 0 else 0
            tier_tex = tier.replace('$', r'\$').replace('>',r'$>$').replace('<',r'$<$')
            lines.append(
                f'{tier_tex} & {len(sub):,} & {sub["sigma_realized"].median():.2f} '
                f'& [{sub["sigma_realized"].quantile(0.25):.2f}, {sub["sigma_realized"].quantile(0.75):.2f}] '
                f'& {sub["sigma_realized"].mean():.2f} & {arch_sub:.0%} \\\\'
            )

    lines.extend([r'\bottomrule', r'\end{tabular}', r'\end{table}'])
    tex = '\n'.join(lines)
    tex_path = os.path.join(OUT_TABLES, 'eiv_summary_stats.tex')
    with open(tex_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved: {tex_path}")

    # ── Save JSON ──
    output = {
        'n_contracts': len(rdf),
        'min_obs': MIN_OBS,
        'window': WINDOW,
        'overall': {
            'median': float(rdf['sigma_realized'].median()),
            'q25': float(rdf['sigma_realized'].quantile(0.25)),
            'q75': float(rdf['sigma_realized'].quantile(0.75)),
            'mean': float(rdf['sigma_realized'].mean()),
        },
        'arch_test': {
            'tested': arch_tested,
            'rejections': arch_rejections,
            'rejection_rate': float(rejection_rate),
        },
        'spearman_vol': {'rho': float(rho), 'p': float(p_rho)},
        'ols_slope': float(coef[0]),
    }
    json_path = os.path.join(OUT_TABLES, 'eiv_empirical.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)
    log.info(f"Saved: {json_path}")

    log.info("\nDone.")
    return output


if __name__ == '__main__':
    main()
