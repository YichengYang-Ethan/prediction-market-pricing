---
title: ""
author: ""
date: ""
geometry: "margin=2.5cm"
fontsize: 11pt
mainfont: "Helvetica Neue"
monofont: "Menlo"
header-includes:
  - \usepackage{graphicx}
  - \usepackage{booktabs}
  - \usepackage{float}
  - \usepackage{amsmath}
  - \usepackage{amssymb}
  - \usepackage{amsthm}
  - \usepackage{hyperref}
  - \usepackage{xcolor}
  - \setlength{\parskip}{6pt}
  - \setlength{\parindent}{0pt}
  - \tolerance=1000
  - \emergencystretch=3em
  - \renewcommand{\abstractname}{Abstract}
  - \newtheorem{proposition}{Proposition}
  - \newtheorem{theorem}{Theorem}
  - \newtheorem{definition}{Definition}
  - \newtheorem{remark}{Remark}
---

\vspace*{-2.5em}
\begin{center}
{\LARGE\textbf{Pricing Prediction Markets:}}\\[4pt]
{\LARGE\textbf{Risk Premiums, Incomplete Markets, and a Decomposition Framework}}
\vspace{0.4cm}

{\large Yicheng Yang\footnote{University of Illinois Urbana-Champaign. Email: \texttt{yy85@illinois.edu}. I thank Polymarket for making market data publicly available via its Gamma and CLOB APIs. All errors are my own. This paper was developed independently; I welcome comments and suggestions.}}\\[2pt]
University of Illinois Urbana-Champaign\\[6pt]
\textbf{Working Paper} --- March 2026\\[1pt]
{\small This version: March 25, 2026}
\end{center}
\vspace{0.2cm}

\begin{abstract}
\small\noindent Prediction markets---binary contracts on real-world events---lack the pricing infrastructure available to every other major asset class. This paper proposes a three-layer decomposition framework that, to my knowledge, is the first to formally separate physical event probability from risk premium in prediction markets. The framework combines a log-odds state variable, jump-diffusion dynamics in log-odds space, and a Wang (2000) probability distortion: $p^{\text{mkt}} = \Phi(\Phi^{-1}(p^*) + \lambda)$. Because prediction market contracts are structurally equivalent to binary options in \textit{incomplete} markets (Manski, 2006; Harrison and Pliska, 1983), observed prices necessarily embed both event probability and a risk premium that no-arbitrage reasoning alone cannot separate. The Wang transform provides a single-parameter decomposition and generates the favorite-longshot bias as a direct mathematical consequence. Calibration on 2,460 resolved Polymarket contracts yields $\hat{\lambda}_{MLE} = 0.176$ ($p < 10^{-10}$), consistent with catastrophe bond markets. Cross-platform validation across $N = 291{,}309$ contracts from Polymarket, Kalshi, Metaculus, Good Judgment Open, INFER, and Manifold confirms a positive, significant $\lambda$ on all real-money platforms (pooled $\hat{\lambda} = 0.183$), while the play-money platform Manifold exhibits $\hat{\lambda} < 0$, consistent with overconfidence absent financial stakes. A stacked panel model reveals that the risk premium is time-varying, decaying with a half-life of 33--77\% of contract lifetime---linking the cross-sectional duration effect to within-contract information arrival.
\end{abstract}
\vspace{0.3em}
\noindent\small\textbf{JEL Classification:} G13, G14, G12, D81
\vspace{2pt}

\noindent\small\textbf{Keywords:} prediction markets, Wang transform, incomplete markets, binary options, favorite-longshot bias, risk premium, distortion risk measures, Polymarket, Kalshi

\newpage
\tableofcontents
\newpage

# 1. Introduction

## 1.1 A Market Without a Model

Prediction markets have crossed the threshold from academic curiosity to consequential financial markets. Polymarket processed over \$3.5 billion in notional volume during the 2024 U.S. presidential election cycle. Kalshi, a CFTC-regulated prediction market exchange, won a landmark federal court ruling in 2024 that legitimized event contracts as financial instruments. ICE invested \$2 billion in Polymarket at an \$8 billion pre-money valuation in 2025.\footnote{Source: ICE Press Release via BusinessWire, October 7, 2025.} In early 2026, Cboe announced plans to launch prediction market contracts packaged as vertical option spreads.\footnote{Source: Cboe press release, February 2026.}

Despite this institutional validation, prediction markets lack the theoretical infrastructure that underpins every other major asset class. Equity options have Black-Scholes (1973) and its descendants. Credit markets have Merton's structural model and reduced-form intensity frameworks. Fixed income has Vasicek, CIR, and HJM. Prediction markets lack a widely accepted pricing framework. Prices are formed by order flow on CLOBs or by automated market makers (Hanson, 2007), but no theory connects these prices to a stochastic process, no implied volatility surface exists, and no formal framework addresses relative value or risk aggregation.

The absence of a pricing paradigm is not merely an aesthetic concern. It has concrete consequences:

1. **No probability decomposition.** Are prediction market prices probabilities? Manski (2006) showed, in a formal model of heterogeneous beliefs, that they are not in general: observed prices embed both beliefs *and* risk preferences, and the equilibrium price need not equal the mean belief. But without a model, there is no way to separate the two.

2. **No relative value.** Contracts on different events cannot be compared on a risk-adjusted basis. Is a Greenland acquisition contract at $p = 0.10$ cheap relative to a Fed rate cut contract at $p = 0.05$? No metric exists.

3. **No risk management.** Portfolio risk across multiple event contracts cannot be aggregated without a model of co-movement.

4. **No explanation of systematic biases.** The favorite-longshot bias (FLB)---documented across 300,000+ Kalshi contracts by Bürgi, Deng, and Whelan (2025)---shows that low-probability events are systematically overpriced, but no structural pricing model explains *why*.

## 1.2 What Practitioners Currently Use

The absence of a paradigm does not mean the absence of trading. Susquehanna (SIG) became Kalshi's first institutional market maker in 2024; Jump Trading reportedly negotiated small equity stakes in both platforms in exchange for liquidity provision, though finalization was not independently confirmed at the time of writing.\footnote{Source: Bloomberg, February 2026.} Over 30\% of Polymarket wallets now employ AI-based trading agents, according to an estimate reported by the on-chain analytics platform LayerHub; the underlying methodology has not, to my knowledge, been independently validated.\footnote{Source: LayerHub via CoinDesk, March 2026.}

What these firms use is an *ad hoc* assembly of tools from adjacent domains:

- **Fair value**: The Black-Scholes cash-or-nothing formula $F = e^{-r\tau}\Phi(d_2)$, applied directly to event contracts. The critical input is $\sigma$---but there is no established method for calibrating it. Each firm uses proprietary models.

- **Quote management**: Avellaneda-Stoikov (2008) optimal market making, with spreads scaled by binary option greeks. No formal adaptation to the bounded probability domain has been published.

- **Position sizing**: Kelly criterion for binary payoffs, $f^* = (bp - q)/b$, typically run at 25--50\% fractional Kelly.

The critical gap is that prediction markets lack a standardized, continuously updated fair-value signal---the kind of pricing infrastructure that every other major asset class takes for granted. This paper proposes a framework that fills this gap.

## 1.3 Contributions

This paper proposes an integrated pricing and decomposition framework for prediction markets and validates it empirically across 291,309 contracts from eight data sources spanning six platforms and eleven years.

\textbf{Framework architecture.} The pricing model has three layers. \textit{Layer 1}: a log-odds state variable that maps bounded prices to $\mathbb{R}$, yielding a natural domain for stochastic modeling (Section 3.2). \textit{Layer 2}: a jump-diffusion dynamics specification in log-odds space, following Dalen (2025), under which the pricing formula reduces to the Black-Scholes binary option formula (Section 3.2). \textit{Layer 3}: the Wang (2000) probability distortion operator---originally developed for catastrophe bond pricing---decomposes observed prices into physical probability and risk premium: $p^{\text{mkt}} = \Phi(\Phi^{-1}(p^*) + \lambda)$. No prior work has applied the Wang transform to prediction markets. The decomposition operationalizes the Manski (2006) critique by providing a specific, estimable functional form for the distortion that separates event probability from a risk loading parameter $\lambda$ (Section 3).

\begin{enumerate}
\item \textit{FLB as risk premium.} As a direct consequence of the pricing framework, $\lambda > 0$ generates the favorite-longshot bias: longshots are proportionally more overpriced than favorites (Section 3.3). This provides a structural, risk-based mechanism complementing existing behavioral accounts. Contract-level calibration against 2,460 resolved Polymarket contracts yields $\hat{\lambda}_{MLE} = 0.176$ ($p < 10^{-10}$) (Section 5).

\item \textit{Cross-platform spread interpretation.} The framework interprets Polymarket--Kalshi price differences as reflecting different risk loadings ($\lambda_K \neq \lambda_P$), providing structural content to the price discovery finding independently documented by Ng et al.\ (2026) (Section 5.5).

\item \textit{Cross-platform and temporal validation.} I validate the framework on $N = 291{,}309$ contracts from eight data sources across six platforms (Polymarket, Kalshi, Metaculus, Good Judgment Open, INFER, Manifold) spanning 2015--2026, confirming that $\lambda > 0$ is a robust feature of real-money prediction markets. The play-money platform Manifold exhibits $\lambda < 0$ (overconfidence), providing a natural control. Kalshi year-by-year estimates demonstrate temporal stability of $\lambda \in [0.15, 0.27]$ over 2022--2026 (Section 6).

\item \textit{Log-odds stylized facts.} Building on the log-odds state variable used concurrently by Dalen (2025), I document that log-odds levels of prediction market contracts exhibit the same stylized facts as equity log-prices---random-walk behavior (unit root in $x_t$), fat tails (kurtosis 6--12 in increments), and volatility clustering---supporting a diffusion-based modeling approach (Section 4).

\item \textit{Incompleteness formalization.} Drawing on the Second Fundamental Theorem of Asset Pricing (Harrison and Pliska, 1983) and the Manski (2006) critique, I formalize the observation that prediction market contracts are structurally equivalent to cash-or-nothing binary options operating in incomplete markets, where the risk-neutral measure is non-unique and prices embed both probability and risk premium (Section 3). This motivates the need for the decomposition framework.
\end{enumerate}

The remainder of the paper is organized as follows. Section 2 positions this work within the relevant literatures. Section 3 develops the theoretical framework: the incompleteness of prediction markets, the log-odds state variable, the Wang transform decomposition, and assembles the complete pricing model (Section 3.5). Section 4 describes the data and documents stylized facts supporting the log-odds framework. Section 5 presents the empirical results, including robustness checks and Monte Carlo validation (Section 5.6). Section 6 validates the framework across eight data sources spanning six platforms and $N = 291{,}309$ contracts (2015--2026). Section 7 discusses extensions. Section 8 concludes.

---

# 2. Related Literature

This paper sits at the intersection of four literatures: stochastic modeling of prediction markets, the interpretation of prediction market prices, the favorite-longshot bias, and applications of the Wang transform.

**Stochastic modeling.** Dalen (2025) proposes a logit jump-diffusion in risk-neutral ($\mathbb{Q}$) space with a martingale drift constraint, calibration pipeline, and belief-volatility surface. Dalen's contribution and mine are complementary and address different problems. Dalen works entirely within the risk-neutral measure, taking $\mathbb{Q}$ as given and building a market-making kernel; this paper asks *which* $\mathbb{Q}$ the market selects and *how* it relates to the physical measure $P$. The Wang transform provides the $P$-to-$\mathbb{Q}$ bridge. In principle, one could use Dalen's logit jump-diffusion for the dynamics and the Wang transform for the measure change, combining both frameworks. Earlier, Archak and Ipeirotis (2009) modeled InTrade prices using Itô diffusions for latent ability processes, deriving contract price volatility as a function of current price and time to expiry.

**Probability interpretation.** Manski (2006) showed that interpreting prediction market prices directly as probabilities lacks formal justification: equilibrium price reflects a quantile of the belief distribution and only partially identifies the mean belief. Wolfers and Zitzewitz (2006) showed prices approximate mean beliefs under log utility and that broader model classes often yield similar results; Gjerstad (2004) proved the sufficiency of the log-utility condition. This paper operationalizes the Manski critique by providing a specific functional form for the distortion.

**Favorite-longshot bias.** The FLB has been documented in horse racing (Griffith, 1949; Snowberg and Wolfers, 2010), sports betting (Whelan, 2024), and prediction markets (Bürgi, Deng, and Whelan, 2025). Explanations include risk-loving preferences (Ali, 1977), probability weighting (Barberis and Huang, 2008), adverse selection (Shin, 1991, 1993), and noise (Ottaviani and Sorensen, 2010). Jullien and Salanié (2000) estimated expected utility, rank-dependent, and cumulative prospect theory models on racetrack data, finding that inverse-S shaped probability weighting---overweighting of small probabilities and underweighting of large ones---was a key driver of FLB, with cumulative prospect theory providing the best fit. The Wang transform provides a parametric complement to these nonparametric estimates. The Wang transform provides a unifying structural mechanism that nests the risk-averse market maker explanation (Whelan, 2024).

**Wang transform applications.** Wang (2000, 2004) applied the transform to catastrophe bond pricing ($\hat{\lambda} \approx 0.45$) and proposed it as a universal pricing framework for financial and insurance risks. Kijima and Muromachi (2008) derived the transform from Bühlmann's economic premium principle, establishing an equilibrium foundation. Hamada and Sherris (2003) showed it recovers the Black-Scholes formula in the lognormal case and related the distortion parameter to systematic risk. Pelsser (2008) showed that the Wang transform is not consistent with arbitrage-free pricing for general stochastic processes, implying it is not a universal pricing framework; the present application to incomplete markets sidesteps this critique. Huang, Sun, and Zhang (2024) recently generalized the transform to flexible probability weighting functions for lottery-like equities, embedding it within the Pi-CAPM framework. The present paper appears to be the first to apply the Wang transform to prediction markets or to derive the favorite-longshot bias as a consequence of the transform.

**Prediction market design and calibration.** Wolfers and Zitzewitz (2004) provide the standard survey on prediction market contract design and information aggregation. Servan-Schreiber, Wolfers, Pennock, and Galebach (2004) compare real-money and play-money prediction markets, finding similar forecasting accuracy---a result relevant to the interpretation of the Manifold play-money control in Section 6. Le (2026) argues that prediction market calibration is structured by horizon, domain, and trade size, complementing the heterogeneity analysis in Sections 5.3 and 5.6. Ostrovsky (2012) proves that in dynamic trading with separable securities, prices converge to the pooled-information posterior---a result relevant to the time-varying $\lambda$ decay documented in Section 5.4. Gneiting, Balabdaoui, and Raftery (2007) provide the foundational treatment of probabilistic calibration, against which the Wang transform can be understood as a parametric recalibration map.

**Bayesian approaches.** Madrigal-Cianci, Monsalve Maya, and Breakey (2026) recast prediction markets as Bayesian inverse problems in log-odds space, providing posterior uncertainty quantification on probability estimates.

---

# 3. Theoretical Framework

