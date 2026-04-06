# Paper

This directory contains the manuscript source and compiled PDF.

## Files

| File | Description |
|------|-------------|
| `Yang_2026_Pricing_Prediction_Markets_FINAL.pdf` | Compiled PDF (April 2026) |
| `paper.tex` | LaTeX source (standalone, self-contained) |
| `research_memo_v3.md` | Earlier Pandoc Markdown draft (v1.1, for reference) |

## Compilation

To recompile from LaTeX source (3 passes for cross-references):

```bash
cd paper/
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

### Requirements

- TeX Live or MacTeX (with `booktabs`, `float`, `amsmath`, `amssymb`, `hyperref`, `graphicx`, `amsthm`)

### Path Resolution

`paper.tex` uses relative paths for tables and figures:
- Tables: `\input{../outputs/tables/...}`
- Figures: `\graphicspath{{../outputs/figures/}}`

Compile from the `paper/` directory so paths resolve correctly.
