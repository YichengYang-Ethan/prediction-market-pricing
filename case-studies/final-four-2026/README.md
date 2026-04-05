# Case Study: Real-Time Pricing Wedge During the 2026 Final Four

**Illinois vs UConn** | April 4, 2026 | UConn 71, Illinois 62

Companion analysis to the main paper. Applies the Wang Transform framework to tick-level prediction market data collected during a single game.

## Key Finding

At competitive probabilities ($p^* \in [0.35, 0.55]$), the intra-game pricing wedge is $\lambda \approx +0.13$ on both Kalshi and Polymarket — consistent with the main paper's cross-sectional estimate of $\hat{\lambda} = 0.183$.

The naive full-sample $\lambda = +0.57$ is an artifact of the probit transform's tail sensitivity at extreme probabilities.

## Data

| File | Size | Description |
|------|------|-------------|
| `kalshi_20260404.jsonl` | 9.4 MB | Kalshi API snapshots, 15-30s intervals |
| `polymarket_20260404.jsonl` | 3.6 MB | Polymarket CLOB snapshots, 15-30s intervals |
| `sportsbook_pregame.json` | 1.5 KB | DraftKings/FanDuel/VegasInsider consensus |
| `espn_401856598.json` | 680 KB | ESPN play-by-play (439 plays, 74 scoring events) |
| `game1_scoring_timeline.csv` | 7 KB | Parsed scoring events with timestamps |

Collection window: 3:51 PM – 7:38 PM CT. 657 Kalshi + 857 Polymarket observations on the game-winner contract.

## Analysis

```bash
# Step 1: Cross-platform price dynamics, championship reaction, price discovery
python analysis/run_analysis.py

# Step 2: Intra-game Wang lambda (corrected for tail artifact)
python analysis/intra_game_lambda_v2.py
```

Requires: `numpy`, `pandas`, `matplotlib`, `scipy`

## Research Note

- [`research_note_final.md`](analysis/research_note_final.md) — Markdown source
- [`research_note_final.pdf`](analysis/research_note_final.pdf) — PDF (6 pages)
- [Blog post](https://yichengyang-ethan.github.io/final-four) — Accessible summary

## Citation

```bibtex
@article{yang2026pricing,
  title   = {Pricing Prediction Markets: Risk Premiums, Incomplete Markets, and a Decomposition Framework},
  author  = {Yang, Yicheng},
  year    = {2026},
  journal = {Working Paper},
  note    = {University of Illinois Urbana-Champaign}
}
```