## 3.1 Prediction Markets as Incomplete-Market Binary Options

A prediction market contract pays \$1 if event $E$ occurs at or before time $T$, and \$0 otherwise. This is the payoff of a cash-or-nothing binary option (Rubinstein and Reiner, 1991):

$$\text{Payoff} = \$1 \cdot \mathbf{1}_{\{E \text{ occurs}\}}$$

In standard options theory, the Black-Scholes price of a cash-or-nothing binary call is:

$$C_{\text{binary}} = e^{-rT}\,\Phi(d_2), \quad d_2 = \frac{\ln(S/K) + (r - \tfrac{1}{2}\sigma^2)T}{\sigma\sqrt{T}}$$

The contract price $p_t$ is the risk-neutral probability of the event:

$$p_t = e^{-r\tau}\,\mathbb{E}^{\mathbb{Q}}\!\big[\mathbf{1}_{\{E\}} \mid \mathcal{F}_t\big]$$

For the short maturities typical of prediction markets (days to months), $e^{-r\tau} \approx 1$, so $p_t \approx \mathbb{E}^{\mathbb{Q}}[\mathbf{1}_E \mid \mathcal{F}_t]$. The structural equivalence tells us *what* to price. But standard tools cannot tell us *how*, because the market is incomplete.

**Terminology.** Throughout this paper, I use the following terms consistently. The \textit{physical probability} $p^*$ denotes the objective likelihood of event $E$ under the data-generating measure $P$. The \textit{market price} $p^{\text{mkt}}$ denotes the observed contract price. The \textit{risk-adjusted probability} $\hat{p}^* = \Phi(\Phi^{-1}(p^{\text{mkt}}) - \hat{\lambda})$ denotes the estimated physical probability after stripping the risk loading. I avoid the terms ``true probability,'' ``fair value,'' and ``actuarially fair value'' except where context requires them, as they can conflate distinct concepts.

\begin{proposition}[Incompleteness]
Let $(\Omega, \mathcal{F}, \{\mathcal{F}_t\}, P)$ be a filtered probability space supporting a prediction market contract $C$ on event $E$. If $E$ is not perfectly correlated with any traded asset, then:
\begin{enumerate}
\item No self-financing portfolio replicates the payoff $\mathbf{1}_E$.
\item The set of equivalent martingale measures $\mathcal{Q}$ contains more than one element.
\item The no-arbitrage price lies in an interval $[\underline{p}, \overline{p}]$ with $\underline{p} < \overline{p}$.
\end{enumerate}
\end{proposition}

*Proof sketch.* The event $E$ introduces a risk factor that is not fully spanned by---i.e., not attainable as a linear combination of payoffs from---existing traded assets. By the Second Fundamental Theorem of Asset Pricing (Harrison and Pliska, 1981, 1983), market completeness requires $|\mathcal{Q}| = 1$, which fails whenever the payoff $\mathbf{1}_E$ is not attainable---i.e., lies outside the marketed subspace generated by admissible self-financing strategies. Even when $E$ is partially correlated with traded assets (e.g., Fed rate decisions that affect bond prices), there generically remains residual event-specific risk that cannot be hedged, ensuring incompleteness. The bounds $\underline{p}$ and $\overline{p}$ are the infimum and supremum of $\mathbb{E}^{\mathbb{Q}}[\mathbf{1}_E]$ over $\mathbb{Q} \in \mathcal{Q}$. $\square$

**Why this matters.** In complete markets, the Black-Scholes delta-hedging argument determines a unique price without reference to risk preferences. In equity options, a trader can continuously hedge by trading the underlying stock, eliminating all risk and pinning down the option's fair value. In prediction markets, the "underlying" is the event itself---a geopolitical outcome, an economic indicator, a sporting result. There is no asset to trade as a hedge. The prediction market contract is its own underlying.

This incompleteness has a fundamental consequence for interpretation: **the observed market price is not a pure probability estimate.** It is a probability *distorted by risk preferences*. Formally, the market selects a specific $\mathbb{Q}^* \in \mathcal{Q}$, and the price reflects $\mathbb{E}^{\mathbb{Q}^*}[\mathbf{1}_E]$, which differs from the physical probability $P(E)$ by the market price of event risk. Existing work identifies the interpretation problem but does not provide a tractable empirical decomposition (Manski, 2006; Wolfers and Zitzewitz, 2006). Section 3.3 proposes such a decomposition.

\begin{remark}[Comparison to incomplete-market pricing approaches]
Several frameworks exist for pricing in incomplete markets: good-deal bounds (Cochrane and Saa-Requejo, 2000), the minimal entropy martingale measure (Frittelli, 2000), and utility-based pricing. The Wang transform offers a complementary approach with a key advantage: it is a single-parameter model with an economically interpretable parameter ($\lambda$ = market price of event risk), which facilitates cross-sectional estimation and comparative analysis. Its axiomatic foundations in the theory of distortion risk measures (Wang, Young, and Panjer, 1997; Yaari, 1987) provide rigorous justification.
\end{remark}

## 3.2 The Log-Odds State Variable

Before decomposing prices, we need a state variable in which standard stochastic tools apply. The contract price $p_t \in (0,1)$ is bounded, violating the support assumptions of standard diffusion models. The resolution is the log-odds (logit) transformation:

$$x_t = \ln\!\left(\frac{p_t}{1 - p_t}\right) = \text{logit}(p_t), \quad x_t \in \mathbb{R}$$

with inverse $p_t = \sigma(x_t) = (1 + e^{-x_t})^{-1}$.

This is the prediction market analog of the log-price transformation $y_t = \ln S_t$ in equity option pricing: just as $\ln S_t$ maps $(0, \infty) \to \mathbb{R}$ and yields geometric Brownian motion as the simplest tractable model, $\text{logit}(p_t)$ maps $(0,1) \to \mathbb{R}$ and yields a "logistic diffusion" as the natural baseline.

**Why log-odds is natural.** The claim rests on two theoretical arguments. First, an *Itô's lemma argument*: if $p_t$ follows a bounded diffusion with volatility $\sigma_p(p_t, t)$, the Jacobian $g'(p) = 1/(p(1-p))$ of the logit automatically compensates for boundary compression. If $\sigma_p(p) = \sigma \cdot p(1-p)$ (the martingale-consistent form), then $x_t$ has constant diffusion coefficient $\sigma$---the simplest possible dynamics. The full Itô expansion of $x_t = \text{logit}(p_t)$ yields $dx_t = [\mu_p/(p(1-p)) + \frac{1}{2}\sigma^2(2p-1)]dt + \sigma\,dW_t$, confirming that the logit transformation produces a constant diffusion coefficient $\sigma$ while introducing a state-dependent drift. The baseline pricing formula assumes the simplified case where the drift contribution is negligible relative to the diffusion term. Second, a *statistical argument*: the logit is the canonical link function for the Bernoulli exponential family in generalized linear models (McCullagh and Nelder, 1989); prediction market contracts *are* binary outcomes, so the logit is the information-theoretically natural parameterization. The empirical validation of these arguments is presented in Section 4.2.

Based on the empirical support, I posit a jump-diffusion in log-odds space, following the specification of Dalen (2025):

$$dx_t = \mu(x_t, t)\,dt + \sigma_b(x_t, t)\,dW_t + J_t\,dN_t$$

where $\sigma_b$ is the *belief volatility*, $J_t$ is the jump amplitude, and $N_t$ is a Poisson process with intensity $\eta$. To derive the baseline pricing formula, I introduce a latent information state $S_t$ that summarizes all available information about event $E$. Under the physical measure $P$, the terminal state follows $S_T \mid S_t \sim N(S_t, \sigma^2\tau)$ in the constant-volatility, no-jump case. The event occurs if and only if $S_T > 0$. The physical probability of the event is therefore:

$$p_t^* = P(S_T > 0 \mid S_t) = \Phi\!\left(\frac{S_t}{\sigma\sqrt{\tau}}\right)$$

This is the prediction market analog of the Black-Scholes derivation: just as the equity option formula arises from log-normal terminal stock prices, the binary contract formula arises from Gaussian terminal information states. In practice, $S_t$ is not directly observed; the log-odds $x_t = \text{logit}(p_t)$ serves as the empirical proxy. The logit and probit functions are approximately proportional ($\text{logit}(p) \approx (\pi/\sqrt{3}) \cdot \Phi^{-1}(p)$), so the qualitative properties documented in Section 4 carry over.

## 3.3 The Wang Transform Decomposition

This subsection contains the paper's core theoretical contribution.

**The decomposition problem.** Recall from Proposition 1 that the observed price $p_t^{\text{mkt}}$ is $\mathbb{E}^{\mathbb{Q}^*}[\mathbf{1}_E \mid \mathcal{F}_t]$ for some $\mathbb{Q}^* \in \mathcal{Q}$, but $\mathbb{Q}^*$ is not unique. The physical (true) probability is $p_t^* = P(E \mid \mathcal{F}_t)$. We seek a decomposition:

$$p_t^{\text{mkt}} = T(p_t^*; \theta)$$

where $T$ is a distortion function parameterized by $\theta$, mapping the physical probability into the market price. The requirements are: (i) $T$ should be a valid probability distortion ($T(0) = 0$, $T(1) = 1$, $T$ increasing); (ii) $T$ should correspond to a well-defined change of measure; and (iii) $\theta$ should be economically interpretable.

\begin{definition}[Wang Transform]
For a random variable $X$ with survival function $S_X(x) = 1 - F_X(x)$, the Wang (2000) transform with parameter $\lambda \in \mathbb{R}$ defines a distorted survival function:
$$\tilde{S}_X(x) = \Phi\!\left(\Phi^{-1}(S_X(x)) + \lambda\right)$$
For a binary event with physical probability $p$ (the survival probability that the event occurs), this reduces to:
$$\tilde{p} = \Phi\!\left(\Phi^{-1}(p) + \lambda\right)$$
\end{definition}

The Wang transform was originally developed for catastrophe bond and insurance pricing (Wang, 2000, 2004) and has been axiomatically characterized within the theory of distortion risk measures (Wang, Young, and Panjer, 1997; Yaari, 1987). Its key properties:

**Measure-theoretic interpretation.** The Wang transform with parameter $\lambda$ corresponds to a Girsanov change of measure with constant market price of risk $\lambda$. Specifically, if $Z \sim N(0,1)$ under $P$, then under the distorted measure $\tilde{P}$:

$$\frac{d\tilde{P}}{dP} = \exp\!\left(\lambda Z - \frac{\lambda^2}{2}\right)$$

This is the Radon-Nikodym derivative for a Girsanov change of measure with constant market price of risk in a single-period Gaussian setting---the same exponential tilt that underlies Black-Scholes pricing when applied to a single terminal normal factor. In continuous-time settings with general stochastic processes, the Wang transform does not necessarily coincide with the Girsanov measure change (Pelsser, 2008); the present application uses the static form appropriate for the binary-event decomposition. When the underlying follows GBM, the Wang transform recovers the Black-Scholes formula (Hamada and Sherris, 2003).

**Consistency with financial theory.** Kijima and Muromachi (2008) showed that the Wang transform can be derived from Bühlmann's economic premium principle, establishing an equilibrium foundation. The parameter $\lambda$ has a direct interpretation as the market-wide Sharpe ratio for bearing event risk.

**Scope and limitations.** Pelsser (2008) showed that the Wang transform is not consistent with arbitrage-free pricing for general stochastic processes, implying it is not a universal pricing framework. This is a significant theoretical restriction---but one that does not apply to the setting of this paper. Pelsser's critique targets the use of the Wang transform for dynamic replication pricing in complete markets (i.e., as a substitute for Black-Scholes). In prediction markets, the market is incomplete and no replication is possible; the Wang transform is used not for dynamic pricing but for *static* probability distortion, which is its original actuarial application and remains fully valid.

**Application to prediction markets.** I propose that the observed market price $p_t^{\text{mkt}}$ is the Wang-distorted version of the physical probability $p_t^*$:

$$p_t^{\text{mkt}} = \Phi\!\left(\Phi^{-1}(p_t^*) + \lambda\right) \tag{1}$$

where $\lambda$ is the market price of event risk. When $\lambda = 0$, the price equals the physical probability. When $\lambda > 0$, the market charges a risk premium: the price exceeds the physical probability.

\begin{theorem}[Risk Premium Properties]
Under the Wang transform decomposition (1) with $\lambda > 0$:
\begin{enumerate}
\item $p^{\text{mkt}} > p^*$ for all $p^* \in (0, 1)$: all events are overpriced.
\item The overpricing $\Delta p = p^{\text{mkt}} - p^*$ is maximized at $p^* = \Phi(-\lambda/2) \approx 0.5$ for small $\lambda$, and vanishes at the boundaries.
\item The overpricing \textit{ratio} $p^{\text{mkt}} / p^*$ is monotonically decreasing in $p^*$: longshots are proportionally more overpriced than favorites.
\item This overpricing-ratio pattern is qualitatively consistent with the \textbf{favorite-longshot bias} documented by Bürgi, Deng, and Whelan (2025) across 300,000+ Kalshi contracts and by Snowberg and Wolfers (2010) across 6.4 million horse racing starts.
\end{enumerate}
\end{theorem}

*Proof.* For (1): $\lambda > 0$ implies $\Phi^{-1}(p^{\text{mkt}}) = \Phi^{-1}(p^*) + \lambda > \Phi^{-1}(p^*)$, so $p^{\text{mkt}} > p^*$. For (3): define $R(p) = \Phi(\Phi^{-1}(p) + \lambda)/p$. Taking the derivative and using $\phi(\Phi^{-1}(p)) > 0$, one can show $R'(p) < 0$ for $\lambda > 0$. For (4): Property (3) predicts longshots (low $p^*$) have higher overpricing ratios than favorites (high $p^*$), which is the definition of FLB. $\square$

The monotonicity of the overpricing ratio $R(p)$ is a known property of concave probability distortion functions (Yaari, 1987); the contribution here is to show that the Wang transform provides a specific, one-parameter functional form that generates this pattern with a directly interpretable risk-loading parameter $\lambda$.

\begin{remark}[Relation to alternative FLB explanations]
The FLB has been attributed to risk-loving preferences (Ali, 1977), probability misperceptions via prospect theory (Snowberg and Wolfers, 2010), adverse selection among informed bettors (Shin, 1991, 1993), and noise-to-signal ratios (Ottaviani and Sorensen, 2010). The Wang transform explanation is complementary: it provides a structural, risk-premium-based mechanism through the supply side. Whelan's (2024) competitive bookmaker model, in which FLB arises from risk-averse market makers, is the closest analog---$\lambda$ in the Wang transform can be interpreted as the aggregate risk aversion of market makers.
\end{remark}

\begin{remark}[Binary complementarity]
Under the Wang transform, relabeling the event as $\neg E$ transforms $\lambda$ to $-\lambda$, so the distortion is not framing-invariant. This is a known property of directional distortion operators and does not affect the empirical estimates, which are always computed relative to the YES contract. The asymmetry is economically interpretable: prediction market contracts are directional instruments---a trader buys YES or NO, and the risk loading applies to the purchased contract. The generalized two-parameter test in Section 5.6 confirms that the one-parameter specification is empirically adequate.

