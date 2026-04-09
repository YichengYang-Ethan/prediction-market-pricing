# Replication Guide

Step-by-step instructions to reproduce all results in "Pricing Prediction Markets: Incomplete Markets, Selection Rules, and Risk Premia."

## Prerequisites

- Python 3.10+
- Dependencies: `pip install -r requirements.txt`
- ~500 MB disk space for raw data
- ~30 minutes total runtime on a modern laptop

## Step 0: Data

The analysis-ready datasets are included in `data/`. To reproduce from raw API pulls:

```bash
# Optional: re-fetch raw data from public APIs
python fetch_polymarket.py       # Polymarket Gamma + CLOB APIs
python fetch_kalshi_v2.py        # Kalshi public market data API

# Download HuggingFace datasets for cross-platform validation (Section 6)
pip install datasets
python data/download_huggingface.py
```

The HuggingFace script downloads two public datasets:
- **LightningRodLabs/outcome-rl-test-dataset**: Polymarket 2025 sample (N=985)
- **YuehHanChen/forecasting**: Multi-platform data covering Metaculus, GJOpen, INFER, Manifold (N=4,887)

## Step 1: Core Wang Transform Estimation (Section 4-5)

```bash
python src/models/hierarchical_wang_mle.py
```

**Reproduces**:
- Table 5: One-stage hierarchical Wang MLE (main specification)
- Table 6: Comparison with two-stage OLS
- Tables 7-9: Sub-sample estimates by category, volume tier, duration
- `outputs/tables/hierarchical_wang_main.tex`
- `outputs/tables/hierarchical_wang_results.json`

**Key result**: $\hat{\lambda} = 0.176$ with robust SE = 0.017, $p < 10^{-10}$

## Step 2: Time-Varying Risk Premium (Section 5.5)

```bash
python src/models/stacked_panel_lambda.py
```

**Reproduces**:
- Tables 10-11: Stacked panel parameters and derived quantities
- Figure 3: $f(\tau)$ decay curve (12-day horizon)
- `outputs/tables/stacked_panel_params_12day.tex`
- `outputs/figures/fig_stacked_panel_f_tau_12day.png`

**Key result**: Risk premium half-life = 33-77% of contract lifetime

## Step 3: External Benchmark Validation (Section 5.4)

```bash
python src/identification/external_benchmark.py
```

**Reproduces**:
- Tables 12-13: NBA Elo benchmark results
- `outputs/tables/external_benchmark_results.tex`
- `outputs/figures/fig_lambda_nba_external.png`

**Data**: Requires `data/processed/matched_nba_contracts.csv` and `data/processed/nba_elo_2025_26.csv`

## Step 4: Cross-Platform Validation (Section 6)

```bash
# Kalshi hierarchical MLE
python src/models/kalshi_hierarchical_mle.py

# Kalshi sub-analyses (duration split, contract types)
python src/models/kalshi_subanalysis.py

# Timing harmonization (Appendix A)
python src/models/timing_harmonization.py
```

**Reproduces**:
- Table 14-15: Kalshi pooled and category-level estimates
- Table 16-17: Duration split and contract type sub-analyses
- Tables A3-A4: Polymarket timing ladder and L1/L2 distance metrics
- `outputs/tables/kalshi_hierarchical.tex`
- `outputs/tables/polymarket_timing_ladder.tex`
- `outputs/tables/polymarket_vs_kalshi_timing_distance.tex`

## Step 5: Extensions (Section 7)

```bash
# Errors-in-variables volatility
python src/extensions/eiv_empirical.py

# Hazard rate term structure
python src/extensions/hazard_rate_empirical.py
```

**Reproduces**:
- Tables 19-20: EIV summary statistics and cross-sectional volatility distribution
- Table 21: Hazard rate term structure
- `outputs/figures/fig_eiv_distribution.png`

## Step 6: Robustness (Appendix A)

```bash
python src/robustness/opening_price_measures.py
```

**Reproduces**:
- Table A1: Opening price sensitivity analysis

## Verification

After running all scripts, verify key outputs:

```bash
# Check all tables generated
ls outputs/tables/*.tex | wc -l    # Expected: ~20 .tex files

# Check all figures generated
ls outputs/figures/*.png | wc -l   # Expected: ~7 .png files

# Verify headline number
grep -o "0.176" outputs/tables/hierarchical_wang_results.json
```

## Compilation

To compile the paper PDF from source:

```bash
cd paper/
pandoc research_memo_v3.md -o paper.tex --standalone --pdf-engine=xelatex
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

## Known Issues

- **Apple Silicon + NumPy**: On macOS with Apple Accelerate BLAS, large matrix operations may produce NaN. The code handles this with `_CHUNK = 30000` chunking.
- **Kalshi API rate limits**: The fetcher implements exponential backoff. Full Kalshi pull takes ~15 minutes.
- **LaTeX `%` in tables**: All percentage symbols in generated `.tex` files are properly escaped as `\%`.

## Runtime Estimates

| Script | Approximate Runtime |
|--------|-------------------|
| `hierarchical_wang_mle.py` | 2-3 min |
| `stacked_panel_lambda.py` | 5-8 min |
| `kalshi_hierarchical_mle.py` | 3-5 min |
| `kalshi_subanalysis.py` | 2-3 min |
| `timing_harmonization.py` | 3-5 min |
| `external_benchmark.py` | 1-2 min |
| `eiv_empirical.py` | 5-10 min |
| `hazard_rate_empirical.py` | 1-2 min |
| `opening_price_measures.py` | 1-2 min |
| **Total** | **~25-40 min** |
