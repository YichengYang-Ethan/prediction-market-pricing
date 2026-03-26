# Data Dictionary

Variable definitions for all datasets used in this paper.

## Contract-Level Dataset (`combined_markets.parquet`, `kalshi_analysis_dataset.parquet`)

### Identifiers

| Variable | Type | Description |
|----------|------|-------------|
| `condition_id` / `ticker` | string | Unique contract identifier (Polymarket / Kalshi) |
| `question` / `title` | string | Contract description text |
| `slug` | string | URL-friendly contract identifier |

### Outcome

| Variable | Type | Description |
|----------|------|-------------|
| `outcome` | int | Realized outcome: 1 = Yes, 0 = No |
| `resolved` | bool | Whether the contract has settled |

### Pricing Variables

| Variable | Type | Description |
|----------|------|-------------|
| `p_mkt` | float | Market price at measurement time, $\in (0,1)$ |
| `p_open` | float | Opening price (first traded price) |
| `p_mid` | float | Mid-life price (at 50% of contract lifetime) |
| `p_20pct` | float | Price at 20% of contract lifetime |
| `p_80pct` | float | Price at 80% of contract lifetime |
| `p_close` | float | Final settlement price (near 0 or 1) |

### Covariates ($X_i$ vector)

| Variable | Type | Description | Paper Notation |
|----------|------|-------------|----------------|
| `sigma` | float | Event volatility proxy: rolling SD of hourly log-odds increments (annualized) | $\sigma_i$ |
| `duration_days` | float | Contract lifetime in days (creation to resolution) | $d_i$ |
| `extremity` | float | Price extremity: $\|p^{\text{mkt}} - 0.5\|$ | $\text{ext}_i$ |
| `log_volume` | float | Log total trading volume (USD) | $\ln V_i$ |

### Metadata

| Variable | Type | Description |
|----------|------|-------------|
| `category` | string | Contract category (Sports, Politics, Crypto, Tech, Other) |
| `platform` | string | Source platform (Polymarket, Kalshi, Metaculus, GJOpen, INFER, Manifold) |
| `created_at` | datetime | Contract creation timestamp |
| `resolved_at` | datetime | Contract resolution timestamp |
| `volume` | float | Total trading volume in USD |
| `volume_tier` | string | Volume bucket: Low (<$500), Med ($500-2K), High ($2K-10K), Very High (>$10K) |

## Price History (`combined_histories.json`)

JSON structure: `{condition_id: [{timestamp, price, volume}, ...]}` for hourly OHLCV data.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | int | Unix epoch seconds |
| `price` | float | Midpoint or last trade price at hour close |
| `volume` | float | Hourly trading volume (USD) |

## Stacked Panel Dataset (constructed by `stacked_panel_lambda.py`)

| Variable | Type | Description |
|----------|------|-------------|
| `tau` | float | Normalized time-to-expiry $\tau \in [0,1]$, where 1 = contract opening, 0 = resolution |
| `z_mkt` | float | Probit-transformed market price: $\Phi^{-1}(p^{\text{mkt}})$ |
| `y` | int | Realized outcome |
| `lambda_hat` | float | Estimated risk loading at this $\tau$ |

## NBA Benchmark Data (`data/processed/`)

### `matched_nba_contracts.csv`

| Variable | Type | Description |
|----------|------|-------------|
| `condition_id` | string | Polymarket contract ID |
| `home_team` / `away_team` | string | NBA team names |
| `p_mkt` | float | Polymarket price at game start |
| `p_elo` | float | Elo-implied win probability |
| `p_odds` | float | Sportsbook-implied probability (vig-adjusted) |
| `outcome` | int | Game outcome |

### `nba_elo_2025_26.csv`

| Variable | Type | Description |
|----------|------|-------------|
| `team` | string | NBA team name |
| `elo_rating` | float | FiveThirtyEight Elo rating |
| `date` | date | Rating date |

### `odds_api_nba_current.csv`

| Variable | Type | Description |
|----------|------|-------------|
| `game_id` | string | Game identifier |
| `home_odds` / `away_odds` | float | Decimal odds from sportsbooks |
| `implied_prob_home` | float | Vig-adjusted implied probability |

## Derived Variables (computed in estimation)

| Variable | Formula | Description |
|----------|---------|-------------|
| `z_i` | $\Phi^{-1}(p_i^{\text{mkt}})$ | Probit-transformed price (known offset in MLE) |
| `lambda_i` | $z_i - \Phi^{-1}(p_i^*)$ | Contract-level risk loading |
| `f(tau)` | Estimated from stacked panel | Time-varying premium decay function |

## Estimation Outputs (`outputs/tables/*.json`)

All JSON result files follow a common structure:

```json
{
  "model": "model_name",
  "n_obs": 14406,
  "coefficients": {
    "beta_0": {"estimate": 0.176, "se": 0.017, "p_value": 1e-10},
    "beta_vol": {"estimate": ..., "se": ..., "p_value": ...},
    ...
  },
  "log_likelihood": -9876.54,
  "aic": 19761.08,
  "bic": 19791.22
}
```