This framing dependence is a genuine limitation of the one-parameter Wang specification: it implies that $\lambda$ is a direction-specific calibration parameter tied to the YES contract, not a universal property of the event. A complement-invariant extension would require a two-parameter distortion or a symmetric specification. The generalized distortion test in Section 5.6 (which estimates both intercept and slope) provides partial evidence that the one-parameter restriction is empirically adequate, but the theoretical asymmetry remains.
\end{remark}

## 3.4 Testable Predictions

The framework generates two testable predictions and a set of quantitative benchmarks.

**Prediction 1: Favorite-longshot bias.** If $\lambda > 0$, Theorem 1 predicts that market prices systematically overstate event probabilities, with the overpricing ratio decreasing in $p^*$. This is testable by comparing market prices to realized resolution frequencies.

**Prediction 2: Cross-platform spread.** If two platforms have different risk loadings ($\lambda_K \neq \lambda_P$), then systematic price differences arise: $p_K - p_P = \Phi(\Phi^{-1}(p^*) + \lambda_K) - \Phi(\Phi^{-1}(p^*) + \lambda_P)$. This is testable using aligned Polymarket-Kalshi data.

**Numerical benchmarks.** To build intuition, Table \ref{tab:wang_benchmarks} shows the Wang transform for several values of $\lambda$.

\begin{table}[H]
\centering
\begin{tabular}{ccccc}
\toprule
True prob.\ $p^*$ & $\lambda = 0$ & $\lambda = 0.1$ & $\lambda = 0.3$ & $\lambda = 0.5$ \\
\midrule
0.05 & 0.050 & 0.061 & 0.089 & 0.126 \\
0.10 & 0.100 & 0.119 & 0.163 & 0.217 \\
0.20 & 0.200 & 0.229 & 0.294 & 0.366 \\
0.30 & 0.300 & 0.336 & 0.411 & 0.490 \\
0.50 & 0.500 & 0.540 & 0.618 & 0.691 \\
0.70 & 0.700 & 0.734 & 0.795 & 0.847 \\
0.90 & 0.900 & 0.916 & 0.943 & 0.963 \\
0.95 & 0.950 & 0.959 & 0.974 & 0.984 \\
\bottomrule
\end{tabular}
\caption{Wang-distorted probabilities $\tilde{p} = \Phi(\Phi^{-1}(p^*) + \lambda)$. The distortion is strongest at low probabilities and weakest at high probabilities, generating the FLB pattern.}
\label{tab:wang_benchmarks}
\end{table}

## 3.5 The Complete Pricing Model

The preceding subsections developed three components: the binary option structure (3.1), the log-odds state variable (3.2), and the Wang transform decomposition (3.3). This subsection assembles them into a single, implementable pricing model---the prediction market analog of Black-Scholes for equity options or Merton/Jarrow-Turnbull for credit risk.

\begin{definition}[Prediction Market Pricing Model]
Let $p_t^{\text{mkt}} \in (0,1)$ denote the observed market price of a binary contract on event $E$ with time-to-expiry $\tau = T - t$. The model has three layers:

\textbf{Layer 1 --- State variable.} The log-odds transformation maps bounded prices to an unbounded state space:
$$x_t = \text{logit}(p_t) = \ln\!\left(\frac{p_t}{1-p_t}\right), \quad x_t \in \mathbb{R}$$

\textbf{Layer 2 --- Dynamics.} The log-odds follow a jump-diffusion:
$$dx_t = \mu(x_t,t)\,dt + \sigma\,dW_t + J_t\,dN_t$$
where $\sigma$ is the belief volatility, $J_t$ the jump amplitude, and $N_t$ a Poisson process with intensity $\eta$. Layer 2 operates entirely under the physical measure $P$ and delivers the physical probability $p_t^*$ as a function of the latent information state $S_t$ (see Section 3.2). In the baseline constant-volatility, no-jump case, $p_t^* = \Phi(S_t / (\sigma\sqrt{\tau}))$.

\textbf{Layer 3 --- Risk premium.} The observed market price is the Wang-distorted physical probability. Layer 3 performs the unique $P$-to-$\mathbb{Q}$ transformation: the observed market price $p_t^{\text{mkt}}$ is the Wang-distorted physical probability. This is the only point in the framework where the change of measure occurs, paralleling the role of the Girsanov theorem in Black-Scholes.
\begin{equation}
p_t^{\text{mkt}} = \Phi\!\left(\Phi^{-1}(p_t^*) + \lambda\right) \tag{1}
\end{equation}
where $p_t^*$ is the physical probability and $\lambda$ is the market price of event risk.
\end{definition}

**Forward pricing.** Given a physical probability estimate $\hat{p}^*$ and a calibrated risk loading $\hat{\lambda}$, the model-implied market price is:
$$\hat{p}^{\text{mkt}} = \Phi\!\left(\Phi^{-1}(\hat{p}^*) + \hat{\lambda}\right)$$

**Inverse: physical probability extraction.** Given an observed market price $p^{\text{mkt}}$ and a calibrated $\hat{\lambda}$, the risk-adjusted probability is:
$$\hat{p}^* = \Phi\!\left(\Phi^{-1}(p^{\text{mkt}}) - \hat{\lambda}\right)$$

This is the central empirical application: recovering physical probabilities from observed market prices.

**Calibration procedure.** The parameter $\lambda$ is estimated from a cross-section of $N$ resolved contracts $(p_i^{\text{mkt}}, y_i)$, where $y_i \in \{0,1\}$ is the resolution outcome:
$$\hat{\lambda}_{MLE} = \arg\max_\lambda \sum_{i=1}^{N} \left[y_i \ln \Phi\!\left(\Phi^{-1}(p_i^{\text{mkt}}) - \lambda\right) + (1-y_i)\ln\!\left(1 - \Phi\!\left(\Phi^{-1}(p_i^{\text{mkt}}) - \lambda\right)\right)\right]$$

Standard errors are computed from the observed Fisher information (numerical Hessian). The likelihood ratio test against $H_0: \lambda = 0$ (prices are perfectly calibrated probabilities) has one degree of freedom.

**Model sensitivities.** The Wang transform implies analytic sensitivities of the market price to model inputs:

- \textit{Lambda sensitivity}: $\displaystyle\frac{\partial p^{\text{mkt}}}{\partial \lambda} = \phi\!\left(\Phi^{-1}(p^*) + \lambda\right) > 0$. The market price is monotonically increasing in the risk loading, with maximum sensitivity at $p^* \approx 0.5$.
- \textit{Probability sensitivity}: $\displaystyle\frac{\partial p^{\text{mkt}}}{\partial p^*} = \frac{\phi(\Phi^{-1}(p^*) + \lambda)}{\phi(\Phi^{-1}(p^*))}$, the local amplification factor of the Wang distortion.
- \textit{Overpricing}: $\Delta p = p^{\text{mkt}} - p^*$, maximized near $p^* = 0.5$ (Theorem 1).

**Summary.** The complete model reduces prediction market pricing to three objects: a state variable ($x_t = \text{logit}(p_t)$), a dynamics specification (log-odds diffusion with belief volatility $\sigma$), and a one-parameter risk distortion ($\lambda$). It takes a market price as input and outputs a risk-adjusted probability; or takes a probability forecast and outputs a model-implied fair price. The empirical calibration of $\lambda$ is the subject of Section 5.

## 3.6 Economic Interpretation of $\lambda$

The Wang transform decomposition in Section~3.3 is estimated as a reduced-form pricing model: $\lambda$ is calibrated from the cross-section of market prices and resolution outcomes without imposing a structural model of trader preferences or market equilibrium. This subsection provides a benchmark economic interpretation of $\lambda$ that connects the empirical framework to standard asset pricing concepts. The interpretation is offered as a special-case lens, not as the estimated model of the paper.

\medskip
\noindent\textbf{Benchmark setup.}
Section~3.3 noted that $\lambda$ has an interpretation as the market-wide Sharpe ratio for bearing event risk, following the equilibrium foundation established by Kijima and Muromachi (2008). To make this interpretation concrete, consider a benchmark CARA-normal environment: a representative agent with constant absolute risk aversion $a > 0$ prices a binary event claim under Gaussian residual uncertainty about the event outcome. In this setting, the certainty-equivalent valuation of the binary payoff takes the form of equation~(1) with $\lambda = a \cdot \tilde{\sigma}$, where $\tilde{\sigma}$ measures residual event uncertainty. This closed-form relationship is a special case of the stochastic discount factor characterization derived by Johnston (2007), who showed that in a CARA-normal economy the Wang parameter equals the product of absolute risk aversion and the standard deviation of the priced risk factor. The benchmark is not a general-equilibrium derivation of the paper's framework. It is a convenient special case that gives $\lambda$ an economic interpretation in terms of two quantities: the effective risk aversion of the marginal pricing agent and the residual uncertainty about the event outcome.

\medskip
\noindent\textbf{Implications for the empirical patterns.}
The representation $\lambda = a \cdot \tilde{\sigma}$ provides economic intuition for three patterns documented in Sections~5 and~6. First, the positive $\hat{\lambda}$ on all real-money platforms is consistent with risk-averse agents demanding compensation for bearing unhedgeable event risk. The estimated $\hat{\lambda} \approx 0.18$ is consistent with nontrivial effective risk aversion applied to residual event uncertainty, though the benchmark does not separately identify these two components.

Second, the time-varying decay documented in Section~5.4---where the risk premium declines from $\hat{\lambda}(0.05) = 0.173$ at market opening to $\hat{\lambda}(0.80) = 0.037$ near resolution---maps naturally onto the benchmark: as information arrives over the contract's lifetime, residual event uncertainty $\tilde{\sigma}$ decreases, reducing $\lambda$. This interpretation is consistent with Ostrovsky (2012), who proves that in dynamic trading with separable securities, prices converge to the pooled-information posterior as trading proceeds.

Third, the negative coefficient on $\ln(\text{Volume})$ in the hierarchical model (Table~5) is consistent with equilibrium models of prediction market pricing under heterogeneous beliefs. He and Treich (2017) showed that prediction market prices equal mean beliefs if and only if the common utility function is logarithmic; for non-logarithmic utility, prices deviate systematically from physical probabilities. Greater trading activity, proxied by volume, is consistent with a more compressed pricing wedge---potentially through deeper participation, faster information aggregation, or stronger competition among traders and market makers.

\medskip
\noindent\textbf{Scope and limitations.}
Several caveats are essential. First, the benchmark assumes CARA utility, Gaussian uncertainty, and a representative agent. Prediction markets feature heterogeneous beliefs, non-Gaussian information arrivals (jumps), and diverse participant types. The benchmark provides a convenient closed-form interpretation, not a complete description of price formation.

Second, prediction market event contracts are typically unspanned: event outcomes such as elections, weather events, and sporting results have low or zero correlation with aggregate consumption or wealth. In a standard consumption-based asset pricing framework, this would imply $\lambda \approx 0$. A positive $\hat{\lambda}$ therefore suggests that the effective risk aversion governing prediction market pricing reflects factors beyond the consumption-CAPM---potentially including market incompleteness (Proposition~1), limited participation, or behavioral probability distortion.

