# FRL Short Note — Option A: Play-Money Sign Reversal

## Title
**Are Prediction Market Prices Probabilities? Evidence from a Play-Money Natural Control**

## Abstract (~250 words)

Prediction market prices are widely interpreted as event probabilities, but
testing whether they embed systematic distortions is difficult without an
external probability benchmark. This paper exploits a natural control: the
play-money platform Manifold, where participants face no financial stakes.
Applying a one-parameter Wang transform specification as a measurement device,
I estimate the pricing-measure selection parameter on 291,309 resolved
contracts across six platforms. The two traded real-money venues—Polymarket
(blockchain-based) and Kalshi (CFTC-regulated)—yield positive and highly
significant estimates (λ = 0.166 and 0.187, respectively), indicating
systematic probability compression in which longshots are disproportionately
overpriced. Three forecasting platforms operating under reputational or
prize-based incentives (Metaculus, Good Judgment Open, INFER) also exhibit
positive distortion parameters, though the economic interpretation differs
from traded venues since participants do not bear direct financial risk.
Manifold, the play-money platform, yields λ = −0.22 (p < 10⁻¹¹)—a sign
reversal consistent with overconfidence dominating when risk-bearing costs are
absent. The cross-platform sign pattern is robust to alternative price
measures, sample restrictions, and complement-invariant specifications. These
results suggest that the positive price–probability wedge on real-money
platforms reflects risk-bearing costs rather than purely cognitive biases, and
that the Wang transform provides a tractable one-parameter benchmark for
measuring this distortion across heterogeneous platform architectures.

## Section Outline (target: <2500 words)

### 1. Introduction (~400 words)
- Prediction market prices ≠ probabilities (Manski 2006)
- Testing requires external benchmark or contrast
- Natural control: play-money platform removes financial stakes
- Preview: sign reversal across real-money vs play-money

### 2. Wang Transform as Measurement Device (~300 words)
- One equation: p_mkt = Φ(Φ⁻¹(p*) + λ)
- λ > 0 → compression; λ < 0 → overconfidence
- MLE estimation from resolved contracts (Bernoulli likelihood)
- Cite full structural derivation in [Yang 2026, SSRN/Zenodo]

### 3. Data (~300 words)
- 6 platforms, 291,309 contracts
- Distinguish clearly:
  - Traded real-money: Polymarket, Kalshi
  - Forecasting tournaments: Metaculus, GJ Open, INFER
  - Play-money: Manifold
- Sample construction, filters

### 4. Results (~600 words)
- Table 1: Platform-level λ estimates (6 rows)
- Key findings:
  1. Polymarket λ = 0.166***, Kalshi λ = 0.187***
  2. Forecasting platforms: positive but different economic object
  3. Manifold λ = −0.22*** (sign reversal)
  4. Magnitude gradient: deeper markets → smaller wedge
- One figure: forest plot of λ by platform with CIs

### 5. Robustness (~400 words)
- Alternative price timing (opening, midlife, near-settlement)
- Complement-invariant specification
- Sample restrictions (price range, duration)

### 6. Conclusion (~200 words)
- Sign reversal = natural control for risk-bearing interpretation
- Forecasting platforms as ancillary evidence, not identical objects
- Cite full paper for structural theory

## Key Differences from Full Paper (no salami-slicing)
- Full paper: structural pricing theory (Proposition 1, latent factor,
  exact Wang derivation, FLB corollary, factor-loading interpretation,
  time-varying analysis, EIV, external benchmark)
- This note: purely empirical cross-platform FACT using Wang as
  measurement device. No theory beyond one equation.
- Cites full paper for structural foundations.
