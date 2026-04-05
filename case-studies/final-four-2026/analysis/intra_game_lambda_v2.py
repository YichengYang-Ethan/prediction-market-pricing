#!/usr/bin/env python3
"""
Intra-Game Wang λ Analysis v2 — CORRECTED
Filters to competitive range (0.15 < p_model < 0.85) to avoid probit tail artifact.
"""
import json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from scipy.stats import norm, ttest_1samp, ttest_ind, linregress
import warnings
warnings.filterwarnings('ignore')

DATA = os.path.expanduser("~/final_four_2026/data")
OUT  = os.path.expanduser("~/final_four_2026/analysis")
CT = timezone(timedelta(hours=-5))

def parse_ts(ts_str):
    ts_str = str(ts_str)
    if '+' in ts_str or ts_str.endswith('Z'):
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    else:
        return datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)

def to_ct_naive(dt):
    return dt.astimezone(CT).replace(tzinfo=None)

def wang_lambda(p_market, p_model):
    p_m = np.clip(p_market, 0.005, 0.995)
    p_b = np.clip(p_model, 0.005, 0.995)
    return norm.ppf(p_m) - norm.ppf(p_b)

# ══════════════════════════════════════════════════════════════
# Load ESPN + market data (reuse v1 pipeline)
# ══════════════════════════════════════════════════════════════
with open(f"{DATA}/espn_401856598.json") as f:
    espn = json.load(f)

plays = espn['plays']
wp_dict = {w['playId']: w['homeWinPercentage'] for w in espn['winprobability']}

# Build timeline
timeline_rows = []
for p in plays:
    period = p['period']['number']
    clock_str = p['clock']['displayValue']
    parts = clock_str.split(':')
    clock_sec = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
    if period == 1:
        sec_elapsed = 20 * 60 - clock_sec
    else:
        sec_elapsed = 20 * 60 + (20 * 60 - clock_sec)
    sec_remaining = max(2400 - sec_elapsed, 0)
    wallclock = parse_ts(p['wallclock'])
    margin = p['awayScore'] - p['homeScore']  # ILL - UCONN
    espn_uconn_wp = wp_dict.get(p['id'], None)
    espn_ill_wp = 1.0 - espn_uconn_wp if espn_uconn_wp is not None else None

    timeline_rows.append({
        'wallclock': wallclock, 'sec_elapsed': sec_elapsed,
        'sec_remaining': sec_remaining, 'ill_score': p['awayScore'],
        'uconn_score': p['homeScore'], 'margin': margin,
        'espn_ill_wp': espn_ill_wp,
    })

timeline = pd.DataFrame(timeline_rows).sort_values('wallclock').reset_index(drop=True)

def ncaa_win_prob(margin, seconds_remaining):
    if seconds_remaining <= 0:
        return 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0)
    sigma = 11.0 * np.sqrt(seconds_remaining / 2400.0)
    return norm.cdf(margin / sigma)

timeline['p_model'] = timeline.apply(lambda r: ncaa_win_prob(r['margin'], r['sec_remaining']), axis=1)
TIPOFF = timeline['wallclock'].iloc[0]
GAME_END = timeline['wallclock'].iloc[-1]

# Load market data
def load_jsonl(path):
    records = []
    with open(path) as f:
        for line in f:
            try: records.append(json.loads(line.strip()))
            except: pass
    return records

kalshi_raw = load_jsonl(f"{DATA}/kalshi_20260404.jsonl")
pm_raw = load_jsonl(f"{DATA}/polymarket_20260404.jsonl")

g1k = [r for r in kalshi_raw if r.get('ticker') == 'KXNCAAMBGAME-26APR04ILLCONN-ILL' and 'error' not in r]
g1k_df = pd.DataFrame(g1k)
g1k_df['dt'] = g1k_df['timestamp'].apply(parse_ts)
g1k_df['p_kalshi'] = (g1k_df['yes_bid'].astype(float) + g1k_df['yes_ask'].astype(float)) / 2
g1k_df = g1k_df.sort_values('dt').reset_index(drop=True)

g1p = [r for r in pm_raw if r.get('market') == 'game1_ill_uconn_ml' and 'error' not in r]
g1p_df = pd.DataFrame(g1p)
g1p_df['dt'] = g1p_df['timestamp'].apply(parse_ts)
g1p_df['p_pm'] = g1p_df['price_illinois_fighting_illini'].astype(float)
g1p_df = g1p_df.sort_values('dt').reset_index(drop=True)