Third, the estimated $\hat{\lambda}$ from Sections~5--6 remains a reduced-form object. It may absorb multiple forces simultaneously: rational risk compensation by risk-averse market makers, behavioral probability weighting (Snowberg and Wolfers, 2010; Jullien and Salani\'{e}, 2000), and microstructure frictions such as bid-ask spreads and stale quotes. The benchmark interpretation identifies one economically grounded channel---risk aversion applied to event uncertainty---but does not claim to decompose $\hat{\lambda}$ into its constituent sources. The empirical framework of this paper is reduced-form, and should be read accordingly.

---

# 4. Data and Descriptive Statistics

## 4.1 Data Sources and Sample Construction

**Primary sample (Polymarket).** I collect contract-level data from Polymarket via its public Gamma API (market metadata) and CLOB API (hourly price histories). The Gamma API provides market-level attributes including resolution outcome, trading volume, creation and resolution timestamps, and contract descriptions. The CLOB API provides hourly mid-price snapshots for each contract's trading history.

The raw sample consists of 15,525 resolved binary markets from February 24 to March 24, 2026, spanning 28 days. I apply the following filters: (i) exclude pure randomness markets (e.g., crypto "up or down" on 5-minute intervals, esports over/under markets); (ii) require at least 4 hourly price observations to ensure meaningful price dynamics; and (iii) restrict to $p \in (0.02, 0.98)$ to avoid boundary artifacts where the logit transformation amplifies noise. The final Polymarket estimation sample contains $N = 13{,}738$ contracts spanning sports, politics, crypto, economics, and other categories. For each contract, I extract the *opening price* (first 5\% of the market's lifetime) and the *resolution outcome* (1 if the event occurred, 0 otherwise). For the time-varying analysis (Section 5.4), I also extract prices at ten percentage-of-lifetime horizons and at fixed clock-time intervals before resolution.

For the cross-platform analysis (Section 5.5), I use a separate dataset: aligned daily prices for the Greenland acquisition contract on both Polymarket and Kalshi, collected via their respective APIs.

**Extended sample (cross-platform).** For the cross-platform validation (Section 6), I assemble four additional data sources: (i) Kalshi settled binary markets ($N = 271{,}699$) from both the historical and live API tiers, spanning 2021--2026, filtered to volume $\geq 100$ contracts and $p \in (0.02, 0.98)$; (ii) a Polymarket 2025 sample ($N = 985$) from HuggingFace (LightningRodLabs/outcome-rl-test-dataset), covering February--March 2025; (iii) multi-platform forecasting data ($N = 4{,}887$) from HuggingFace (YuehHanChen/forecasting), covering Metaculus, Good Judgment Open, INFER (formerly CSET-foretell), Polymarket, and Manifold questions from 2015--2024; and (iv) the primary Polymarket CLOB sample described above. The pooled cross-platform sample totals $N = 291{,}309$ resolved contracts.

## 4.2 Stylized Facts in Log-Odds Space

Before proceeding to the Wang transform calibration, I validate the log-odds state variable empirically. If log-odds is the correct state variable, its empirical properties should mirror those of equity log-returns, which have been extensively documented (Cont, 2001).

Table \ref{tab:distributional} compares distributional properties of raw price increments $\Delta p_t$ and log-odds increments $\Delta x_t$ for selected contracts.

\begin{table}[H]
\centering
\begin{tabular}{lrrrrr}
\toprule
Contract & $N$ & \multicolumn{2}{c}{Excess Kurtosis} & \multicolumn{2}{c}{Skewness} \\
\cmidrule(lr){3-4} \cmidrule(lr){5-6}
 & & $\Delta p$ & $\Delta x$ & $\Delta p$ & $\Delta x$ \\
\midrule
Fed No Change (hourly) & 628 & 7.0 & 6.0 & $-$0.50 & $-$0.14 \\
Fed Cut 25bps (hourly) & 613 & 11.3 & 6.5 & $-$0.24 & $-$0.26 \\
Greenland Acquisition (daily) & 89 & 16.8 & 12.1 & $-$2.02 & $-$1.04 \\
\bottomrule
\end{tabular}
\caption{Distributional properties of price increments. Log-odds increments have systematically lower excess kurtosis and reduced skewness, moving closer to the Gaussian benchmark.}
\label{tab:distributional}
\end{table}

Table \ref{tab:stylized_facts} confirms the broader correspondence with equity log-return stylized facts.

\begin{table}[H]
\centering
\begin{tabular}{lp{4.8cm}p{5.2cm}}
\toprule
Stylized Fact & Equity Log-Returns & Prediction Market $\Delta x_t$ \\
\midrule
Random walk & Log-prices: unit root (ADF); returns stationary & Levels $x_t$: unit root (ADF $t = -0.03$ to $-2.23$); $\Delta x_t$ stationary \\[3pt]
Fat tails & Excess kurtosis 3--50 & Excess kurtosis 6--12 \\[3pt]
Vol.\ clustering & $\rho(\Delta r^2_t, \Delta r^2_{t-1}) > 0$ & $\rho(\Delta x^2_t, \Delta x^2_{t-1}) = 0.13$--$0.14$*** \\[3pt]
Negative lag-1 AC & Bid-ask bounce & $\rho_1 = -0.11$ to $-0.17$*** \\[3pt]
Asymmetric vol. & Leverage effect & Event-driven spikes \\
\bottomrule
\end{tabular}
\caption{Stylized facts comparison. *** denotes significance at 1\%. Log-odds increments exhibit the same statistical signature as equity log-returns.}
\label{tab:stylized_facts}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig5_stylized_facts.png}
\caption{Log-odds stylized facts across 2,036 contracts (148,114 pooled increments). (a) Q-Q plot of $\Delta x$ against the normal distribution. (b) Distribution of $\Delta x$ with normal overlay. (c) Distribution of per-contract excess kurtosis. (d) Distribution of autocorrelation of squared increments (volatility clustering measure).}
\end{figure}

**Pooled sample statistics.** Across 2,036 contracts with sufficient price history (148,114 total log-odds increments), the median per-contract excess kurtosis is 9.0 (range 6--12 for well-traded contracts), confirming the fat-tail stylized fact. The median autocorrelation of squared increments---a nonparametric volatility clustering measure---is $\text{AC}_1(\Delta x^2_t) = 0.16$, confirming significant ARCH effects. An Engle ARCH(1) LM test on the pooled sample is overwhelmingly significant ($p < 10^{-20}$). Ljung-Box tests reject white noise in both $\Delta x$ ($Q_{10} = 91.3$, $p < 10^{-14}$) and $\Delta x^2$ ($Q_{10} = 131.0$, $p < 10^{-22}$).

These stylized facts---random-walk behavior in levels, fat tails, volatility clustering, and improved normality under the logit transformation---validate the log-odds state variable and support the diffusion-based modeling approach adopted in Section 3.2.

---

# 5. Empirical Results

## 5.1 Identification Strategy

The physical probability $p^*$ is unobservable at any individual-contract level. At resolution, one observes only the realized outcome $Y_i \in \{0,1\}$, not the ex ante probability. However, for a cross-section of resolved contracts, a calibration approach is available: by grouping contracts into bins by market price and computing the empirical resolution frequency $\hat{p}^*_k$ in each bin, one can estimate the relationship between market prices and physical probabilities under an exchangeability assumption---that contracts with similar market prices share similar physical probabilities.

From equation (1):

$$\lambda = \Phi^{-1}(p^{\text{mkt}}) - \Phi^{-1}(p^*)$$

The cross-sectional estimator is:

$$\hat{\lambda} = \frac{1}{K}\sum_{k=1}^K \left[\Phi^{-1}(\bar{p}_k^{\text{mkt}}) - \Phi^{-1}(\hat{p}_k^*)\right]$$

where $\bar{p}_k^{\text{mkt}}$ is the average market price in bin $k$ and $\hat{p}_k^*$ is the empirical resolution frequency.

## 5.2 Wang Parameter Estimation

**MLE estimation.** I estimate a global $\lambda$ by maximum likelihood. Under the Wang transform, the probability of resolution conditional on market price is $\Pr(Y_i = 1 \mid p_i^{\text{mkt}}) = \Phi(\Phi^{-1}(p_i^{\text{mkt}}) - \lambda)$, giving Bernoulli log-likelihood:

$$\hat{\lambda}_{MLE} = \arg\max_\lambda \sum_{i=1}^N \left[y_i \ln \hat{p}_i^*(\lambda) + (1 - y_i)\ln(1 - \hat{p}_i^*(\lambda))\right]$$

where $\hat{p}_i^*(\lambda) = \Phi(\Phi^{-1}(p_i^{\text{mkt}}) - \lambda)$. The standard error is computed from the observed Fisher information (numerical Hessian). A likelihood ratio test against $H_0: \lambda = 0$ (perfect calibration) has 1 degree of freedom.

**Binned calibration.** As a nonparametric complement, I group contracts into quantile bins by market price, compute the empirical resolution rate $\hat{p}^*_k$ in each bin, and estimate $\hat{\lambda}_k = \Phi^{-1}(\bar{p}_k^{\text{mkt}}) - \Phi^{-1}(\hat{p}_k^*)$ with bootstrap standard errors (2,000 replications).

\begin{table}[H]
\centering
\small
\caption{Wang transform calibration: Polymarket contract-level data (March 13--24, 2026; $N = 2{,}460$ contracts with $p \in (0.05, 0.95)$). $\hat{\lambda}$ per bin via $\hat{\lambda} = \Phi^{-1}(\bar{p}^{\text{mkt}}) - \Phi^{-1}(\hat{p}^*)$. Bootstrap standard errors from 2,000 replications; MLE via Bernoulli log-likelihood with observed Fisher information.}
\label{tab:calibration}
\begin{tabular}{rrrrrr}
\toprule
$\bar{p}^{\text{mkt}}$ & $\hat{p}^*$ & $N$ & $\hat{\lambda}$ & SE & 95\% CI \\
\midrule
0.079 & 0.061 & 164 & 0.138 & 0.159 & [$-$0.174, 0.449] \\
0.151 & 0.110 & 164 & 0.194 & 0.136 & [$-$0.073, 0.461] \\
0.217 & 0.161 & 174 & 0.207 & 0.116 & [$-$0.020, 0.434] \\
0.262 & 0.195 & 154 & 0.224 & 0.115 & [$-$0.001, 0.449] \\
0.331 & 0.345 & 171 & $-$0.040 & 0.101 & [$-$0.238, 0.158] \\
0.414 & 0.343 & 172 & 0.188 & 0.100 & [$-$0.007, 0.383] \\
0.463 & 0.311 & 151 & 0.400 & 0.109 & [0.186, 0.613] \\
0.489 & 0.303 & 251 & 0.489 & 0.084 & [0.325, 0.654] \\
0.499 & 0.382 & 374 & 0.299 & 0.066 & [0.169, 0.429] \\
0.505 & 0.514 & 142 & $-$0.023 & 0.105 & [$-$0.228, 0.183] \\
0.524 & 0.509 & 163 & 0.038 & 0.097 & [$-$0.152, 0.228] \\
0.595 & 0.606 & 142 & $-$0.026 & 0.108 & [$-$0.238, 0.185] \\
0.771 & 0.822 & 163 & $-$0.182 & 0.116 & [$-$0.410, 0.045] \\
\midrule
\textbf{Binned (wtd)} & & \textbf{2,460} & \textbf{0.173} & 0.029 & [0.116, 0.230] \\
\textbf{MLE} & & \textbf{2,460} & \textbf{0.176} & 0.027 & [0.123, 0.230] \\
\bottomrule
\end{tabular}
\end{table}

**Key findings:**

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig1_wang_calibration.png}
\caption{Wang transform calibration. (a) Market price vs.\ empirical resolution rate with MLE Wang fit ($\hat{\lambda} = 0.176$) and 95\% CI. Points are quantile bins, sized by $\sqrt{N}$. The Wang curve (red) captures the systematic overpricing relative to perfect calibration (dashed). (b) Bin-level $\hat{\lambda}_k$ with 95\% CIs, showing the FLB pattern (negative slope).}
\end{figure}

1. **$\hat{\lambda}_{MLE} = 0.176$ (SE $= 0.027$, $p = 7.1 \times 10^{-11}$).** The likelihood ratio test decisively rejects perfect calibration ($\chi^2 = 42.5$, $p < 10^{-10}$): prediction market prices embed a statistically significant positive risk premium.

2. **Consistent estimation.** The binned weighted average ($\hat{\lambda} = 0.173$, SE $= 0.029$) is within one standard error of the MLE, confirming robustness to the parametric functional form.

3. **Order of magnitude.** $\hat{\lambda} \approx 0.18$ is substantially below the catastrophe bond estimate of $\lambda \approx 0.45$ (Wang, 2004), consistent with prediction markets carrying lower risk loading than catastrophe insurance. This makes economic sense: much of event risk in prediction markets is idiosyncratic---unlike catastrophe exposure, which involves heavily correlated tail risk---though systematic factors (e.g., macro shocks, correlated political events) may introduce common risk components.

4. **Economic magnitude.** Under the estimated Wang transform, a contract with physical probability $p^* = 10\%$ trades at $\Phi(\Phi^{-1}(0.10) + 0.176) \approx 13.5\%$---an overpricing of 35\%. At $p^* = 50\%$, the market price is $\Phi(0.176) \approx 57.0\%$---a 7.0 cent premium on a \$1 contract.

5. **Bootstrap confirmation.** A nonparametric bootstrap (2,000 replications) yields SE $= 0.027$ and a 95\% CI of $[0.125, 0.229]$, virtually identical to the analytical estimates, confirming that the MLE is well-behaved and the Gaussian approximation is adequate.

6. **Expanded sample confirmation.** Extending the Polymarket sample from 12 to 28 days (February 24 to March 24, 2026; $N = 13{,}738$) yields $\hat{\lambda}_{MLE} = 0.166$ (SE $= 0.011$, LR $= 212.1$, $p < 10^{-15}$), confirming the primary estimate. The Wang correction reduces the Expected Calibration Error by 55.6\% and the Brier score by 1.9\% on this expanded sample.

7. **Non-constant $\hat{\lambda}$ across bins.** The bin-level estimates range from $-0.18$ to $+0.49$, with systematically higher values at lower prices---the favorite-longshot bias. This motivates the extended model in Section 5.3.

## 5.3 Cross-Sectional Determinants of $\lambda$

The non-constant $\hat{\lambda}$ across bins motivates allowing the risk loading to depend on contract characteristics. I estimate a one-stage probit model with known offset $z_i = \Phi^{-1}(p_i^{\text{mkt}})$, where the risk loading $\lambda_i = X_i\beta$ depends on contract characteristics:

$$\Pr(y_i = 1 \mid p_i^{\text{mkt}}, X_i) = \Phi\!\bigl(\Phi^{-1}(p_i^{\text{mkt}}) - X_i\beta\bigr)$$

This eliminates the generated-regressor problem inherent in the two-step approach (first estimating $\hat{\lambda}_i$ from smoothed resolution rates, then regressing on covariates), which understates standard errors by ignoring first-stage estimation error. The one-stage MLE jointly estimates all parameters by maximum likelihood, yielding correct standard errors without the need for bootstrap correction.

\begin{table}[H]
\centering
\small
\caption{One-stage hierarchical Wang MLE. Dependent variable: binary outcome $y_i$. Model: $\Pr(y_i = 1) = \Phi(\Phi^{-1}(p_i^{\text{mkt}}) - X_i\beta)$. Fisher and sandwich robust standard errors reported.}
\label{tab:hierarchical}
\begin{tabular}{lrrrrrr}
\toprule
 & \multicolumn{3}{c}{Full sample ($N = 13{,}274$)} & \multicolumn{3}{c}{12-day subsample ($N = 2{,}134$)} \\
\cmidrule(lr){2-4} \cmidrule(lr){5-7}
Variable & Coef. & SE (Fisher) & SE (Robust) & Coef. & SE (Fisher) & SE (Robust) \\
\midrule
Constant & 0.259$^{***}$ & (0.063) & (0.064) & 0.387$^{**}$ & (0.144) & (0.146) \\
$\ln(\text{Volume})$ & $-$0.072$^{***}$ & (0.005) & (0.005) & $-$0.100$^{***}$ & (0.013) & (0.013) \\
$\ln(\text{Duration})$ & 0.143$^{***}$ & (0.012) & (0.012) & 0.176$^{***}$ & (0.024) & (0.024) \\
$|p - 0.5|$ (extremity) & $-$0.477$^{***}$ & (0.100) & (0.099) & $-$0.698$^{**}$ & (0.252) & (0.259) \\
Spread & 0.127 & (0.384) & (0.423) & $-$10.000$^{*}$ & (4.466) & (5.893) \\
\midrule
Log-likelihood & \multicolumn{3}{r}{$-7{,}937.9$} & \multicolumn{3}{r}{$-1{,}263.5$} \\
LR test ($\lambda = \text{const}$) & \multicolumn{3}{r}{$\chi^2 = 361.3$, $p < 10^{-15}$} & \multicolumn{3}{r}{$\chi^2 = 124.5$, $p < 10^{-15}$} \\
AIC & \multicolumn{3}{r}{$15{,}885.8$} & \multicolumn{3}{r}{$2{,}537.1$} \\
$N$ & \multicolumn{3}{r}{13,274} & \multicolumn{3}{r}{2,134} \\
\bottomrule
\end{tabular}
\end{table}

**Results.** Three variables are statistically significant in both samples. (i) $\ln(\text{Volume})$ enters negatively ($\hat{\beta} = -0.072$, $p < 10^{-15}$), confirming that higher-liquidity markets carry lower risk premiums. (ii) $\ln(\text{Duration})$ enters positively ($\hat{\beta} = 0.143$, $p < 10^{-15}$), establishing a formal term structure of event risk---longer-duration contracts carry proportionally larger risk premiums (Section 5.6). (iii) \textit{Extremity} $|p - 0.5|$ enters negatively ($\hat{\beta} = -0.477$, $p < 10^{-5}$), indicating that contracts near 50\% (maximum uncertainty) carry the highest risk premiums, while extreme-probability contracts, where the outcome is more predictable, carry lower premiums. This is consistent with a Bayesian learning interpretation: the risk premium compensates for uncertainty about $p^*$, which is maximal at 50\%. Spread is not statistically significant on the full sample ($\hat{\beta} = 0.127$, $p = 0.76$), consistent with spread being a noisy proxy for illiquidity in this sample. A likelihood ratio test decisively rejects the null $\lambda_i = \text{const}$ ($\chi^2 = 361.3$, $p < 10^{-15}$), confirming that contract characteristics jointly explain significant variation in the risk loading. Fisher and robust (sandwich) standard errors are nearly identical, indicating that the probit variance function is well-specified.

## 5.4 Time-Varying Risk Premium

