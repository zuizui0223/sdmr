"""Pre-successor numerical determinism probe using noncontract known-truth seeds.

This probe never evaluates generating-process truth.  It reruns the frozen
nontruth fitting path in independent GitHub jobs under a single-thread numerical
environment and compares every emitted scientific frame at the original frozen
floating tolerance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import sklearn

from .prospective_identification_validation import (
    EXECUTION_PATH,
    fit_case_nontruth,
    load_execution,
)
from .transport_parity import assert_transport_frame_parity

PROBE_CASES = (("asymmetric", 9902), ("observation_confounded", 9903))
FRAME_NAMES = (
    "case_summary",
    "process_status",
    "baseline_summary",
    "knockout_summary",
    "fold_evidence",
    "comparator_metrics",
)


def run_probe(output_dir: str | Path, *, replicate: int) -> None:
    if int(replicate) not in (1, 2):
        raise ValueError("replicate must be 1 or 2")
    execution = load_execution(EXECUTION_PATH)
    accumulated: dict[str, list[pd.DataFrame]] = {name: [] for name in FRAME_NAMES}
    for family, seed in PROBE_CASES:
        frames = fit_case_nontruth(
            family,
            seed,
            replicate=int(replicate),
            execution=execution,
        )
        for name in FRAME_NAMES:
            frame = frames[name]
            if len(frame):
                accumulated[name].append(frame)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, frames in accumulated.items():
        result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if len(result):
            sort_cols = [
                x for x in (
                    "replicate", "family", "seed", "process", "model_label",
                    "candidate", "route", "fold"
                ) if x in result.columns
            ]
            result = result.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
        result.to_csv(out / f"{name}.csv", index=False)
    receipt = {
        "purpose": "ecological_identification_noncontract_determinism_probe",
        "replicate": int(replicate),
        "probe_cases": [{"family": f, "seed": s} for f, s in PROBE_CASES],
        "hidden_process_truth_opened": False,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "single_thread_environment_required": True,
    }
    (out / "probe_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def compare_probe(first_dir: str | Path, second_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    execution = load_execution(EXECUTION_PATH)
    det = execution["determinism"]
    rtol = float(det["numeric_relative_tolerance"])
    atol = float(det["numeric_absolute_tolerance"])
    first = Path(first_dir)
    second = Path(second_dir)
    summaries: dict[str, object] = {}
    for name in FRAME_NAMES:
        a = pd.read_csv(first / f"{name}.csv").drop(columns="replicate", errors="ignore")
        b = pd.read_csv(second / f"{name}.csv").drop(columns="replicate", errors="ignore")
        result = assert_transport_frame_parity(a, b, rtol=rtol, atol=atol)
        summaries[name] = result.as_dict()
    payload = {
        "purpose": "ecological_identification_noncontract_determinism_probe_decision",
        "determinism_passed": True,
        "numeric_relative_tolerance": rtol,
        "numeric_absolute_tolerance": atol,
        "probe_cases": [{"family": f, "seed": s} for f, s in PROBE_CASES],
        "hidden_process_truth_opened": False,
        "frame_summaries": summaries,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "determinism_probe_decision.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--replicate", type=int, required=True, choices=(1, 2))
    run.add_argument("--output-dir", required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--first-dir", required=True)
    compare.add_argument("--second-dir", required=True)
    compare.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "run":
        run_probe(args.output_dir, replicate=args.replicate)
    else:
        compare_probe(args.first_dir, args.second_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
