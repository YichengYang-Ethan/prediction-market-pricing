# Data

## Overview

All data used in this paper comes from public APIs. No proprietary or restricted-access data is required.

## Data Sources

| Source | Contracts | Period | API |
|--------|-----------|--------|-----|
| Polymarket | ~14,400 | 2020-2026 | [Gamma API](https://gamma-api.polymarket.com), [CLOB API](https://clob.polymarket.com) |
| Kalshi | ~200,000 | 2021-2026 | [Kalshi API](https://trading-api.kalshi.com/trade-api/v2) |
| Metaculus | ~50,000 | 2015-2026 | [Metaculus API](https://www.metaculus.com/api2/) |
| Good Judgment Open | ~1,800 | 2015-2026 | Public question pages |
| INFER | ~700 | 2020-2026 | Public question pages |
| Manifold | ~25,000 | 2022-2026 | [Manifold API](https://api.manifold.markets/v0) |
| FiveThirtyEight | NBA Elo | 2025-26 season | Public CSV |
| The Odds API | NBA lines | 2025-26 season | [API](https://the-odds-api.com) (free tier) |

## Directory Structure

```
data/
├── raw/                    # Raw API responses (large, not in git)
│   ├── .gitkeep
│   ├── combined_markets.parquet
│   ├── combined_histories.json
│   ├── kalshi_markets_fast.json
│   └── ...
└── processed/              # Analysis-ready files (in git)
    ├── matched_nba_contracts.csv
    ├── nba_elo_2025_26.csv
    └── odds_api_nba_current.csv
```

## Collecting Raw Data

To reproduce from scratch, run the data collection scripts:

```bash
# Polymarket (public, no auth required)
python fetch_polymarket.py

# Kalshi (public, no auth required for market data)
python fetch_kalshi_v2.py
```

These scripts write to `data/raw/`. The analysis scripts in `src/` read from `data/` and auto-detect whether to use raw or processed files.

## File Sizes

| File | Size | Description |
|------|------|-------------|
| `combined_markets.parquet` | ~50 MB | All Polymarket contract metadata |
| `kalshi_analysis_dataset.parquet` | ~200 MB | Kalshi contracts with price histories |
| `processed/*.csv` | ~2 MB | NBA benchmark data |

See [`data_dictionary.md`](../data_dictionary.md) for variable definitions.
