#!/usr/bin/env python3
"""
Hazard Rate Term Structure — Empirical Analysis
================================================
Searches for multi-maturity contract families (same event, different
expiry dates) and, if found, bootstraps hazard rates and fits
Nelson-Siegel.

Author: Yicheng Yang (UIUC)
"""

import os, json, re, logging, warnings
import numpy as np
import pandas as pd
from scipy import stats, optimize
from collections import defaultdict
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
        logging.FileHandler(os.path.join(OUT_LOGS, 'hazard_rate_empirical.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

LAMBDA_HAT = 0.166  # pooled Wang parameter estimate


def find_maturity_families():
    """Find same-event contracts with different maturities."""
    markets = pd.read_parquet(os.path.join(DATA_DIR, 'combined_markets.parquet'))
    with open(os.path.join(DATA_DIR, 'combined_histories.json')) as f:
        hist_data = json.load(f)
    hist_ids = set(hist_data.keys())

    date_pattern = re.compile(
        r'(by|before|end of|through)\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)',
        re.IGNORECASE
    )

    stems = defaultdict(list)
    for _, row in markets.iterrows():
        q = str(row.get('question', ''))
        m = date_pattern.search(q)
        if m:
            stem = q[:m.start()].strip().rstrip('?').rstrip()
            if len(stem) > 15:
                mid = str(row['id'])
                if mid in hist_ids:
                    # Parse closed_time for ordering
                    ct = pd.to_datetime(row.get('closed_time', ''), errors='coerce', utc=True)
                    stems[stem].append({
                        'id': mid,
                        'question': q,
                        'closed_time': ct,
                        'volume': row.get('volume', 0),
                        'resolved_yes': row.get('resolved_yes', None),
                    })

    families = {k: sorted(v, key=lambda x: x['closed_time'] if pd.notna(x['closed_time']) else pd.Timestamp.max)
                for k, v in stems.items() if len(v) >= 3}

    log.info(f"Found {len(families)} maturity families with ≥3 contracts")
    return families, hist_data


def get_opening_price(hist_data, contract_id):
    """Get opening price from history (first 5% midpoint)."""
    hist = hist_data.get(contract_id, {}).get('history', [])
    if not hist:
        return None
    prices = [float(h['p']) for h in hist]
    idx = min(int(0.05 * len(prices)), len(prices) - 1)
    return prices[idx]


def bootstrap_hazard_rates(family, hist_data):
    """Bootstrap hazard rates from a maturity strip.

    Returns list of (days_to_maturity, p_market, p_physical, hazard_rate).
    """
    # Get opening prices and compute days-to-maturity
    strip = []
    ref_time = family[0]['closed_time']

    for c in family:
        p_mkt = get_opening_price(hist_data, c['id'])
        if p_mkt is None or p_mkt <= 0.01 or p_mkt >= 0.99:
            continue
        ct = c['closed_time']
        if pd.isna(ct) or pd.isna(ref_time):
            continue
        days = (ct - ref_time).total_seconds() / 86400
        if days < 0:
            days = 0

        # Strip risk premium
        z = stats.norm.ppf(p_mkt)
        p_phys = stats.norm.cdf(z - LAMBDA_HAT)
        p_phys = np.clip(p_phys, 0.001, 0.999)

        strip.append({
            'id': c['id'],
            'question': c['question'],
            'days': float(days),
            'p_mkt': float(p_mkt),
            'p_phys': float(p_phys),
            'resolved': c['resolved_yes'],
        })

    if len(strip) < 3:
        return None

    # Sort by days
    strip.sort(key=lambda x: x['days'])

    # Bootstrap hazard rates between adjacent maturities
    for i in range(len(strip)):
        if i == 0:
            strip[i]['hazard'] = None
        else:
            dt = strip[i]['days'] - strip[i-1]['days']
            if dt <= 0:
                strip[i]['hazard'] = None
                continue
            surv_prev = 1 - strip[i-1]['p_phys']
            surv_curr = 1 - strip[i]['p_phys']
            if surv_prev <= 0 or surv_curr <= 0:
                strip[i]['hazard'] = None
                continue
            # h = -[ln(1-p_i) - ln(1-p_{i-1})] / (T_i - T_{i-1})
            h = -(np.log(surv_curr) - np.log(surv_prev)) / dt
            strip[i]['hazard'] = float(h)

    return strip


def nelson_siegel(T, beta0, beta1, beta2, tau):
    """Nelson-Siegel term structure."""
    x = T / max(tau, 0.01)
    factor1 = (1 - np.exp(-x)) / x if x > 1e-6 else 1.0
    factor2 = factor1 - np.exp(-x) if x > 1e-6 else 0.0
    return beta0 + beta1 * factor1 + beta2 * factor2


def fit_nelson_siegel(days, hazards):
    """Fit Nelson-Siegel to hazard rates."""
    valid = [(d, h) for d, h in zip(days, hazards) if h is not None and d > 0]
    if len(valid) < 3:
        return None
    T = np.array([v[0] for v in valid])
    h = np.array([v[1] for v in valid])
    try:
        popt, _ = optimize.curve_fit(nelson_siegel, T, h,
                                      p0=[h.mean(), 0, 0, T.mean()],
                                      maxfev=5000)
        return {'beta0': float(popt[0]), 'beta1': float(popt[1]),
                'beta2': float(popt[2]), 'tau': float(popt[3])}
    except:
        return None


def main():
    log.info("=" * 70)
    log.info("HAZARD RATE TERM STRUCTURE — EMPIRICAL")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    families, hist_data = find_maturity_families()

    if len(families) < 3:
        log.info("INSUFFICIENT DATA: < 3 maturity families found")
        log.info("Recommendation: mark Section 7.2 as theoretical extension")
        return {'status': 'insufficient_data', 'n_families': len(families)}

    # Process top families
    log.info("")
    log.info("=" * 60)
    log.info("HAZARD RATE BOOTSTRAP")
    log.info("=" * 60)

    all_strips = {}
    ns_fits = {}

    for stem, contracts in sorted(families.items(), key=lambda x: -len(x[1])):
        log.info(f"\nFamily: \"{stem[:60]}\" ({len(contracts)} maturities)")
        strip = bootstrap_hazard_rates(contracts, hist_data)
        if strip is None:
            log.info("  Skipped (insufficient valid prices)")
            continue

        all_strips[stem] = strip
        for s in strip:
            h_str = f"{s['hazard']:.6f}" if s['hazard'] is not None else "---"
            log.info(f"  days={s['days']:>6.0f}  p_mkt={s['p_mkt']:.3f}  "
                     f"p_phys={s['p_phys']:.3f}  h={h_str}  q={s['question'][:50]}")

        # Fit Nelson-Siegel
        days = [s['days'] for s in strip]
        hazards = [s['hazard'] for s in strip]
        ns = fit_nelson_siegel(days, hazards)
        if ns:
            ns_fits[stem] = ns
            log.info(f"  Nelson-Siegel: β0={ns['beta0']:.4f}, β1={ns['beta1']:.4f}, "
                     f"β2={ns['beta2']:.4f}, τ={ns['tau']:.1f}")

    log.info(f"\nTotal families processed: {len(all_strips)}")
    log.info(f"Nelson-Siegel fits: {len(ns_fits)}")

    # ── Plot term structures for top 4 families ──
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    top_stems = list(all_strips.keys())[:4]
    if top_stems:
        n_plots = min(len(top_stems), 4)
        fig, axes = plt.subplots(1, n_plots, figsize=(4 * n_plots, 4))
        if n_plots == 1:
            axes = [axes]

        for ax, stem in zip(axes, top_stems):
            strip = all_strips[stem]
            days = [s['days'] for s in strip if s['hazard'] is not None]
            hazards = [s['hazard'] for s in strip if s['hazard'] is not None]

            ax.bar(range(len(days)), hazards, color='steelblue', alpha=0.7)
            ax.set_xticks(range(len(days)))
            ax.set_xticklabels([f'{d:.0f}d' for d in days], fontsize=8, rotation=45)
            ax.set_ylabel('Hazard rate $\\hat{h}$ (per day)', fontsize=9)
            ax.set_title(stem[:35] + '...', fontsize=9)
            ax.axhline(y=0, color='black', linewidth=0.5)

            # Nelson-Siegel overlay
            if stem in ns_fits:
                ns = ns_fits[stem]
                d_fine = np.linspace(min(days), max(days), 100)
                h_fine = [nelson_siegel(d, ns['beta0'], ns['beta1'], ns['beta2'], ns['tau'])
                          for d in d_fine]
                ax.plot(np.interp(d_fine, days, range(len(days))), h_fine,
                        'r-', linewidth=1.5, label='Nelson-Siegel')
                ax.legend(fontsize=7)

        plt.suptitle('Event Hazard Rate Term Structures', fontsize=12, y=1.02)
        plt.tight_layout()
        fig_path = os.path.join(OUT_FIGS, 'fig_hazard_rate_term_structure.png')
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        plt.close()
        log.info(f"Saved figure: {fig_path}")

    # ── LaTeX table ──
    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{Hazard rate term structure: bootstrapped event intensities from '
        r'multi-maturity prediction market strips. Physical probabilities obtained by '
        r'stripping the Wang risk premium ($\hat{\lambda} = 0.166$).}',
        r'\label{tab:hazard_rate}',
        r'\begin{tabular}{llrrrr}',
        r'\toprule',
        r'Event & Maturity (days) & $p^{\text{mkt}}$ & $\hat{p}^*$ & $\hat{h}$ (per day) & $N$ maturities \\',
        r'\midrule',
    ]

    for stem in list(all_strips.keys())[:5]:
        strip = all_strips[stem]
        short_stem = stem[:40].replace('&', r'\&')
        n_mat = len(strip)
        first = True
        for s in strip:
            if s['hazard'] is not None:
                h_str = f'{s["hazard"]:.5f}'
            else:
                h_str = '---'
            label = short_stem if first else ''
            n_str = str(n_mat) if first else ''
            lines.append(
                f'{label} & {s["days"]:.0f} & {s["p_mkt"]:.3f} & {s["p_phys"]:.3f} & {h_str} & {n_str} \\\\'
            )
            first = False
        lines.append(r'\midrule')

    # Remove last midrule, add bottomrule
    if lines[-1] == r'\midrule':
        lines[-1] = r'\bottomrule'
    lines.extend([r'\end{tabular}', r'\end{table}'])

    tex = '\n'.join(lines)
    tex_path = os.path.join(OUT_TABLES, 'hazard_rate_term_structure.tex')
    with open(tex_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved: {tex_path}")

    # ── JSON ──
    output = {
        'status': 'success',
        'n_families': len(all_strips),
        'n_ns_fits': len(ns_fits),
        'families': {k: v for k, v in list(all_strips.items())[:10]},
        'nelson_siegel_fits': ns_fits,
    }
    json_path = os.path.join(OUT_TABLES, 'hazard_rate_empirical.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    log.info(f"Saved: {json_path}")

    log.info("\nDone.")
    return output


if __name__ == '__main__':
    main()
