#!/usr/bin/env python3
"""
Final Four 2026 Prediction Market Analysis
Yang (2026), SSRN Abstract ID 6468338 — Wang Transform Case Study
"""
import json, os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

# ── Paths ──
DATA = os.path.expanduser("~/final_four_2026/data")
OUT  = os.path.expanduser("~/final_four_2026/analysis")
os.makedirs(OUT, exist_ok=True)

CT = timezone(timedelta(hours=-5))  # CDT = UTC-5 in April

# ── Helper: load JSONL ──
def load_jsonl(path):
    records = []
    with open(path) as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except:
                pass
    return records

# ── Helper: parse timestamp ──
def parse_ts(ts_str):
    ts_str = str(ts_str)
    if '+' in ts_str or ts_str.endswith('Z'):
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    else:
        dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
    return dt

def to_ct(dt):
    return dt.astimezone(CT)

def to_ct_naive(dt):
    """Convert to CT then strip tzinfo so matplotlib doesn't re-convert."""
    return dt.astimezone(CT).replace(tzinfo=None)

# ── Wang Transform ──
def wang_lambda(p_market, p_benchmark):
    z_mkt = norm.ppf(np.clip(p_market, 0.001, 0.999))
    z_bench = norm.ppf(np.clip(p_benchmark, 0.001, 0.999))
    return z_mkt - z_bench

# ══════════════════════════════════════════════════════════════
# STEP 1: LOAD AND EXPLORE
# ══════════════════════════════════════════════════════════════
print("=" * 70)
print("STEP 1: LOAD AND EXPLORE")
print("=" * 70)

kalshi_raw = load_jsonl(f"{DATA}/kalshi_20260404.jsonl")
pm_raw     = load_jsonl(f"{DATA}/polymarket_20260404.jsonl")
with open(f"{DATA}/sportsbook_pregame.json") as f:
    sportsbook = json.load(f)

print(f"\n1. Record counts:")
print(f"   Kalshi:      {len(kalshi_raw):,}")
print(f"   Polymarket:  {len(pm_raw):,}")

kalshi_good = [r for r in kalshi_raw if 'error' not in r]
pm_good     = [r for r in pm_raw if 'error' not in r]
print(f"   Kalshi (no errors):     {len(kalshi_good):,}")
print(f"   Polymarket (no errors): {len(pm_good):,}")

kalshi_ts = [parse_ts(r['timestamp']) for r in kalshi_good]
pm_ts     = [parse_ts(r['timestamp']) for r in pm_good]

print(f"\n2. Time range:")
print(f"   Kalshi:     {to_ct(min(kalshi_ts)).strftime('%Y-%m-%d %I:%M:%S %p CT')} -> {to_ct(max(kalshi_ts)).strftime('%Y-%m-%d %I:%M:%S %p CT')}")
print(f"   Polymarket: {to_ct(min(pm_ts)).strftime('%Y-%m-%d %I:%M:%S %p CT')} -> {to_ct(max(pm_ts)).strftime('%Y-%m-%d %I:%M:%S %p CT')}")

# Tickers/contracts
kalshi_tickers = set()
for r in kalshi_good:
    t = r.get('ticker', '?')
    if t.startswith('KXMARMAD') or t.startswith('KXNCAAMB'):
        kalshi_tickers.add(t)

pm_teams  = set(r.get('team','') for r in pm_good if r.get('team'))
pm_markets = set(r.get('market','') for r in pm_good if r.get('market'))

print(f"\n3. Contracts tracked:")
print(f"   Kalshi championship: {sorted([t for t in kalshi_tickers if 'ARMAD' in t])}")
print(f"   Kalshi game:         {sorted([t for t in kalshi_tickers if 'GAME' in t])}")
print(f"   Kalshi spread:       {sorted([t for t in kalshi_tickers if 'SPREAD' in t])}")
print(f"   PM teams (champ):    {sorted(pm_teams)}")
print(f"   PM game markets:     {sorted(pm_markets)}")

print(f"\n4. Contract classification:")
print(f"   Championship: KXMARMAD-26-* (Kalshi), midpoint/book by team (PM)")
print(f"   Game-specific: KXNCAAMBGAME-* (Kalshi), game1/game2 ML (PM)")

print(f"\n5. Sample records (3 from each source):")
print(f"\n   --- Kalshi (championship) ---")
for r in [r for r in kalshi_good if r.get('ticker','').startswith('KXMARMAD')][:3]:
    print(f"   {json.dumps(r)}")
