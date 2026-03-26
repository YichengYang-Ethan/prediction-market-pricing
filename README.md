# Pricing Prediction Markets: Risk Premiums, Incomplete Markets, and a Decomposition Framework

**Yicheng Yang** | University of Illinois Urbana-Champaign | [yy85@illinois.edu](mailto:yy85@illinois.edu)

**Working Paper** -- March 2026

SSRN: [https://papers.ssrn.com/sol3/papers.cfm?abstract_id=XXXXXXX](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=XXXXXXX)

---

## Abstract

Prediction markets---binary contracts on real-world events---lack the pricing infrastructure available to every other major asset class. This paper proposes a three-layer decomposition framework that formally separates physical event probability from risk premium. The framework combines a log-odds state variable, jump-diffusion dynamics in log-odds space, and a Wang (2000) probability distortion:

$$p^{\text{mkt}} = \Phi\bigl(\Phi^{-1}(p^*) + \lambda\bigr)$$

Calibration on 2,460 resolved Polymarket contracts yields $\hat{\lambda}_{\text{MLE}} = 0.176$ ($p < 10^{-10}$). Cross-platform validation across $N = 291{,}309$ contracts from six platforms (Polymarket, Kalshi, Metaculus, Good Judgment Open, INFER, Manifold) confirms a positive, significant $\lambda$ on all real-money platforms (pooled $\hat{\lambda} = 0.183$), while the play-money platform Manifold exhibits $\hat{\lambda} < 0$, consistent with overconfidence absent financial stakes.

## Repository Structure

```
prediction-market-pricing/
├── README.md                  # This file
├── LICENSE                    # MIT License
├── CITATION.cff               # Citation metadata
├── requirements.txt           # Python dependencies
├── .gitignore
├── paper/
│   └── README.md              # Paper files and compilation instructions
├── src/
│   ├── README.md              # Code overview
│   ├── models/                # Core estimation (Wang MLE, stacked panel)
│   │   └── README.md
│   ├── extensions/            # EIV, hazard rate extensions
│   │   └── README.md
│   ├── identification/        # External benchmark validation
│   │   └── README.md
│   └── robustness/            # Opening price robustness checks
│       └── README.md
├── data/
│   ├── README.md              # Data sources and access instructions
│   ├── raw/                   # Raw API pulls (not distributed)
│   └── processed/             # Analysis-ready datasets
├── outputs/
│   ├── tables/                # LaTeX tables (.tex) and JSON results
│   ├── figures/               # Publication figures (.png)
│   └── logs/                  # Estimation logs
├── replication_guide.md       # Step-by-step replication instructions
└── data_dictionary.md         # Variable definitions for all datasets
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YichengYang-Ethan/prediction-market-pricing.git
cd prediction-market-pricing

# 2. Install dependencies
pip install -r requirements.txt

# 3. Replicate main results (Table 5: hierarchical Wang MLE)
python src/models/hierarchical_wang_mle.py

# 4. Replicate stacked panel (Table 10-11, Figure 3)
python src/models/stacked_panel_lambda.py

# 5. Replicate cross-platform validation (Table 14)
python src/models/kalshi_hierarchical_mle.py
```

See [`replication_guide.md`](replication_guide.md) for the full pipeline and expected output.

## Key Results

| Result | Script | Output |
|--------|--------|--------|
| Wang MLE $\hat{\lambda} = 0.176$ | `src/models/hierarchical_wang_mle.py` | `outputs/tables/hierarchical_wang_main.tex` |
| Time-varying risk premium (half-life 33-77%) | `src/models/stacked_panel_lambda.py` | `outputs/tables/stacked_panel_params_12day.tex` |
| Cross-platform pooled $\hat{\lambda} = 0.183$ | `src/models/kalshi_hierarchical_mle.py` | `outputs/tables/kalshi_hierarchical.tex` |
| Kalshi covariate heterogeneity | `src/models/kalshi_subanalysis.py` | `outputs/tables/kalshi_duration_split.tex` |
| Timing harmonization (37% gap closure) | `src/models/timing_harmonization.py` | `outputs/tables/polymarket_timing_ladder.tex` |
| External benchmark (NBA Elo) | `src/identification/external_benchmark.py` | `outputs/tables/external_benchmark_results.tex` |
| EIV empirical volatility | `src/extensions/eiv_empirical.py` | `outputs/tables/eiv_summary_stats.tex` |
| Opening price robustness | `src/robustness/opening_price_measures.py` | `outputs/tables/opening_price_robustness.tex` |

## Data Availability

- **Polymarket**: Public via [Gamma API](https://gamma-api.polymarket.com) and [CLOB API](https://clob.polymarket.com). Raw pulls included in `data/raw/`.
- **Kalshi**: Public via [Kalshi API](https://trading-api.kalshi.com/trade-api/v2). Raw pulls included in `data/raw/`.
- **Metaculus, GJOpen, INFER, Manifold**: Public APIs. See `data/README.md` for endpoints.
- **NBA Elo ratings**: FiveThirtyEight (public). Processed file in `data/processed/`.
- **Implied odds**: The Odds API (free tier). Processed file in `data/processed/`.

No proprietary or restricted-access data is used.

## Software Requirements

- Python 3.10+
- NumPy, SciPy, pandas (see `requirements.txt`)
- LaTeX distribution (for paper compilation)

## Citation

If you use this code or data, please cite:

```bibtex
@article{yang2026pricing,
  title   = {Pricing Prediction Markets: Risk Premiums, Incomplete Markets, and a Decomposition Framework},
  author  = {Yang, Yicheng},
  year    = {2026},
  journal = {Working Paper},
  note    = {University of Illinois Urbana-Champaign}
}
```

## License

[MIT License](LICENSE)
