#!/usr/bin/env python3
"""
External Benchmark: NBA Sportsbook vs Polymarket
=================================================
Constructs an external physical-probability benchmark for Polymarket NBA
contracts using (a) an Elo rating model built from 2025-26 season results
and (b) live sportsbook moneyline odds from The Odds API.

The Elo model is validated against sportsbook odds for games where both
are available, then applied as the external benchmark for the full sample
of resolved Polymarket NBA contracts.

Author: Yicheng Yang (UIUC)
"""

import os, sys, json, re, time, logging, warnings
import numpy as np
import pandas as pd
from scipy import stats, optimize
from datetime import datetime, timedelta
import urllib.request

np.random.seed(42)
warnings.filterwarnings('ignore')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(ROOT, 'data')
PROC_DIR = os.path.join(ROOT, 'data/processed')
OUT_TABLES = os.path.join(ROOT, 'outputs/tables')
OUT_FIGS = os.path.join(ROOT, 'outputs/figures')
OUT_LOGS = os.path.join(ROOT, 'outputs/logs')
for d in [PROC_DIR, OUT_TABLES, OUT_FIGS, OUT_LOGS]:
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUT_LOGS, 'external_benchmark.log'), mode='w'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

_CHUNK = 30000  # BLAS bug workaround

ODDS_API_KEY = os.environ.get('ODDS_API_KEY', '')  # set via environment variable

# ─── NBA team name alias mapping ──────────────────────────────────────
TEAM_ALIASES = {
    # Polymarket name → canonical
    'lakers': 'Los Angeles Lakers', 'celtics': 'Boston Celtics',
    'warriors': 'Golden State Warriors', '76ers': 'Philadelphia 76ers',
    'sixers': 'Philadelphia 76ers', 'nets': 'Brooklyn Nets',
    'knicks': 'New York Knicks', 'heat': 'Miami Heat',
    'bucks': 'Milwaukee Bucks', 'nuggets': 'Denver Nuggets',
    'suns': 'Phoenix Suns', 'mavericks': 'Dallas Mavericks',
    'mavs': 'Dallas Mavericks', 'clippers': 'LA Clippers',
    'rockets': 'Houston Rockets', 'bulls': 'Chicago Bulls',
    'cavaliers': 'Cleveland Cavaliers', 'cavs': 'Cleveland Cavaliers',
    'hawks': 'Atlanta Hawks', 'pistons': 'Detroit Pistons',
    'grizzlies': 'Memphis Grizzlies', 'timberwolves': 'Minnesota Timberwolves',
    'wolves': 'Minnesota Timberwolves', 'pelicans': 'New Orleans Pelicans',
    'thunder': 'Oklahoma City Thunder', 'magic': 'Orlando Magic',
    'pacers': 'Indiana Pacers', 'blazers': 'Portland Trail Blazers',
    'trail blazers': 'Portland Trail Blazers', 'kings': 'Sacramento Kings',
    'raptors': 'Toronto Raptors', 'spurs': 'San Antonio Spurs',
    'jazz': 'Utah Jazz', 'wizards': 'Washington Wizards',
    'hornets': 'Charlotte Hornets',
    # Full names
    'los angeles lakers': 'Los Angeles Lakers',
    'boston celtics': 'Boston Celtics',
    'golden state warriors': 'Golden State Warriors',
    'philadelphia 76ers': 'Philadelphia 76ers',
    'brooklyn nets': 'Brooklyn Nets',
    'new york knicks': 'New York Knicks',
    'miami heat': 'Miami Heat',
    'milwaukee bucks': 'Milwaukee Bucks',
    'denver nuggets': 'Denver Nuggets',
    'phoenix suns': 'Phoenix Suns',
    'dallas mavericks': 'Dallas Mavericks',
    'la clippers': 'LA Clippers',
    'houston rockets': 'Houston Rockets',
    'chicago bulls': 'Chicago Bulls',
    'cleveland cavaliers': 'Cleveland Cavaliers',
    'atlanta hawks': 'Atlanta Hawks',
    'detroit pistons': 'Detroit Pistons',
    'memphis grizzlies': 'Memphis Grizzlies',
    'minnesota timberwolves': 'Minnesota Timberwolves',
    'new orleans pelicans': 'New Orleans Pelicans',
    'oklahoma city thunder': 'Oklahoma City Thunder',
    'orlando magic': 'Orlando Magic',
    'indiana pacers': 'Indiana Pacers',
    'portland trail blazers': 'Portland Trail Blazers',
    'sacramento kings': 'Sacramento Kings',
    'toronto raptors': 'Toronto Raptors',
    'san antonio spurs': 'San Antonio Spurs',
    'utah jazz': 'Utah Jazz',
    'washington wizards': 'Washington Wizards',
    'charlotte hornets': 'Charlotte Hornets',
}

