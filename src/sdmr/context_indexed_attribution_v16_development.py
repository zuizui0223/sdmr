"""Consumed-development runner for context-indexed attribution v16."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .alignment_transport_v15_development import fit_family as fit_v15_family
from .context_indexed_attribution import summarize_context_indexed_attribution
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "context_indexed_attribution_v16_development.json"


def _config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "context_indexed_attribution_v16_development_only":
        raise ValueError("wrong v16 development contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v16 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001, 15011)):
        raise ValueError("v16 must remain on consumed seeds 15001-15010")
    if cfg.get("new_scientific_thresholds_allowed") is not False or cfg.get("post_outcome_rule_changes_allowed") is not False:
        raise ValueError("v16 threshold/rule changes are forbidden")
    return cfg


def fit_family(family: str, output_dir: str | Path):
    cfg = _config()
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    v15_dir = out / "v15"
    fit_v15_family(family, v15_dir)
    pairs = pd.read_csv(v15_dir / "pair_summary.csv")
    if pairs.empty:
        pd.DataFrame(columns=["family","seed","target_process","target_block","n_evaluable_source_maps","n_reproduced_source_maps","reproduction_rate","context_status"]).to_csv(out / "target_context_summary.csv", index=False)
        pd.DataFrame(columns=["family","seed","target_process","source_block","n_evaluable_target_blocks","n_reproduced_target_blocks","reproduction_rate"]).to_csv(out / "source_context_summary.csv", index=False)
        pd.DataFrame(columns=["family","seed","target_process","n_target_contexts","n_context_replaceable","n_context_contributory","n_context_unresolved","n_context_insufficient","target_context_rate_sd","source_map_rate_sd","target_variation_exceeds_source_variation"]).to_csv(out / "cell_context_summary.csv", index=False)
        return {"family": family, "n_focus_cells": 0}

    targets, sources, cells = summarize_context_indexed_attribution(
        pairs,
        minimum_evaluable_sources=int(cfg["minimum_evaluable_source_maps"]),
    )
    targets.to_csv(out / "target_context_summary.csv", index=False)
    sources.to_csv(out / "source_context_summary.csv", index=False)
    cells.to_csv(out / "cell_context_summary.csv", index=False)
    return {"family": family, "n_focus_cells": int(len(cells)), "n_target_contexts": int(len(targets))}


def _read(path: Path):
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def aggregate(input_dir: str | Path, output_dir: str | Path):
    root = Path(input_dir)
    expected = len(KNOWN_TRUTH_FAMILIES)
    names = ["target_context_summary.csv", "source_context_summary.csv", "cell_context_summary.csv"]
    files = {name: list(root.rglob(name)) for name in names}
    if any(len(paths) != expected for paths in files.values()):
        raise ValueError("v16 aggregate requires one artifact per family")
    merged = {name: pd.concat([_read(path) for path in paths], ignore_index=True) for name, paths in files.items()}
    cells = merged["cell_context_summary.csv"]
    targets = merged["target_context_summary.csv"]
    if len(cells) != 9:
        raise ValueError("v16 aggregate must preserve the frozen 9-cell denominator")
    counts = targets["context_status"].astype(str).value_counts()
    result = {
        "purpose": "context_indexed_attribution_v16_consumed_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_focus_cells": 9,
        "n_target_contexts": int(len(targets)),
        "n_context_replaceable": int(counts.get("context_replaceable", 0)),
        "n_context_contributory": int(counts.get("context_contributory", 0)),
        "n_context_unresolved": int(counts.get("context_unresolved", 0)),
        "n_context_insufficient": int(counts.get("insufficient", 0)),
        "n_cells_target_variation_exceeds_source_variation": int(cells["target_variation_exceeds_source_variation"].astype(bool).sum()),
        "fresh_known_truth_validation_authorized": False,
        "fresh_empirical_validation_authorized": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in merged.items():
        frame.to_csv(out / name, index=False)
    (out / "development_decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit-family")
    f.add_argument("--family", required=True)
    f.add_argument("--output-dir", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--input-dir", required=True)
    a.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    result = fit_family(args.family, args.output_dir) if args.cmd == "fit-family" else aggregate(args.input_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