print(f"\n   --- Polymarket (midpoint) ---")
for r in [r for r in pm_good if r.get('type') == 'midpoint'][:3]:
    print(f"   {json.dumps(r)}")

# Median interval
def median_interval(records, key_fn, ts_fn):
    from collections import defaultdict
    groups = defaultdict(list)
    for r in records:
        groups[key_fn(r)].append(ts_fn(r))
    intervals = []
    for k, times in groups.items():
        times.sort()
        for i in range(1, len(times)):
            dt = (times[i] - times[i-1]).total_seconds()
            if 0 < dt < 300:
                intervals.append(dt)
    return np.median(intervals) if intervals else None

kalshi_med = median_interval(
    [r for r in kalshi_good if r.get('ticker','').startswith('KXMARMAD')],
    lambda r: r['ticker'],
    lambda r: parse_ts(r['timestamp'])
)
pm_med = median_interval(
    [r for r in pm_good if r.get('type') == 'midpoint'],
    lambda r: r['team'],
    lambda r: parse_ts(r['timestamp'])
)
print(f"\n6. Median inter-record interval (same ticker):")
print(f"   Kalshi (championship): {kalshi_med:.1f}s")
print(f"   Polymarket (midpoint): {pm_med:.1f}s")


# ══════════════════════════════════════════════════════════════
# STEP 2: SEPARATE GAME DATA
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("STEP 2: SEPARATE GAME DATA")
print("=" * 70)

def build_df(records, ts_key='timestamp'):
    df = pd.DataFrame(records)
    df['dt'] = df[ts_key].apply(parse_ts)
    df['dt_ct'] = df['dt'].apply(to_ct_naive)
    df = df.sort_values('dt').reset_index(drop=True)
    return df

# Game 1: Kalshi
g1k_ill = build_df([r for r in kalshi_good if r.get('ticker') == 'KXNCAAMBGAME-26APR04ILLCONN-ILL'])
g1k_uconn = build_df([r for r in kalshi_good if r.get('ticker') == 'KXNCAAMBGAME-26APR04ILLCONN-CONN'])

# Game 1: Polymarket
g1p = build_df([r for r in pm_good if r.get('market') == 'game1_ill_uconn_ml'])

# Game 2: Kalshi
g2k_mich = build_df([r for r in kalshi_good if r.get('ticker') == 'KXNCAAMBGAME-26APR04MICHARIZ-MICH'])
g2k_ariz = build_df([r for r in kalshi_good if r.get('ticker') == 'KXNCAAMBGAME-26APR04MICHARIZ-ARIZ'])

# Game 2: Polymarket
g2p = build_df([r for r in pm_good if r.get('market') == 'game2_mich_ariz_ml'])

# Championship: Kalshi
champ_k = {}
for team in ['ILL', 'CONN', 'MICH', 'ARIZ']:
    champ_k[team] = build_df([r for r in kalshi_good if r.get('ticker') == f'KXMARMAD-26-{team}'])

# Championship: Polymarket (midpoint)
champ_p = {}
for team in ['Illinois', 'Connecticut', 'Michigan', 'Arizona']:
    champ_p[team] = build_df([r for r in pm_good if r.get('type') == 'midpoint' and r.get('team') == team])

# Extract price columns
for df in [g1k_ill, g1k_uconn, g2k_mich, g2k_ariz]:
    if len(df) > 0:
        df['mid'] = (df['yes_bid'].astype(float) + df['yes_ask'].astype(float)) / 2

if len(g1p) > 0:
    g1p['ill_prob'] = g1p['price_illinois_fighting_illini'].astype(float)
    g1p['uconn_prob'] = g1p['price_connecticut_huskies'].astype(float)

if len(g2p) > 0:
    for col in g2p.columns:
        if 'michigan' in col.lower():
            g2p['mich_prob'] = g2p[col].astype(float)
        if 'arizona' in col.lower():
            g2p['ariz_prob'] = g2p[col].astype(float)

for team, df in champ_k.items():
    df['mid'] = (df['yes_bid'].astype(float) + df['yes_ask'].astype(float)) / 2

for team, df in champ_p.items():
    df['mid'] = df['mid'].astype(float)

print(f"Game 1 Kalshi (ILL):  {len(g1k_ill)} records, {to_ct(g1k_ill['dt'].min()).strftime('%H:%M')}-{to_ct(g1k_ill['dt'].max()).strftime('%H:%M')} CT")
print(f"Game 1 PM:            {len(g1p)} records, {to_ct(g1p['dt'].min()).strftime('%H:%M')}-{to_ct(g1p['dt'].max()).strftime('%H:%M')} CT")
print(f"Game 2 Kalshi (MICH): {len(g2k_mich)} records")
print(f"Game 2 PM:            {len(g2p)} records")
for team in ['ILL', 'CONN', 'MICH', 'ARIZ']:
    print(f"Champ Kalshi {team}:     {len(champ_k[team])} records")
