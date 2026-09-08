"""Technical-successor runner for v6 prospective known-truth validation.

The first v6 prospective attempt stopped before generating-process truth was opened
because independently executed family artifacts exceeded an unrealistically tight
floating transport tolerance while every discrete decision and finite mask matched.
This wrapper preserves the estimator and all scientific thresholds, retires the
first seed denominator, and swaps in the fresh successor contract.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, TypeVar

from . import proxy_closed_route_process_validation as _base
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "proxy_closed_route_process_challenge_v6_known_truth_validation_successor_v2.json"
T = TypeVar("T")


def load_contract(path: str | Path = CONFIG) -> dict:
    c = json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("purpose") != "proxy_closed_route_process_challenge_v6_prospective_known_truth_validation_successor_v2":
        raise ValueError("wrong v6 known-truth successor contract")
    if c.get("scientific_run_authorized") is not True:
        raise ValueError("v6 known-truth successor scientific run is not authorized")
    if c.get("technical_successor_only") is not True:
        raise ValueError("v6 successor lost technical-only status")
    if c.get("predecessor_terminal") != "determinism_gate_not_supported":
        raise ValueError("v6 successor predecessor terminal changed")
    if c.get("predecessor_generating_process_truth_opened") is not False:
        raise ValueError("v6 successor may only follow a truth-unopened determinism failure")
    if tuple(int(x) for x in c.get("predecessor_seed_denominator_retired", ())) != tuple(range(14001, 14011)):
        raise ValueError("retired v6 denominator changed")
    if tuple(c.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v6 successor family denominator changed")
    if tuple(int(x) for x in c.get("seeds", ())) != tuple(range(15001, 15011)):
        raise ValueError("v6 successor seed denominator changed")
    if int(c.get("n_cases", -1)) != 60 or int(c.get("n_process_cells", -1)) != 300:
        raise ValueError("v6 successor denominator changed")
    if c.get("technical_change_does_not_modify_estimator_or_scientific_thresholds") is not True:
        raise ValueError("v6 successor scientific rule changed")
    if int(c.get("technical_probe_discrete_differences", -1)) != 0:
        raise ValueError("v6 technical probe had discrete differences")
    if int(c.get("technical_probe_finite_mask_differences", -1)) != 0:
        raise ValueError("v6 technical probe had finite-mask differences")
    det = c.get("determinism", {})
    if det.get("discrete_identity_must_match") is not True:
        raise ValueError("v6 successor must preserve exact discrete identity")
    if float(det.get("numeric_absolute_tolerance", -1)) != 1e-4:
        raise ValueError("v6 successor absolute transport tolerance changed")
    if float(det.get("numeric_relative_tolerance", -1)) != 1e-6:
        raise ValueError("v6 successor relative transport tolerance changed")
    for flag in ("post_outcome_changes_allowed", "threshold_relaxation_allowed", "seed_replacement_allowed", "family_replacement_allowed"):
        if c.get(flag) is not False:
            raise ValueError(f"v6 successor governance changed: {flag}")
    if c.get("consumed_real_positive_controls_are_excluded_from_validation") is not True:
        raise ValueError("consumed empirical controls entered v6 successor validation")
    return c


def _run_with_successor_contract(func: Callable[..., T], *args, **kwargs) -> T:
    original = _base.load_contract
    _base.load_contract = load_contract
    try:
        return func(*args, **kwargs)
    finally:
        _base.load_contract = original


def fit_family(family: str, replicate: int, output_dir: str | Path) -> None:
    _run_with_successor_contract(_base.fit_family, family, replicate, output_dir)


def evaluate_terminal(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    return _run_with_successor_contract(_base.evaluate_terminal, input_dir, output_dir)


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
        decision = evaluate_terminal(args.input_dir, args.output_dir)
        print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