def normalize_team(name):
    """Map any team name variant to canonical full name."""
    key = name.strip().lower()
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    # Try last word (e.g. "Trail Blazers" → look up "blazers")
    last = key.split()[-1]
    if last in TEAM_ALIASES:
        return TEAM_ALIASES[last]
    return None


# ═══════════════════════════════════════════════════════════════════════
#  STEP 1a: Fetch current sportsbook odds from The Odds API
# ═══════════════════════════════════════════════════════════════════════
def fetch_odds_api():
    """Fetch current NBA moneyline odds (single API call, 1 credit)."""
    url = (f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds/'
           f'?apiKey={ODDS_API_KEY}&regions=us&markets=h2h&oddsFormat=american')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            remaining = resp.headers.get('x-requests-remaining', '?')
            log.info(f"Odds API: {len(data)} games, credits remaining: {remaining}")
            return data
    except Exception as e:
        log.warning(f"Odds API failed: {e}")
        return []


def american_to_prob(odds):
    """Convert American moneyline odds to implied probability."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def parse_odds_api(games):
    """Parse Odds API response into a DataFrame with consensus probabilities."""
    rows = []
    for g in games:
        home = g['home_team']
        away = g['away_team']
        commence = g['commence_time']

        # Average moneyline across bookmakers
        home_probs, away_probs = [], []
        for bk in g.get('bookmakers', []):
            for mkt in bk.get('markets', []):
                if mkt['key'] != 'h2h':
                    continue
                for o in mkt.get('outcomes', []):
                    p = american_to_prob(o['price'])
                    if o['name'] == home:
                        home_probs.append(p)
                    elif o['name'] == away:
                        away_probs.append(p)

        if not home_probs or not away_probs:
            continue

        # Consensus = mean across books, then remove overround
        raw_home = np.mean(home_probs)
        raw_away = np.mean(away_probs)
        total = raw_home + raw_away
        rows.append({
            'home_team': home,
            'away_team': away,
            'commence_time': commence,
            'p_home_book': raw_home / total,
            'p_away_book': raw_away / total,
            'n_books': len(home_probs),
            'overround': total,
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
#  STEP 1b: Build Elo ratings from 2025-26 NBA season
# ═══════════════════════════════════════════════════════════════════════
def build_elo_ratings():
    """Build Elo ratings from nba_api game data."""
    from nba_api.stats.endpoints import leaguegamefinder
    time.sleep(1)
    gf = leaguegamefinder.LeagueGameFinder(
        season_nullable='2025-26', league_id_nullable='00', timeout=30)
    games_raw = gf.get_data_frames()[0]

    # Each game appears twice (one row per team). Deduplicate.
    games_raw['GAME_DATE'] = pd.to_datetime(games_raw['GAME_DATE'])
    games_raw = games_raw.sort_values(['GAME_DATE', 'GAME_ID'])

    # Parse home/away from MATCHUP column ("BOS vs. NYK" = BOS home, "NYK @ BOS" = NYK away)
    games = []
    seen = set()
    for _, row in games_raw.iterrows():
        gid = row['GAME_ID']
        if gid in seen:
            continue
        seen.add(gid)
        # Find both rows for this game
        pair = games_raw[games_raw['GAME_ID'] == gid]
        if len(pair) != 2:
            continue
        home_row = pair[pair['MATCHUP'].str.contains('vs.', na=False)]
        away_row = pair[pair['MATCHUP'].str.contains('@', na=False)]
        if len(home_row) != 1 or len(away_row) != 1:
            continue
        home_row = home_row.iloc[0]
        away_row = away_row.iloc[0]
        games.append({
            'game_id': gid,
            'date': home_row['GAME_DATE'],
            'home_team': home_row['TEAM_NAME'],
            'away_team': away_row['TEAM_NAME'],
            'home_pts': int(home_row['PTS']),
            'away_pts': int(away_row['PTS']),
            'home_won': int(home_row['WL'] == 'W'),
        })

    gdf = pd.DataFrame(games).sort_values('date').reset_index(drop=True)

    # Filter out preseason / All-Star game teams
    NBA_TEAMS = {
        'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
        'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
        'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
        'LA Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies', 'Miami Heat',
        'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans',
        'New York Knicks', 'Oklahoma City Thunder', 'Orlando Magic',
        'Philadelphia 76ers', 'Phoenix Suns', 'Portland Trail Blazers',
        'Sacramento Kings', 'San Antonio Spurs', 'Toronto Raptors', 'Utah Jazz',
        'Washington Wizards',
    }
    before_filter = len(gdf)
    gdf = gdf[gdf['home_team'].isin(NBA_TEAMS) & gdf['away_team'].isin(NBA_TEAMS)].reset_index(drop=True)
    log.info(f"Filtered out {before_filter - len(gdf)} non-NBA games (All-Star, preseason)")
    log.info(f"NBA games loaded: {len(gdf)} (season 2025-26)")
    log.info(f"Date range: {gdf['date'].min().date()} to {gdf['date'].max().date()}")

    # ── Elo computation ──
    # Modern NBA HCA ~56% for equal teams → ~42 Elo points
    # K=28 balances responsiveness vs stability (cf. FiveThirtyEight NBA Elo)
    K = 28
    HCA = 42        # home court advantage in Elo points (~56% baseline)
    INIT_ELO = 1500

    elo = {}
    elo_history = []  # (game_id, date, home, away, elo_home_pre, elo_away_pre, p_home_elo, home_won)

    for _, g in gdf.iterrows():
        h, a = g['home_team'], g['away_team']
        if h not in elo:
            elo[h] = INIT_ELO
        if a not in elo:
            elo[a] = INIT_ELO

        # Pre-game Elo
        elo_h = elo[h] + HCA
        elo_a = elo[a]

        # Win probability
        p_home = 1.0 / (1.0 + 10 ** ((elo_a - elo_h) / 400))

        elo_history.append({
            'game_id': g['game_id'],
            'date': g['date'],
            'home_team': h,
            'away_team': a,
            'elo_home_pre': elo[h],
            'elo_away_pre': elo[a],
            'p_home_elo': p_home,
            'home_won': g['home_won'],
        })

        # Update Elo
        actual = g['home_won']
        elo[h] += K * (actual - p_home)
        elo[a] += K * ((1 - actual) - (1 - p_home))

    edf = pd.DataFrame(elo_history)

    # Elo calibration check
    edf['elo_bin'] = pd.cut(edf['p_home_elo'], bins=10)
    cal = edf.groupby('elo_bin', observed=True).agg(
        pred=('p_home_elo', 'mean'), actual=('home_won', 'mean'), n=('home_won', 'count'))
    log.info("Elo calibration (binned):")
    for _, r in cal.iterrows():
        log.info(f"  pred={r['pred']:.3f}  actual={r['actual']:.3f}  N={r['n']}")

    brier = np.mean((edf['p_home_elo'] - edf['home_won'])**2)
    log.info(f"Elo Brier score: {brier:.4f}")

    return gdf, edf


# ═══════════════════════════════════════════════════════════════════════
#  STEP 2: Match Polymarket NBA contracts to Elo benchmark
# ═══════════════════════════════════════════════════════════════════════
def match_polymarket_to_elo(edf):
    """Match Polymarket NBA contracts to Elo-based win probabilities."""
    df = pd.read_parquet(os.path.join(DATA_DIR, 'combined_analysis_dataset.parquet'))
    markets = pd.read_parquet(os.path.join(DATA_DIR, 'combined_markets.parquet'))
    q_map = dict(zip(markets['id'].astype(str), markets['question'].fillna('')))
    spread_map = dict(zip(markets['id'].astype(str), markets['spread']))
    df['question'] = df['id'].astype(str).map(q_map)
    df['spread'] = df['id'].astype(str).map(spread_map)

    # Filter NBA game contracts
    nba_team_keywords = list(set(TEAM_ALIASES.keys()))

    def is_nba_vs(q):
        q_lower = q.lower()
        if ' vs' not in q_lower:
            return False
        return any(t in q_lower for t in nba_team_keywords if len(t) > 3)

    nba = df[df['question'].fillna('').apply(is_nba_vs)].copy()
    log.info(f"Polymarket NBA 'vs' contracts: {len(nba)}")

    # Parse team names from title
    def parse_teams(q):
        m = re.match(r'^(.+?)\s+vs\.?\s+(.+?)$', q.strip(), re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None, None

    nba['team1_raw'], nba['team2_raw'] = zip(*nba['question'].apply(parse_teams))
    nba['team1'] = nba['team1_raw'].apply(lambda x: normalize_team(x) if x else None)
    nba['team2'] = nba['team2_raw'].apply(lambda x: normalize_team(x) if x else None)

    # Drop contracts where team normalization failed
    before = len(nba)
    nba = nba.dropna(subset=['team1', 'team2'])
    log.info(f"After team normalization: {len(nba)} ({before - len(nba)} dropped)")

    # Get game dates from Polymarket timestamps
    nba['pm_date'] = pd.to_datetime(nba['first_timestamp'], unit='s').dt.date

    # Build lookup from Elo data: (team_set, date) → elo row
    edf['date_key'] = edf['date'].dt.date
    edf['team_set'] = edf.apply(lambda r: frozenset([r['home_team'], r['away_team']]), axis=1)

    # For matching: each Polymarket contract opened ~1-3 days before the game.
    # The contract's first_timestamp is when it was created, and the game
    # typically happens during the contract's lifetime.
    # Strategy: match team pair to the closest Elo game within ±3 days of pm_date
    matched = []
    unmatched = []

    for _, row in nba.iterrows():
        pm_teams = frozenset([row['team1'], row['team2']])
        pm_date = row['pm_date']

        # Find Elo games with this team pair within ±3 days
        candidates = edf[
            (edf['team_set'] == pm_teams) &
            (edf['date_key'] >= pm_date - timedelta(days=1)) &
            (edf['date_key'] <= pm_date + timedelta(days=5))
        ]

        if len(candidates) == 0:
            unmatched.append(row)
            continue

        # Take the closest game
        candidates = candidates.copy()
        candidates['date_diff'] = candidates['date_key'].apply(
            lambda d: abs((d - pm_date).days))
        best = candidates.sort_values('date_diff').iloc[0]

        # Determine which team the Polymarket YES contract refers to
        # In "Team1 vs. Team2", Team1 is typically the team whose win = YES
        # (Polymarket convention: first-named team)
        pm_yes_team = row['team1']

        if pm_yes_team == best['home_team']:
            p_star_elo = best['p_home_elo']
        else:
            p_star_elo = 1 - best['p_home_elo']

        matched.append({
            'id': row['id'],
            'question': row['question'],
            'team1': row['team1'],
            'team2': row['team2'],
            'pm_date': pm_date,
            'game_date': best['date_key'],
            'home_team': best['home_team'],
            'away_team': best['away_team'],
            'p_open': row['p_open'],
            'p_star_elo': p_star_elo,
            'resolved_yes': row['resolved_yes'],
            'volume': row['volume'],
            'spread': row.get('spread', np.nan),
            'duration_hours': row['duration_hours'],
            'elo_home_pre': best['elo_home_pre'],
            'elo_away_pre': best['elo_away_pre'],
        })

    mdf = pd.DataFrame(matched)
    log.info(f"Matched: {len(mdf)}, Unmatched: {len(unmatched)}")

    return mdf, unmatched


# ═══════════════════════════════════════════════════════════════════════
#  STEP 3: Compute contract-level λ
# ═══════════════════════════════════════════════════════════════════════
def compute_lambda(mdf):
    """Compute contract-level λ_i = Φ⁻¹(p_polymarket) - Φ⁻¹(p*_elo)."""
    # Clip to avoid infinities
    mdf = mdf.copy()
    mdf['p_open_clip'] = np.clip(mdf['p_open'], 0.01, 0.99)
    mdf['p_star_clip'] = np.clip(mdf['p_star_elo'], 0.01, 0.99)

    mdf['z_pm'] = stats.norm.ppf(mdf['p_open_clip'])
    mdf['z_star'] = stats.norm.ppf(mdf['p_star_clip'])
    mdf['lambda_i'] = mdf['z_pm'] - mdf['z_star']

    return mdf


# ═══════════════════════════════════════════════════════════════════════
#  STEP 4: Analysis
# ═══════════════════════════════════════════════════════════════════════
def run_analysis(mdf):
    """Summary stats, regression, plots."""
    log.info("")
    log.info("=" * 60)
    log.info("EXTERNAL BENCHMARK ANALYSIS")
    log.info("=" * 60)

    # ── 4a. Summary statistics ──
    lam = mdf['lambda_i']
    log.info(f"N matched contracts: {len(mdf)}")
    log.info(f"λ_i: mean={lam.mean():.4f}, median={lam.median():.4f}, "
             f"std={lam.std():.4f}")
    log.info(f"  Q25={lam.quantile(0.25):.4f}, Q75={lam.quantile(0.75):.4f}")

    # t-test against 0
    t_stat, t_pval = stats.ttest_1samp(lam, 0)
    log.info(f"t-test (H₀: λ=0): t={t_stat:.3f}, p={t_pval:.4e}")

    # Wilcoxon signed-rank (non-parametric)
    w_stat, w_pval = stats.wilcoxon(lam)
    log.info(f"Wilcoxon: W={w_stat:.0f}, p={w_pval:.4e}")

    # ── 4b. Regression ──
    log.info("")
    log.info("OLS: λ_i = α + β₁·ln(Volume) + β₂·|p-0.5| + ε")

    mdf_reg = mdf[mdf['volume'] > 0].copy()
    mdf_reg['ln_vol'] = np.log(mdf_reg['volume'])
    mdf_reg['extremity'] = np.abs(mdf_reg['p_open'] - 0.5)

    # Include spread only if it has meaningful variation
    has_spread = (mdf_reg['spread'].notna().sum() > len(mdf_reg) * 0.5 and
                  mdf_reg['spread'].dropna().std() > 0.001)

    X_cols = ['ln_vol', 'extremity']
    if has_spread:
        mdf_reg['spread_clean'] = mdf_reg['spread'].fillna(mdf_reg['spread'].median())
        X_cols.append('spread_clean')

    X = mdf_reg[X_cols].values
    X = np.column_stack([np.ones(len(X)), X])
    y = mdf_reg['lambda_i'].values

    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        resid = y - X @ beta
        n, k = X.shape
        sigma2 = np.sum(resid**2) / (n - k)
        var_beta = sigma2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(var_beta))
        t_vals = beta / se
        p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), df=n-k))
        r2 = 1 - np.sum(resid**2) / np.sum((y - y.mean())**2)

        labels = ['Constant', 'ln(Volume)', '|p - 0.5|']
        if has_spread:
            labels.append('Spread')
        log.info(f"  R² = {r2:.4f}, N = {n}")
        for i, lab in enumerate(labels):
            sig = '***' if p_vals[i] < 0.001 else '**' if p_vals[i] < 0.01 else '*' if p_vals[i] < 0.05 else ''
            log.info(f"  {lab:<15} β={beta[i]:>8.4f}  SE={se[i]:.4f}  t={t_vals[i]:>6.2f}  p={p_vals[i]:.4f}{sig}")

        reg_results = {
            'labels': labels, 'beta': beta.tolist(), 'se': se.tolist(),
            't': t_vals.tolist(), 'p': p_vals.tolist(), 'r2': r2, 'n': n
        }
    except Exception as e:
        log.warning(f"Regression failed: {e}")
        reg_results = None
        beta = None

    # ── 4c. Comparison with Table 14 (Sports category λ̂ = 0.070) ──
    log.info("")
    log.info("Comparison with aggregate Sports λ̂:")
    log.info(f"  Aggregate (Table 14, probit MLE): λ̂ = 0.070 (SE=0.042, p=0.092)")
    log.info(f"  External benchmark mean:          λ̄ = {lam.mean():.4f} (SE={lam.std()/np.sqrt(len(lam)):.4f})")

    # ── 4d. Plots ──
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Panel (a): λ_i vs ln(Volume)
    ax = axes[0]
    mask = mdf_reg['volume'] > 0
    ax.scatter(mdf_reg['ln_vol'], mdf_reg['lambda_i'], alpha=0.3, s=12, color='steelblue')
    if beta is not None:
        x_line = np.linspace(mdf_reg['ln_vol'].min(), mdf_reg['ln_vol'].max(), 100)
        y_line = beta[0] + beta[1] * x_line
        ax.plot(x_line, y_line, 'r--', linewidth=1.5,
                label=f'OLS: slope={beta[1]:.4f}')
        ax.legend(fontsize=9)
    ax.axhline(0, color='black', linewidth=0.5, linestyle='-')
    ax.axhline(lam.mean(), color='red', linewidth=0.8, linestyle=':',
               label=f'mean={lam.mean():.3f}')
    ax.set_xlabel('$\\ln(\\text{Volume})$', fontsize=11)
    ax.set_ylabel('Contract-level $\\hat{\\lambda}_i$', fontsize=11)
    rho, rho_p = stats.spearmanr(mdf_reg['ln_vol'], mdf_reg['lambda_i'])
    ax.set_title(f'(a) $\\hat{{\\lambda}}_i$ vs Volume (Spearman $\\rho={rho:.3f}$, $p={rho_p:.3f}$)',
                 fontsize=11)

    # Panel (b): Histogram of λ_i
    ax = axes[1]
    ax.hist(lam, bins=40, color='steelblue', alpha=0.7, edgecolor='white', density=True)
    ax.axvline(0, color='black', linewidth=1, linestyle='-')
    ax.axvline(lam.mean(), color='red', linewidth=1.5, linestyle='--',
               label=f'mean = {lam.mean():.3f}')
    ax.axvline(lam.median(), color='orange', linewidth=1.5, linestyle=':',
               label=f'median = {lam.median():.3f}')
    # Normal overlay
    x_norm = np.linspace(lam.min(), lam.max(), 200)
    ax.plot(x_norm, stats.norm.pdf(x_norm, lam.mean(), lam.std()),
            'k-', linewidth=1, alpha=0.5)
    ax.set_xlabel('Contract-level $\\hat{\\lambda}_i$', fontsize=11)
    ax.set_ylabel('Density', fontsize=11)
    ax.set_title(f'(b) Distribution of $\\hat{{\\lambda}}_i$ ($N={len(lam)}$)', fontsize=11)
    ax.legend(fontsize=9)

    plt.tight_layout()
    fig_path = os.path.join(OUT_FIGS, 'fig_lambda_nba_external.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    log.info(f"Saved: {fig_path}")

    # ── 4e. LaTeX table ──
    lines = [
        r'\begin{table}[H]',
        r'\centering',
        r'\small',
        r'\caption{External benchmark: contract-level $\hat{\lambda}_i$ for NBA game contracts. '
        r'Physical probability $\hat{p}^*$ estimated from pre-game Elo ratings '
        r'(2025--26 season, $K=28$, home-court advantage $= 42$ Elo points). '
        r'$\hat{\lambda}_i = \Phi^{-1}(p_i^{\text{Polymarket}}) - \Phi^{-1}(\hat{p}_i^{\text{Elo}})$.}',
        r'\label{tab:external_benchmark}',
    ]

    # Panel A: summary stats
    lines += [
        r'\vspace{0.3em}',
        r'\textbf{Panel A: Summary Statistics}\\[3pt]',
        r'\begin{tabular}{lr}',
        r'\toprule',
        r'Statistic & Value \\',
        r'\midrule',
        f'$N$ matched contracts & {len(mdf)} \\\\',
        f'Mean $\\hat{{\\lambda}}_i$ & {lam.mean():.4f} \\\\',
        f'Median $\\hat{{\\lambda}}_i$ & {lam.median():.4f} \\\\',
        f'Std.~dev. & {lam.std():.4f} \\\\',
        f'IQR & [{lam.quantile(0.25):.4f}, {lam.quantile(0.75):.4f}] \\\\',
        f'$t$-test ($H_0\\colon \\lambda = 0$) & $t = {t_stat:.2f}$, $p = {t_pval:.4f}$ \\\\',
        f'Wilcoxon signed-rank & $p = {w_pval:.4f}$ \\\\',
        r'\midrule',
        f'Aggregate Sports $\\hat{{\\lambda}}$ (Table 14) & 0.070 (SE $= 0.042$) \\\\',
        r'\bottomrule',
        r'\end{tabular}',
    ]

    # Panel B: regression
    if reg_results is not None:
        lines += [
            r'',
            r'\vspace{0.5em}',
            r'\textbf{Panel B: OLS Regression} $\hat{\lambda}_i = \alpha + \beta_1 \ln(\text{Vol}_i) '
            r'+ \beta_2 |p_i - 0.5| + \varepsilon_i$\\[3pt]',
            r'\begin{tabular}{lrrrr}',
            r'\toprule',
            r'Variable & Coef. & SE & $t$ & $p$ \\',
            r'\midrule',
        ]
        for i, lab in enumerate(reg_results['labels']):
            sig = '***' if reg_results['p'][i] < 0.001 else '**' if reg_results['p'][i] < 0.01 else '*' if reg_results['p'][i] < 0.05 else ''
            tex_lab = lab.replace('ln(Volume)', r'$\ln(\text{Volume})$')
            tex_lab = tex_lab.replace('|p - 0.5|', r'$|p - 0.5|$')
            lines.append(
                f'{tex_lab} & {reg_results["beta"][i]:.4f}{sig} & '
                f'{reg_results["se"][i]:.4f} & {reg_results["t"][i]:.2f} & '
                f'{reg_results["p"][i]:.4f} \\\\'
            )
        lines += [
            r'\midrule',
            f'$R^2$ & \\multicolumn{{4}}{{r}}{{{reg_results["r2"]:.4f}}} \\\\',
            f'$N$ & \\multicolumn{{4}}{{r}}{{{reg_results["n"]}}} \\\\',
            r'\bottomrule',
            r'\end{tabular}',
        ]

    lines += [r'\end{table}']
    tex = '\n'.join(lines)
    tex_path = os.path.join(OUT_TABLES, 'external_benchmark_results.tex')
    with open(tex_path, 'w') as f:
        f.write(tex)
    log.info(f"Saved: {tex_path}")

    return {
        'n_matched': len(mdf),
        'lambda_mean': float(lam.mean()),
        'lambda_median': float(lam.median()),
        'lambda_std': float(lam.std()),
        't_stat': float(t_stat),
        't_pval': float(t_pval),
        'w_pval': float(w_pval),
        'regression': reg_results,
    }


# ═══════════════════════════════════════════════════════════════════════
#  STEP 5: Validate Elo against sportsbook odds
# ═══════════════════════════════════════════════════════════════════════
def validate_elo_vs_sportsbook(edf, odds_df):
    """Compare Elo predictions to sportsbook odds for games where both exist."""
    if odds_df is None or len(odds_df) == 0:
        log.info("No sportsbook odds available for Elo validation.")
        return

    log.info("")
    log.info("=" * 60)
    log.info("ELO vs SPORTSBOOK VALIDATION")
    log.info("=" * 60)

    # Match by team pair
    matched = []
    for _, orow in odds_df.iterrows():
        home_canon = normalize_team(orow['home_team'])
        away_canon = normalize_team(orow['away_team'])
        if home_canon is None or away_canon is None:
            continue

        # Find in Elo (latest entry for this team pair)
        candidates = edf[
            (edf['home_team'] == home_canon) & (edf['away_team'] == away_canon)
        ]
        if len(candidates) == 0:
            # Try reversed
            candidates = edf[
                (edf['home_team'] == away_canon) & (edf['away_team'] == home_canon)
            ]
            if len(candidates) == 0:
                continue
            # Use latest Elo state to predict
            last = candidates.iloc[-1]
            p_elo = 1 - last['p_home_elo']  # Elo for original away team as "home"
        else:
            last = candidates.iloc[-1]
            p_elo = last['p_home_elo']

        matched.append({
            'home': home_canon,
            'away': away_canon,
            'p_home_book': orow['p_home_book'],
            'p_home_elo': p_elo,
        })

    if not matched:
        log.info("No overlapping games for validation.")
        return

    vdf = pd.DataFrame(matched)
    corr = vdf['p_home_book'].corr(vdf['p_home_elo'])
    mae = np.mean(np.abs(vdf['p_home_book'] - vdf['p_home_elo']))
    rmse = np.sqrt(np.mean((vdf['p_home_book'] - vdf['p_home_elo'])**2))

    log.info(f"Matched games: {len(vdf)}")
    log.info(f"Correlation (Elo vs Book): {corr:.3f}")
    log.info(f"MAE: {mae:.4f}")
    log.info(f"RMSE: {rmse:.4f}")

    for _, r in vdf.iterrows():
        log.info(f"  {r['away']:<30} @ {r['home']:<30} "
                 f"book={r['p_home_book']:.3f}  elo={r['p_home_elo']:.3f}  "
                 f"diff={r['p_home_book']-r['p_home_elo']:+.3f}")

    return vdf


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    log.info("=" * 70)
    log.info("EXTERNAL BENCHMARK: NBA SPORTSBOOK vs POLYMARKET")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # Step 1a: Fetch sportsbook odds (1 API call)
    log.info("")
    log.info("─── Step 1a: Sportsbook odds (Odds API) ───")
    odds_raw = fetch_odds_api()
    odds_df = parse_odds_api(odds_raw) if odds_raw else None
    if odds_df is not None and len(odds_df) > 0:
        log.info(f"Parsed {len(odds_df)} games with consensus moneyline odds")
        odds_df.to_csv(os.path.join(PROC_DIR, 'odds_api_nba_current.csv'), index=False)
    else:
        log.info("No sportsbook odds available")

    # Step 1b: Build Elo ratings
    log.info("")
    log.info("─── Step 1b: Elo model ───")
    gdf, edf = build_elo_ratings()
    edf.to_csv(os.path.join(PROC_DIR, 'nba_elo_2025_26.csv'), index=False)
    log.info(f"Elo ratings built for {edf['home_team'].nunique()} teams, {len(edf)} games")

    # Step 1c: Validate Elo against sportsbook
    log.info("")
    log.info("─── Step 1c: Elo validation ───")
    validate_elo_vs_sportsbook(edf, odds_df)

    # Step 2: Match Polymarket contracts
    log.info("")
    log.info("─── Step 2: Matching ───")
    mdf, unmatched = match_polymarket_to_elo(edf)

    if len(mdf) < 30:
        log.warning(f"Only {len(mdf)} matches — below minimum threshold of 30")
        log.warning("Consider expanding matching criteria or using different data")
        # Still proceed but flag it

    mdf.to_csv(os.path.join(PROC_DIR, 'matched_nba_contracts.csv'), index=False)

    # Step 3: Compute λ_i
    log.info("")
    log.info("─── Step 3: Contract-level λ ───")
    mdf = compute_lambda(mdf)

    # Step 4: Analysis
    results = run_analysis(mdf)

    # Save full results JSON
    json_path = os.path.join(OUT_TABLES, 'external_benchmark_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    log.info(f"Saved: {json_path}")

    log.info("")
    log.info("Done.")
    return results


if __name__ == '__main__':
    main()
