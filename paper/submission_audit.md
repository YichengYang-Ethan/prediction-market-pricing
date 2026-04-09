# Submission Package Audit

**Generated**: 2026-04-09
**Scope**: All TeX sources, compiled PDFs, supporting files in `paper/`, plus repo-level metadata

---

## 1. Canonical Source Files

Determined by: git tracking status, git log history, and file modification timestamps.

| Item | Canonical File | Status | Last Modified | Compiled PDF |
|------|---------------|--------|---------------|-------------|
| Main paper | `paper/paper.tex` | git-tracked, HEAD = v14 (1bbac5a) | Apr 9 10:05 | `paper.pdf` (58 pp, Apr 9 10:07) |
| FRL short note | `paper/frl_draft_v3.tex` | git-tracked, HEAD = v14 (1bbac5a) | Apr 9 10:08 | `frl_draft_v3.pdf` (5 pp, Apr 9 10:08) |
| QF cover letter | `paper/cover_letter_QF.tex` | git-tracked, HEAD = v14 (1bbac5a) | Apr 9 10:06 | `cover_letter_QF.pdf` (2 pp, Apr 9 10:07) |
| RDR cover letter | `paper/cover_letter_RDR.tex` | git-tracked, HEAD = v14 (1bbac5a) | Apr 8 21:00 | `cover_letter_RDR.pdf` (2 pp, Apr 8 21:00) |

**Note**: `paper.tex` line 1 says `v11 (2026-04-08 final mechanical patch)` but the file has been edited through v14 per git log. The version marker is stale by 3 revisions.

---

## 2. Cross-File Consistency Checks

### 2.1 Title

| Location | Title |
|----------|-------|
| `paper.tex` (lines 79-80) | "Pricing Prediction Markets: Incomplete Markets, Selection Rules, and Risk Premia" |
| `frl_draft_v3.tex` (line 11) | "Do Prediction Market Prices Equal Probabilities? Evidence from a Play-Money Contrast" |
| `cover_letter_QF.tex` (line 15) | "Pricing Prediction Markets: Incomplete Markets, Selection Rules, and Risk Premia" |
| `cover_letter_RDR.tex` (line 14) | "Pricing Prediction Markets: Incomplete Markets, Selection Rules, and Risk Premia" |
| `CITATION.cff` (lines 3, 27) | **STALE**: "Pricing Prediction Markets: Risk Premiums, Incomplete Markets, and a Decomposition Framework" |
| `README.md` (line 1) | **STALE**: "Pricing Prediction Markets: Risk Premiums, Incomplete Markets, and a Decomposition Framework" |
| `replication_guide.md` (line 3) | **STALE**: "Pricing Prediction Markets: Risk Premiums, Incomplete Markets, and a Decomposition Framework" |
| `case-studies/final-four-2026/README.md` | **STALE**: uses old title |

**ISSUE**: CITATION.cff, README.md, replication_guide.md, and case-study files use the old subtitle ("Risk Premiums... Decomposition Framework") instead of the current one ("Incomplete Markets, Selection Rules, and Risk Premia").

### 2.2 Version Date

| File | Date Shown |
|------|-----------|
| `paper.tex` line 86 | "This version: April 8, 2026" |
| `paper_v11.tex` line 85 | "This version: April 7, 2026" |
| `frl_draft_v3.tex` line 13 | "April 2026" (month only) |
| Cover letters | No date shown |

**ISSUE**: `paper.tex` says "April 8, 2026" but the file was last modified April 9 and is at v14 per git log (commit message: "GPT Pro final text replacements (v14)"). The version date is one day stale.

### 2.3 Sample Counts (291,309 vs 290,730)

Both numbers are correct and intentionally different:

- **291,309** = pooled total across 8 data sources (includes 579 Polymarket observations from the multi-platform forecasting dataset)
- **290,730** = total across 6 platforms in the FRL note's one-row-per-platform structure (excludes 579 double-counted Polymarket forecasting observations)

Arithmetic checks:
- Paper table: 13,738 + 985 + 579 + 271,699 + 1,845 + 692 + 90 + 1,681 = **291,309** (correct)
- FRL table: 14,723 + 271,699 + 1,845 + 692 + 90 + 1,681 = **290,730** (correct)

| File | Abstract | Body/Table | Footnote |
|------|----------|------------|----------|
| `paper.tex` | 291,309 | 291,309 (Table 7) | N/A |
| `frl_draft_v3.tex` | 290,730 | 290,730 (Table 1 sums) | Footnote explains 291,309 vs 290,730 difference |
| `cover_letter_QF.tex` | 291,309 | N/A | N/A |
| `cover_letter_RDR.tex` | 291,309 | N/A | N/A |
| `README.md` | 291,309 + stale "2,460" Polymarket count | N/A | N/A |

**ISSUES**:
1. `frl_draft_v1.tex` (stale) has 291,309 in both abstract and body -- an internal inconsistency since it uses the 6-platform structure but the 8-source total.
2. `frl_draft_v2.tex` (stale) has 291,309 in the abstract intro paragraph but 290,730 in the data section -- the abstract was not updated.
3. `README.md` still references "2,460 resolved Polymarket contracts" (an earlier sample size); the current Polymarket CLOB sample is 13,738.