def lookup_game_state(market_dt):
    mask = timeline['wallclock'] <= market_dt
    if not mask.any():
        return None
    idx = mask.values.nonzero()[0][-1]
    row = timeline.iloc[idx]
    return {
        'ill_score': row['ill_score'], 'uconn_score': row['uconn_score'],
        'margin': row['margin'], 'sec_remaining': row['sec_remaining'],
        'sec_elapsed': row['sec_elapsed'], 'p_model': row['p_model'],
        'espn_ill_wp': row['espn_ill_wp'],
    }

# Merge Kalshi
kalshi_merged = []
for _, row in g1k_df.iterrows():
    if row['dt'] < TIPOFF or row['dt'] > GAME_END:
        continue
    state = lookup_game_state(row['dt'])
    if state is None:
        continue
    game_sec = (row['dt'] - TIPOFF).total_seconds()
    kalshi_merged.append({
        'dt_ct': to_ct_naive(row['dt']), 'game_seconds': game_sec,
        'game_minutes': game_sec / 60.0, 'p_kalshi': row['p_kalshi'], **state,
    })
kalshi_m = pd.DataFrame(kalshi_merged)
kalshi_m['lambda_k'] = wang_lambda(kalshi_m['p_kalshi'].values, kalshi_m['p_model'].values)
kalshi_m['lambda_k_espn'] = wang_lambda(kalshi_m['p_kalshi'].values, kalshi_m['espn_ill_wp'].values)

# Merge Polymarket
pm_merged = []
for _, row in g1p_df.iterrows():
    if row['dt'] < TIPOFF or row['dt'] > GAME_END:
        continue
    state = lookup_game_state(row['dt'])
    if state is None:
        continue
    game_sec = (row['dt'] - TIPOFF).total_seconds()
    pm_merged.append({
        'dt_ct': to_ct_naive(row['dt']), 'game_seconds': game_sec,
        'game_minutes': game_sec / 60.0, 'p_pm': row['p_pm'], **state,
    })
pm_m = pd.DataFrame(pm_merged)
pm_m['lambda_p'] = wang_lambda(pm_m['p_pm'].values, pm_m['p_model'].values)
pm_m['lambda_p_espn'] = wang_lambda(pm_m['p_pm'].values, pm_m['espn_ill_wp'].values)

print("=" * 70)
print("FULL-SAMPLE vs FILTERED COMPARISON")
print("=" * 70)

# ══════════════════════════════════════════════════════════════
# FILTER TO COMPETITIVE RANGE
# ══════════════════════════════════════════════════════════════
LO, HI = 0.15, 0.85

kalshi_full = kalshi_m.copy()
pm_full = pm_m.copy()

kalshi_comp = kalshi_m[(kalshi_m['p_model'] >= LO) & (kalshi_m['p_model'] <= HI)].copy()
pm_comp = pm_m[(pm_m['p_model'] >= LO) & (pm_m['p_model'] <= HI)].copy()

print(f"\nFull sample:       Kalshi N={len(kalshi_full)}, PM N={len(pm_full)}")
print(f"Competitive range: Kalshi N={len(kalshi_comp)} ({len(kalshi_comp)/len(kalshi_full)*100:.0f}%), PM N={len(pm_comp)} ({len(pm_comp)/len(pm_full)*100:.0f}%)")

# Game time coverage
if len(kalshi_comp) > 0:
    print(f"Competitive period: {kalshi_comp['game_minutes'].min():.0f} - {kalshi_comp['game_minutes'].max():.0f} min elapsed")
    print(f"p_model range in comp: [{kalshi_comp['p_model'].min():.3f}, {kalshi_comp['p_model'].max():.3f}]")

# ── Comparison table ──
print(f"\n{'Metric':<40} {'Full Sample':<20} {'Competitive Only':<20}")
print("-" * 80)

# Full sample
lk_full = kalshi_full['lambda_k'].dropna().values
lp_full = pm_full['lambda_p'].dropna().values
t_kf, p_kf = ttest_1samp(lk_full, 0)
t_pf, p_pf = ttest_1samp(lp_full, 0)

