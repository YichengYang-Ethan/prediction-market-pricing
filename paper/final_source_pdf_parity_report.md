# Final Source–PDF Parity Report

**Date**: 2026-04-09
**Auditor**: Claude Code (automated line-by-line reconciliation)

---

## Executive Summary

The external analysis that flagged paper/cover-letter/FRL artifacts as out of sync with their reports was **comparing against stale file versions**. The actual `.tex` files on disk already contain all report-described edits. Only one substantive fix was needed: narrowing a complement-invariant robustness claim in the FRL to reflect fresh rerun findings.

---

## 1. paper.tex vs qf_optimization_report.md

| Report-described edit | Status in source | Line(s) |
|---|---|---|
| "systematically distorted" → "systematic price-probability wedge under the maintained Wang family" | ✅ Already present | 91 |
| "correct incomplete-markets foundation" → "formal incomplete-market foundation" | ✅ Already present | 121 |
| "Universality" → "Pervasiveness" | ✅ Already present | 1931 |
| Bottazzi & Giachini (2019) paragraph added in Section 2 | ✅ Already present | 202 |
| Whelan (2023) bibliography entry added | ✅ Already present | 2428 |
| Bottazzi (2019) bibliography entry added | ✅ Already present | 2244 |

**Edits applied this session**: None needed.

**Compilation**: Clean, 58 pages. 2 pre-existing overfull hboxes (preamble and Table 5), no new issues.

**Figure dependencies**: All 11 `\includegraphics` references resolve to existing files in `outputs/figures/`. The `\graphicspath` directive (`../outputs/figures/`) makes `paper.tex` self-contained within the repo structure, but the `paper/` directory alone is not a portable build — figures must be co-located or the graphicspath adjusted for journal submission.

---

## 2. cover_letter_QF.tex vs qf_optimization_report.md

| Report-described state | Status in source | Line(s) |
|---|---|---|
| No "correct incomplete-markets foundation" | ✅ Correct — uses "maintained one-parameter Gaussian selection family" | 17 |
| hidelinks, xurl, urlstyle{same} | ✅ Present | 3–5 |
| SSRN/GitHub on clean separate lines with `\url{...}` | ✅ Present | 25, 29 |
| Short, punchy, no theory overload | ✅ Correct | — |

**Edits applied this session**: None needed.

**Compilation**: Clean, 2 pages (letter with signature page).

---

## 3. frl_draft_v3.tex vs frl_finalization_report.md + fresh_robustness_rerun.md

### Checklist from frl_finalization_report.md

| # | Check | Status | Line(s) |
|---|---|---|---|
| 1 | "separate working paper" (not "companion paper") | ✅ Already correct | 40, 72 |
| 2 | "attenuate or possibly reverse" (not "eliminate or reverse") | ✅ Already correct | 36 |
| 3 | Sample counts sum to 290,730; 579-exclusion footnote | ✅ Already correct | 72 |
| 4 | CI: "reorients each contract to the less-likely outcome" | ✅ Already correct | 112 |
| 5 | Whelan is Economica 2024 (not QF 2023) | ✅ Already correct | 132 |
| 6 | Takeaway ending in conclusion | ✅ Already correct | 118 |
| 7 | Compiles to 5 pages | ✅ Confirmed | — |

### Fresh robustness rerun reconciliation (NEW)

The fresh rerun shows the complement-invariant specification **flips sign** on Metaculus (λ_CI = −0.127) and GJOpen (λ_CI = −0.390), while preserving the positive sign on Polymarket/Kalshi and negative sign on Manifold. Two blanket CI claims in the FRL needed narrowing:

| Location | Old text | New text |
|---|---|---|
| Abstract (line 19) | "robust to sample restrictions and complement-invariant specifications" | "robust to sample restrictions; under a complement-invariant specification, the positive/negative contrast between traded real-money venues and Manifold is preserved" |
| Robustness §5 (line 112) | "attenuates the magnitude on all platforms but preserves the sign pattern" | "attenuates the magnitude and preserves the positive/negative sign contrast between traded real-money venues and Manifold, though it reverses the sign on some forecasting platforms where asymmetric resolution rates rather than risk premia may drive the directional estimate" |

**Edits applied this session**: 2 (both CI claim narrowings).

**Compilation**: Clean, **5 pages**. 1 pre-existing overfull hbox (keywords line, 0.53pt, cosmetic).

---

## 4. Numerical Results

No numerical results were changed. All estimates, standard errors, p-values, and sample sizes are untouched.

---

## 5. Files Produced

| File | Pages | Size |
|---|---|---|
| paper.pdf | 58 | 3.5 MB |
| cover_letter_QF.pdf | 2 | 34 KB |
| frl_draft_v3.pdf | 5 | 222 KB |
| final_source_pdf_parity_report.md | — | this file |
| final_submission_checklist.md | — | see below |
