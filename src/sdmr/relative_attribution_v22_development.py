"""Development-only orchestration for v22 relative attribution.

The first gate is denominator preservation: derive the unordered co-supported
pair manifest mechanically from the authoritative v21 terminal table and check
its frozen row/context/pair counts before any directional pair evidence is run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .relative_attribution_v22 import build_supported_pair_manifest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "relative_attribution_v22_development.json"


def load_contract() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "relative_attribution_v22_development":
        raise ValueError("wrong v22 contract")
    if cfg.get("scope") != "development_only_on_consumed_v21_seeds":
        raise ValueError("v22 must remain consumed-development only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(17001, 17011)):
        raise ValueError("v22 seed denominator changed")
    rule = cfg.get("pairwise_rule", {})
    if rule.get("symmetry_required") is not True:
        raise ValueError("v22 requires mirrored pair evidence")
    forbidden = set(cfg.get("forbidden", ()))
    required_forbidden = {
        "seasonality_specific_penalty",
        "process_name_specific_threshold",
        "post_truth_threshold_tuning",
        "fresh_empirical_claim",
    }
    if not required_forbidden.issubset(forbidden):
        raise ValueError("v22 forbidden-rule set weakened")
    return cfg


def freeze_pair_manifest(context_decisions_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    cfg = load_contract()
    source = cfg["authoritative_v21_source"]
    frame = pd.read_csv(context_decisions_csv)
    expected_rows = int(source["expected_context_rows"])
    if len(frame) != expected_rows:
        raise ValueError(f"v21 context row denominator drift: {len(frame)} != {expected_rows}")
    seeds = tuple(sorted(pd.to_numeric(frame["seed"], errors="raise").astype(int).unique().tolist()))
    if seeds != tuple(cfg["consumed_seed_denominator"]):
        raise ValueError("v21 seed denominator drift")
    families = tuple(sorted(frame["family"].astype(str).unique().tolist()))
    if families != tuple(sorted(cfg["families"])):
        raise ValueError("v21 family denominator drift")
    processes = tuple(sorted(frame["target_process"].astype(str).unique().tolist()))
    if processes != tuple(sorted(cfg["processes"])):
        raise ValueError("v21 process denominator drift")

    pairs = build_supported_pair_manifest(frame, process_order=tuple(cfg["processes"]))
    contexts = pairs[["family", "seed", "target_block"]].drop_duplicates()
    expected_contexts = int(source["expected_contexts_with_at_least_two_supported_processes"])
    expected_pairs = int(source["expected_unordered_supported_pairs"])
    if len(contexts) != expected_contexts:
        raise ValueError(f"co-supported context denominator drift: {len(contexts)} != {expected_contexts}")
    if len(pairs) != expected_pairs:
        raise ValueError(f"pair denominator drift: {len(pairs)} != {expected_pairs}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(out / "pair_manifest.csv", index=False)
    receipt = {
        "purpose": "relative_attribution_v22_frozen_pair_manifest",
        "development_only": True,
        "source_v21_workflow_run": int(source["workflow_run"]),
        "source_v21_terminal_artifact": int(source["terminal_artifact"]),
        "source_v21_artifact_digest": str(source["artifact_digest"]),
        "n_context_rows": int(len(frame)),
        "n_co_supported_contexts": int(len(contexts)),
        "n_unordered_supported_pairs": int(len(pairs)),
        "generating_truth_used_for_pair_selection": False,
        "fresh_validation_authorized": False,
    }
    (out / "pair_manifest_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    freeze = sub.add_parser("freeze-pairs")
    freeze.add_argument("--context-decisions", required=True)
    freeze.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "freeze-pairs":
        result = freeze_pair_manifest(args.context_decisions, args.output_dir)
    else:  # pragma: no cover
        raise AssertionError(args.cmd)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