# Filtered
lk_comp = kalshi_comp['lambda_k'].dropna().values
lp_comp = pm_comp['lambda_p'].dropna().values
t_kc, p_kc = ttest_1samp(lk_comp, 0)
t_pc, p_pc = ttest_1samp(lp_comp, 0)

print(f"{'Kalshi mean lambda':<40} {np.mean(lk_full):+.4f} (p<0.001)    {np.mean(lk_comp):+.4f} (p={p_kc:.4f})")
print(f"{'PM mean lambda':<40} {np.mean(lp_full):+.4f} (p<0.001)    {np.mean(lp_comp):+.4f} (p={p_pc:.4f})")
print(f"{'Kalshi median lambda':<40} {np.median(lk_full):+.4f}              {np.median(lk_comp):+.4f}")
print(f"{'PM median lambda':<40} {np.median(lp_full):+.4f}              {np.median(lp_comp):+.4f}")

# Decay test (filtered)
if len(kalshi_comp) > 20:
    gf_k = kalshi_comp['game_seconds'].values / kalshi_comp['game_seconds'].max()
    gf_p = pm_comp['game_seconds'].values / pm_comp['game_seconds'].max()
    sl_k, _, _, psl_k, _ = linregress(gf_k, lk_comp)
    sl_p, _, _, psl_p, _ = linregress(gf_p, lp_comp)
    print(f"{'Kalshi time slope (filtered)':<40} {'N/A':<20} {sl_k:+.4f} (p={psl_k:.4f})")
    print(f"{'PM time slope (filtered)':<40} {'N/A':<20} {sl_p:+.4f} (p={psl_p:.4f})")

# 1st half vs 2nd half (filtered)
lk_1h = kalshi_comp[kalshi_comp['sec_elapsed'] < 1200]['lambda_k'].values
lk_2h = kalshi_comp[kalshi_comp['sec_elapsed'] >= 1200]['lambda_k'].values
lp_1h = pm_comp[pm_comp['sec_elapsed'] < 1200]['lambda_p'].values
lp_2h = pm_comp[pm_comp['sec_elapsed'] >= 1200]['lambda_p'].values

if len(lk_1h) > 5 and len(lk_2h) > 5:
    t_h, p_h = ttest_ind(lk_1h, lk_2h)
    print(f"\n1st vs 2nd half (filtered, Kalshi):  1H={np.mean(lk_1h):+.4f} (n={len(lk_1h)})  2H={np.mean(lk_2h):+.4f} (n={len(lk_2h)})  p={p_h:.4f}")
if len(lp_1h) > 5 and len(lp_2h) > 5:
    t_h, p_h = ttest_ind(lp_1h, lp_2h)
    print(f"1st vs 2nd half (filtered, PM):      1H={np.mean(lp_1h):+.4f} (n={len(lp_1h)})  2H={np.mean(lp_2h):+.4f} (n={len(lp_2h)})  p={p_h:.4f}")

# ── Also compute λ against ESPN benchmark (filtered) ──
lk_espn_comp = kalshi_comp['lambda_k_espn'].dropna().values
lp_espn_comp = pm_comp['lambda_p_espn'].dropna().values
if len(lk_espn_comp) > 5:
    t_ke, p_ke = ttest_1samp(lk_espn_comp, 0)
    t_pe, p_pe = ttest_1samp(lp_espn_comp, 0)
    print(f"\nVs ESPN benchmark (filtered):")
    print(f"  Kalshi mean lambda_ESPN: {np.mean(lk_espn_comp):+.4f} (p={p_ke:.4f})")
    print(f"  PM mean lambda_ESPN:     {np.mean(lp_espn_comp):+.4f} (p={p_pe:.4f})")


# ══════════════════════════════════════════════════════════════
# ROBUSTNESS: λ by p_model bin
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("ROBUSTNESS: LAMBDA BY P_MODEL BIN")
print("=" * 70)

bins = [0.0, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 1.0]
bin_labels = [f"{bins[i]:.2f}-{bins[i+1]:.2f}" for i in range(len(bins)-1)]

print(f"\n{'Bin':<12} {'N_k':>5} {'lam_k':>8} {'N_p':>5} {'lam_p':>8} {'Note':<20}")
print("-" * 65)

bin_data_k = []
bin_data_p = []

