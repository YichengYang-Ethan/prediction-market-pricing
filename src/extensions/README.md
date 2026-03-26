# extensions/

Theoretical extensions with empirical implementation.

## Scripts

### `eiv_empirical.py` -- Errors-in-Variables Volatility Analysis

**Paper**: Section 7.1, Tables 19-20

Computes realized event volatility $\hat{\sigma}_{\text{realized}}$ as the median rolling standard deviation of hourly log-odds increments (annualized). Tests for ARCH(1) effects in prediction market price series.

**Outputs**: `eiv_summary_stats.tex`, `eiv_empirical.json`, `fig_eiv_distribution.png`

### `hazard_rate_empirical.py` -- Hazard Rate Term Structure

**Paper**: Section 7.3, Table 21

Estimates the empirical hazard rate term structure from contract resolution patterns. Connects to the theoretical jump-diffusion framework.

**Outputs**: `hazard_rate_term_structure.tex`, `hazard_rate_empirical.json`, `fig_hazard_rate_term_structure.png`
