#!/usr/bin/env python3
"""
Download HuggingFace datasets used in cross-platform validation (Section 6).

Datasets:
  1. LightningRodLabs/outcome-rl-test-dataset
     - Polymarket resolved contracts (Feb-Mar 2025), N≈985 after filtering
     - Schema: prediction_polymarket, resolution, volume, ...
     - Saved as: huggingface_outcome_rl_train.parquet

  2. YuehHanChen/forecasting
     - Multi-platform forecasting questions (2015-2024)
     - Platforms: Metaculus, GJOpen, INFER, Polymarket, Manifold
     - Schema: community_predictions (JSON), resolution, is_resolved, platform, ...
     - Saved as: huggingface_forecasting_{train,validation,test}.parquet

Usage:
    pip install datasets
    python data/download_huggingface.py

Both datasets are public and freely available. No authentication required.
"""

import os
import sys

def main():
    try:
        from datasets import load_dataset
    except ImportError:
        print("Error: 'datasets' package not installed.")
        print("Install with: pip install datasets")
        sys.exit(1)

    out_dir = os.path.dirname(os.path.abspath(__file__))

    # ── 1. LightningRodLabs/outcome-rl-test-dataset ──────────────
    print("Downloading LightningRodLabs/outcome-rl-test-dataset ...")
    ds1 = load_dataset("LightningRodLabs/outcome-rl-test-dataset")
    for split in ds1:
        path = os.path.join(out_dir, f"huggingface_outcome_rl_{split}.parquet")
        ds1[split].to_parquet(path)
        print(f"  Saved {split}: {len(ds1[split]):,} rows -> {path}")

    # ── 2. YuehHanChen/forecasting ───────────────────────────────
    print("Downloading YuehHanChen/forecasting ...")
    ds2 = load_dataset("YuehHanChen/forecasting")
    for split in ds2:
        path = os.path.join(out_dir, f"huggingface_forecasting_{split}.parquet")
        ds2[split].to_parquet(path)
        print(f"  Saved {split}: {len(ds2[split]):,} rows -> {path}")

    print("\nDone. All HuggingFace datasets saved to", out_dir)


if __name__ == "__main__":
    main()