for i in range(len(bins)-1):
    lo, hi_b = bins[i], bins[i+1]
    label = bin_labels[i]
    in_comp = "  <-- competitive" if lo >= LO and hi_b <= HI else "  (tail)" if lo < LO or hi_b > HI else ""

    mk = kalshi_full[(kalshi_full['p_model'] >= lo) & (kalshi_full['p_model'] < hi_b)]
    mp = pm_full[(pm_full['p_model'] >= lo) & (pm_full['p_model'] < hi_b)]

    nk = len(mk)
    np_ = len(mp)
    lk_bin = mk['lambda_k'].mean() if nk > 0 else float('nan')
    lp_bin = mp['lambda_p'].mean() if np_ > 0 else float('nan')

    bin_data_k.append({'bin': label, 'lo': lo, 'hi': hi_b, 'mid': (lo+hi_b)/2, 'n': nk, 'mean_lam': lk_bin})
    bin_data_p.append({'bin': label, 'lo': lo, 'hi': hi_b, 'mid': (lo+hi_b)/2, 'n': np_, 'mean_lam': lp_bin})

    print(f"{label:<12} {nk:>5} {lk_bin:>+8.4f} {np_:>5} {lp_bin:>+8.4f}{in_comp}")

bk = pd.DataFrame(bin_data_k)
bp = pd.DataFrame(bin_data_p)


# ══════════════════════════════════════════════════════════════
# FIGURES
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("GENERATING CORRECTED FIGURES")
print("=" * 70)

plt.rcParams.update({
    'font.size': 11, 'font.family': 'sans-serif',
    'figure.facecolor': 'white', 'axes.facecolor': '#fafafa',
    'axes.grid': True, 'grid.alpha': 0.3,
})

# ── Figure A v2: λ trajectory with competitive range shaded ──
fig_a, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1], sharex=True)

# Shade non-competitive regions
# Find game-minute boundaries where p_model enters/exits competitive range
all_obs = pd.concat([
    kalshi_full[['game_minutes', 'p_model']],
    pm_full[['game_minutes', 'p_model']],
]).sort_values('game_minutes')

# Plot all λ (gray for non-competitive, colored for competitive)
k_nc = kalshi_full[(kalshi_full['p_model'] < LO) | (kalshi_full['p_model'] > HI)]
k_c  = kalshi_comp
p_nc = pm_full[(pm_full['p_model'] < LO) | (pm_full['p_model'] > HI)]
p_c  = pm_comp

ax1.scatter(k_nc['game_minutes'], k_nc['lambda_k'], color='gray', alpha=0.10, s=8, zorder=1)
ax1.scatter(p_nc['game_minutes'], p_nc['lambda_p'], color='gray', alpha=0.10, s=8, zorder=1)
ax1.scatter(k_c['game_minutes'], k_c['lambda_k'], color='red', alpha=0.20, s=10, zorder=2)
ax1.scatter(p_c['game_minutes'], p_c['lambda_p'], color='blue', alpha=0.20, s=10, zorder=2)

# Smoothed — competitive only
if len(k_c) > 10:
    k_sm = k_c.set_index('game_minutes')['lambda_k'].rolling(window=8, min_periods=3, center=True).mean()
    ax1.plot(k_sm.index, k_sm.values, 'r-', linewidth=2.5, label='Kalshi (competitive, smoothed)', zorder=4)
if len(p_c) > 10:
    p_sm = p_c.set_index('game_minutes')['lambda_p'].rolling(window=8, min_periods=3, center=True).mean()
    ax1.plot(p_sm.index, p_sm.values, 'b-', linewidth=2.5, label='Polymarket (competitive, smoothed)', zorder=4)

ax1.axhline(0, color='black', linestyle='--', linewidth=0.8)
ax1.axvline(20, color='gray', linestyle=':', alpha=0.6, linewidth=1.5, label='Halftime')

# Shade non-competitive regions lightly
# Find when p_model exits [0.15, 0.85]
exit_time = None
for _, row in kalshi_full.sort_values('game_minutes').iterrows():
    if row['p_model'] < LO or row['p_model'] > HI:
        if exit_time is None:
            exit_time = row['game_minutes']
    else:
        exit_time = None

