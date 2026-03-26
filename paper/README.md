# Paper

This directory contains the manuscript source and compiled PDF.

## Files

| File | Description |
|------|-------------|
| `research_memo_v3.md` | Pandoc-flavored Markdown source with LaTeX math |
| `Pricing_Prediction_Markets_Yang_2026.pdf` | Compiled PDF |

## Compilation

The paper compiles via pandoc + pdflatex (3 passes for cross-references):

```bash
cd paper/

# Step 1: Markdown -> LaTeX
pandoc research_memo_v3.md -o paper.tex --standalone \
  --pdf-engine=xelatex

# Step 2: LaTeX -> PDF (3 passes)
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

### Requirements

- pandoc >= 3.0
- TeX Live or MacTeX (with `booktabs`, `float`, `amsmath`, `amssymb`, `hyperref`, `graphicx`)
- Fonts: Helvetica Neue, Menlo (or adjust `mainfont`/`monofont` in YAML header)

### Note on Table Inputs

The paper source uses `\input{outputs/tables/...}` for all tables. When compiling, either:
1. Run from the repository root so paths resolve correctly, or
2. Create symlinks from `paper/outputs/` to `../outputs/`