### 2.4 Platform Counts and Taxonomy

| File | Taxonomy |
|------|----------|
| `paper.tex` | "eight data sources spanning six platforms" |
| `frl_draft_v3.tex` | "six platforms spanning three distinct institutional architectures" |
| `cover_letter_QF.tex` | "six platforms" |
| `cover_letter_RDR.tex` | "six platforms" |

This is consistent. The main paper distinguishes 8 data sources (Polymarket CLOB, Polymarket 2025, Polymarket forecasting, Kalshi, Metaculus, GJO, INFER, Manifold) across 6 platforms. The FRL note and cover letters simplify to 6 platforms.

### 2.5 Whelan Citations

Two Whelan-related references are used:

| Citation Key | Reference | Journal | Used In |
|-------------|-----------|---------|---------|
| `whelan2024` | Whelan, K. (2024). Risk Aversion and Favourite-Longshot Bias in a Competitive Fixed-Odds Betting Market. | *Economica*, 91(361), 188--209 | `paper.tex`, `frl_draft_v3.tex` |
| `burgi2025` | Burgi, C., Deng, W. and Whelan, K. (2025). Makers and Takers: The Economics of the Kalshi Prediction Market. | *CEPR Discussion Paper* 20631 | `paper.tex` only |

**Consistent across all tracked files.** The FRL note cites only Whelan (2024), not Burgi et al. (2025), which is appropriate since the note does not discuss Kalshi market microstructure.

### 2.6 SSRN / Zenodo / GitHub Links

| Link | QF Cover Letter | RDR Cover Letter | FRL Note |
|------|----------------|-----------------|----------|
| SSRN `ssrn.com/abstract=6468338` | Yes (bare URL) | Yes (href) | Yes (in Yang 2026 bibitem) |
| Zenodo `doi.org/10.5281/zenodo.19447557` | **No** | Yes (href) | **No** |
| GitHub `github.com/YichengYang-Ethan/prediction-market-pricing` | Yes (bare URL) | Yes (href) | Yes (author footnote) |

**ISSUE**: Zenodo link appears only in the RDR cover letter, not in the QF cover letter. This is a minor inconsistency -- if Zenodo is relevant, it should appear in both; if not, in neither.

### 2.7 Submission-Status Language

| File | Language |
|------|---------|
| `cover_letter_QF.tex` | "The paper has not been submitted to any other journal." |
| `cover_letter_RDR.tex` | "The paper has not been submitted to any other journal." |

**CRITICAL**: Both cover letters contain the same exclusivity claim. If submitting to both journals simultaneously, this is a material misrepresentation. If submitting sequentially, only one should be active at a time.

### 2.8 Filter Range Discrepancy

| File | Filter |
|------|--------|
| `paper.tex` lines 932, 950 | $p \in (0.02, 0.98)$ |
| `frl_draft_v3.tex` line 72 | $p \in (0.02, 0.98)$ |
| `frl_draft_final.tex` line 72 (untracked) | $p \in (0.05, 0.95)$ -- stale |
| `frl_draft_v2.tex` line 72 (untracked) | $p \in (0.05, 0.95)$ -- stale |
| `frl_draft_v1.tex` line 70 (untracked) | $p \in (0.05, 0.95)$ -- stale |

The canonical `frl_draft_v3.tex` and `paper.tex` are now consistent at $(0.02, 0.98)$. Older untracked drafts used $(0.05, 0.95)$.

---

## 3. Compilation Diagnostics

### 3.1 paper.tex (58 pages)

| Check | Result |
|-------|--------|
| Undefined references | **None** |
| Undefined citations | **None** |
| Missing figures | **None** (all 11 includegraphics resolve) |
| Overfull hboxes (>10pt) | **2 found** |
| Warnings | **None** |

Overfull boxes:
1. **Lines 6-22** (preamble/font loading): 106.5pt too wide -- this is in the preamble `\ifPDFTeX\else` block, likely invisible in output
2. **Lines 1178-1196** (Table 5, hierarchical Wang MLE): 52.4pt too wide -- **visible in output**, the 7-column table with two sample panels overflows margins

### 3.2 frl_draft_v3.tex (5 pages)

| Check | Result |
|-------|--------|
| Undefined references | **None** |
| Undefined citations | **None** |
| Missing figures | N/A (no figures) |
| Overfull hboxes (>10pt) | **None** (one at 0.5pt, negligible) |
| Warnings | **None** |

### 3.3 cover_letter_QF.tex (2 pages)

| Check | Result |
|-------|--------|
| Errors/Warnings | **None** |
| Overfull hboxes | **None** |

### 3.4 cover_letter_RDR.tex (2 pages)

| Check | Result |
|-------|--------|
| Errors/Warnings | Minor: "File cover_letter_RDR.out has changed" (rerun advisory, harmless) |
| Overfull hboxes | **None** |

---

## 4. Stale / Duplicate Files to Clean Up