# Approximate: shade from when game leaves competitive range to end
if len(k_nc) > 0:
    nc_start = k_nc['game_minutes'].min()
    # Find the last entry to competitive range
    if len(k_c) > 0:
        last_comp = k_c['game_minutes'].max()
        ax1.axvspan(last_comp, kalshi_full['game_minutes'].max(), alpha=0.08, color='gray', zorder=0)
        ax1.annotate('Non-competitive\n(tail artifact zone)', xy=(last_comp + 5, 1.4),
                     fontsize=9, color='gray', fontstyle='italic')

ax1.set_ylabel(r'Wang $\lambda(t)$', fontsize=13)
ax1.set_title('Figure A (corrected): Intra-Game Pricing Wedge\nGray = outside competitive range (0.15 < p* < 0.85)', fontsize=13, fontweight='bold')
ax1.legend(loc='upper left', fontsize=9)
ax1.set_ylim(-0.8, 2.2)

# Score margin panel
scoring = timeline[timeline.apply(lambda r: r.get('ill_score', 0) + r.get('uconn_score', 0) > 0 or r['sec_elapsed'] == 0, axis=1)]
scoring_plot = timeline.drop_duplicates(subset='sec_elapsed', keep='last').sort_values('sec_elapsed')
ax2.fill_between(scoring_plot['sec_elapsed']/60, scoring_plot['margin'], 0,
                 where=scoring_plot['margin'] >= 0, color='#E84A27', alpha=0.3, label='ILL leads')
ax2.fill_between(scoring_plot['sec_elapsed']/60, scoring_plot['margin'], 0,
                 where=scoring_plot['margin'] < 0, color='#0E1A3D', alpha=0.3, label='UCONN leads')
ax2.step(scoring_plot['sec_elapsed']/60, scoring_plot['margin'], color='black', linewidth=0.8, where='post')
ax2.axhline(0, color='black', linewidth=0.5)
ax2.axvline(20, color='gray', linestyle=':', alpha=0.6)
ax2.set_xlabel('Minutes Elapsed', fontsize=12)
ax2.set_ylabel('Margin\n(ILL-UCONN)', fontsize=10)
ax2.legend(loc='lower left', fontsize=8)

fig_a.tight_layout()
fig_a.savefig(f"{OUT}/fig_lambda_trajectory_v2.png", dpi=200, bbox_inches='tight')
print("  Saved fig_lambda_trajectory_v2.png")


# ── Figure E: Robustness — λ by p_model bin ──
fig_e, ax_e = plt.subplots(figsize=(10, 5))

x_k = np.arange(len(bk))
x_p = x_k + 0.35
width = 0.32

# Color bars: gray for tail, colored for competitive
colors_k = ['#d62728' if (bk.iloc[i]['lo'] >= LO and bk.iloc[i]['hi'] <= HI) else '#cccccc' for i in range(len(bk))]
colors_p = ['#1f77b4' if (bp.iloc[i]['lo'] >= LO and bp.iloc[i]['hi'] <= HI) else '#aaaaaa' for i in range(len(bp))]

bars_k = ax_e.bar(x_k, bk['mean_lam'], width, color=colors_k, edgecolor='white', label='Kalshi')
bars_p = ax_e.bar(x_p, bp['mean_lam'], width, color=colors_p, edgecolor='white', label='Polymarket')

# Add N labels on top
for i, (bar, row) in enumerate(zip(bars_k, bk.itertuples())):
    if row.n > 0:
        ax_e.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                  f'n={row.n}', ha='center', va='bottom', fontsize=7, color='gray')
for i, (bar, row) in enumerate(zip(bars_p, bp.itertuples())):
    if row.n > 0:
        ax_e.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                  f'n={row.n}', ha='center', va='bottom', fontsize=7, color='gray')

ax_e.axhline(0, color='black', linewidth=0.8)
ax_e.set_xticks(x_k + 0.175)
ax_e.set_xticklabels(bin_labels, rotation=45, ha='right', fontsize=9)
ax_e.set_xlabel(r'Model probability bin $p^*(t)$', fontsize=12)
ax_e.set_ylabel(r'Mean Wang $\lambda$', fontsize=12)
ax_e.set_title(r'Figure E: Pricing Wedge by Model Probability Bin' + '\nColored = competitive range (0.15-0.85), Gray = tail bins',
               fontsize=13, fontweight='bold')
