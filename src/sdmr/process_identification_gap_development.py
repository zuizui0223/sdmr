"""Crosswalk fixed v3.2 and oracle development artifacts.

No model is fit here. The runner only joins two already-completed development
artifacts on family x seed x process and quantifies the gap between what the
complete truth surface says is representation-identifiable and what the sealed
occurrence-only learner recovered.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .process_identification_gap import compare_process_identification_to_oracle


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "process_identification_gap_development.json"


def _load_config() -> dict:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    if payload.get("purpose") != "process_identification_gap_development_only":
        raise ValueError("wrong process identification gap config")
    if payload.get("development_only") is not True:
        raise ValueError("identification-gap analysis must remain development-only")
    if payload.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("identification-gap development cannot become prospective evidence")
    if int(payload.get("expected_rows", -1)) != 300:
        raise ValueError("identification-gap expected row denominator changed")
    if tuple(int(x) for x in payload.get("development_seeds", ())) != tuple(range(13001, 13011)):
        raise ValueError("identification-gap development seeds changed")
    return payload


def _find_file(root: str | Path, filename: str) -> Path:
    matches = list(Path(root).rglob(filename))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {filename!r}, found {len(matches)}")
    return matches[0]


def run(learner_dir: str | Path, oracle_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    config = _load_config()
    learner_path = _find_file(learner_dir, str(config["learner_source"]["process_file"]))
    oracle_path = _find_file(oracle_dir, str(config["oracle_source"]["process_file"]))
    learner = pd.read_csv(learner_path)
    oracle = pd.read_csv(oracle_path)
    if len(learner) != int(config["expected_rows"]) or len(oracle) != int(config["expected_rows"]):
        raise ValueError("identification-gap source denominator changed")

    result = compare_process_identification_to_oracle(
        learner,
        oracle,
        key_columns=tuple(config["key_columns"]),
    )
    observed_seeds = tuple(sorted(set(result.comparison["seed"].astype(int))))
    if observed_seeds != tuple(int(x) for x in config["development_seeds"]):
        raise ValueError("identification-gap source seeds changed")
    observed_cases = result.comparison[["family", "seed"]].drop_duplicates()
    if len(observed_cases) != int(config["expected_cases"]):
        raise ValueError("identification-gap case denominator changed")

    decision = {
        "purpose": "process_identification_gap_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_rows": int(len(result.comparison)),
        "n_cases": int(len(observed_cases)),
        "learner_source": config["learner_source"],
        "oracle_source": config["oracle_source"],
        "overall_metrics": result.overall_metrics,
        "selection_receipt": result.selection_receipt,
        "product_a_reopened": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.comparison.to_csv(out / "identification_gap_comparison.csv", index=False)
    result.by_process.to_csv(out / "identification_gap_by_process.csv", index=False)
    result.by_family.to_csv(out / "identification_gap_by_family.csv", index=False)
    (out / "identification_gap_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learner-dir", required=True)
    parser.add_argument("--oracle-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    decision = run(args.learner_dir, args.oracle_dir, args.output_dir)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