### 4.1 Untracked TeX Source Files (stale duplicates)

These are local-only copies not tracked in git. They represent earlier revisions that have been superseded by `paper.tex` and `frl_draft_v3.tex`.

| File | Version Tag | Superseded By |
|------|-------------|--------------|
| `paper/paper_v7.tex` | v7 (Apr 7) | `paper.tex` (v14) |
| `paper/paper_v8.tex` | v8 (Apr 7) | `paper.tex` (v14) |
| `paper/paper_v9.tex` | v9 (Apr 7) | `paper.tex` (v14) |
| `paper/paper_v10.tex` | v10 (Apr 8) | `paper.tex` (v14) |
| `paper/paper_v11.tex` | v11 (Apr 8) | `paper.tex` (v14) |
| `paper/frl_draft_v1.tex` | v1 (Apr 8) | `frl_draft_v3.tex` |
| `paper/frl_draft_v2.tex` | v2 (Apr 8) | `frl_draft_v3.tex` |
| `paper/frl_draft_final.tex` | Unversioned (Apr 8) | `frl_draft_v3.tex` (diverged, older) |

### 4.2 Stale Compiled PDFs

| File | Date | Status |
|------|------|--------|
| `paper/Yang_2026_Pricing_Prediction_Markets_FINAL.pdf` | Apr 6 | **Stale** -- compiled from an earlier version (pre-v7). `paper.pdf` (Apr 9) is the current compilation. |
| `paper/frl_draft_v1.pdf` | Apr 8 | Stale |
| `paper/frl_draft_v2.pdf` | Apr 8 | Stale |

### 4.3 Untracked Supporting Files

| File | Status |
|------|--------|
| `paper/FRL_note_outline.md` | Planning artifact, not needed for submission |
| `paper/cover_letter_QF.pdf` | Generated output, untracked (regenerable) |
| `paper/cover_letter_RDR.pdf` | Generated output, untracked (regenerable) |
| `paper/paper.pdf` | Generated output, untracked (regenerable) |
| `paper/frl_draft_v3.pdf` | Generated output, untracked (regenerable) |

### 4.4 Unreferenced Figures (in outputs/figures/ but not in paper.tex)

These 13 figures exist on disk but are not `\includegraphics`'d in the current `paper.tex`:

- `fig_binlevel_fit.png`
- `fig_distortion_curves.png`
- `fig_flb_overpricing.png`
- `fig_forest_plot.png`
- `fig_hazard_rate_term_structure.png`
- `fig_implied_wedge.png`
- `fig_lambda_horizons.png`
- `fig_lr_bar.png`
- `fig_stacked_panel_f_tau_covariates_12day.png`
- `fig_stacked_panel_f_tau_covariates.png`
- `fig_stacked_panel_f_tau.png`
- `fig_wang_calibration.png`
- `fig_wang_transform_curves.png`

These may have been used in earlier versions or may be supplementary. Not a bug, but worth confirming intent.

---

## 5. Summary of Issues Requiring Action

### Critical

1. **Dual submission language**: Both QF and RDR cover letters claim "has not been submitted to any other journal." Ensure only one is active at submission time, or update language if submitting sequentially.

### High

2. **Title mismatch in repo metadata**: `CITATION.cff`, `README.md`, `replication_guide.md`, and case-study files use the old subtitle. Should be updated to match the current paper title.
3. **Version marker stale in paper.tex**: Line 1 says `v11` but the file is at v14. Line 86 says "April 8, 2026" but content was last modified April 9.

### Medium

4. **Overfull hbox in Table 5** (paper.tex lines 1178-1196): 52.4pt overflow on the hierarchical Wang MLE table. Needs `\resizebox`, `\footnotesize`, or column width adjustment.
5. **README.md stale data**: Still says "2,460 resolved Polymarket contracts" and uses the old abstract framing ("three-layer decomposition framework").
6. **Zenodo link asymmetry**: Present in RDR cover letter but absent from QF cover letter.

### Low

7. **Stale `Yang_2026_Pricing_Prediction_Markets_FINAL.pdf`**: Compiled Apr 6, superseded by `paper.pdf` (Apr 9). Should be removed or regenerated.
8. **13 unreferenced figures** in `outputs/figures/`: Confirm whether these are intentionally retained or should be cleaned up.
9. **8 stale `.tex` files** (paper_v7 through paper_v11, frl_draft_v1, frl_draft_v2, frl_draft_final): Untracked, superseded. Safe to delete.
10. **Overfull hbox in preamble** (paper.tex lines 6-22): 106.5pt, but in `\ifPDFTeX\else` block -- unlikely visible. Harmless.

---

## 6. File Inventory (Git-Tracked in paper/)

```
paper/README.md
paper/Yang_2026_Pricing_Prediction_Markets_FINAL.pdf  (stale)
paper/changelog.md
paper/cover_letter_QF.tex    <-- canonical
paper/cover_letter_RDR.tex   <-- canonical
paper/frl_draft_v3.tex       <-- canonical FRL note
paper/paper.tex              <-- canonical main paper
paper/research_memo_v3.md
```