ax_e.legend(fontsize=10)
fig_e.tight_layout()
fig_e.savefig(f"{OUT}/fig_lambda_by_bin.png", dpi=200, bbox_inches='tight')
print("  Saved fig_lambda_by_bin.png")


# ── Figure C v2: Calibration scatter with competitive range marked ──
fig_c, ax_c = plt.subplots(figsize=(7, 7))

# Non-competitive (gray)
ax_c.scatter(k_nc['p_model'], k_nc['p_kalshi'], alpha=0.15, s=12, c='gray', zorder=1)
ax_c.scatter(p_nc['p_model'], p_nc['p_pm'], alpha=0.15, s=12, c='gray', zorder=1)
# Competitive (colored)
ax_c.scatter(k_c['p_model'], k_c['p_kalshi'], alpha=0.35, s=15, c='red', label='Kalshi (competitive)', zorder=2)
ax_c.scatter(p_c['p_model'], p_c['p_pm'], alpha=0.35, s=15, c='blue', label='Polymarket (competitive)', zorder=2)

ax_c.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Perfect calibration')
ax_c.axvline(LO, color='gray', linestyle=':', alpha=0.5)
ax_c.axvline(HI, color='gray', linestyle=':', alpha=0.5)
ax_c.set_xlabel(r'Model Win Probability $p^*(t)$', fontsize=12)
ax_c.set_ylabel(r'Market Price $p_{mkt}(t)$', fontsize=12)
ax_c.set_title('Figure C (corrected): Market vs Model\nCompetitive range highlighted', fontsize=13, fontweight='bold')
ax_c.legend(fontsize=9)
ax_c.set_xlim(-0.02, 1.02); ax_c.set_ylim(-0.02, 1.02)
ax_c.set_aspect('equal')
fig_c.tight_layout()
fig_c.savefig(f"{OUT}/fig_calibration_scatter_v2.png", dpi=200, bbox_inches='tight')
print("  Saved fig_calibration_scatter_v2.png")


# ══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("=== CORRECTED INTRA-GAME WANG LAMBDA ANALYSIS ===")
print("=" * 70)

print(f"\n--- Full sample (ARTIFACT-CONTAMINATED) ---")
print(f"  Kalshi:     mean lambda = {np.mean(lk_full):+.4f}")
print(f"  Polymarket: mean lambda = {np.mean(lp_full):+.4f}")

print(f"\n--- Competitive range only (0.15 < p_model < 0.85) ---")
print(f"  N: Kalshi={len(kalshi_comp)}, Polymarket={len(pm_comp)}")
print(f"  Kalshi:     mean lambda = {np.mean(lk_comp):+.4f} (t={t_kc:.2f}, p={p_kc:.4f})")
print(f"  Polymarket: mean lambda = {np.mean(lp_comp):+.4f} (t={t_pc:.2f}, p={p_pc:.4f})")

if len(kalshi_comp) > 20:
    print(f"\n  Decay (filtered): Kalshi slope={sl_k:+.4f} (p={psl_k:.4f}), PM slope={sl_p:+.4f} (p={psl_p:.4f})")

if len(lk_1h) > 5 and len(lk_2h) > 5:
    print(f"  1H vs 2H (Kalshi):  {np.mean(lk_1h):+.4f} vs {np.mean(lk_2h):+.4f}")
    print(f"  1H vs 2H (PM):      {np.mean(lp_1h):+.4f} vs {np.mean(lp_2h):+.4f}")

if len(lk_espn_comp) > 5:
    print(f"\n  Vs ESPN benchmark (filtered):")
    print(f"    Kalshi:     {np.mean(lk_espn_comp):+.4f} (p={p_ke:.4f})")
    print(f"    Polymarket: {np.mean(lp_espn_comp):+.4f} (p={p_pe:.4f})")

print(f"\n  Main paper cross-sectional lambda: ~0.176")
print(f"  Intra-game competitive lambda:     {np.mean(lk_comp):+.4f} (Kalshi), {np.mean(lp_comp):+.4f} (PM)")
ratio = np.mean(lk_comp) / 0.176 if abs(np.mean(lk_comp)) > 0.001 else 0
print(f"  Ratio to main paper:               {ratio:.2f}x")

print(f"\nAll corrected outputs saved to: {OUT}/")
