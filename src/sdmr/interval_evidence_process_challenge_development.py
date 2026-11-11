"""Development-only evaluator for abstention-preserving process challenge v5.

This module does not open a new validation denominator. It reuses the already
burned 13001-13010 x six-family development set to measure the consequence of a
single logical change: relative evidence is three-state
(noninferior/inferior/indeterminate), and viable indeterminate routes abstain.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .density_ratio_process_challenge_development import _load as _load_v4
from .interval_evidence_process_challenge import fit_interval_evidence_process_challenge
from .known_truth_response import infer_true_processes
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .process_challenge_development import _metrics, _specs
from .process_proxy_audit import audit_process_proxy_reconstructability
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .shared_carrier_attribution import attribute_shared_carrier_process_summary
from .validation import make_spatial_partition


ROOT = Path(__file__).resolve().parents[2]
DEV_CONFIG = ROOT / "configs" / "interval_evidence_process_challenge_v5_development.json"


def _load() -> tuple[dict, dict, dict]:
    dev = json.loads(DEV_CONFIG.read_text(encoding="utf-8"))
    v4, base = _load_v4()
    if dev.get("purpose") != "interval_evidence_process_challenge_v5_development_only":
        raise ValueError("wrong v5 development config")
    if dev.get("development_only") is not True or dev.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v5 development must remain non-prospective")
    if dev.get("product_a_reopened") is not False:
        raise ValueError("Product A must remain closed")
    if tuple(dev.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v5 development families changed")
    seeds = tuple(int(x) for x in dev.get("seeds", ()))
    if seeds != tuple(range(13001, 13011)):
        raise ValueError("v5 development seeds changed")
    if int(dev.get("n_cases", -1)) != len(KNOWN_TRUTH_FAMILIES) * len(seeds):
        raise ValueError("v5 development denominator changed")
    if dev.get("no_threshold_changes_from_v4") is not True:
        raise ValueError("v5 must not retune v4 thresholds")
    if dev.get("shared_carrier_attribution_unchanged") is not True:
        raise ValueError("v5 shared-carrier attribution must remain unchanged")

    density = v4["density_ratio"]
    if not np.isclose(float(dev["rank_margin"]), float(v4["rank_relative_noninferiority_margin"])):
        raise ValueError("v5 rank margin differs from v4")
    if not np.isclose(float(dev["rank_sem_multiplier"]), float(v4["rank_relative_sem_multiplier"])):
        raise ValueError("v5 rank SEM multiplier differs from v4")
    if not np.isclose(float(dev["density_margin_nats"]), float(density["noninferiority_margin_nats"])):
        raise ValueError("v5 density margin differs from v4")
    if not np.isclose(float(dev["density_sem_multiplier"]), float(density["sem_multiplier"])):
        raise ValueError("v5 density SEM multiplier differs from v4")
    if tuple(dev["families"]) != tuple(v4["families"]) or tuple(dev["seeds"]) != tuple(v4["seeds"]):
        raise ValueError("v5 denominator differs from v4 development")
    return dev, v4, base


def _truth_for_family(family: str) -> set[str]:
    frame = pd.DataFrame(
        {"scenario": [family], "temperature": [0.0], "water": [0.0], "soil": [0.0]}
    )
    return set(infer_true_processes(frame))


def _fit_family(family: str, dev: dict, v4: dict, base: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    if family not in tuple(dev["families"]):
        raise ValueError(f"family outside v5 development denominator: {family}")
    sim_cfg = base["simulation"]
    learner_cfg = base["learner"]
    density_cfg = v4["density_ratio"]
    attr_cfg = v4["shared_carrier_attribution"]
    ecological_predictors = tuple(str(x) for x in base["ecological_predictors"])
    observation_predictors = tuple(str(x) for x in base["observation_predictors"])
    processes = tuple(str(x) for x in base["process_universe"])
    registry = pd.DataFrame(base["process_registry"])[["predictor", "process", "role"]].copy()
    truth = _truth_for_family(family)

    process_rows: list[pd.DataFrame] = []
    case_rows: list[dict[str, object]] = []
    for seed in tuple(int(x) for x in dev["seeds"]):
        simulation = simulate_known_truth_plant_niche(
            family,
            seed=seed,
            n_cells=int(sim_cfg["n_cells"]),
            n_occurrences=int(sim_cfg["n_occurrences"]),
            n_target_group=int(sim_cfg["n_target_group"]),
        )
        occurrences, background = _selection_frames(simulation, family=family, seed=seed)
        split = freeze_occurrence_answer_check_split(
            occurrences,
            id_col="occurrence_id",
            lon_col="longitude",
            lat_col="latitude",
            n_blocks=int(sim_cfg["outer_n_blocks"]),
            holdout_fraction=float(sim_cfg["answer_check_fraction"]),
            random_state=int(sim_cfg["outer_random_state_offset"]) + seed,
        )
        model_presence = split.model_pool(occurrences)
        inner = make_spatial_partition(
            model_presence["longitude"].to_numpy(float),
            model_presence["latitude"].to_numpy(float),
            background["longitude"].to_numpy(float),
            background["latitude"].to_numpy(float),
            n_blocks=int(sim_cfg["inner_n_blocks"]),
            holdout_fraction=0.20,
            random_state=int(sim_cfg["inner_random_state_offset"]) + seed,
        )
        fit = fit_interval_evidence_process_challenge(
            model_presence,
            background,
            inner.presence_blocks,
            inner.background_blocks,
            ecological_predictors=ecological_predictors,
            observation_predictors=observation_predictors,
            process_registry=registry,
            process_universe=processes,
            model_specs=_specs(base),
            n_splits=int(sim_cfg["inner_n_splits"]),
            chance_score=float(learner_cfg["chance_score"]),
            minimum_margin=float(learner_cfg["minimum_margin"]),
            sem_multiplier=float(learner_cfg["sem_multiplier"]),
            relative_noninferiority_margin=float(dev["rank_margin"]),
            relative_sem_multiplier=float(dev["rank_sem_multiplier"]),
            density_noninferiority_margin=float(dev["density_margin_nats"]),
            density_sem_multiplier=float(dev["density_sem_multiplier"]),
            density_probability_epsilon=float(density_cfg["probability_epsilon"]),
            observation_signal_chance=float(learner_cfg["observation_signal_chance"]),
            observation_signal_margin=float(learner_cfg["observation_signal_margin"]),
            observation_signal_sem_multiplier=float(learner_cfg["observation_signal_sem_multiplier"]),
            observation_weight_truncation_quantile=float(learner_cfg["observation_weight_truncation_quantile"]),
            observation_weight_probability_epsilon=float(learner_cfg["observation_weight_probability_epsilon"]),
            occurrence_split=split,
            occurrence_id_col="occurrence_id",
        )

        summary = fit.process_summary.merge(
            fit.v4_fit.process_summary[["process", "status"]].rename(columns={"status": "v4_status"}),
            on="process",
            how="left",
            validate="one_to_one",
        ).merge(
            fit.v4_fit.v3_fit.process_summary[["process", "status"]].rename(columns={"status": "v3_status"}),
            on="process",
            how="left",
            validate="one_to_one",
        )
        audit = audit_process_proxy_reconstructability(
            background.loc[:, list(ecological_predictors)],
            registry,
            process_universe=processes,
            predictor_universe=ecological_predictors,
            groups=inner.background_blocks,
            n_splits=int(attr_cfg["proxy_audit_n_splits"]),
            degree=int(attr_cfg["proxy_audit_degree"]),
        )
        attributed = attribute_shared_carrier_process_summary(
            summary,
            registry,
            process_universe=processes,
            predictor_universe=ecological_predictors,
            proxy_candidate_summary=audit.candidate_summary,
            minimum_univariate_cv_r2=float(attr_cfg["minimum_univariate_cv_r2"]),
            minimum_abs_spearman=float(attr_cfg["minimum_abs_spearman"]),
            require_other_process_challenge_signal=bool(attr_cfg["require_other_process_challenge_signal"]),
        )
        p = attributed.process_summary.copy()
        p.insert(0, "seed", seed)
        p.insert(0, "family", family)
        p["expected_true_process"] = p["process"].astype(str).isin(truth)
        p["v5_changed_from_v4"] = p["status"].astype(str).ne(p["v4_status"].astype(str))
        p["v5_changed_from_v3"] = p["status"].astype(str).ne(p["v3_status"].astype(str))
        process_rows.append(p)
        case_rows.append(
            {
                "family": family,
                "seed": seed,
                "selection_receipt": fit.selection_receipt,
                "attribution_receipt": attributed.selection_receipt,
                "prediction_model_label": fit.prediction_model_label,
                "n_model_pool_occurrences": len(model_presence),
                "n_answer_check_occurrences": len(split.answer_check_ids),
                "answer_check_used_in_fit": False,
                "proxy_audit_used_outcome": False,
                "proxy_audit_modified_registry": False,
            }
        )
    return pd.concat(process_rows, ignore_index=True), pd.DataFrame(case_rows)


def _write_bundle(process: pd.DataFrame, cases: pd.DataFrame, output_dir: str | Path, *, dev: dict) -> dict[str, object]:
    family_rows = []
    for family, group in process.groupby("family", sort=True):
        row = {"family": family}
        row.update(_metrics(group))
        row["n_v5_status_changes_from_v4"] = int(group["v5_changed_from_v4"].astype(bool).sum())
        row["n_unresolved"] = int(group["attribution_status"].astype(str).eq("unresolved").sum())
        family_rows.append(row)
    decision = {
        "purpose": "interval_evidence_process_challenge_v5_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(len(cases)),
        "rank_margin": float(dev["rank_margin"]),
        "density_margin_nats": float(dev["density_margin_nats"]),
        "n_v5_status_changes_from_v4": int(process["v5_changed_from_v4"].astype(bool).sum()),
        "overall_metrics": _metrics(process),
        "n_unresolved": int(process["attribution_status"].astype(str).eq("unresolved").sum()),
        "product_a_reopened": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    process.sort_values(["family", "seed", "process"], kind="mergesort").to_csv(out / "process_evaluation.csv", index=False)
    cases.sort_values(["family", "seed"], kind="mergesort").to_csv(out / "case_summary.csv", index=False)
    pd.DataFrame(family_rows).to_csv(out / "family_metrics.csv", index=False)
    (out / "development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def run_family(family: str, output_dir: str | Path) -> dict[str, object]:
    dev, v4, base = _load()
    process, cases = _fit_family(family, dev, v4, base)
    decision = _write_bundle(process, cases, output_dir, dev=dev)
    decision["family"] = family
    (Path(output_dir) / "development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    dev, _, _ = _load()
    root = Path(input_dir)
    process_files = list(root.rglob("process_evaluation.csv"))
    case_files = list(root.rglob("case_summary.csv"))
    if len(process_files) != len(dev["families"]) or len(case_files) != len(dev["families"]):
        raise ValueError("v5 aggregate requires exactly one artifact per family")
    process = pd.concat([pd.read_csv(path) for path in process_files], ignore_index=True)
    cases = pd.concat([pd.read_csv(path) for path in case_files], ignore_index=True)
    expected_pairs = {(str(f), int(s)) for f in dev["families"] for s in dev["seeds"]}
    observed_pairs = set(zip(cases["family"].astype(str), cases["seed"].astype(int), strict=True))
    if observed_pairs != expected_pairs or len(cases) != int(dev["n_cases"]):
        raise ValueError("v5 development denominator changed")
    if cases["answer_check_used_in_fit"].astype(bool).any():
        raise ValueError("sealed answer-check leaked into v5 fit")
    if cases["proxy_audit_used_outcome"].astype(bool).any():
        raise ValueError("outcome leaked into v5 proxy audit")
    if cases["proxy_audit_modified_registry"].astype(bool).any():
        raise ValueError("v5 proxy audit modified registry")
    return _write_bundle(process, cases, output_dir, dev=dev)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--family", choices=KNOWN_TRUTH_FAMILIES)
    parser.add_argument("--input-dir")
    args = parser.parse_args(argv)
    if args.family and args.input_dir:
        raise ValueError("choose either --family or --input-dir")
    if args.family:
        result = run_family(args.family, args.output_dir)
    elif args.input_dir:
        result = aggregate(args.input_dir, args.output_dir)
    else:
        dev, v4, base = _load()
        parts = [_fit_family(str(f), dev, v4, base) for f in dev["families"]]
        result = _write_bundle(
            pd.concat([x[0] for x in parts], ignore_index=True),
            pd.concat([x[1] for x in parts], ignore_index=True),
            args.output_dir,
            dev=dev,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