A novel finding emerges from measuring $\lambda$ at different points in the market's lifetime. Rather than estimating separate MLEs at each horizon---which ignores information across adjacent horizons and cannot impose smoothness---I estimate a stacked panel model where each contract contributes observations at nine percentage-of-lifetime horizons. The risk premium is modeled as a smooth function $f(\tau)$ of elapsed lifetime, estimated jointly by maximum likelihood with contract-clustered standard errors (Liang and Zeger, 1986):

$$\Pr(y_i = 1 \mid p_{it}) = \Phi\!\bigl(\Phi^{-1}(p_{it}) - f(\tau_{it}) - X_i\beta\bigr)$$

where $f(\tau) = \gamma_1 \tau + \gamma_2 \tau^2$ is a quadratic polynomial with the constraint $f(0) = 0$, so that $\beta_0$ captures the baseline risk loading at market opening. Each contract $i$ contributes up to nine rows (one per horizon $\tau \in \{0.05, 0.10, \ldots, 0.80\}$) with repeated outcome $y_i$. The stacked panel comprises 111,889 observations from 13,607 contracts (mean 8.2 observations per contract) on the full sample.

\begin{table}[H]
\centering
\small
\caption{Stacked panel time-varying $\hat{\lambda}$. Model: $\Pr(y_i = 1 \mid p_{it}) = \Phi(\Phi^{-1}(p_{it}) - f(\tau_{it}) - X_i\beta)$, where $f(\tau) = \gamma_1\tau + \gamma_2\tau^2$. Contract-clustered standard errors (Liang--Zeger). Specification (1) includes only the time-decay function; specification (2) adds cross-sectional covariates.}
\label{tab:stacked_panel}
\begin{tabular}{lrrrr}
\toprule
 & \multicolumn{2}{c}{(1) $f(\tau)$ only} & \multicolumn{2}{c}{(2) $f(\tau) + X_i\beta$} \\
\cmidrule(lr){2-3} \cmidrule(lr){4-5}
Parameter & Estimate & Cluster SE & Estimate & Cluster SE \\
\midrule
\textit{Time-decay parameters} & & & & \\
$\tau$ & $-$0.232$^{***}$ & (0.020) & $-$0.156$^{***}$ & (0.022) \\
$\tau^2$ & 0.151$^{***}$ & (0.025) & 0.074$^{**}$ & (0.025) \\
\midrule
\textit{Covariates} & & & & \\
Constant ($\beta_0$) & 0.170$^{***}$ & (0.012) & 0.253$^{***}$ & (0.064) \\
$\ln(\text{Volume})$ & --- & --- & $-$0.057$^{***}$ & (0.005) \\
$\ln(\text{Duration})$ & --- & --- & 0.109$^{***}$ & (0.012) \\
$|p - 0.5|$ (extremity) & --- & --- & $-$0.290$^{***}$ & (0.081) \\
Spread & --- & --- & 0.211 & (0.438) \\
\midrule
Log-likelihood & \multicolumn{2}{r}{$-65{,}074.4$} & \multicolumn{2}{r}{$-64{,}216.3$} \\
AIC & \multicolumn{2}{r}{$130{,}154.9$} & \multicolumn{2}{r}{$128{,}446.5$} \\
Contracts (clusters) & \multicolumn{2}{r}{13,607} & \multicolumn{2}{r}{13,607} \\
Total observations & \multicolumn{2}{r}{111,889} & \multicolumn{2}{r}{111,889} \\
\bottomrule
\end{tabular}
\end{table}

As a nonparametric validation, I also estimate a horizon fixed-effects specification with one dummy per horizon (reference: $\tau = 0.05$). All eight horizon dummies are significant ($p < 10^{-10}$) and monotonically decreasing, confirming that the quadratic polynomial provides an adequate smooth approximation to the unrestricted pattern.

\begin{figure}[H]
\centering
\includegraphics[width=0.85\textwidth]{fig_stacked_panel_f_tau_12day.png}
\caption{Time-varying risk premium: stacked panel estimate. The solid line shows the smooth function $\hat{\lambda}(\tau) = f(\tau) + \hat{\beta}_0$ estimated from the 12-day subsample ($N = 2{,}151$ contracts, $17{,}519$ stacked observations). The shaded band is a 95\% pointwise confidence interval based on contract-clustered standard errors. Red points with error bars show the per-horizon separate MLEs from the baseline calibration for comparison; the spline passes through all of them. The half-life (green triangle) is 33\% of contract lifetime.}
\label{fig:f_tau}
\end{figure}

The estimates show a clear monotonic decay. In the baseline no-covariates specification on the 12-day subsample, the risk loading falls from $\hat{\lambda}(0.05) = 0.173$ at market opening to $\hat{\lambda}(0.50) = 0.056$ at mid-life and $\hat{\lambda}(0.80) = 0.037$ near resolution, with a model-derived half-life of 33\% of contract lifetime. This is consistent with the per-horizon point estimates, which the smooth curve passes through (Figure \ref{fig:f_tau}). Adding covariates in specification (2) does not materially change the time-decay pattern: $\gamma_1$ and $\gamma_2$ remain significant and the covariate signs match those in Section 5.3.

On the full 28-day sample ($N = 13{,}607$ contracts, $111{,}889$ stacked observations), which includes a larger share of longer-duration contracts, the half-life extends to 77\% of contract lifetime, reflecting slower premium decay in contracts with greater residual uncertainty. The difference in half-lives across samples reveals that contract duration affects not only the \emph{level} of the risk premium (Table \ref{tab:hierarchical}) but also its \emph{persistence}: longer-horizon contracts exhibit both higher initial $\lambda$ and slower convergence toward zero. This reinforces the term structure of event risk documented in Section 5.6.

The time-varying pattern suggests that risk premiums are embedded in the initial price-setting process---by market makers or early traders---and are subsequently competed away as information arrives and the event probability is more precisely known. The result is consistent with a Bayesian learning model where initial uncertainty about $p^*$ commands a premium that shrinks as the posterior concentrates.

This time-varying pattern also provides a natural reconciliation of the literature: studies measuring calibration close to resolution (e.g., Page and Clemen, 2013) find prediction markets are approximately well-calibrated ($\lambda \approx 0$), while the Wang transform reveals that the \textit{initial} price formation embeds a non-trivial risk premium. Both findings are correct---they simply reflect different stages of the same dynamic process.

The per-horizon separate MLEs from the baseline calibration are reported in Appendix Table \ref{tab:horizons_appendix} for reference.

## 5.5 Cross-Platform Evidence

The framework predicts that the same event trades at different prices on Polymarket and Kalshi if the two platforms have different risk loadings $\lambda_P$ and $\lambda_K$. If $\lambda_K > \lambda_P$ (Kalshi has higher regulatory costs, smaller participant pool, lower liquidity), then Kalshi prices are systematically higher:

$$p_K - p_P = \Phi(\Phi^{-1}(p^*) + \lambda_K) - \Phi(\Phi^{-1}(p^*) + \lambda_P)$$

I test this prediction using aligned daily data for the Greenland acquisition contract. The data are consistent with the framework: the mean spread is $-5.73$ percentage points (Kalshi higher), with maximum divergence of 28.5 pp, consistent with $\lambda_K > \lambda_P$.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{analysis_greenland_cross_platform.png}
\caption{Cross-platform analysis: Greenland acquisition contract. Top-left: raw prices on both platforms. Top-right: log-odds transformation. Bottom-left: price spread (mean $-5.73$ pp, Kalshi higher). Bottom-right: Hasbrouck (1995) Information Share. The persistent Kalshi premium is consistent with $\lambda_K > \lambda_P$.}
\end{figure}

**Granger causality.** Table \ref{tab:granger} shows that Polymarket Granger-causes Kalshi at all tested lags, while the reverse holds only at lag 1.

\begin{table}[H]
\centering
\begin{tabular}{lrrlrr}
\toprule
 & \multicolumn{2}{c}{Poly $\to$ Kalshi} & & \multicolumn{2}{c}{Kalshi $\to$ Poly} \\
\cmidrule{2-3} \cmidrule{5-6}
Lag & $F$-stat & $p$-value & & $F$-stat & $p$-value \\
\midrule
1 & 17.372 & 0.0001*** & & 9.228 & 0.0036*** \\
2 & 3.887 & 0.0266** & & 2.411 & 0.0995 \\
3 & 4.789 & 0.0052*** & & 0.262 & 0.8525 \\
4 & 2.621 & 0.0466** & & 1.015 & 0.4093 \\
5 & 2.819 & 0.0271** & & 0.545 & 0.7414 \\
\bottomrule
\end{tabular}
\caption{Granger causality in log-odds space. Polymarket leads at all lags ($p < 0.05$); Kalshi influence is absorbed within one period.}
\label{tab:granger}
\end{table}

The Hasbrouck information share assigns a larger contribution to Kalshi, while Granger causality tests show Polymarket leads at all lags. This is not contradictory: information share measures the variance contribution to the common efficient price, while Granger causality captures the direction of lead-lag adjustment. Kalshi's larger information share likely reflects its higher price level (due to higher $\lambda_K$), which mechanically increases its variance contribution.

**Interpretation within the Wang framework.** If Polymarket leads in price discovery and both platforms converge to the same $p^*$ at resolution, then the convergence dynamics are driven by $\lambda_K$ adjusting toward $\lambda_P$---the regulated market gradually adopts the risk pricing of the more liquid, lower-friction platform. This extends the stock-options price discovery analysis of Muravyev, Pearson, and Broussard (2013) to prediction markets, with an additional structural explanation for *why* prices differ (different $\lambda$, not just different speeds of information incorporation). The finding is independently confirmed by Ng, Peng, Tao, and Zhou (2026).

## 5.6 Robustness

I conduct several robustness checks to verify that the Wang parameter estimate is not an artifact of sample construction or estimation methodology.

**Sensitivity to price range.** The MLE is insensitive to the price boundary cutoff used to exclude boundary artifacts:

\begin{table}[H]
\centering
\small
\caption{Sensitivity of $\hat{\lambda}_{MLE}$ to price range restrictions. The estimate is stable across all tested cutoffs.}
\begin{tabular}{lrrrr}
\toprule
Price range & $N$ & $\hat{\lambda}_{MLE}$ & SE & $p$-value \\
\midrule
$[0.01, 0.99]$ & 2,675 & 0.177$^{***}$ & 0.027 & $4.0 \times 10^{-11}$ \\
$[0.05, 0.95]$ (baseline) & 2,460 & 0.176$^{***}$ & 0.027 & $7.1 \times 10^{-11}$ \\
$[0.10, 0.90]$ & 2,291 & 0.178$^{***}$ & 0.028 & $9.2 \times 10^{-11}$ \\
$[0.15, 0.85]$ & 2,178 & 0.183$^{***}$ & 0.028 & $6.1 \times 10^{-11}$ \\
$[0.20, 0.80]$ & 2,012 & 0.183$^{***}$ & 0.029 & $1.9 \times 10^{-10}$ \\
\bottomrule
\end{tabular}
\end{table}

**Opening price construction.** The baseline opening price is the midpoint of the first 5\% of each contract's lifetime. To assess sensitivity to early-stage microstructure effects, I re-estimate the global $\hat{\lambda}$ using three alternative opening measures: (i) post-settle prices that skip the first two hourly observations, excluding listing noise; (ii) a five-price average of the first five distinct hourly prices; and (iii) a filtered sample retaining only contracts with non-stale quotes and below-median spreads.

\begin{table}[H]
\centering
\small
\caption{Sensitivity of $\hat{\lambda}_{MLE}$ to opening price construction. Each row uses a different method to extract the opening price from the hourly CLOB price history. All other estimation details are identical to the baseline specification (Section 5.2).}
\label{tab:opening_robustness}
\begin{tabular}{lrrrrr}
\toprule
Opening Measure & $N$ & $\hat{\lambda}_{MLE}$ & SE & $p$-value & $\Delta\%$ \\
\midrule
First-5\% midpoint (baseline) & 13,196 & 0.166$^{***}$ & 0.012 & $< 10^{-15}$ & --- \\
Post-settle (skip first 2h) & 13,098 & 0.149$^{***}$ & 0.012 & $< 10^{-15}$ & $-$10.1\% \\
5-price average & 13,221 & 0.154$^{***}$ & 0.012 & $< 10^{-15}$ & $-$7.2\% \\
Filtered (non-stale, low-spread) & 9,010 & 0.131$^{***}$ & 0.014 & $< 10^{-15}$ & $-$20.7\% \\
\bottomrule
\end{tabular}
\end{table}

The risk premium remains highly significant ($p < 10^{-15}$) across all four measures, with estimates ranging from 0.131 to 0.166. The most conservative measure---filtering out stale quotes and high-spread contracts---reduces $\hat{\lambda}$ by approximately 21\%, suggesting that roughly four-fifths of the baseline estimate reflects genuine risk compensation rather than microstructure artifacts. Covariate signs and the volume-stratified pattern ($\hat{\lambda} \approx 0$ in very-high-volume markets) are unchanged across all measures.

**Sensitivity to bin count.** The nonparametric binned estimator is stable across $K = 5$ to $K = 25$ quantile bins, with a range of $[0.168, 0.182]$---well within the MLE's confidence interval.

**Contract duration.** A striking pattern emerges when the sample is split by contract duration:

\begin{table}[H]
\centering
\small
\caption{Wang parameter by contract duration. The risk premium increases monotonically with duration (Spearman $\rho = 0.90$, $p = 0.037$), establishing a term structure of event risk. Short-duration contracts ($<$24h) show mixed results---including a significant \textit{negative} $\hat{\lambda}$ at 6--24h---while longer contracts exhibit large positive risk premiums.}
\begin{tabular}{lrrrr}
\toprule
Duration & $N$ & $\hat{\lambda}_{MLE}$ & SE & $p$-value \\
\midrule
2--6h & 235 & 0.078 & 0.082 & 0.342 \\
6--24h & 395 & $-$0.138$^{*}$ & 0.065 & 0.034 \\
1--3d & 494 & 0.121$^{*}$ & 0.059 & 0.041 \\
3--7d & 718 & 0.227$^{***}$ & 0.055 & $<0.001$ \\
$>$7d & 618 & 0.444$^{***}$ & 0.056 & $<0.001$ \\
\bottomrule
\end{tabular}
\end{table}

This pattern is economically intuitive: short-duration contracts resolve quickly, leaving little time for risk premiums to accumulate; longer contracts face greater uncertainty about $p^*$ and command correspondingly larger loadings. The monotonic increase in $\hat{\lambda}$ with duration is consistent with a term-structure of event risk.

**Jackknife.** A leave-10\%-out jackknife (50 replications) yields a mean $\hat{\lambda} = 0.176$ with SE $= 0.009$ and range $[0.148, 0.198]$, confirming that no small subset of markets is driving the result.

**Monte Carlo validation.** To verify that the MLE is unbiased and the confidence interval has correct coverage, I simulate 1,000 datasets from the Wang model with $\lambda_{\text{true}} = 0.176$ and $N = 2{,}460$. The results confirm the estimator's properties:

