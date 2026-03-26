# models/

Core estimation scripts for the Wang transform pricing framework.

## Scripts

### `hierarchical_wang_mle.py` -- One-Stage Hierarchical Wang MLE

**Paper**: Section 5.3, Tables 5-9

Estimates the hierarchical probit-offset model:

$$\Pr(y_i = 1 \mid p_i^{\text{mkt}}, X_i) = \Phi\bigl(\Phi^{-1}(p_i^{\text{mkt}}) - X_i \beta\bigr)$$

where $X_i = [\mathbf{1}, \sigma_i, d_i, \text{ext}_i]$ (intercept, volatility, duration, extremity).

**Outputs**: `hierarchical_wang_main.tex`, `hierarchical_wang_comparison.tex`, `hierarchical_wang_results.json`

### `stacked_panel_lambda.py` -- Time-Varying Risk Premium

**Paper**: Section 5.5, Tables 10-11, Figure 3

Stacked panel model estimating $\lambda(\tau)$ as a function of normalized time-to-expiry $\tau \in [0,1]$. Reveals the risk premium decay pattern (half-life 33-77% of contract lifetime).

**Outputs**: `stacked_panel_params_12day.tex`, `stacked_panel_derived_12day.tex`, `fig_stacked_panel_f_tau_12day.png`

### `kalshi_hierarchical_mle.py` -- Cross-Platform Validation (Kalshi)

**Paper**: Section 6.1, Tables 14-15

Applies the hierarchical Wang MLE to 200K+ Kalshi contracts. Confirms positive $\lambda$ on an independent regulated platform.

**Outputs**: `kalshi_hierarchical.tex`, `kalshi_hierarchical_results.json`

### `kalshi_subanalysis.py` -- Kalshi Covariate Heterogeneity

**Paper**: Section 6.1, Tables 16-17

Duration-split and contract-type sub-analyses diagnosing covariate sign differences between Polymarket and Kalshi.

**Outputs**: `kalshi_duration_split.tex`, `kalshi_contract_types.tex`

### `timing_harmonization.py` -- Timing Ladder Analysis

**Paper**: Appendix A, Tables A3-A4

Re-estimates the Polymarket model at different lifecycle pricing points (5%, 20%, 50%, 80%) to quantify how much price timing explains cross-platform coefficient differences. Computes L1/L2 distance metrics.

**Outputs**: `polymarket_timing_ladder.tex`, `polymarket_vs_kalshi_timing_distance.tex`