for team in ['Illinois', 'Connecticut', 'Michigan', 'Arizona']:
    print(f"Champ PM {team:12s}:  {len(champ_p[team])} records")


# ══════════════════════════════════════════════════════════════
# STEP 3: GAME OUTCOMES
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("STEP 3: GAME OUTCOMES")
print("=" * 70)

ill_final_k  = g1k_ill['mid'].iloc[-1]
uconn_final_k = g1k_uconn['mid'].iloc[-1]
ill_final_p  = g1p['ill_prob'].iloc[-1] if len(g1p) > 0 else None
uconn_final_p = g1p['uconn_prob'].iloc[-1] if len(g1p) > 0 else None

print(f"\nGame 1: Illinois vs UConn")
print(f"  Final Kalshi prices:     ILL={ill_final_k:.3f}  UCONN={uconn_final_k:.3f}")
if ill_final_p is not None:
    print(f"  Final Polymarket prices: ILL={ill_final_p:.4f}  UCONN={uconn_final_p:.4f}")
g1_winner = "UConn" if ill_final_k < 0.1 else "Illinois"
print(f"  -> WINNER: {g1_winner}")

mich_final_k = champ_k['MICH']['mid'].iloc[-1]
ariz_final_k = champ_k['ARIZ']['mid'].iloc[-1]
print(f"\nGame 2: Michigan vs Arizona")
print(f"  (Data collection stopped before Game 2 tipoff at 7:49 PM CT)")
print(f"  Last championship prices: MICH={mich_final_k:.3f}  ARIZ={ariz_final_k:.3f}")
if len(g2k_mich) > 0:
    print(f"  Last game ML prices:      MICH={g2k_mich['mid'].iloc[-1]:.3f}  ARIZ={g2k_ariz['mid'].iloc[-1]:.3f}")
print(f"  -> Game 2 outcome: UNRESOLVED in data (collection stopped pre-tipoff)")


# ══════════════════════════════════════════════════════════════
# STEP 4: FIGURES
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("STEP 4: GENERATING FIGURES")
print("=" * 70)

plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'figure.facecolor': 'white',
    'axes.facecolor': '#fafafa',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'figure.dpi': 100,
})

TIPOFF_G1 = datetime(2026, 4, 4, 22, 9, tzinfo=timezone.utc)   # 5:09 PM CT
TIPOFF_G2 = datetime(2026, 4, 5, 0, 49, tzinfo=timezone.utc)    # 7:49 PM CT

# ── Figure 1: Intra-Game Price Dynamics (Game 1) ──
fig1, ax1 = plt.subplots(figsize=(14, 6))

ax1.plot(g1k_ill['dt_ct'], g1k_ill['mid'] * 100, color='#d62728', linewidth=1.2,
         alpha=0.85, label='Kalshi')
if len(g1p) > 0:
    ax1.plot(g1p['dt_ct'], g1p['ill_prob'] * 100, color='#1f77b4', linewidth=1.2,
             alpha=0.85, label='Polymarket')

tipoff_ct = to_ct_naive(TIPOFF_G1)
ax1.axvline(tipoff_ct, color='green', linestyle='--', alpha=0.7, linewidth=1.5, label='Tipoff (5:09 PM)')

# Find game end
game_end_mask = g1k_ill['mid'] < 0.05
if game_end_mask.any():
    game_end_idx = game_end_mask.idxmax()
    game_end_time = g1k_ill.loc[game_end_idx, 'dt_ct']
    ax1.axvline(game_end_time, color='black', linestyle='--', alpha=0.7, linewidth=1.5,
                label=f'~Game decided ({game_end_time.strftime("%I:%M %p")} CT)')

ax1.axhline(50, color='gray', linestyle=':', alpha=0.4)
ax1.set_xlabel('Time (CT)', fontsize=12)
ax1.set_ylabel('Illinois Win Probability (%)', fontsize=12)
ax1.set_title('Figure 1: Illinois vs UConn — Intra-Game Win Probability\n2026 NCAA Final Four Semifinal, April 4', fontsize=14, fontweight='bold')
ax1.legend(loc='upper right', fontsize=10)
ax1.set_ylim(-2, 102)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
fig1.autofmt_xdate()
fig1.tight_layout()
fig1.savefig(f"{OUT}/fig1_game1_price_dynamics.png", dpi=200, bbox_inches='tight')
print("  Saved fig1_game1_price_dynamics.png")