\begin{table}[H]
\centering
\small
\caption{Monte Carlo validation of MLE ($\lambda_{\text{true}} = 0.176$, $N = 2{,}460$, 1,000 simulations).}
\begin{tabular}{lr}
\toprule
Statistic & Value \\
\midrule
Mean recovered $\hat{\lambda}$ & 0.176 \\
Bias & 0.000 \\
SE (simulated) & 0.028 \\
SE (analytical) & 0.027 \\
95\% CI coverage & 95.1\% \\
RMSE & 0.028 \\
\bottomrule
\end{tabular}
\end{table}

The coverage is virtually identical to the nominal 95\%, the bias is negligible, and the simulated SE closely matches the analytical SE, confirming that the estimator is well-calibrated at the sample size of this study.

**Bayesian analysis.** A Bayesian posterior for $\lambda$ using a weakly informative $N(0, 0.5^2)$ prior yields a posterior mean of $0.176$ with 95\% highest posterior density interval $[0.123, 0.229]$, virtually identical to the frequentist MLE. The posterior probability of $\lambda > 0$ is approximately 1.0, and the Bayes factor in favor of a positive risk premium exceeds $10^{10}$---decisive evidence by any conventional threshold.

**Expected Calibration Error (ECE).** The Wang correction reduces the Expected Calibration Error from 0.077 (raw) to 0.057 (corrected), a 26.5\% reduction. This exceeds the Brier score improvement because ECE directly measures systematic miscalibration rather than overall forecast accuracy.

**Comparison with alternative recalibration methods.** The Wang transform achieves the same Brier score improvement as logistic recalibration using only one parameter rather than two:

\begin{table}[H]
\centering
\small
\caption{Brier score comparison across recalibration methods. The Wang transform (1 parameter) achieves the same improvement as logistic recalibration (2 parameters).}
\begin{tabular}{lrrr}
\toprule
Model & Parameters & Brier Score & Improvement \\
\midrule
Naive (no correction) & 0 & 0.2018 & --- \\
Wang transform ($\lambda$) & 1 & 0.1978 & $+2.03\%$ \\
Linear recalibration & 2 & 0.1982 & $+1.82\%$ \\
Logistic recalibration & 2 & 0.1974 & $+2.20\%$ \\
Isotonic regression & $N$ & 0.1919 & $+4.96\%$ \\
\bottomrule
\end{tabular}
\end{table}

The Wang transform's parsimony is notable: with a single parameter it achieves a 2.03\% Brier score improvement, outperforming the two-parameter linear recalibration (1.82\%) and approaching the logistic model (2.20\%). The isotonic regression (4.96\%) provides an upper bound on calibration improvement but uses $N$ parameters and lacks economic interpretability. The improvement is economically meaningful: the Wang correction reduces the Brier score from 0.2018 to 0.1978, implying that treating prediction market prices as raw probabilities incurs a systematic and quantifiable forecasting cost. The Hosmer--Lemeshow test (Hosmer and Lemeshow, 2000) rejects perfect calibration ($\chi^2 = 28.8$, $p < 0.001$), confirming that the risk premium is real and non-negligible.

**Temporal stability.** Splitting the sample into first half (March 13--18) and second half (March 18--24) yields $\hat{\lambda}_1 = 0.193$ (SE $= 0.038$) and $\hat{\lambda}_2 = 0.160$ (SE $= 0.039$), with no significant difference ($z = 0.60$, $p = 0.55$). This confirms that the risk premium estimate is stable across the sample period.

**Out-of-sample validation.** A five-fold cross-validation confirms that the Wang correction generalizes beyond the training sample: $\hat{\lambda}$ is stable across folds ($0.177 \pm 0.009$) and the out-of-sample Brier improvement is 1.99\%, comparable to the in-sample improvement of 2.03\%. A paired $t$-test on per-observation Brier differences between the naive and Wang-corrected forecasts is highly significant ($t = 3.49$, $p = 0.0005$), confirming that the improvement is not driven by overfitting or chance.

**Category-specific analysis.** I classify contracts into five categories using keyword matching on market questions and estimate $\hat{\lambda}$ separately for each.\footnote{Categories are assigned by regex matching on contract titles: Sports (NBA, NFL, UFC, etc.), Politics (election, president, congress, etc.), Crypto (bitcoin, ethereum, etc.), Science/Tech (Apple, Google, AI, SpaceX, etc.), and Other (residual). Each contract is assigned to the first matching category; unmatched contracts default to Other. Full keyword lists are available upon request.}

\begin{table}[H]
\centering
\small
\caption{Wang parameter by event category. The risk premium varies substantially across categories. Sports and politics markets---where informed trading is pervasive---show insignificant $\lambda$, while less-liquid categories exhibit significant positive premiums.}
\begin{tabular}{lrrrrl}
\toprule
Category & $N$ & $\hat{\lambda}_{MLE}$ & SE & 95\% CI & $p$-value \\
\midrule
Sports & 973 & 0.070 & 0.042 & [$-$0.012, 0.151] & 0.092 \\
Politics & 71 & 0.054 & 0.157 & [$-$0.253, 0.362] & 0.730 \\
Crypto & 305 & 0.253$^{***}$ & 0.077 & [0.101, 0.404] & 0.001 \\
Science/Tech & 414 & 0.268$^{***}$ & 0.079 & [0.112, 0.423] & 0.001 \\
Other & 692 & 0.282$^{***}$ & 0.051 & [0.182, 0.381] & $<0.001$ \\
\bottomrule
\end{tabular}
\end{table}

The cross-category variation is striking: sports markets ($\hat{\lambda} = 0.070$, insignificant) and politics markets ($\hat{\lambda} = 0.054$, insignificant) exhibit near-zero risk premiums, consistent with deep liquidity and informed participation in these categories. In contrast, crypto ($\hat{\lambda} = 0.253$), science/tech ($\hat{\lambda} = 0.268$), and other categories ($\hat{\lambda} = 0.282$) show large, significant premiums. This pattern is consistent with the volume effect (Section 5.3): sports and politics markets attract the most volume and the risk premium is competed to zero.

**Volume-stratified analysis.** Stratifying by trading volume reveals that the aggregate risk premium is driven entirely by low- and medium-volume contracts:

\begin{table}[H]
\centering
\small
\caption{Wang parameter by trading volume. High-volume markets ($>$\$10K) show zero risk premium; the aggregate $\hat{\lambda} = 0.176$ is driven by less-liquid contracts.}
\begin{tabular}{lrrrr}
\toprule
Volume tier & $N$ & $\hat{\lambda}_{MLE}$ & SE & $p$-value \\
\midrule
Low ($<$\$500) & 352 & 0.354$^{***}$ & 0.071 & $<0.001$ \\
Medium (\$500--\$2K) & 540 & 0.285$^{***}$ & 0.057 & $<0.001$ \\
High (\$2K--\$10K) & 600 & 0.316$^{***}$ & 0.059 & $<0.001$ \\
Very high ($>$\$10K) & 968 & $-$0.031 & 0.043 & 0.472 \\
\bottomrule
\end{tabular}
\end{table}

This finding has implications for market efficiency: the Wang risk premium vanishes in the most liquid markets, where competitive trading eliminates mispricing. The residual premium in low-volume markets is consistent with illiquidity-driven overpricing, analogous to the small-stock premium in equities.

**Power analysis.** Monte Carlo power simulations using the empirical price distribution establish minimum sample size requirements. At the estimated effect size ($\lambda = 0.18$), the MLE achieves $>95\%$ power with $N \geq 1{,}000$ contracts and essentially 100\% power at $N \geq 2{,}000$. At smaller effect sizes ($\lambda = 0.10$), $N \geq 2{,}000$ is needed for 93\% power; at $\lambda = 0.05$, even $N = 3{,}000$ yields only 56\% power, explaining why the risk premium may go undetected in smaller samples.

**Information half-life.** The stacked panel spline model (Section 5.4) directly yields a model-based half-life of 33\% of contract lifetime on the 12-day subsample: the risk premium is halved by the time a contract has lived one-third of its duration. On the full 28-day sample---which includes more long-duration contracts---the half-life extends to 77\%, consistent with longer-horizon contracts exhibiting slower premium convergence.

**Stacked panel knot sensitivity.** The stacked panel results are robust to the functional form of $f(\tau)$: linear ($K=1$), quadratic ($K=2$), and cubic ($K=3$) polynomial bases all yield monotonically decreasing $f(\tau)$ with comparable AIC (130,157 for linear; 130,155 for quadratic; 130,157 for cubic). A horizon fixed-effects specification with 8 dummies confirms the smooth-function restriction: all dummies are significant and monotonically decreasing. Leave-one-duration-quintile-out analysis shows that $f(\tau)$ is monotonically decreasing in all five subsamples, with $\hat{\lambda}$ at opening ranging from 0.113 to 0.197---confirming stability across the duration distribution.

**Generalized distortion test.** A natural concern is whether the one-parameter Wang specification is too restrictive. I test the generalized model $\Pr(Y = 1 \mid p^{\text{mkt}}) = \Phi(a + b \cdot \Phi^{-1}(p^{\text{mkt}}))$, where $b = 1$ recovers the Wang transform and $a = -\lambda$. Estimating by MLE on the primary sample yields $\hat{a} = -0.164$ (SE $= 0.029$) and $\hat{b} = 1.081$ (SE $= 0.062$). A likelihood ratio test fails to reject the restriction $b = 1$ ($\chi^2 = 1.71$, $p = 0.19$), confirming that the one-parameter Wang specification is empirically adequate. The two-parameter model does not significantly improve fit over the parsimonious Wang transform.

**External benchmark validation.** As a complementary identification strategy, I construct an external benchmark that replaces ex-post resolution outcomes with an independent probability estimate derived entirely outside Polymarket: a pre-game Elo rating model for NBA basketball (see Appendix B for model details and validation). I match 51 Polymarket NBA game contracts to Elo pre-game probabilities and compute the contract-level Wang parameter as $\hat{\lambda}_i = \Phi^{-1}(p_i^{\text{Polymarket}}) - \Phi^{-1}(\hat{p}_i^{\text{Elo}})$. The mean $\hat{\lambda}_i$ is $0.125$ (SE $= 0.049$, $p = 0.014$; Wilcoxon $p = 0.020$), significantly positive and of the same order of magnitude as the Sports category pooled MLE ($\hat{\lambda} = 0.070$). Table \ref{tab:external_benchmark} and Figure \ref{fig:lambda_nba_external} report the full results. The Elo model is noisier than sportsbook closing lines (Brier score 0.218 vs.\ approximately 0.20 for sharp books), so the external-benchmark $\hat{\lambda}$ should be interpreted as an upper bound. Replication with sportsbook closing-line data---available from commercial providers---would provide a sharper test. Nonetheless, the directional finding is clear: an independent physical-probability proxy confirms a positive and significant wedge between Polymarket prices and fundamental value, consistent with the risk premium identified through the pooled MLE.

\input{outputs/tables/external_benchmark_results.tex}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{outputs/figures/fig_lambda_nba_external.png}
\caption{External benchmark: contract-level $\hat{\lambda}_i$ for 51 NBA game contracts. Panel (a): $\hat{\lambda}_i$ versus $\ln(\text{Volume})$; the Spearman correlation is small and insignificant. Panel (b): distribution of $\hat{\lambda}_i$, with mean $= 0.125$ and median $= 0.099$, both positive. The distribution is centered above zero, consistent with a positive risk premium.}
\label{fig:lambda_nba_external}
\end{figure}

---

# 6. Cross-Platform and Extended Sample Validation

The primary calibration in Section 5 uses Polymarket data from a single platform over a limited time window. To establish that the positive Wang parameter is a robust feature of prediction markets rather than a platform- or period-specific artifact, I estimate $\hat{\lambda}_{MLE}$ across eight data sources spanning six platforms, multiple years, and $N = 291{,}309$ total contracts.

## 6.1 Cross-Platform Comparison

Table \ref{tab:cross_platform} reports Wang parameter estimates for each data source. The estimation procedure is identical to Section 5.2: Bernoulli MLE with standard errors from the numerical Hessian.

\begin{table}[H]
\centering
\small
\caption{Cross-platform Wang parameter estimates. All real-money platforms exhibit $\hat{\lambda} > 0$ (positive risk premium). Manifold, a play-money platform, shows $\hat{\lambda} < 0$ (overconfidence). Pooled estimate across all sources: $\hat{\lambda} = 0.183$ (SE $= 0.003$).}
\label{tab:cross_platform}
\begin{tabular}{lrrrrrr}
\toprule
Platform & $N$ & $\hat{\lambda}_{MLE}$ & SE & LR stat & $p$-value & Period \\
\midrule
Polymarket (CLOB) & 13,738 & 0.166$^{***}$ & 0.011 & 212.1 & $<10^{-15}$ & 2026 \\
Polymarket (2025) & 985 & 0.143$^{**}$ & 0.045 & 10.3 & 0.001 & 2025 \\
Polymarket (forecasting) & 579 & 0.013 & 0.056 & 0.1 & 0.813 & 2015--2024 \\
Kalshi & 271,699 & 0.187$^{***}$ & 0.003 & 3,186.0 & $<10^{-15}$ & 2021--2026 \\
Metaculus & 1,845 & 0.287$^{***}$ & 0.033 & 76.1 & $<10^{-15}$ & 2015--2024 \\
Good Judgment Open & 692 & 0.570$^{***}$ & 0.055 & 111.5 & $<10^{-15}$ & 2015--2024 \\
INFER & 90 & 0.635$^{***}$ & 0.180 & 13.7 & $<0.001$ & 2015--2024 \\
Manifold (play-money) & 1,681 & $-$0.218$^{***}$ & 0.032 & 45.8 & $<10^{-11}$ & 2015--2024 \\
\midrule
\textbf{Pooled (all)} & \textbf{291,309} & \textbf{0.183}$^{***}$ & \textbf{0.003} & \textbf{3,420.4} & $<10^{-15}$ & 2015--2026 \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig14_cross_platform.png}
\caption{Cross-platform Wang parameter estimates with 95\% confidence intervals. All real-money platforms exhibit $\hat{\lambda} > 0$; the play-money platform Manifold shows $\hat{\lambda} < 0$, consistent with overconfidence absent financial stakes. The pooled estimate (gray band) is $\hat{\lambda} = 0.183 \pm 0.006$.}
\end{figure}

**Key findings from the cross-platform analysis:**

1. **Universality of the positive risk premium.** Every traded-contract platform---whether blockchain-based (Polymarket) or CFTC-regulated (Kalshi)---exhibits a statistically significant positive $\hat{\lambda}$. The forecasting platforms (Metaculus, Good Judgment Open, INFER), which operate as prediction tournaments with reputational or prize-based incentives rather than direct financial risk, also show $\hat{\lambda} > 0$, suggesting the distortion extends beyond traditional market settings---though the economic interpretation differs, as participants on these platforms do not bear financial risk in the same sense as on traded-contract venues.

2. **Magnitude gradient.** The risk premium increases with market friction and participant expertise: Polymarket ($\hat{\lambda} \approx 0.15$--$0.17$) $<$ Kalshi ($\hat{\lambda} = 0.19$) $<$ Metaculus ($\hat{\lambda} = 0.29$) $<$ Good Judgment Open ($\hat{\lambda} = 0.57$). This gradient is consistent with the liquidity effect documented in Section 5.3: platforms with deeper liquidity and more sophisticated participants exhibit lower risk premiums.

