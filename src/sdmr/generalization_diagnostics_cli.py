"""CLI for descriptive inner-CV to outer-sealed transfer diagnostics."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .generalization_diagnostics import discovery_generalization_diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose whether model-pool spatial-CV AUC rankings survive the outer sealed test. "
            "This command is descriptive only and never selects or promotes a Product-A method."
        )
    )
    parser.add_argument("--discovery-metrics", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    discovery = pd.read_csv(args.discovery_metrics)
    cases, summary = discovery_generalization_diagnostics(discovery)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    cases.to_csv(output / "inner_outer_case_diagnostics.csv", index=False)
    summary.to_csv(output / "inner_outer_generalization_summary.csv", index=False)
    (output / "GENERALIZATION_DIAGNOSTIC_BOUNDARY.txt").write_text(
        "Descriptive post-selection diagnostic only. These statistics do not enter Product-A method selection, "
        "promotion, or differentiation thresholds.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
