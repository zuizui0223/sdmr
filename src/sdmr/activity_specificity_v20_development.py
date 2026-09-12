"""Development-only diagnosis of geometry eligibility versus occurrence-based activity (v20)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .alignment_transport_v15_development import _pair_routes
from .attribution_eligibility_v19_prospective import V15_CONFIG, V16_CONFIG, _base_objects, _frames
from .context_indexed_attribution import summarize_context_indexed_attribution
from .interval_evidence_process_challenge import _classify_processes as _classify_interval_processes
from .process_challenge_learner import CONTRIBUTORY

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "activity_specificity_v20_development.json"
V19_RUN_ID = 34604615305
V19_TERMINAL_ARTIFACT_ID = 10266322163
V19_TERMINAL_DIGEST = "sha256:365c3c370f7a735a2f1d8bbf8ff5c71d8523cbc4ddf26ae3622ad813b92c152d"


def _config() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "activity_specificity_v20_development_only":
        raise ValueError("wrong v20 contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v20 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(16001, 16011)):
        raise ValueError("v20 denominator must remain consumed seeds 16001-16010")
    if cfg.get("new_scientific_thresholds_allowed") is not False or cfg.get("post_outcome_rule_changes_allowed") is not False:
        raise ValueError("v20 may not add or retune scientific thresholds")
    return cfg


def activity_shard(family: str, process: str, output_dir: str | Path):
    cfg = _config()
    if family not in tuple(cfg["families"]) or process not in tuple(cfg["false_processes"]):
        raise ValueError("v20 newly computes activity only for frozen false-process controls")
    dev, v6, sim, registry, ecological, observation, processes, specs = _base_objects()
    learner = v6["learner"]
    v15 = json.loads(V15_CONFIG.read_text(encoding="utf-8"))
    v16 = json.loads(V16_CONFIG.read_text(encoding="utf-8"))
    pair_rows = []
    for seed in cfg["consumed_seed_denominator"]:
        presence, background, p_groups, b_groups = _frames(family, int(seed), sim)
        target_blocks = sorted(set(p_groups.tolist()) & set(b_groups.tolist()))
        source_blocks = sorted(set(b_groups.tolist()))
        for target in target_blocks:
            for source in source_blocks:
                if int(source) == int(target):
                    continue
                routes, evaluable, reason = _pair_routes(
                    presence, background, p_groups, b_groups,
                    process=str(process), source_block=int(source), target_block=int(target),
                    ecological=ecological, observation=observation, registry=registry, processes=processes,
                    specs=specs, learner=learner, degree=int(dev["knockout_degree"]),
                    ridge_alpha=float(dev["knockout_ridge_alpha"]),
                    minimum_source_rows=int(v15["minimum_source_complete_rows"]),
                )
                pair_status = "unresolved"
                reproduces = False
                if evaluable:
                    classified = _classify_interval_processes(
                        routes, (str(process),), expected_model_labels=tuple(s.label for s in specs)
                    )
                    pair_status = str(classified.iloc[0]["status"])
                    reproduces = pair_status != CONTRIBUTORY
                pair_rows.append({
                    "family": str(family), "seed": int(seed), "target_process": str(process),
                    "source_block": int(source), "target_block": int(target), "evaluable": bool(evaluable),
                    "reproduces_v8_noncontributory": bool(reproduces), "pair_status": pair_status,
                    "reason": str(reason),
                })
    pairs = pd.DataFrame(pair_rows)
    targets, _, _ = summarize_context_indexed_attribution(
        pairs, minimum_evaluable_sources=int(v16["minimum_evaluable_source_maps"])
    )
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    targets.to_csv(out / "activity_contexts.csv", index=False)
    receipt = {
        "purpose": "activity_specificity_v20_false_process_activity_shard",
        "family": family,
        "target_process": process,
        "n_contexts": int(len(targets)),
        "v19_geometry_recomputed": False,
        "true_process_activity_recomputed": False,
    }
    (out / "activity_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _gate_metrics(frame: pd.DataFrame, positive_col: str) -> dict:
    pos = frame[positive_col].astype(bool)
    true = frame["generating_process_true"].astype(bool)
    n_pos = int(pos.sum())
    tp = int((pos & true).sum())
    fp = int((pos & ~true).sum())
    true_n = int(true.sum())
    false_n = int((~true).sum())
    return {
        "n_positive_calls": n_pos,
        "positive_process_precision": float(tp / n_pos) if n_pos else float("nan"),
        "true_process_positive_rate": float(tp / true_n) if true_n else float("nan"),
        "false_process_positive_rate": float(fp / false_n) if false_n else float("nan"),
    }


def aggregate(input_dir: str | Path, v19_dir: str | Path, output_dir: str | Path):
    cfg = _config()
    root = Path(input_dir)
    act_files = list(root.rglob("activity_contexts.csv"))
    expected = len(cfg["families"]) * len(cfg["false_processes"])
    if len(act_files) != expected:
        raise ValueError(f"v20 requires exactly {expected} false-process activity shards")
    act = pd.concat([pd.read_csv(x) for x in act_files], ignore_index=True)

    v19_root = Path(v19_dir)
    true_files = list(v19_root.rglob("true_process_context_decisions.csv"))
    false_files = list(v19_root.rglob("false_process_negative_controls.csv"))
    if len(true_files) != 1 or len(false_files) != 1:
        raise ValueError("v20 requires the single authoritative v19 terminal artifact")
    true = pd.read_csv(true_files[0])
    false_pred = pd.read_csv(false_files[0])

    key = ["family", "seed", "target_process", "target_block"]
    false = false_pred.merge(
        act[key + ["context_status"]], on=key, how="inner", validate="one_to_one"
    )
    needed = key + ["eligibility_prediction", "context_status"]
    frame = pd.concat([true[needed], false[needed]], ignore_index=True)
    frame["generating_process_true"] = frame["target_process"].isin(cfg["true_processes"])
    frame["geometry_positive"] = frame["eligibility_prediction"].astype(str).eq("eligible")
    frame["activity_positive"] = frame["context_status"].astype(str).eq("context_contributory")
    frame["combined_positive"] = frame["geometry_positive"] & frame["activity_positive"]

    metrics = {
        "geometry_only": _gate_metrics(frame, "geometry_positive"),
        "activity_only": _gate_metrics(frame, "activity_positive"),
        "combined": _gate_metrics(frame, "combined_positive"),
    }
    by_process = []
    for process, g in frame.groupby("target_process", sort=True):
        by_process.append({
            "target_process": str(process),
            "n_contexts": int(len(g)),
            "generating_process_true": bool(g["generating_process_true"].iloc[0]),
            "geometry_positive_rate": float(g["geometry_positive"].mean()),
            "activity_positive_rate": float(g["activity_positive"].mean()),
            "combined_positive_rate": float(g["combined_positive"].mean()),
        })

    result = {
        "purpose": "activity_specificity_v20_consumed_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "v19_authoritative_run_id": V19_RUN_ID,
        "v19_terminal_artifact_id": V19_TERMINAL_ARTIFACT_ID,
        "v19_terminal_digest": V19_TERMINAL_DIGEST,
        "n_contexts": int(len(frame)),
        "metrics": metrics,
        "fresh_known_truth_validation_authorized": False,
        "fresh_empirical_validation_authorized": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out / "context_decisions.csv", index=False)
    pd.DataFrame(by_process).to_csv(out / "process_summary.csv", index=False)
    (out / "development_decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("activity-shard")
    s.add_argument("--family", required=True)
    s.add_argument("--process", required=True)
    s.add_argument("--output-dir", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--input-dir", required=True)
    a.add_argument("--v19-dir", required=True)
    a.add_argument("--output-dir", required=True)
    args = p.parse_args(argv)
    result = activity_shard(args.family, args.process, args.output_dir) if args.cmd == "activity-shard" else aggregate(args.input_dir, args.v19_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
