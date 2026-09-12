"""Prospective fresh known-truth validation of two-tier process support (v21)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .activity_specificity_v20_development import activity_shard as _v20_activity_shard
from .attribution_eligibility_v19 import predict_eligibility
from .attribution_eligibility_v19_prospective import _base_objects, _frames, _closure_and_conditioning
from .context_geometry_v17 import context_geometry_features

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "two_tier_process_support_v21_prospective.json"


def load_contract() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "two_tier_process_support_v21_prospective_known_truth_validation":
        raise ValueError("wrong v21 contract")
    if tuple(int(x) for x in cfg.get("fresh_seed_denominator", ())) != tuple(range(17001, 17011)):
        raise ValueError("v21 fresh denominator changed")
    if tuple(cfg.get("true_processes", ())) != ("temperature", "water"):
        raise ValueError("v21 true-process set changed")
    if tuple(cfg.get("false_processes", ())) != ("seasonality", "noise"):
        raise ValueError("v21 false-process set changed")
    if cfg.get("target_selection_uses_outcomes") is not False:
        raise ValueError("v21 target selection must remain outcome-blind")
    if cfg.get("classifier_refit_allowed") is not False:
        raise ValueError("v21 may not refit the geometry classifier")
    if cfg.get("new_scientific_thresholds_allowed") is not False or cfg.get("post_outcome_rule_changes_allowed") is not False:
        raise ValueError("v21 may not tune scientific rules after outcome inspection")
    return cfg


def geometry_shard(family: str, process: str, output_dir: str | Path):
    cfg = load_contract()
    allowed = tuple(cfg["true_processes"]) + tuple(cfg["false_processes"])
    if family not in tuple(cfg["families"]) or process not in allowed:
        raise ValueError("family/process outside v21 denominator")
    _, _, sim, registry, _, _, processes, _ = _base_objects()
    rows = []
    for seed in cfg["fresh_seed_denominator"]:
        _, background, p_groups, b_groups = _frames(family, int(seed), sim)
        closure, conditioning, ok = _closure_and_conditioning(registry, processes, str(process))
        if not ok:
            continue
        target_blocks = sorted(set(p_groups.tolist()) & set(b_groups.tolist()))
        for target in target_blocks:
            ref = background.loc[b_groups != int(target)].reset_index(drop=True)
            tgt = background.loc[b_groups == int(target)].reset_index(drop=True)
            geom = context_geometry_features(
                ref,
                tgt,
                process_predictors=closure,
                conditioning_predictors=conditioning,
            )
            rows.append({
                "family": str(family),
                "seed": int(seed),
                "target_process": str(process),
                "target_block": int(target),
                "conditional_residual_shift": geom.conditional_residual_shift,
                "conditional_residual_scale_ratio": geom.conditional_residual_scale_ratio,
                "conditional_target_r2": geom.conditional_target_r2,
                "process_support_shift": geom.process_support_shift,
                "conditioning_support_shift": geom.conditioning_support_shift,
                "n_reference": int(geom.n_reference),
                "n_target": int(geom.n_target),
            })
    frame = predict_eligibility(pd.DataFrame(rows)) if rows else pd.DataFrame()
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out / "geometry_predictions.csv", index=False)
    return frame


def activity_shard(family: str, process: str, output_dir: str | Path):
    """Same frozen v20 activity machinery, but with the v21 seed denominator."""
    cfg = load_contract()
    allowed = tuple(cfg["true_processes"]) + tuple(cfg["false_processes"])
    if family not in tuple(cfg["families"]) or process not in allowed:
        raise ValueError("family/process outside v21 denominator")

    # Reproduce v20 activity logic with only the denominator changed.
    from .alignment_transport_v15_development import _pair_routes
    from .attribution_eligibility_v19_prospective import V15_CONFIG, V16_CONFIG
    from .context_indexed_attribution import summarize_context_indexed_attribution
    from .interval_evidence_process_challenge import _classify_processes as _classify_interval_processes
    from .process_challenge_learner import CONTRIBUTORY

    dev, v6, sim, registry, ecological, observation, processes, specs = _base_objects()
    learner = v6["learner"]
    v15 = json.loads(V15_CONFIG.read_text(encoding="utf-8"))
    v16 = json.loads(V16_CONFIG.read_text(encoding="utf-8"))
    pair_rows = []
    for seed in cfg["fresh_seed_denominator"]:
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
                pair_status = "unresolved"; reproduces = False
                if evaluable:
                    classified = _classify_interval_processes(
                        routes, (str(process),), expected_model_labels=tuple(s.label for s in specs)
                    )
                    pair_status = str(classified.iloc[0]["status"])
                    reproduces = pair_status != CONTRIBUTORY
                pair_rows.append({
                    "family": str(family), "seed": int(seed), "target_process": str(process),
                    "source_block": int(source), "target_block": int(target), "evaluable": bool(evaluable),
                    "reproduces_v8_noncontributory": bool(reproduces), "pair_status": pair_status, "reason": str(reason),
                })
    pairs = pd.DataFrame(pair_rows)
    targets, _, _ = summarize_context_indexed_attribution(
        pairs, minimum_evaluable_sources=int(v16["minimum_evaluable_source_maps"])
    )
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    targets.to_csv(out / "activity_contexts.csv", index=False)
    return targets


def fit_shard(family: str, process: str, output_dir: str | Path):
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    geom = geometry_shard(family, process, out)
    act = activity_shard(family, process, out)
    receipt = {
        "purpose": "two_tier_process_support_v21_preterminal_shard",
        "family": family,
        "target_process": process,
        "n_geometry_contexts": int(len(geom)),
        "n_activity_contexts": int(len(act)),
        "generating_truth_read": False,
        "classifier_refit": False,
        "scientific_threshold_changed": False,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _metrics(frame: pd.DataFrame, col: str) -> dict:
    pos = frame[col].astype(bool)
    truth = frame["generating_process_true"].astype(bool)
    tp = int((pos & truth).sum()); fp = int((pos & ~truth).sum())
    npos = int(pos.sum()); nt = int(truth.sum()); nf = int((~truth).sum())
    return {
        "n_positive_calls": npos,
        "positive_process_precision": float(tp / npos) if npos else float("nan"),
        "true_process_positive_rate": float(tp / nt) if nt else float("nan"),
        "false_process_positive_rate": float(fp / nf) if nf else float("nan"),
    }


def terminal(input_dir: str | Path, output_dir: str | Path):
    cfg = load_contract(); root = Path(input_dir)
    geom_files = list(root.rglob("geometry_predictions.csv"))
    act_files = list(root.rglob("activity_contexts.csv"))
    expected = len(cfg["families"]) * (len(cfg["true_processes"]) + len(cfg["false_processes"]))
    if len(geom_files) != expected or len(act_files) != expected:
        raise ValueError(f"v21 requires {expected} geometry and activity shards")
    geom = pd.concat([pd.read_csv(x) for x in geom_files], ignore_index=True)
    act = pd.concat([pd.read_csv(x) for x in act_files], ignore_index=True)
    key = ["family", "seed", "target_process", "target_block"]
    frame = geom.merge(act[key + ["context_status"]], on=key, how="inner", validate="one_to_one")
    frame["generating_process_true"] = frame["target_process"].isin(cfg["true_processes"])
    frame["supported"] = frame["context_status"].astype(str).eq("context_contributory")
    frame["high_confidence_supported"] = frame["supported"] & frame["eligibility_prediction"].astype(str).eq("eligible")

    metrics = {
        "supported": _metrics(frame, "supported"),
        "high_confidence_supported": _metrics(frame, "high_confidence_supported"),
    }
    checks = {}
    for tier in ("supported", "high_confidence_supported"):
        m = metrics[tier]; c = cfg["success_criteria"][tier]
        checks[tier] = {
            "positive_process_precision": bool(m["positive_process_precision"] >= float(c["positive_process_precision_min"])),
            "true_process_positive_rate": bool(m["true_process_positive_rate"] >= float(c["true_process_positive_rate_min"])),
            "false_process_positive_rate": bool(m["false_process_positive_rate"] <= float(c["false_process_positive_rate_max"])),
        }
        checks[tier]["all_pass"] = bool(all(checks[tier].values()))

    supported = bool(checks["supported"]["all_pass"] and checks["high_confidence_supported"]["all_pass"])
    by_process = []
    for process, g in frame.groupby("target_process", sort=True):
        by_process.append({
            "target_process": str(process),
            "n_contexts": int(len(g)),
            "generating_process_true": bool(g["generating_process_true"].iloc[0]),
            "supported_rate": float(g["supported"].mean()),
            "high_confidence_supported_rate": float(g["high_confidence_supported"].mean()),
        })
    result = {
        "purpose": "two_tier_process_support_v21_fresh_known_truth_decision",
        "n_contexts": int(len(frame)),
        "metrics": metrics,
        "criteria_pass": checks,
        "prospective_supported": supported,
        "fresh_empirical_validation_authorized": supported,
    }
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out / "context_decisions.csv", index=False)
    pd.DataFrame(by_process).to_csv(out / "process_summary.csv", index=False)
    (out / "prospective_decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("fit-shard"); s.add_argument("--family", required=True); s.add_argument("--process", required=True); s.add_argument("--output-dir", required=True)
    t = sub.add_parser("terminal"); t.add_argument("--input-dir", required=True); t.add_argument("--output-dir", required=True)
    args = p.parse_args(argv)
    result = fit_shard(args.family, args.process, args.output_dir) if args.cmd == "fit-shard" else terminal(args.input_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