# ── Figure 2: Cross-Platform Spread (Game 1) ──
g1k_ts = g1k_ill.set_index('dt')[['mid']].rename(columns={'mid': 'kalshi'})
g1p_ts = g1p.set_index('dt')[['ill_prob']].rename(columns={'ill_prob': 'pm'}) if len(g1p) > 0 else pd.DataFrame()

spread_df = pd.DataFrame()  # default empty
if len(g1p_ts) > 0:
    g1k_30s = g1k_ts.resample('30s').mean().dropna()
    g1p_30s = g1p_ts.resample('30s').mean().dropna()
    spread_df = g1k_30s.join(g1p_30s, how='inner').dropna()
    spread_df['spread_pp'] = (spread_df['kalshi'] - spread_df['pm']) * 100
    spread_df['dt_ct'] = spread_df.index.map(to_ct_naive)

    fig2, ax2 = plt.subplots(figsize=(14, 5))
    ax2.plot(spread_df['dt_ct'], spread_df['spread_pp'], color='#2ca02c', linewidth=1.0, alpha=0.8)
    ax2.axhline(0, color='black', linewidth=1, alpha=0.5)
    ax2.axhline(3, color='red', linestyle=':', alpha=0.4, label='+3pp threshold')
    ax2.axhline(-3, color='red', linestyle=':', alpha=0.4, label='-3pp threshold')

    exceed = spread_df[spread_df['spread_pp'].abs() > 3]
    if len(exceed) > 0:
        ax2.fill_between(spread_df['dt_ct'], spread_df['spread_pp'], 0,
                         where=spread_df['spread_pp'].abs() > 3, alpha=0.2, color='red')

    ax2.axvline(to_ct_naive(TIPOFF_G1), color='green', linestyle='--', alpha=0.5, label='Tipoff')
    ax2.set_xlabel('Time (CT)', fontsize=12)
    ax2.set_ylabel('Kalshi - Polymarket (pp)', fontsize=12)
    ax2.set_title('Figure 2: Cross-Platform Price Spread — Game 1 (ILL vs UCONN)', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    fig2.autofmt_xdate()
    fig2.tight_layout()
    fig2.savefig(f"{OUT}/fig2_cross_platform_spread.png", dpi=200, bbox_inches='tight')
    print("  Saved fig2_cross_platform_spread.png")
else:
    print("  [SKIP] Figure 2: insufficient Polymarket data for spread")

# ── Figure 3: Championship Market Reaction ──
fig3, (ax3a, ax3b) = plt.subplots(2, 1, figsize=(14, 9), sharex=True)

colors_k = {'ILL': '#E84A27', 'CONN': '#0E1A3D', 'MICH': '#FFCB05', 'ARIZ': '#CC0033'}
labels_k = {'ILL': 'Illinois', 'CONN': 'UConn', 'MICH': 'Michigan', 'ARIZ': 'Arizona'}

for team in ['ILL', 'CONN', 'MICH', 'ARIZ']:
    df = champ_k[team]
    ax3a.plot(df['dt_ct'], df['mid'] * 100, color=colors_k[team], linewidth=1.3,
              alpha=0.9, label=labels_k[team])

ax3a.axvline(to_ct_naive(TIPOFF_G1), color='green', linestyle='--', alpha=0.6, label='G1 Tipoff')
ax3a.set_ylabel('Championship Prob (%)', fontsize=12)
ax3a.set_title('Figure 3: Championship Probabilities Over Time', fontsize=14, fontweight='bold')
ax3a.legend(loc='upper left', fontsize=10)
ax3a.set_ylim(-2, 72)

colors_p = {'Illinois': '#E84A27', 'Connecticut': '#0E1A3D', 'Michigan': '#FFCB05', 'Arizona': '#CC0033'}
for team in ['Illinois', 'Connecticut', 'Michigan', 'Arizona']:
    df = champ_p[team]
    ax3b.plot(df['dt_ct'], df['mid'] * 100, color=colors_p[team], linewidth=1.3,
              alpha=0.9, label=team)

ax3b.axvline(to_ct_naive(TIPOFF_G1), color='green', linestyle='--', alpha=0.6, label='G1 Tipoff')
ax3b.set_xlabel('Time (CT)', fontsize=12)
ax3b.set_ylabel('Championship Prob (%)', fontsize=12)
ax3b.set_title('Polymarket', fontsize=12)
ax3b.legend(loc='upper left', fontsize=10)
ax3b.set_ylim(-2, 72)
ax3b.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

fig3.autofmt_xdate()
fig3.tight_layout()
fig3.savefig(f"{OUT}/fig3_championship_reaction.png", dpi=200, bbox_inches='tight')
print("  Saved fig3_championship_reaction.png")

# ── Figure 4: Game 2 pre-game ──
if len(g2k_mich) > 10:
    fig4, ax4 = plt.subplots(figsize=(14, 6))
    ax4.plot(g2k_mich['dt_ct'], g2k_mich['mid'] * 100, color='#d62728', linewidth=1.2, label='Kalshi')
    if len(g2p) > 10 and 'mich_prob' in g2p.columns:
        ax4.plot(g2p['dt_ct'], g2p['mich_prob'] * 100, color='#1f77b4', linewidth=1.2, label='Polymarket')
    ax4.axvline(to_ct_naive(TIPOFF_G2), color='green', linestyle='--', alpha=0.7, label='G2 Tipoff (7:49 PM)')
    ax4.set_xlabel('Time (CT)')
    ax4.set_ylabel('Michigan Win Probability (%)')
    ax4.set_title('Figure 4: Michigan vs Arizona — Pre-Game Win Probability\n(Data collection ended before tipoff)', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.set_ylim(-2, 102)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    fig4.autofmt_xdate()
    fig4.tight_layout()
    fig4.savefig(f"{OUT}/fig4_game2_price_dynamics.png", dpi=200, bbox_inches='tight')
    print("  Saved fig4_game2_price_dynamics.png")
else:
    print("  [SKIP] Figure 4: insufficient Game 2 data")


# ══════════════════════════════════════════════════════════════
# STEP 5: WANG TRANSFORM ANALYSIS
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("STEP 5: WANG TRANSFORM ANALYSIS")
print("=" * 70)

# Sportsbook benchmarks — de-vig from user-provided consensus
ill_sb_raw = 0.565
uconn_sb_raw = 0.476
overround1 = ill_sb_raw + uconn_sb_raw
ill_sb = ill_sb_raw / overround1
uconn_sb = uconn_sb_raw / overround1

mich_sb_raw = 0.549
ariz_sb_raw = 0.495
overround2 = mich_sb_raw + ariz_sb_raw
mich_sb = mich_sb_raw / overround2
ariz_sb = ariz_sb_raw / overround2

print(f"\nSportsbook de-vigged probabilities:")
print(f"  Game 1: ILL={ill_sb:.4f}  UCONN={uconn_sb:.4f}  (overround={overround1:.3f})")
print(f"  Game 2: MICH={mich_sb:.4f}  ARIZ={ariz_sb:.4f}  (overround={overround2:.3f})")

# Pre-game market prices
ill_pregame_k = g1k_ill['mid'].iloc[:5].mean()
uconn_pregame_k = g1k_uconn['mid'].iloc[:5].mean()
ill_pregame_p = g1p['ill_prob'].iloc[:5].mean() if len(g1p) > 0 else None
uconn_pregame_p = g1p['uconn_prob'].iloc[:5].mean() if len(g1p) > 0 else None

mich_pregame_k = g2k_mich['mid'].iloc[:5].mean() if len(g2k_mich) > 5 else None
mich_pregame_p = g2p['mich_prob'].iloc[:5].mean() if len(g2p) > 5 and 'mich_prob' in g2p.columns else None

print(f"\nPre-game market prices (first 5 obs avg):")
print(f"  Kalshi  ILL game ML: {ill_pregame_k:.4f}")
if ill_pregame_p is not None:
    print(f"  PM      ILL game ML: {ill_pregame_p:.4f}")
if mich_pregame_k is not None:
    print(f"  Kalshi  MICH game ML: {mich_pregame_k:.4f}")
if mich_pregame_p is not None:
    print(f"  PM      MICH game ML: {mich_pregame_p:.4f}")

lam_k_g1 = wang_lambda(ill_pregame_k, ill_sb)
lam_p_g1 = wang_lambda(ill_pregame_p, ill_sb) if ill_pregame_p else None

print(f"\nWang lambda (Illinois favorite, Game 1):")
print(f"  lam_Kalshi     = phi_inv({ill_pregame_k:.4f}) - phi_inv({ill_sb:.4f}) = {lam_k_g1:+.4f}")
if lam_p_g1 is not None:
    print(f"  lam_Polymarket = phi_inv({ill_pregame_p:.4f}) - phi_inv({ill_sb:.4f}) = {lam_p_g1:+.4f}")

print(f"\n  lam > 0 => market overprices favorites relative to sportsbook")
print(f"  lam < 0 => market underprices favorites")
print(f"  Kalshi  lam = {lam_k_g1:+.4f} -> {'OVERPRICES' if lam_k_g1 > 0 else 'UNDERPRICES'} favorite")
if lam_p_g1 is not None:
    print(f"  PM      lam = {lam_p_g1:+.4f} -> {'OVERPRICES' if lam_p_g1 > 0 else 'UNDERPRICES'} favorite")

lam_k_g2 = None
lam_p_g2 = None
if mich_pregame_k is not None:
    lam_k_g2 = wang_lambda(mich_pregame_k, mich_sb)
    print(f"\nWang lambda (Michigan favorite, Game 2):")
    print(f"  lam_Kalshi     = {lam_k_g2:+.4f}")
if mich_pregame_p is not None:
    lam_p_g2 = wang_lambda(mich_pregame_p, mich_sb)
    print(f"  lam_Polymarket = {lam_p_g2:+.4f}")


# ══════════════════════════════════════════════════════════════
# STEP 6: INTRA-GAME SPREAD / LAMBDA DECAY
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("STEP 6: INTRA-GAME SPREAD / LAMBDA DECAY")
print("=" * 70)

g1k_ingame = g1k_ill[g1k_ill['dt'] >= TIPOFF_G1].copy()

if len(g1k_ingame) > 20:
    g1k_ingame['spread_pct'] = (g1k_ingame['yes_ask'].astype(float) - g1k_ingame['yes_bid'].astype(float)) * 100
    g1k_ingame['game_elapsed'] = (g1k_ingame['dt'] - TIPOFF_G1).dt.total_seconds()
    max_time = g1k_ingame['game_elapsed'].max()
    g1k_ingame['game_pct'] = g1k_ingame['game_elapsed'] / max_time

    g1k_ingame['segment'] = pd.cut(g1k_ingame['game_pct'], bins=10, labels=range(10))

    seg_stats = g1k_ingame.groupby('segment', observed=False).agg(
        avg_mid=('mid', 'mean'),
        avg_spread=('spread_pct', 'mean'),
        n_obs=('mid', 'count'),
        avg_game_pct=('game_pct', 'mean')
    ).reset_index()

    print(f"\nGame 1 -- 10-segment breakdown (tipoff to end):")
    print(f"{'Seg':>3} {'Game%':>6} {'Avg Mid':>8} {'Spread(pp)':>11} {'N obs':>6}")
    for _, row in seg_stats.iterrows():
        print(f"{int(row['segment']):>3} {row['avg_game_pct']*100:>5.0f}% {row['avg_mid']:>8.3f} {row['avg_spread']:>10.1f}pp {int(row['n_obs']):>6}")

    # Figure 5: Spread decay
    fig5, ax5 = plt.subplots(figsize=(10, 5))
    ax5.bar(seg_stats['segment'].astype(int), seg_stats['avg_spread'], color='#ff7f0e', alpha=0.8, edgecolor='white')
    ax5.set_xlabel('Game Segment (0=tipoff, 9=final buzzer)', fontsize=12)
    ax5.set_ylabel('Average Bid-Ask Spread (pp)', fontsize=12)
    ax5.set_title('Figure 5: Bid-Ask Spread Decay During Game 1\n(Proxy for pricing wedge compression)', fontsize=14, fontweight='bold')
    fig5.tight_layout()
    fig5.savefig(f"{OUT}/fig5_spread_decay.png", dpi=200, bbox_inches='tight')
    print("  Saved fig5_spread_decay.png")
else:
    print("  [SKIP] Insufficient in-game data for spread decay analysis")


# ══════════════════════════════════════════════════════════════
# STEP 7: CROSS-PLATFORM PRICE DISCOVERY
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("STEP 7: CROSS-PLATFORM PRICE DISCOVERY")
print("=" * 70)

leader = "N/A"

if len(g1p) > 0 and len(g1k_ill) > 0:
    k_series = g1k_ill.set_index('dt')['mid'].resample('15s').mean()
    p_series = g1p.set_index('dt')['ill_prob'].resample('15s').mean()

    aligned = pd.DataFrame({'kalshi': k_series, 'pm': p_series}).dropna()

    if len(aligned) > 50:
        aligned['logit_k'] = np.log(aligned['kalshi'].clip(0.01, 0.99) / (1 - aligned['kalshi'].clip(0.01, 0.99)))
        aligned['logit_p'] = np.log(aligned['pm'].clip(0.01, 0.99) / (1 - aligned['pm'].clip(0.01, 0.99)))

        aligned['dk'] = aligned['logit_k'].diff()
        aligned['dp'] = aligned['logit_p'].diff()
        aligned = aligned.dropna()

        max_lag = 20
        dk = aligned['dk'].values
        dp = aligned['dp'].values

        dk_norm = (dk - dk.mean()) / (dk.std() + 1e-10)
        dp_norm = (dp - dp.mean()) / (dp.std() + 1e-10)

        lags = list(range(-max_lag, max_lag + 1))
        xcorr = []
        for lag in lags:
            if lag >= 0:
                c = np.corrcoef(dk_norm[lag:], dp_norm[:len(dp_norm)-lag if lag > 0 else len(dp_norm)])[0, 1]
            else:
                c = np.corrcoef(dk_norm[:len(dk_norm)+lag], dp_norm[-lag:])[0, 1]
            xcorr.append(c if np.isfinite(c) else 0)

        peak_idx = np.argmax(np.abs(xcorr))
        peak_lag = lags[peak_idx]
        peak_corr = xcorr[peak_idx]

        print(f"\nCross-correlation analysis (15s grid, log-odds changes):")
        print(f"  Aligned observations: {len(aligned)}")
        print(f"  Peak cross-corr: {peak_corr:.3f} at lag {peak_lag} ({peak_lag*15}s)")

        if peak_lag > 0:
            print(f"  -> Kalshi leads Polymarket by ~{peak_lag*15}s")
            leader = "Kalshi"
        elif peak_lag < 0:
            print(f"  -> Polymarket leads Kalshi by ~{abs(peak_lag)*15}s")
            leader = "Polymarket"
        else:
            print(f"  -> Contemporaneous (no clear lead)")
            leader = "Contemporaneous"

        # Granger causality
        from numpy.linalg import lstsq

        def granger_f_test(x, y, max_p=4):
            n = len(x)
            if n < max_p + 10:
                return None, None
            Y = y[max_p:]
            X_r = np.column_stack([np.ones(n - max_p)] + [y[max_p-i:n-i] for i in range(1, max_p+1)])
            beta_r = lstsq(X_r, Y, rcond=None)[0]
            ssr_r = np.sum((Y - X_r @ beta_r) ** 2)

            X_u = np.column_stack([X_r] + [x[max_p-i:n-i] for i in range(1, max_p+1)])
            beta_u = lstsq(X_u, Y, rcond=None)[0]
            ssr_u = np.sum((Y - X_u @ beta_u) ** 2)

            df1 = max_p
            df2 = n - 2 * max_p - 1
            if ssr_u > 0 and df2 > 0:
                F = ((ssr_r - ssr_u) / df1) / (ssr_u / df2)
                from scipy.stats import f as fdist
                p_val = 1 - fdist.cdf(F, df1, df2)
                return F, p_val
            return None, None

        dk_vals = aligned['dk'].values
        dp_vals = aligned['dp'].values

        F_k2p, p_k2p = granger_f_test(dk_vals, dp_vals, max_p=4)
        F_p2k, p_p2k = granger_f_test(dp_vals, dk_vals, max_p=4)

        print(f"\nGranger Causality (log-odds changes, 4 lags = 60s):")
        if F_k2p is not None:
            sig = '***' if p_k2p < 0.01 else '**' if p_k2p < 0.05 else '*' if p_k2p < 0.1 else ''
            print(f"  Kalshi -> Polymarket:  F={F_k2p:.2f}, p={p_k2p:.4f} {sig}")
        if F_p2k is not None:
            sig = '***' if p_p2k < 0.01 else '**' if p_p2k < 0.05 else '*' if p_p2k < 0.1 else ''
            print(f"  Polymarket -> Kalshi:  F={F_p2k:.2f}, p={p_p2k:.4f} {sig}")

        if F_k2p is not None and F_p2k is not None:
            if p_k2p < 0.05 and p_p2k >= 0.05:
                print(f"  -> Kalshi leads price discovery")
                leader = "Kalshi"
            elif p_p2k < 0.05 and p_k2p >= 0.05:
                print(f"  -> Polymarket leads price discovery")
                leader = "Polymarket"
            elif p_k2p < 0.05 and p_p2k < 0.05:
                print(f"  -> Bidirectional causality (feedback)")
                leader = "Bidirectional"
            else:
                print(f"  -> No significant Granger causality detected")
                leader = "Inconclusive"

        # Figure 6: Cross-correlation
        lag_seconds = [l * 15 for l in lags]
        fig6, ax6 = plt.subplots(figsize=(10, 4))
        ax6.bar(lag_seconds, xcorr, width=12, color='steelblue', alpha=0.8)
        ax6.axvline(0, color='black', linewidth=1)
        ax6.axvline(peak_lag * 15, color='red', linestyle='--', alpha=0.7,
                     label=f'Peak: lag={peak_lag*15}s, rho={peak_corr:.3f}')
        ax6.set_xlabel('Lag (seconds, positive = Kalshi leads)', fontsize=11)
        ax6.set_ylabel('Cross-correlation', fontsize=11)
        ax6.set_title('Figure 6: Lagged Cross-Correlation of Log-Odds Changes\nKalshi vs Polymarket (Game 1)', fontsize=13, fontweight='bold')
        ax6.legend(fontsize=10)
        fig6.tight_layout()
        fig6.savefig(f"{OUT}/fig6_cross_correlation.png", dpi=200, bbox_inches='tight')
        print("  Saved fig6_cross_correlation.png")
    else:
        print("  [SKIP] Insufficient aligned data for price discovery analysis")
else:
    print("  [SKIP] Missing one platform's data")


# ══════════════════════════════════════════════════════════════
# STEP 8: SUMMARY STATISTICS TABLE
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("STEP 8: SUMMARY STATISTICS")
print("=" * 70)

max_spread = spread_df['spread_pp'].abs().max() if len(spread_df) > 0 else None

summary = {
    "game1": {
        "matchup": "Illinois vs UConn",
        "winner": g1_winner,
        "pregame_kalshi_favorite": round(ill_pregame_k, 4),
        "pregame_pm_favorite": round(ill_pregame_p, 4) if ill_pregame_p else None,
        "pregame_sportsbook_devigged": round(ill_sb, 4),
        "wang_lambda_kalshi": round(lam_k_g1, 4),
        "wang_lambda_pm": round(lam_p_g1, 4) if lam_p_g1 else None,
        "max_cross_platform_spread_pp": round(max_spread, 2) if max_spread else None,
        "kalshi_records": len(g1k_ill),
        "pm_records": len(g1p),
        "price_discovery_leader": leader
    },
    "game2": {
        "matchup": "Michigan vs Arizona",
        "winner": "Unresolved (data ended pre-tipoff)",
        "pregame_kalshi_favorite": round(mich_pregame_k, 4) if mich_pregame_k else None,
        "pregame_pm_favorite": round(mich_pregame_p, 4) if mich_pregame_p else None,
        "pregame_sportsbook_devigged": round(mich_sb, 4),
        "wang_lambda_kalshi": round(lam_k_g2, 4) if lam_k_g2 else None,
        "wang_lambda_pm": round(lam_p_g2, 4) if lam_p_g2 else None,
        "max_cross_platform_spread_pp": None,
        "kalshi_records": len(g2k_mich),
        "pm_records": len(g2p),
        "price_discovery_leader": "N/A (no in-game data)"
    }
}

print(f"\n{'Metric':<45} {'Game 1 (ILL vs UCONN)':<25} {'Game 2 (MICH vs ARIZ)':<25}")
print("-" * 95)
for key in ['winner', 'pregame_kalshi_favorite', 'pregame_pm_favorite', 'pregame_sportsbook_devigged',
            'wang_lambda_kalshi', 'wang_lambda_pm', 'max_cross_platform_spread_pp',
            'kalshi_records', 'pm_records', 'price_discovery_leader']:
    label = key.replace('_', ' ').title()
    v1 = summary['game1'].get(key, 'N/A')
    v2 = summary['game2'].get(key, 'N/A')
    print(f"{label:<45} {str(v1):<25} {str(v2):<25}")

with open(f"{OUT}/summary_statistics.json", 'w') as f:
    json.dump(summary, f, indent=2)
print(f"\n  Saved summary_statistics.json")


# ══════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print("ANALYSIS COMPLETE")
print("=" * 70)
print(f"\nKey findings:")
print(f"  1. Game 1 Winner: {g1_winner}")
print(f"  2. Pre-game Illinois prob: Kalshi {ill_pregame_k:.1%}, PM {ill_pregame_p:.1%}, Sportsbook {ill_sb:.1%}")
print(f"  3. Wang lam (Kalshi): {lam_k_g1:+.4f} -- {'positive (overpricing)' if lam_k_g1 > 0 else 'negative (underpricing)'}")
if lam_p_g1:
    print(f"  4. Wang lam (PM): {lam_p_g1:+.4f}")
if max_spread:
    print(f"  5. Max cross-platform spread: {max_spread:.1f}pp")
print(f"  6. Price discovery leader: {leader}")
print(f"\nAll outputs saved to: {OUT}/")
