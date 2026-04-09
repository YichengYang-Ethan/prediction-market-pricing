# QF Optimization Report

**Date**: 2026-04-09
**Scope**: paper.tex + cover_letter_QF.tex targeted for Quantitative Finance submission

---

## 1. Over-Claiming Phrases (Abstract, Introduction, Contributions)

### Already fixed in prior revisions -- no changes needed

| Phrase checked | Status | Current text |
|---|---|---|
| "correct incomplete-markets foundation" | NOT PRESENT | Uses "formal incomplete-market foundation" (line 121) |
| "systematically distorted relative to physical probabilities" | NOT PRESENT | Uses "systematic price-probability wedge under the maintained Wang family" (abstract, line 91) |

The abstract, introduction, and contributions paragraph are already model-conditional throughout. Key hedging language already in place:
- "Under this maintained Gaussian family" (abstract)
- "This claim is conditional on the maintained Gaussian family; it is not implied by no-arbitrage alone" (intro, line 112)
- "I do not claim that no-arbitrage or market completeness uniquely selects the Wang transform" (Section 3.3, line 466)
- "model-dependent pricing benchmark---conditional on the maintained Wang family and its identifying assumptions" (conclusion, line 2211)

No edits needed for Task 1.

---

## 2. QF-Anchoring Citations Added (Section 2)

### New paragraph added: "Prediction market returns and equilibrium"

Inserted before the "Bayesian approaches" paragraph in Section 2. Two QF-published papers now anchor the paper to the journal's own prediction-market track:

1. **Bottazzi and Giachini (2019)** -- "Far from the Madding Crowd: Collective Wisdom in Prediction Markets," *Quantitative Finance* 19(9), 1461--1471.
   - Relevance: wealth-driven selection and slow convergence in prediction markets; connects to the persistence of the pricing wedge.

2. **Whelan (2023)** -- "On Prices and Returns in Commercial Prediction Markets," *Quantitative Finance* 23(2), 283--295.
   - Relevance: derives expected returns and risk premia in binary markets under risk aversion; provides an equilibrium foundation consistent with the positive lambda estimated in the paper.

Both bibliography entries added in alphabetical order.

---

## 3. "Universality" Softened to "Pervasiveness"

In the Section 6 cross-platform findings (line 1929), the bold heading:

> **Universality of the positive pricing wedge.**

was changed to:

> **Pervasiveness of the positive pricing wedge.**

**Rationale**: "Universality" implies an unconditional law. The finding covers 6 platforms, which is broad but not literally universal. "Pervasiveness" conveys the same empirical breadth without over-claiming, and is more consistent with the model-conditional framing used throughout.

---

## 4. QF Cover Letter Review

The cover letter (`cover_letter_QF.tex`, 36 lines) is already:
- Short and punchy (one page of substance)
- Not theory-dense (no equations, no proofs, no theorem references)
- Correctly addressed to Professors Gatheral and Tebaldi
- States the paper's QF fit clearly: "treats binary event contracts as an incomplete-market derivatives-pricing problem"
- Includes SSRN and GitHub links
- Contains the exclusivity statement

**Verdict**: Ready as-is. No trims needed.

---

## 5. Compilation Diagnostics (Post-Edit)

### paper.tex

| Check | Result |
|---|---|
| Undefined references | None |
| Undefined citations | None |
| Missing figures | None |
| Hyperlink issues | None |
| New overfull hboxes | None introduced |
| Pre-existing overfull >10pt | 2 (unchanged from before edits) |

Pre-existing overfull boxes (not introduced by these edits):
1. Lines 6--22 (preamble font block): 106.5pt -- invisible in output
2. Lines 1180--1198 (Table 5): 52.4pt -- visible, needs `\resizebox` or `\footnotesize` (separate fix)

### cover_letter_QF.tex

| Check | Result |
|---|---|
| Errors/Warnings | None |
| Overfull hboxes | None |

---

## 6. Unified Diff

```diff
--- a/paper/paper.tex
+++ b/paper/paper.tex
@@ (Section 2, before "Bayesian approaches" paragraph)
+\textbf{Prediction market returns and equilibrium.} Within the \textit{Quantitative Finance} literature, Bottazzi and Giachini (2019) study wealth-driven selection in prediction markets, showing that beliefs closer to the truth survive in the long run but that convergence can be slow and non-monotone---a result relevant to the persistence of the pricing wedge documented here. Whelan (2023) derives analytic expressions for expected returns in binary prediction markets and shows that risk premia arise naturally when traders are risk-averse, providing an equilibrium foundation consistent with the positive $\hat{\lambda}$ estimated in Sections~5--6.
+

@@ (Section 6, cross-platform findings)
-  \textbf{Universality of the positive pricing wedge.} Every
+  \textbf{Pervasiveness of the positive pricing wedge.} Every

@@ (Bibliography, after Barberis 2008)
+\bibitem{bottazzi2019} Bottazzi, G. and Giachini, D. (2019). Far from the Madding Crowd:
+  Collective Wisdom in Prediction Markets. \emph{Quantitative Finance},
+  19(9), 1461--1471.
+

@@ (Bibliography, before Whelan 2024)
+\bibitem{whelan2023} Whelan, K. (2023). On Prices and Returns in Commercial Prediction
+  Markets. \emph{Quantitative Finance}, 23(2), 283--295.
+
```

---

## 7. Summary

| Task | Action |
|---|---|
| Soften over-claiming phrases | Already fixed in prior revisions; no changes needed |
| Add QF-track citations | Added Bottazzi & Giachini (2019) and Whelan (2023) with paragraph and bib entries |
| Soften "Universality" heading | Changed to "Pervasiveness" |
| Cover letter review | Ready as-is; short, punchy, no trims needed |
| Compilation check | Clean; no new issues introduced |
