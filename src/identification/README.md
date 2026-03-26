# identification/

External benchmark validation for model identification.

## Scripts

### `external_benchmark.py` -- NBA Elo Benchmark

**Paper**: Section 5.4, Tables 12-13

Validates the Wang transform framework using NBA game outcomes where independent physical probabilities are available from Elo ratings (FiveThirtyEight). Compares model-implied $p^*$ against Elo-implied probabilities.

**Data requirements**:
- `data/processed/matched_nba_contracts.csv` -- Polymarket NBA contracts matched to Elo
- `data/processed/nba_elo_2025_26.csv` -- FiveThirtyEight Elo ratings
- `data/processed/odds_api_nba_current.csv` -- Market implied odds

**Outputs**: `external_benchmark_results.tex`, `external_benchmark_results.json`, `fig_lambda_nba_external.png`
