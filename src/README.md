# Source Code

All estimation and analysis scripts. Each module is self-contained: it reads from `data/`, writes results to `outputs/tables/` (LaTeX + JSON) and `outputs/figures/` (PNG).

## Module Overview

| Module | Paper Section | Description |
|--------|--------------|-------------|
| `models/` | Sections 4-6 | Core Wang MLE, stacked panel, cross-platform estimation |
| `extensions/` | Section 7 | EIV volatility, hazard rate term structure |
| `identification/` | Section 5.4 | External benchmark validation (NBA Elo) |
| `robustness/` | Appendix | Opening price sensitivity |

## Running All Analyses

```bash
# From repository root:
python src/models/hierarchical_wang_mle.py        # Table 5-9
python src/models/stacked_panel_lambda.py          # Table 10-11, Figure 3
python src/models/kalshi_hierarchical_mle.py       # Table 14-15
python src/models/kalshi_subanalysis.py            # Table 16-17
python src/models/timing_harmonization.py          # Table A3-A4
python src/identification/external_benchmark.py    # Table 12-13
python src/extensions/eiv_empirical.py             # Table 19-20
python src/extensions/hazard_rate_empirical.py     # Table 21
python src/robustness/opening_price_measures.py    # Table A1
```

## Conventions

- All scripts use `ROOT` as the repository root (auto-detected or configurable)
- Random seed: `np.random.seed(42)` for reproducibility
- Optimization: `scipy.optimize.minimize` (L-BFGS-B) with analytic gradients
- Standard errors: robust sandwich estimator (Huber-White)
- Chunk size: `_CHUNK = 30000` for NumPy operations (Apple Accelerate BLAS compatibility)
