# Final Submission Checklist

**Date**: 2026-04-09

---

## QF Main Paper (paper.tex → paper.pdf)

- [x] Abstract uses model-conditional language ("under the maintained Wang family")
- [x] Contributions paragraph: "formal incomplete-market foundation" (not "correct")
- [x] Section 6: "Pervasiveness" (not "Universality")
- [x] QF-anchoring citations: Bottazzi & Giachini (2019), Whelan (2023) added
- [x] All 11 figures compile from `outputs/figures/`
- [x] No undefined references or citations
- [x] Compiles: 58 pages, clean
- [ ] **Action needed**: For journal submission, copy figures into `paper/` or provide full repo structure. Currently relies on `\graphicspath{../outputs/figures/}`.

## QF Cover Letter (cover_letter_QF.tex → cover_letter_QF.pdf)

- [x] No over-claiming phrases
- [x] Addressed to Professors Gatheral and Tebaldi
- [x] SSRN and GitHub on clean separate `\url{...}` lines
- [x] hidelinks/xurl/urlstyle{same}
- [x] Exclusivity statement present
- [x] Compiles: 2 pages, clean

## FRL Note (frl_draft_v3.tex → frl_draft_v3.pdf)

- [x] "separate working paper" (not "companion paper")
- [x] "attenuate or possibly reverse" mechanism language
- [x] Sample: 290,730 contracts, 579-exclusion footnote
- [x] CI: "reorients each contract to the less-likely outcome"
- [x] Whelan: Economica 2024 (correct)
- [x] Takeaway ending present
- [x] CI robustness claim narrowed to core real-money/play-money contrast (fresh rerun reconciliation)
- [x] Compiles: **5 pages**, clean
- [x] Sidecar files: `frl_highlights.txt`, `frl_competing_interest.txt`, `frl_ai_statement.txt`

## Robustness Rerun

- [x] 70 lattice cells (40 fresh, 30 pre-computed)
- [x] Polymarket-HF-2025 λ positive and significant across all 7 specifications
- [x] Manifold negative across all specifications
- [x] CI sign flips on Metaculus/GJOpen acknowledged in FRL
- [ ] **Note**: Full Polymarket/Kalshi re-estimation requires missing parquet files and fetch scripts (not blocking for submission)

## Outstanding Items

1. **Figure portability**: `paper.tex` needs `outputs/figures/` at `../outputs/figures/` relative to `paper/`. Bundle for submission.
2. **FRL sidecar files**: Verify `frl_highlights.txt` bullets are <85 chars each per FRL guidelines.
3. **Working Paper date**: paper.tex says "March 2026" with "This version: April 9, 2026" — confirm this is intentional.
