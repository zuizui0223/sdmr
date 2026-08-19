"""CLI for the predeclared conventional-evaluation differentiation gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .differentiation import assess_differentiation, read_differentiation_criteria


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--criteria", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    summary = pd.read_csv(args.summary)
    criteria = read_differentiation_criteria(args.criteria)
    detail, passed = assess_differentiation(summary, criteria)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    detail.to_csv(output / "product_a_differentiation_detail.csv", index=False)
    (output / "product_a_differentiation_result.json").write_text(
        json.dumps(
            {
                "status": "transfer_advantage_supported" if passed else "transfer_advantage_not_demonstrated",
                "passes_all_required_comparators": bool(passed),
                "required_comparators": list(criteria.required_comparators),
                "min_runs": criteria.min_runs,
                "min_pairs_per_comparator": criteria.min_pairs_per_comparator,
                "min_mean_delta_presence_rank": criteria.min_mean_delta_presence_rank,
                "min_positive_pair_fraction": criteria.min_positive_pair_fraction,
                "min_positive_run_fraction": criteria.min_positive_run_fraction,
                "interpretation_boundary": (
                    "This gate tests empirical transfer advantage over conventional AUC/Boyce selectors; "
                    "it does not replace model-level AUC/Boyce scores and does not change Product-A promotion criteria."
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    # Not demonstrating differentiation is a valid scientific outcome, not a CI failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
