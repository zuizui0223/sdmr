"""Deterministic successor wrapper for prospective ecological-identification validation.

The predecessor scientific run stopped before process truth was opened because
independent processes differed at the frozen floating-point tolerance.  This
successor changes only the numerical execution environment and uses a fresh seed
denominator.  All scientific fields are required to match the predecessor
execution receipt exactly.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path

from . import prospective_identification_validation as base
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES

SUCCESSOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "ecological_identification_learner_validation_successor_v2.json"
)

PURPOSE = "prospective_ecological_identification_learner_validation_deterministic_successor_v2"
SUCCESSOR_SEEDS = tuple(range(12001, 12021))
SCIENTIFIC_FIELDS = (
    "families",
    "simulation",
    "ecological_predictors",
    "observation_predictors",
    "process_registry",
    "process_universe",
    "learner",
    "primary_process_thresholds",
    "prediction_guardrails",
    "determinism",
    "failed_or_null_cases_must_remain_in_denominator",
)
EXPECTED_NUMERICAL_ENVIRONMENT = {
    "PYTHONHASHSEED": "0",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "BLIS_NUM_THREADS": "1",
}


def load_successor_execution(path: str | Path = SUCCESSOR_PATH) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("wrong deterministic successor purpose")
    if payload.get("scientific_run_authorized") is not True:
        raise ValueError("deterministic successor is not authorized")
    if payload.get("successor_of_workflow_run_id") != 33972810926:
        raise ValueError("successor predecessor run changed")
    if payload.get("predecessor_terminal") != "determinism_gate_not_supported":
        raise ValueError("successor predecessor terminal changed")
    if payload.get("predecessor_process_truth_opened") is not False:
        raise ValueError("successor may only follow a predecessor with unopened process truth")
    if payload.get("technical_change_only") is not True:
        raise ValueError("successor must remain a technical-only change")
    if payload.get("technical_change") != "single_thread_numerical_execution":
        raise ValueError("unexpected successor technical change")
    if payload.get("technical_probe_workflow_run_id") != 34007658753:
        raise ValueError("successor determinism probe source changed")
    if payload.get("technical_probe_passed_at_original_tolerance") is not True:
        raise ValueError("successor requires a passing pre-run determinism probe")
    if tuple(int(x) for x in payload.get("seeds", ())) != SUCCESSOR_SEEDS:
        raise ValueError("deterministic successor seed denominator changed")
    if int(payload.get("n_cases", -1)) != len(KNOWN_TRUTH_FAMILIES) * len(SUCCESSOR_SEEDS):
        raise ValueError("deterministic successor case denominator changed")
    if tuple(str(x) for x in payload.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("deterministic successor family denominator changed")
    retired = tuple(int(x) for x in payload.get("predecessor_seed_denominator_retired", ()))
    if retired != tuple(range(4101, 4121)):
        raise ValueError("predecessor seed retirement record changed")
    if payload.get("numerical_environment") != EXPECTED_NUMERICAL_ENVIRONMENT:
        raise ValueError("deterministic successor numerical environment changed")

    predecessor = json.loads(base.EXECUTION_PATH.read_text(encoding="utf-8"))
    for field in SCIENTIFIC_FIELDS:
        if payload.get(field) != predecessor.get(field):
            raise ValueError(f"successor scientific field differs from predecessor: {field}")
    for field in (
        "post_outcome_changes_allowed",
        "threshold_relaxation_allowed",
        "seed_replacement_allowed",
        "family_replacement_allowed",
    ):
        if payload.get(field) is not False:
            raise ValueError(f"successor must keep {field}=false")
    if payload.get("product_a_reopened") is not False:
        raise ValueError("successor may not reopen Product A")
    return payload


@contextmanager
def _successor_loader():
    previous = base.load_execution
    base.load_execution = load_successor_execution
    try:
        yield
    finally:
        base.load_execution = previous


def fit_family(family: str, replicate: int, output_dir: str | Path) -> None:
    load_successor_execution()
    with _successor_loader():
        base.fit_family(
            family,
            replicate,
            output_dir,
            execution_path=SUCCESSOR_PATH,
        )


def evaluate_terminal(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    load_successor_execution()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        with _successor_loader():
            return base.evaluate_terminal(
                input_dir,
                output_dir,
                execution_path=SUCCESSOR_PATH,
            )
    except AssertionError as error:
        payload = {
            "purpose": "prospective_ecological_identification_successor_v2_technical_terminal",
            "terminal": "determinism_gate_not_supported",
            "error_class": type(error).__name__,
            "error": str(error),
            "process_truth_performance_interpretable": False,
            "post_outcome_changes_allowed": False,
        }
        (out / "technical_terminal.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    fit = sub.add_parser("fit-family")
    fit.add_argument("--family", required=True, choices=KNOWN_TRUTH_FAMILIES)
    fit.add_argument("--replicate", required=True, type=int, choices=(1, 2))
    fit.add_argument("--output-dir", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--input-dir", required=True)
    evaluate.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "fit-family":
        fit_family(args.family, args.replicate, args.output_dir)
    else:
        evaluate_terminal(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
