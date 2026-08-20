"""CLI for Product-B v2 niche-geometry process synthesis.

This CLI builds development/pre-promotion evidence only. Formal Product-B
scientific execution remains governed by the Product-A promotion gate.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .product_b_v2 import (
    pair_process_knockout_losses,
    repeat_process_core_splits,
    summarize_taxon_process_support,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate frozen Product-A niche-recovery process knockouts into Product-B v2 evidence."
    )
    parser.add_argument("--base-metrics", required=True)
    parser.add_argument("--knockout-metrics", required=True)
    parser.add_argument("--frozen-candidate", required=True)
    parser.add_argument("--expected-M", nargs="+", required=True)
    parser.add_argument("--expected-folds", nargs="+", type=int, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33, 44, 55])
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    base = pd.read_csv(args.base_metrics)
    knockout = pd.read_csv(args.knockout_metrics)
    taxa = sorted(base["taxon"].astype(str).unique())
    paired = pair_process_knockout_losses(
        base,
        knockout,
        frozen_candidate=args.frozen_candidate,
        expected_taxa=taxa,
        expected_M=args.expected_M,
        expected_folds=args.expected_folds,
    )
    taxon_summary = summarize_taxon_process_support(
        paired,
        expected_M=args.expected_M,
        expected_folds=args.expected_folds,
    )
    repeated = repeat_process_core_splits(taxon_summary, seeds=args.seeds)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paired.to_csv(out / "paired_process_niche_losses.csv", index=False)
    taxon_summary.to_csv(out / "taxon_process_support.csv", index=False)
    repeated.split_summary.to_csv(out / "taxon_split_process_confirmation.csv", index=False)
    repeated.process_stability.to_csv(out / "universal_process_stability.csv", index=False)
    (out / "PRODUCT_B_V2_DEVELOPMENT_ONLY.txt").write_text(
        "This evidence pipeline does not itself unblock formal Product B.\n"
        "Formal empirical claims still require an explicit Product-A promotion decision.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