3. **Play-money control.** Manifold Markets, where participants trade with play-money tokens, exhibits a significant \textit{negative} $\hat{\lambda} = -0.218$ ($p < 10^{-11}$). This is consistent with overconfidence: absent real financial stakes, participants overstate their confidence in event outcomes, pushing prices beyond physical probabilities in the opposite direction from the risk premium observed on real-money platforms. The play-money result provides a natural placebo test for the risk-based interpretation of $\lambda > 0$.

4. **Consistency across Polymarket samples.** The 2025 Polymarket sample ($\hat{\lambda} = 0.143$) and the 2026 CLOB sample ($\hat{\lambda} = 0.166$) yield estimates within one standard error of each other, confirming temporal stability within the same platform.

**Cross-platform covariate heterogeneity.** A one-stage hierarchical MLE on the Kalshi sample ($N = 200{,}226$) yields covariate signs reversed relative to the Polymarket opening-price specification. A timing-ladder diagnostic---re-estimating the Polymarket model at four lifecycle points (5\%, 20\%, 50\%, 80\%)---shows strict monotonic convergence toward the Kalshi coefficient pattern: the $L_1$ distance between the Polymarket and Kalshi slope vectors falls from 1.033 at 5\% to 0.651 at 80\%, a 37\% reduction. However, no Polymarket coefficient changes sign even at the latest timing point, implying that price timing explains a substantial share, but not all, of the cross-platform gap. Additional diagnostic evidence indicates that the remaining difference is consistent with Kalshi's concentration in short-duration contracts (86.9\% have duration $< 24$ hours) and broader differences in contract ecology and market microstructure. I therefore interpret the cross-platform covariate differences as a measurement- and composition-sensitive heterogeneity result, rather than as evidence that either platform's risk-premium structure falsifies the other. Details are reported in Appendix~A.

## 6.2 Temporal Stability: Kalshi Year-by-Year

The Kalshi dataset, with $N = 271{,}699$ contracts spanning 2021--2026, permits a year-by-year analysis of temporal stability. Table \ref{tab:kalshi_temporal} reports annual estimates.

\begin{table}[H]
\centering
\small
\caption{Kalshi Wang parameter by year. The risk premium is consistently positive and significant across all years with sufficient sample size, with $\hat{\lambda} \in [0.15, 0.27]$.}
\label{tab:kalshi_temporal}
\begin{tabular}{lrrrrl}
\toprule
Year & $N$ & $\hat{\lambda}_{MLE}$ & SE & LR stat & Significance \\
\midrule
2021 & 334 & 0.042 & 0.095 & 0.2 & n.s. \\
2022 & 3,814 & 0.222$^{***}$ & 0.030 & 57.0 & $p < 10^{-13}$ \\
2023 & 8,769 & 0.153$^{***}$ & 0.018 & 70.6 & $p < 10^{-15}$ \\
2024 & 16,092 & 0.174$^{***}$ & 0.014 & 147.6 & $p < 10^{-15}$ \\
2025 & 18,079 & 0.272$^{***}$ & 0.014 & 411.7 & $p < 10^{-15}$ \\
2026 & 224,611 & 0.182$^{***}$ & 0.004 & 2,548.3 & $p < 10^{-15}$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig15_kalshi_temporal.png}
\caption{Kalshi Wang parameter estimates by year with 95\% CIs. The risk premium is consistently positive across 2022--2026, with year-to-year variation that may reflect changing market composition, regulatory environment, and participant base. The 2021 estimate is insignificant due to small sample size ($N = 334$).}
\end{figure}

The temporal analysis reveals several patterns: (i) the Wang parameter is consistently positive and significant across all years with sufficient data ($N > 1{,}000$); (ii) the range $\hat{\lambda} \in [0.15, 0.27]$ is remarkably stable given the rapid growth of Kalshi's market over this period (from 334 settled contracts in 2021 to 224,611 in 2026); (iii) the 2025 estimate ($\hat{\lambda} = 0.272$) is the highest, potentially reflecting the surge of retail participation during the 2024 U.S. presidential election cycle and its aftermath.

## 6.3 Discussion

The cross-platform results have three implications for the theoretical framework:

First, the positive $\lambda$ is not a microstructure artifact. It persists across centralized limit order books (Polymarket, Kalshi) and forecasting tournaments (Metaculus, GJ Open), which have fundamentally different price formation mechanisms. This suggests that the risk premium is intrinsic to prediction markets as an asset class, consistent with the incomplete market interpretation in Section 3.

Second, the magnitude gradient across platforms is consistent with the liquidity-premium hypothesis: deeper, more efficient markets price risk more aggressively, shrinking the wedge between market prices and physical probabilities. The convergence of Polymarket and Kalshi estimates ($\hat{\lambda}_P = 0.166$ vs. $\hat{\lambda}_K = 0.187$) suggests that as both platforms mature and attract institutional flow, the risk premium is being competed toward a common equilibrium level.

Third, the Manifold result ($\hat{\lambda} < 0$) provides a natural placebo test for the risk premium mechanism. When the financial channel is shut off (play-money), the risk premium vanishes and is replaced by overconfidence. This is difficult to reconcile with purely behavioral explanations of the FLB (e.g., probability weighting), which should operate identically whether or not real money is at stake. The sign reversal supports the risk-based interpretation: $\lambda > 0$ on real-money platforms reflects compensation for bearing event risk, not cognitive bias.

---

# 7. Extensions

## 7.1 Event Implied Volatility

The log-odds framework yields a natural volatility measure, though care is needed to distinguish two related but distinct objects.

**Model-implied EIV.** Under the baseline model (Section 3.2), a latent information state $S_t$ drives the physical probability via $p_t^* = \Phi(S_t / (\sigma\sqrt{\tau}))$, where $S_T \mid S_t \sim N(S_t, \sigma^2\tau)$ and the event occurs iff $S_T > 0$. Inverting gives $S_t = \sigma\sqrt{\tau} \cdot \Phi^{-1}(p_t)$. The *model-implied Event Implied Volatility* is:

$$\sigma_{\text{EIV}} = \frac{S_t}{\sqrt{\tau} \cdot \Phi^{-1}(p_t)} = \sigma$$

which recovers the model's belief volatility parameter $\sigma$ by construction. Note that $S_t$ is a latent information state distinct from the observed log-odds $x_t = \text{logit}(p_t)$; the logit and probit functions are approximately proportional ($\text{logit}(p) \approx (\pi/\sqrt{3}) \cdot \Phi^{-1}(p)$), so the qualitative properties carry over, but the ratio $x_t / \Phi^{-1}(p_t)$ is not constant and is undefined at $p = 0.5$.

**Empirical (realized) event volatility.** Separately, the realized event volatility is the rolling annualized standard deviation of log-odds increments:

$$\widehat{\sigma}_{\text{realized}}(t) = \text{sd}(\Delta x_{t-w}, \ldots, \Delta x_t) \times \sqrt{N_{\text{ann}}}$$

