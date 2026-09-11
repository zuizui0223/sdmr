"""Fresh prospective known-truth validation for attribution eligibility v19."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from .alignment_transport_v15_development import _pair_routes
from .attribution_eligibility_v19 import load_contract, predict_eligibility
from .conditional_shared_knockout_v8_development import _load as _load_v8, _specs
from .context_geometry_v17 import context_geometry_features
from .context_indexed_attribution import summarize_context_indexed_attribution
from .interval_evidence_process_challenge import _classify_processes as _classify_interval_processes
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .process_challenge_learner import CONTRIBUTORY
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
V15_CONFIG = ROOT / "configs" / "alignment_transport_v15_development.json"
V16_CONFIG = ROOT / "configs" / "context_indexed_attribution_v16_development.json"


def _base_objects():
    dev, v6 = _load_v8()
    sim = v6["simulation"]
    registry = pd.DataFrame(v6["process_registry"])[["predictor", "process", "role"]]
    ecological = tuple(v6["ecological_predictors"])
    observation = tuple(v6["observation_predictors"])
    processes = tuple(v6["process_universe"])
    specs = _specs(v6)
    return dev, v6, sim, registry, ecological, observation, processes, specs


def _frames(family: str, seed: int, sim: dict):
    simulation = simulate_known_truth_plant_niche(
        family,
        seed=int(seed),
        n_cells=int(sim["n_cells"]),
        n_occurrences=int(sim["n_occurrences"]),
        n_target_group=int(sim["n_target_group"]),
    )
    occurrences, background = _selection_frames(simulation, family=family, seed=int(seed))
    split = freeze_occurrence_answer_check_split(
        occurrences,
        id_col="occurrence_id",
        lon_col="longitude",
        lat_col="latitude",
        n_blocks=int(sim["outer_n_blocks"]),
        holdout_fraction=float(sim["answer_check_fraction"]),
        random_state=int(sim["outer_random_state_offset"]) + int(seed),
    )
    presence = split.model_pool(occurrences)
    inner = make_spatial_partition(
        presence["longitude"].to_numpy(float),
        presence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=int(sim["inner_n_blocks"]),
        holdout_fraction=0.20,
        random_state=int(sim["inner_random_state_offset"]) + int(seed),
    )
    return presence, background, np.asarray(inner.presence_blocks), np.asarray(inner.background_blocks)


def _closure_and_conditioning(registry: pd.DataFrame, processes: tuple[str, ...], process: str):
    closure = tuple(process_information_closure(registry, process))
    others = [tuple(process_information_closure(registry, q)) for q in processes if q != process]
    overlap = set(closure) & set(x for cols in others for x in cols)
    conditioning = tuple(dict.fromkeys(x for cols in others for x in cols if x not in set(closure)))
    if overlap or not conditioning:
        return closure, tuple(), False
    return closure, conditioning, True


def predict_shard(family: str, process: str, output_dir: str | Path):
    contract = load_contract()
    if family not in tuple(contract["families"]):
        raise ValueError("family outside frozen v19 denominator")
    allowed = tuple(contract["target_processes"]) + tuple(contract["negative_control_processes"])
    if process not in allowed:
        raise ValueError("process outside frozen v19 denominator")
    _, _, sim, registry, _, _, processes, _ = _base_objects()
    rows = []
    for seed in contract["fresh_seed_denominator"]:
        presence, background, p_groups, b_groups = _frames(family, int(seed), sim)
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
    frame.to_csv(out / "pretruth_predictions.csv", index=False)
    receipt = {
        "purpose": "attribution_eligibility_v19_pretruth_prediction_shard",
        "family": family,
        "target_process": process,
        "n_contexts": int(len(frame)),
        "generating_truth_read": False,
        "context_status_read": False,
        "classifier_refit": False,
        "threshold_changed": False,
    }
    (out / "pretruth_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def truth_shard(family: str, process: str, output_dir: str | Path):
    contract = load_contract()
    if family not in tuple(contract["families"]) or process not in tuple(contract["target_processes"]):
        raise ValueError("truth shard outside frozen positive-process denominator")
    dev, v6, sim, registry, ecological, observation, processes, specs = _base_objects()
    learner = v6["learner"]
    v15 = json.loads(V15_CONFIG.read_text(encoding="utf-8"))
    v16 = json.loads(V16_CONFIG.read_text(encoding="utf-8"))
    pair_rows = []
    for seed in contract["fresh_seed_denominator"]:
        presence, background, p_groups, b_groups = _frames(family, int(seed), sim)
        target_blocks = sorted(set(p_groups.tolist()) & set(b_groups.tolist()))
        source_blocks = sorted(set(b_groups.tolist()))
        for target in target_blocks:
            for source in source_blocks:
                if int(source) == int(target):
                    continue
                routes, evaluable, reason = _pair_routes(
                    presence,
                    background,
                    p_groups,
                    b_groups,
                    process=str(process),
                    source_block=int(source),
                    target_block=int(target),
                    ecological=ecological,
                    observation=observation,
                    registry=registry,
                    processes=processes,
                    specs=specs,
                    learner=learner,
                    degree=int(dev["knockout_degree"]),
                    ridge_alpha=float(dev["knockout_ridge_alpha"]),
                    minimum_source_rows=int(v15["minimum_source_complete_rows"]),
                )
                pair_status = "unresolved"
                reproduces = False
                if evaluable:
                    classified = _classify_interval_processes(
                        routes,
                        (str(process),),
                        expected_model_labels=tuple(s.label for s in specs),
                    )
                    pair_status = str(classified.iloc[0]["status"])
                    reproduces = pair_status != CONTRIBUTORY
                pair_rows.append({
                    "family": str(family),
                    "seed": int(seed),
                    "target_process": str(process),
                    "source_block": int(source),
                    "target_block": int(target),
                    "evaluable": bool(evaluable),
                    "reproduces_v8_noncontributory": bool(reproduces),
                    "pair_status": pair_status,
                    "reason": str(reason),
                })
    pairs = pd.DataFrame(pair_rows)
    targets, _, _ = summarize_context_indexed_attribution(
        pairs,
        minimum_evaluable_sources=int(v16["minimum_evaluable_source_maps"]),
    )
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    targets.to_csv(out / "context_truth.csv", index=False)
    return {"family": family, "target_process": process, "n_contexts": int(len(targets))}


def terminal(prediction_dir: str | Path, truth_dir: str | Path, output_dir: str | Path):
    contract = load_contract()
    pred_files = list(Path(prediction_dir).rglob("pretruth_predictions.csv"))
    expected_pred_shards = len(contract["families"]) * (len(contract["target_processes"]) + len(contract["negative_control_processes"]))
    if len(pred_files) != expected_pred_shards:
        raise ValueError(f"v19 requires {expected_pred_shards} frozen prediction shards before truth open")
    pred = pd.concat([pd.read_csv(x) for x in pred_files], ignore_index=True)
    truth_files = list(Path(truth_dir).rglob("context_truth.csv"))
    expected_truth_shards = len(contract["families"]) * len(contract["target_processes"])
    if len(truth_files) != expected_truth_shards:
        raise ValueError(f"v19 requires {expected_truth_shards} truth shards")
    truth = pd.concat([pd.read_csv(x) for x in truth_files], ignore_index=True)

    key = ["family", "seed", "target_process", "target_block"]
    positive = pred.loc[pred["target_process"].isin(contract["target_processes"])].merge(
        truth[key + ["context_status"]], on=key, how="inner", validate="one_to_one"
    )
    positive["truth_eligibility"] = np.where(
        positive["context_status"].astype(str).eq("context_contributory"),
        "eligible",
        np.where(
            positive["context_status"].astype(str).isin(["context_replaceable", "context_unresolved"]),
            "not_eligible",
            "insufficient",
        ),
    )
    eval_frame = positive.loc[
        positive["truth_eligibility"].isin(["eligible", "not_eligible"])
        & positive["eligibility_prediction"].isin(["eligible", "not_eligible"])
    ].copy()
    labels = ["eligible", "not_eligible"]
    macro = float(f1_score(eval_frame.truth_eligibility, eval_frame.eligibility_prediction, labels=labels, average="macro", zero_division=0))
    baseline_pred = np.full(len(eval_frame), str(contract["fixed_baseline_class"]), object)
    baseline = float(f1_score(eval_frame.truth_eligibility, baseline_pred, labels=labels, average="macro", zero_division=0))
    precision = float(precision_score(eval_frame.truth_eligibility, eval_frame.eligibility_prediction, pos_label="eligible", zero_division=0))
    recall = float(recall_score(eval_frame.truth_eligibility, eval_frame.eligibility_prediction, pos_label="eligible", zero_division=0))

    negative = pred.loc[pred["target_process"].isin(contract["negative_control_processes"])].copy()
    negative = negative.loc[negative["eligibility_prediction"].isin(["eligible", "not_eligible"])]
    false_eligible_rate = float(negative["eligibility_prediction"].eq("eligible").mean()) if len(negative) else float("nan")

    criteria = contract["success_criteria"]
    checks = {
        "eligible_precision": bool(precision >= float(criteria["eligible_precision_min"])),
        "eligible_recall": bool(recall >= float(criteria["eligible_recall_min"])),
        "macro_f1_gain": bool((macro - baseline) >= float(criteria["macro_f1_gain_over_fixed_baseline_min"])),
        "false_process_eligible_rate": bool(false_eligible_rate <= float(criteria["false_process_eligible_rate_max"])),
    }
    supported = bool(all(checks.values()))
    result = {
        "purpose": "attribution_eligibility_v19_fresh_known_truth_decision",
        "n_evaluable_true_process_contexts": int(len(eval_frame)),
        "n_negative_control_contexts": int(len(negative)),
        "macro_f1": macro,
        "fixed_baseline_macro_f1": baseline,
        "macro_f1_gain": float(macro - baseline),
        "eligible_precision": precision,
        "eligible_recall": recall,
        "false_process_eligible_rate": false_eligible_rate,
        "criteria_pass": checks,
        "prospective_supported": supported,
        "strong_support": bool(supported and precision >= float(contract["strong_support_precision"])),
        "fresh_empirical_validation_authorized": supported,
    }
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    eval_frame.to_csv(out / "true_process_context_decisions.csv", index=False)
    negative.to_csv(out / "false_process_negative_controls.csv", index=False)
    (out / "prospective_decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("predict-shard"); p.add_argument("--family", required=True); p.add_argument("--process", required=True); p.add_argument("--output-dir", required=True)
    t = sub.add_parser("truth-shard"); t.add_argument("--family", required=True); t.add_argument("--process", required=True); t.add_argument("--output-dir", required=True)
    z = sub.add_parser("terminal"); z.add_argument("--prediction-dir", required=True); z.add_argument("--truth-dir", required=True); z.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "predict-shard": result = predict_shard(args.family, args.process, args.output_dir)
    elif args.cmd == "truth-shard": result = truth_shard(args.family, args.process, args.output_dir)
    else: result = terminal(args.prediction_dir, args.truth_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