This is analogous to the implied-vs-realized volatility distinction in equity options: the model-implied EIV is a theoretical construct derived from the pricing formula, while the realized measure is computed directly from observed price movements.

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{analysis_eiv_Fed_No_Change_Apr_2026.png}
\caption{Event Implied Volatility for the Fed ``No Change'' contract (Polymarket, hourly). EIV exhibits clear volatility clustering (ARCH effect), with periods of elevated uncertainty followed by mean-reversion.}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{analysis_eiv_Greenland_Acquisition.png}
\caption{EIV for the Greenland acquisition contract (Polymarket, daily). The mid-January spike coincides with Trump administration statements; EIV decays as the market digests information, consistent with information arrival models (Easley and O'Hara, 1992).}
\end{figure}

EIV provides a descriptive tool for measuring the rate of probability revision---conceptually related to realized volatility measures in equity markets, though not directly analogous to the VIX, which is derived from option-implied volatilities. Combined with the Wang transform, it offers a two-dimensional characterization of prediction market contracts: $\lambda$ captures the level of risk premium, while $\sigma_{\text{EIV}}$ captures the rate of information arrival.

**Cross-contract empirical distribution.** To move beyond case studies, I compute realized event volatility for all $N = 14{,}406$ contracts with $\geq 20$ hourly price observations, using a rolling window of $w = 10$ observations and annualizing by $\sqrt{8{,}760}$. Table \ref{tab:eiv_summary} reports the cross-sectional distribution. The median annualized realized volatility is $\hat{\sigma}_{\text{realized}} = 5.31$, with substantial right skew (mean $= 12.54$) and wide interquartile range $[1.52, 16.73]$. Crypto contracts exhibit the highest median volatility ($11.99$), followed by Tech ($14.06$) and Politics ($8.64$); Sports contracts cluster near the overall median ($5.50$). Volume has negligible correlation with realized volatility (Spearman $\rho = 0.015$, $p = 0.10$), suggesting that EIV captures information arrival intensity rather than liquidity effects.

An ARCH(1) Lagrange multiplier test on squared log-odds increments rejects the null of no volatility clustering at the 5\% level for 22.4\% of contracts ($3{,}231$ out of $14{,}406$), confirming that volatility clustering---a hallmark of financial time series (Cont, 2001)---is present in a substantial fraction of prediction market contracts. The rejection rate varies by category: Crypto contracts show the highest clustering (35\%), consistent with the speculative dynamics in digital asset markets, while Sports contracts show the lowest (12\%), consistent with information arriving in discrete bursts (game outcomes) rather than continuous flow.

\input{outputs/tables/eiv_summary_stats.tex}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{fig_eiv_distribution.png}
\caption{Cross-contract distribution of realized event volatility. Panel (a): scatter of $\hat{\sigma}_{\text{realized}}$ against $\ln(\text{Volume})$, colored by event category; the OLS line (slope $= -0.46$) and Spearman rank correlation ($\rho = 0.015$, $p = 0.10$) confirm negligible volume--volatility association. Panel (b): box plots by category, showing Crypto and Tech contracts exhibit higher and more dispersed realized volatility than Sports or Politics.}
\label{fig:eiv_distribution}
\end{figure}

## 7.2 Hazard Rate Term Structure

This section presents a theoretical extension that awaits empirical implementation; current data limitations prevent successful calibration, as discussed below.

For events with contracts at multiple maturities $T_1 < T_2 < \cdots < T_n$, the framework extends to an event hazard rate term structure. Define the event intensity:

$$h(t) = -\frac{d}{dt}\ln(1 - p^*(t))$$

**Procedure:**

1. **Strip risk premium**: $\hat{p}_i^* = \Phi(\Phi^{-1}(p_i^{\text{mkt}}) - \hat{\lambda})$
2. **Bootstrap hazard rates**: $\hat{h}_i = -[\ln(1-\hat{p}_i^*) - \ln(1-\hat{p}_{i-1}^*)]\,/\,(T_i - T_{i-1})$
3. **Parameterize** with Nelson-Siegel:

$$h(T) = \beta_0 + \beta_1 \frac{1-e^{-T/\tau}}{T/\tau} + \beta_2\left(\frac{1-e^{-T/\tau}}{T/\tau} - e^{-T/\tau}\right)$$

This is directly analogous to CDS curve bootstrapping in credit markets: strip the risk premium, extract default intensities, and fit a parametric term structure. The analogy is suggestive: a prediction market contract on "event $E$ occurs by time $T$" is structurally similar to a credit default swap on "entity $X$ defaults by time $T$," with $h(t)$ playing the role of the default intensity. This hazard rate extension does not appear to have been explored in the prediction market literature.

**Empirical feasibility.** A systematic search of the current sample identifies 16 multi-maturity contract families (same event, $\geq 3$ expiry dates). However, the bootstrapped hazard rates are noisy: most families have closely spaced maturities (often created simultaneously with different resolution dates), producing extreme or negative point estimates of $\hat{h}_i$. Nelson-Siegel fitting fails to converge for all 16 families. The hazard rate term structure thus remains a theoretical extension; empirical implementation at scale requires multi-maturity contract data with well-separated expiry dates---a data structure that may become available as prediction markets mature and exchanges begin listing standardized maturity strips for recurring events (e.g., monthly employment reports, quarterly GDP releases).

---

# 8. Conclusion

This paper has proposed a pricing and decomposition framework for prediction markets---an asset class that, despite annualized trading volumes exceeding \$50 billion across major platforms\footnote{Based on Polymarket monthly volumes of \$2--5 billion (source: Dune Analytics) and Kalshi's reported settlement volumes, annualized industry activity reaches this order of magnitude, though no single authoritative aggregate series exists.}, has lacked the theoretical infrastructure available to equities, options, credit, and fixed income. The framework rests on three pillars: a log-odds state variable, a diffusion-based dynamics specification, and a Wang transform risk premium decomposition. The central observation, rooted in Manski (2006) and formalized here, is that prediction markets are *incomplete*: no replication argument pins down a unique price, so observed prices embed both event probability and a risk premium. The Wang transform layer offers a single-parameter decomposition that separates the two, and generates the favorite-longshot bias as a direct mathematical consequence.

The empirical results support the framework across multiple dimensions. Contract-level calibration on 2,460 Polymarket contracts yields a statistically significant positive risk premium ($\hat{\lambda}_{MLE} = 0.176$, $p < 10^{-10}$), confirmed on an expanded 28-day sample ($N = 13{,}738$, $\hat{\lambda} = 0.166$). Cross-platform validation on $N = 291{,}309$ contracts across Polymarket, Kalshi, Metaculus, Good Judgment Open, and INFER yields a pooled estimate of $\hat{\lambda} = 0.183$ (SE $= 0.003$), with every real-money platform exhibiting a significant positive risk premium. The play-money platform Manifold shows $\hat{\lambda} = -0.22$, providing a natural control that supports the risk-based (rather than behavioral) interpretation of $\lambda > 0$. Year-by-year Kalshi estimates over 2022--2026 confirm temporal stability ($\hat{\lambda} \in [0.15, 0.27]$). The estimate is economically interpretable: an event with 10\% physical probability trades at approximately 13.5\%, a 35\% overpricing that longshot buyers effectively pay as a risk premium. A one-stage hierarchical MLE jointly estimates the baseline risk premium and covariate effects, confirming that volume reduces the premium ($\hat{\beta}_{\text{vol}} < 0$), duration increases it ($\hat{\beta}_{\text{dur}} > 0$), and extremity amplifies it ($\hat{\beta}_{\text{ext}} < 0$; LR $\chi^2 = 361.3$)---generating the favorite-longshot bias pattern as a direct consequence. A novel finding is that the risk premium is time-varying: a stacked panel model with contract-clustered standard errors reveals that the premium is significant at market opening and decays with a half-life of 33\% of contract lifetime (12-day sample) and 77\% (28-day sample), linking the duration effect in the cross section to the time-decay pattern within contracts. Four alternative opening-price constructions yield $\hat{\lambda} \in [0.131, 0.166]$, indicating that approximately 80\% of the baseline estimate reflects genuine risk compensation rather than microstructure artifacts. An external benchmark using Elo-model probabilities for 51 NBA contracts provides independent directional support ($\hat{\lambda} = 0.125$, $p = 0.014$) without relying on ex-post resolution outcomes.

**Limitations.** The calibration approach is reduced-form; separating the risk premium from behavioral probability distortion (prospect theory weighting, overconfidence) requires instruments or natural experiments. Candidates include regulatory shocks (Kalshi CFTC ruling), the time-varying pattern documented in Section 5.4 (which suggests market-microstructure rather than behavioral origins), and the cross-platform dimension (same event, different $\lambda$). The Manifold sign reversal (Section 6) provides suggestive evidence for the risk-based interpretation but is not a definitive causal identification. For the Kalshi cross-platform analysis, the available price data is the last traded price before settlement rather than the opening price used for Polymarket; this limits the interpretation of calibration improvements (ECE, Brier score) for Kalshi, though the $\hat{\lambda}$ point estimates remain valid as they reflect the systematic relationship between price levels and resolution rates. At extreme probabilities, the elevated $\hat{\lambda}$ may reflect overconfidence rather than pure risk premium; the extended model finds extremity is a significant predictor but cannot distinguish risk from misperception. The external benchmark analysis (Section 5.6), using an Elo rating model as an independent probability estimate for 51 NBA contracts, provides directional support for a positive risk premium ($\hat{\lambda} = 0.125$, $p = 0.014$), though the sample is small and the Elo model is noisier than sportsbook closing lines. Replication with commercial closing-line data would strengthen this identification.

No prior work has applied the Wang transform to prediction markets, and the empirical results---spanning 291,309 contracts across eight data sources, six platforms, and eleven years---confirm that the framework captures economically meaningful structure in the data. The framework connects prediction market pricing to three established literatures: (i) distortion risk measures in insurance mathematics (Wang, 2000; Yaari, 1987); (ii) the interpretation of prediction market prices in economics (Manski, 2006; Wolfers and Zitzewitz, 2006); and (iii) incomplete market pricing in mathematical finance (Harrison and Pliska, 1983). By bridging these literatures, it provides practitioners with a principled, model-dependent fair-value signal---subject to the reduced-form nature of the calibration and the assumptions underlying the Wang specification---and researchers with a testable structural model of prediction market mispricing.

\vspace{1em}

\newpage
# References

- Ali, M.M. (1977). Probability and Utility Estimates for Racetrack Bettors. *Journal of Political Economy*, 85(4), 803--815.
- Archak, N. and Ipeirotis, P.G. (2009). Modeling Volatility in Prediction Markets. *Proceedings of the 10th ACM Conference on Electronic Commerce (EC '09)*.
- Avellaneda, M. and Stoikov, S. (2008). High-Frequency Trading in a Limit Order Book. *Quantitative Finance*, 8(3), 217--224.
- Barberis, N. and Huang, M. (2008). Stocks as Lotteries: The Implications of Probability Weighting for Security Prices. *American Economic Review*, 98(5), 2066--2100.
- Black, F. and Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. *Journal of Political Economy*, 81(3), 637--654.
- Bürgi, C., Deng, W. and Whelan, K. (2025). Makers and Takers: The Economics of the Kalshi Prediction Market. *CEPR Discussion Paper* 20631.
- Cochrane, J.H. and Saa-Requejo, J. (2000). Beyond Arbitrage: Good-Deal Asset Price Bounds in Incomplete Markets. *Journal of Political Economy*, 108(1), 79--119.
- Cont, R. (2001). Empirical Properties of Asset Returns: Stylized Facts and Statistical Issues. *Quantitative Finance*, 1(2), 223--236.
- Dalen, S. (2025). Toward Black Scholes for Prediction Markets: A Unified Kernel and Market Maker's Handbook. *arXiv preprint*, arXiv:2510.15205.
- Easley, D. and O'Hara, M. (1992). Time and the Process of Security Price Adjustment. *Journal of Finance*, 47(2), 577--605.
- Frittelli, M. (2000). The Minimal Entropy Martingale Measure and the Valuation Problem in Incomplete Markets. *Mathematical Finance*, 10(1), 39--52.
- Gjerstad, S. (2004). Risk Aversion, Beliefs, and Prediction Market Equilibrium. *Working Paper*, University of Arizona.
- Gneiting, T., Balabdaoui, F. and Raftery, A.E. (2007). Probabilistic Forecasts, Calibration and Sharpness. *Journal of the Royal Statistical Society: Series B*, 69(2), 243--268.
- Griffith, R.M. (1949). Odds Adjustments by American Horse-Race Bettors. *American Journal of Psychology*, 62(2), 290--294.
- Hamada, M. and Sherris, M. (2003). Contingent Claim Pricing Using Probability Distortion Operators: Methods from Insurance Risk Pricing and Their Relationship to Financial Theory. *Applied Mathematical Finance*, 10(1), 19--47.
- Hanson, R. (2007). Logarithmic Market Scoring Rules for Modular Combinatorial Information Aggregation. *Journal of Prediction Markets*, 1(1), 3--15.
- Harrison, J.M. and Pliska, S.R. (1981). Martingales and Stochastic Integrals in the Theory of Continuous Trading. *Stochastic Processes and their Applications*, 11(3), 215--260.
- Harrison, J.M. and Pliska, S.R. (1983). A Stochastic Calculus Model of Continuous Trading: Complete Markets. *Stochastic Processes and their Applications*, 15(3), 313--316.
- Hasbrouck, J. (1995). One Security, Many Markets: Determining the Contributions to Price Discovery. *Journal of Finance*, 50(4), 1175--1199.
- He, X.-Z. and Treich, N. (2017). Prediction Market Prices under Risk Aversion and Heterogeneous Beliefs. *Journal of Mathematical Economics*, 70, 105--114.
- Hosmer, D.W. and Lemeshow, S. (2000). *Applied Logistic Regression*, 2nd ed. Wiley.
- Johnston, M. (2007). Extension of the Capital Asset Pricing Model to Non-normal Dependence Structures. *ASTIN Bulletin*, 37(1), 35--52.
- Jullien, B. and Salanié, B. (2000). Estimating Preferences under Risk: The Case of Racetrack Bettors. *Journal of Political Economy*, 108(3), 503--530.
- Huang, H.H., Sun, J. and Zhang, S. (2024). Asset Pricing for the Lottery-Like Security Under Probability Weighting: Based on Generalized Wang Transform. *North American Journal of Economics and Finance*, 71, 102078.
- Kijima, M. and Muromachi, Y. (2008). An Extension of the Wang Transform Derived from Bühlmann's Economic Premium Principle for Insurance Risk. *Insurance: Mathematics and Economics*, 42(3), 887--896.
- Le, N.A. (2026). Decomposing Crowd Wisdom: Domain-Specific Calibration Dynamics in Prediction Markets. *arXiv preprint*, arXiv:2602.19520.
- Liang, K.-Y. and Zeger, S.L. (1986). Longitudinal Data Analysis Using Generalized Linear Models. *Biometrika*, 73(1), 13--22.
- Madrigal-Cianci, J.P., Monsalve Maya, C. and Breakey, L. (2026). Prediction Markets as Bayesian Inverse Problems: Uncertainty Quantification, Identifiability, and Information Gain from Price-Volume Histories under Latent Types. *arXiv preprint*, arXiv:2601.18815.
- Manski, C.F. (2006). Interpreting the Predictions of Prediction Markets. *Economics Letters*, 91(3), 425--429.
- McCullagh, P. and Nelder, J.A. (1989). *Generalized Linear Models*, 2nd ed. Chapman and Hall.
- Muravyev, D., Pearson, N.D. and Broussard, J.P. (2013). Is There Price Discovery in Equity Options? *Journal of Financial Economics*, 107(2), 259--283.
- Ng, H., Peng, L., Tao, Y. and Zhou, D. (2026). Price Discovery and Trading in Modern Prediction Markets. *SSRN Working Paper*, 5331995.
- Ostrovsky, M. (2012). Information Aggregation in Dynamic Markets with Strategic Traders. *Econometrica*, 80(6), 2595--2647.
- Ottaviani, M. and Sorensen, P.N. (2010). Noise, Information, and the Favorite-Longshot Bias in Parimutuel Predictions. *American Economic Journal: Microeconomics*, 2(1), 58--85.
- Page, L. and Clemen, R.T. (2013). Do Prediction Markets Produce Well-Calibrated Probability Forecasts? *Economic Journal*, 123(568), 491--513.
- Pelsser, A. (2008). On the Applicability of the Wang Transform for Pricing Financial Risks. *ASTIN Bulletin*, 38(1), 171--181.
- Rubinstein, M. and Reiner, E. (1991). Unscrambling the Binary Code. *Risk Magazine*, 4(9), 75--83.
- Servan-Schreiber, E., Wolfers, J., Pennock, D.M. and Galebach, B. (2004). Prediction Markets: Does Money Matter? *Electronic Markets*, 14(3), 243--251.
- Shin, H.S. (1991). Optimal Betting Odds Against Insider Traders. *Economic Journal*, 101(408), 1179--1185.
- Shin, H.S. (1993). Measuring the Incidence of Insider Trading in a Market for State-Contingent Claims. *Economic Journal*, 103(420), 1141--1153.
- Snowberg, E. and Wolfers, J. (2010). Explaining the Favorite-Longshot Bias: Is It Risk-Love or Misperceptions? *Journal of Political Economy*, 118(4), 723--746.
- Wang, S.S. (2000). A Class of Distortion Operators for Pricing Financial and Insurance Risks. *Journal of Risk and Insurance*, 67(1), 15--36.
- Wang, S.S. (2004). Cat Bond Pricing Using Probability Transforms. *Geneva Papers: Études et Dossiers*, No. 278, 19--29.
- Wang, S.S., Young, V.R. and Panjer, H.H. (1997). Axiomatic Characterization of Insurance Prices. *Insurance: Mathematics and Economics*, 21(2), 173--183.
- Whelan, K. (2024). Risk Aversion and Favourite-Longshot Bias in a Competitive Fixed-Odds Betting Market. *Economica*, 91(361), 188--209.
- Wolfers, J. and Zitzewitz, E. (2004). Prediction Markets. *Journal of Economic Perspectives*, 18(2), 107--126.
- Wolfers, J. and Zitzewitz, E. (2006). Interpreting Prediction Market Prices as Probabilities. *NBER Working Paper* 12200.
- Yaari, M.E. (1987). The Dual Theory of Choice Under Risk. *Econometrica*, 55(1), 95--115.

\newpage

# Appendix

## A. Supplementary Tables

\begin{table}[H]
\centering
\small
\caption{Per-horizon separate MLEs (baseline calibration, 12-day subsample). These estimates are superseded by the stacked panel model (Section 5.4), which borrows strength across horizons and provides correct contract-clustered inference.}
\label{tab:horizons_appendix}
\begin{tabular}{lrrrrl}
\toprule
Lifetime \% & $N$ & $\hat{\lambda}_{MLE}$ & SE & 95\% CI & $p$-value \\
\midrule
5\% (Opening) & 2,460 & 0.176$^{***}$ & 0.027 & [0.123, 0.230] & $7.1 \times 10^{-11}$ \\
10\% & 2,409 & 0.158$^{***}$ & 0.027 & [0.104, 0.212] & $8.3 \times 10^{-9}$ \\
20\% & 2,316 & 0.110$^{***}$ & 0.028 & [0.055, 0.165] & $8.8 \times 10^{-5}$ \\
30\% & 2,236 & 0.082$^{**}$ & 0.029 & [0.026, 0.139] & 0.004 \\
40\% & 2,065 & 0.080$^{**}$ & 0.030 & [0.021, 0.138] & 0.008 \\
50\% (Mid-life) & 1,976 & 0.050 & 0.030 & [$-$0.010, 0.110] & 0.102 \\
60\% & 1,902 & 0.052 & 0.031 & [$-$0.008, 0.113] & 0.091 \\
70\% & 1,763 & 0.040 & 0.032 & [$-$0.023, 0.103] & 0.216 \\
80\% & 1,662 & 0.031 & 0.033 & [$-$0.035, 0.096] & 0.357 \\
90\% & 1,359 & 0.062 & 0.038 & [$-$0.011, 0.136] & 0.098 \\
\bottomrule
\end{tabular}
\end{table}

\input{outputs/tables/kalshi_hierarchical.tex}

\input{outputs/tables/cross_platform_category.tex}

\input{outputs/tables/polymarket_timing_ladder.tex}

\input{outputs/tables/polymarket_vs_kalshi_timing_distance.tex}

## B. External Benchmark Details

This appendix provides methodological details for the external benchmark validation reported in Section 5.6.

**Elo model specification.** I build Elo ratings from the complete 2025--26 NBA regular season (1,135 games, 30 teams) using a standard recursive update. The parameters are $K = 28$ (update factor) and home-court advantage $= 42$ Elo points, calibrated to the modern NBA home-win rate of approximately 56\%. All teams are initialized at Elo $= 1500$; preseason and All-Star games are excluded.

**Elo calibration.** The model achieves a Brier score of 0.218 on the 1,135-game sample. Binned calibration shows reasonable alignment between predicted and realized home-win rates, with the strongest calibration in the 30--80\% predicted probability range.

**Sportsbook validation.** To validate the Elo model against a sharper external benchmark, I compare its predictions to consensus moneyline odds from The Odds API for 13 contemporaneous NBA games. The consensus probability is the mean across nine bookmakers, with overround removed by normalization. The correlation between Elo and sportsbook probabilities is $r = 0.618$, with MAE $= 0.166$ and RMSE $= 0.200$. The moderate correlation confirms that the Elo model captures a substantial share of the variation in sharp-market pricing, while the residual noise inflates the contract-level $\hat{\lambda}_i$ estimates relative to what a sportsbook-based benchmark would yield.

**Matching procedure.** I identify Polymarket NBA game contracts by regex matching on the title format ``Team A vs.\ Team B'', requiring both team names to normalize to one of 30 canonical NBA team names via an alias table. Each contract is matched to the closest Elo game involving the same team pair within a $[-1, +5]$-day window around the contract's creation date. Of 80 contracts passing team normalization, 51 are successfully matched; the 29 unmatched contracts reference games outside the matching window or future unplayed games.

**Contract-level $\hat{\lambda}_i$.** For each matched contract, the Wang parameter is computed as $\hat{\lambda}_i = \Phi^{-1}(p_i^{\text{Polymarket}}) - \Phi^{-1}(\hat{p}_i^{\text{Elo}})$, where $p_i^{\text{Polymarket}}$ is the opening price (first-5\% midpoint) and $\hat{p}_i^{\text{Elo}}$ is the pre-game Elo probability assigned to the first-named team.

**OLS regression.** A cross-sectional regression of $\hat{\lambda}_i$ on $\ln(\text{Volume})$ and price extremity $|p_i - 0.5|$ finds neither covariate significant at conventional levels ($N = 51$; Table \ref{tab:external_benchmark}, Panel B), though the negative extremity coefficient ($\hat{\beta} = -0.72$, $p = 0.094$) is suggestive of risk loading concentrated near even-odds contracts. The limited power reflects the small matched sample.
