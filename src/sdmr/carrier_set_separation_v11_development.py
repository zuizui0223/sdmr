"""Consumed-development diagnosis for background-defined carrier sets (v11)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .carrier_set_separation_v11 import qualify_carrier_set
from .conditional_shared_knockout_v8_development import _load as _load_v8, _specs
from .conditional_shared_knockout_process_challenge import fit_conditional_shared_knockout_process_challenge
from .decorrelation_contrast_v10_development import _block_average
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .process_challenge_learner import CONTRIBUTORY
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .separator_block_process_contrast import separator_block_process_contrast
from .separator_pair_decision import classify_separator_pair
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "carrier_set_separation_v11_development.json"

PAIR_COLUMNS = [
    "family", "seed", "target_process", "carrier_process",
    "carrier_median_heldout_r2", "carrier_n_complete_blocks",
    "status", "n_separating_blocks", "separating_blocks", "pair_decision",
]
CASE_COLUMNS = [
    "family", "seed", "n_shared_candidates", "n_eligible_carriers",
    "n_shared_candidates_with_carrier", "n_pair_audits", "n_pairs_with_separator",
    "n_target_favored_pairs", "n_competitor_favored_pairs",
]


def _config() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "carrier_set_separation_v11_development_only":
        raise ValueError("wrong v11 development contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v11 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001, 15011)):
        raise ValueError("v11 must use exactly consumed 15001-15010")
    if cfg.get("carrier_selection_uses_background_only") is not True:
        raise ValueError("v11 carrier selection must remain background-only")
    if cfg.get("competitor_outcome_status_used_for_carrier_selection") is not False:
        raise ValueError("v11 carrier selection must not use competitor outcome status")
    if cfg.get("separator_selection_uses_occurrence_or_truth") is not False:
        raise ValueError("separator selection must remain outcome-blind")
    if cfg.get("post_outcome_threshold_relaxation_allowed") is not False:
        raise ValueError("post-outcome threshold relaxation forbidden")
    return cfg


def fit_family(family: str, output_dir: str | Path) -> dict[str, object]:
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    cfg = _config()
    dev, v6 = _load_v8()
    sim = v6["simulation"]
    learner = v6["learner"]
    ecological = tuple(v6["ecological_predictors"])
    observation = tuple(v6["observation_predictors"])
    processes = tuple(v6["process_universe"])
    specs = _specs(v6)
    registry = pd.DataFrame(v6["process_registry"])[["predictor", "process", "role"]]
    closures = {p: tuple(process_information_closure(registry, p)) for p in processes}

    pair_rows: list[dict[str, object]] = []
    carrier_parts: list[pd.DataFrame] = []
    contrast_parts: list[pd.DataFrame] = []
    case_rows: list[dict[str, object]] = []

    for seed_value in cfg["consumed_seed_denominator"]:
        seed = int(seed_value)
        simulation = simulate_known_truth_plant_niche(
            family,
            seed=seed,
            n_cells=int(sim["n_cells"]),
            n_occurrences=int(sim["n_occurrences"]),
            n_target_group=int(sim["n_target_group"]),
        )
        occurrences, background = _selection_frames(simulation, family=family, seed=seed)
        split = freeze_occurrence_answer_check_split(
            occurrences,
            id_col="occurrence_id",
            lon_col="longitude",
            lat_col="latitude",
            n_blocks=int(sim["outer_n_blocks"]),
            holdout_fraction=float(sim["answer_check_fraction"]),
            random_state=int(sim["outer_random_state_offset"]) + seed,
        )
        model_presence = split.model_pool(occurrences)
        inner = make_spatial_partition(
            model_presence["longitude"].to_numpy(float),
            model_presence["latitude"].to_numpy(float),
            background["longitude"].to_numpy(float),
            background["latitude"].to_numpy(float),
            n_blocks=int(sim["inner_n_blocks"]),
            holdout_fraction=0.20,
            random_state=int(sim["inner_random_state_offset"]) + seed,
        )
        fit = fit_conditional_shared_knockout_process_challenge(
            model_presence, background, inner.presence_blocks, inner.background_blocks,
            ecological_predictors=ecological,
            observation_predictors=observation,
            process_registry=registry,
            process_universe=processes,
            model_specs=specs,
            n_splits=int(sim["inner_n_splits"]),
            chance_score=float(learner["chance_score"]),
            minimum_margin=float(learner["minimum_margin"]),
            sem_multiplier=float(learner["sem_multiplier"]),
            relative_noninferiority_margin=float(learner["relative_noninferiority_margin"]),
            relative_sem_multiplier=float(learner["relative_sem_multiplier"]),
            density_noninferiority_margin=float(learner["density_noninferiority_margin"]),
            density_sem_multiplier=float(learner["density_sem_multiplier"]),
            density_probability_epsilon=float(learner["density_probability_epsilon"]),
            knockout_degree=int(dev["knockout_degree"]),
            knockout_ridge_alpha=float(dev["knockout_ridge_alpha"]),
            observation_signal_chance=float(learner["observation_signal_chance"]),
            observation_signal_margin=float(learner["observation_signal_margin"]),
            observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),
            observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
            observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),
            occurrence_split=split,
            occurrence_id_col="occurrence_id",
        )
        summary = fit.process_summary.copy()
        summary["shared_candidate"] = summary["v5_status"].astype(str).eq(CONTRIBUTORY) & ~summary["status"].astype(str).eq(CONTRIBUTORY)
        shared = summary.loc[summary["shared_candidate"].astype(bool), "process"].astype(str).tolist()

        n_pair = 0
        n_sep = 0
        n_target_favored = 0
        n_competitor_favored = 0
        n_eligible = 0
        shared_with_carrier = 0

        for p in shared:
            carrier_frame, audits = qualify_carrier_set(
                background,
                inner.background_blocks,
                target_process=p,
                process_universe=processes,
                closures=closures,
                minimum_complete_blocks=int(cfg["carrier_minimum_complete_blocks"]),
                median_heldout_r2_min_exclusive=float(cfg["carrier_median_heldout_r2_min_exclusive"]),
                degree=int(cfg["degree"]),
                ridge_alpha=float(cfg["ridge_alpha"]),
                material_r2_drop=float(cfg["material_r2_drop"]),
                sem_multiplier=float(cfg["sem_multiplier"]),
                minimum_complete_rows_per_block=int(cfg["minimum_complete_rows_per_block"]),
            )
            carrier_frame.insert(0, "seed", seed)
            carrier_frame.insert(0, "family", family)
            carrier_parts.append(carrier_frame)
            eligible = carrier_frame.loc[carrier_frame["eligible_carrier"].astype(bool)]
            carriers = eligible["carrier_process"].astype(str).tolist()
            n_eligible += len(carriers)
            if carriers:
                shared_with_carrier += 1

            for q in carriers:
                n_pair += 1
                audit = audits[q]
                row = eligible.loc[eligible["carrier_process"].astype(str).eq(q)].iloc[0]
                record = {
                    "family": family,
                    "seed": seed,
                    "target_process": p,
                    "carrier_process": q,
                    "carrier_median_heldout_r2": float(row["median_heldout_r2"]),
                    "carrier_n_complete_blocks": int(row["n_complete_blocks"]),
                    "status": "no_separator",
                    "n_separating_blocks": int(len(audit.separating_blocks)),
                    "separating_blocks": ",".join(str(x) for x in audit.separating_blocks),
                    "pair_decision": "incomplete",
                }
                if audit.separating_blocks:
                    record["status"] = "separable_in_principle"
                    n_sep += 1
                    spec_parts = []
                    for spec in specs:
                        ev = separator_block_process_contrast(
                            model_presence,
                            background,
                            inner.presence_blocks,
                            inner.background_blocks,
                            separator_blocks=audit.separating_blocks,
                            target_process=p,
                            competitor_process=q,
                            target_predictors=closures[p],
                            competitor_predictors=closures[q],
                            ecological_predictors=ecological,
                            observation_predictors=observation,
                            model_spec=spec,
                            knockout_degree=int(cfg["degree"]),
                            knockout_ridge_alpha=float(cfg["ridge_alpha"]),
                            density_probability_epsilon=float(learner["density_probability_epsilon"]),
                        )
                        ev.insert(0, "model_label", spec.label)
                        ev.insert(0, "carrier_process", q)
                        ev.insert(0, "target_process", p)
                        ev.insert(0, "seed", seed)
                        ev.insert(0, "family", family)
                        spec_parts.append(ev)
                    raw = pd.concat(spec_parts, ignore_index=True)
                    contrast_parts.append(raw)
                    decision = classify_separator_pair(
                        _block_average(raw, len(specs)),
                        rank_margin=float(cfg["pairwise_rank_margin"]),
                        density_margin=float(cfg["pairwise_density_margin"]),
                        sem_multiplier=float(cfg["pairwise_sem_multiplier"]),
                    )
                    record["pair_decision"] = str(decision["state"])
                    if record["pair_decision"] == "target_favored":
                        n_target_favored += 1
                    elif record["pair_decision"] == "competitor_favored":
                        n_competitor_favored += 1
                pair_rows.append(record)

        case_rows.append(
            {
                "family": family,
                "seed": seed,
                "n_shared_candidates": len(shared),
                "n_eligible_carriers": n_eligible,
                "n_shared_candidates_with_carrier": shared_with_carrier,
                "n_pair_audits": n_pair,
                "n_pairs_with_separator": n_sep,
                "n_target_favored_pairs": n_target_favored,
                "n_competitor_favored_pairs": n_competitor_favored,
            }
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pairs = pd.DataFrame(pair_rows, columns=PAIR_COLUMNS)
    cases = pd.DataFrame(case_rows, columns=CASE_COLUMNS)
    carriers = pd.concat(carrier_parts, ignore_index=True) if carrier_parts else pd.DataFrame()
    contrast = pd.concat(contrast_parts, ignore_index=True) if contrast_parts else pd.DataFrame()
    pairs.to_csv(out / "pair_audit.csv", index=False)
    cases.to_csv(out / "case_summary.csv", index=False)
    carriers.to_csv(out / "carrier_audit.csv", index=False)
    contrast.to_csv(out / "pair_contrast_evidence.csv", index=False)
    return {
        "family": family,
        "n_cases": int(len(cases)),
        "n_shared_candidates": int(cases["n_shared_candidates"].sum()),
        "n_shared_candidates_with_carrier": int(cases["n_shared_candidates_with_carrier"].sum()),
        "n_eligible_carriers": int(cases["n_eligible_carriers"].sum()),
        "n_pair_audits": int(len(pairs)),
        "n_pairs_with_separator": int((pairs["status"].astype(str) == "separable_in_principle").sum()) if len(pairs) else 0,
    }


def _read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns)


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(input_dir)
    pfiles = list(root.rglob("pair_audit.csv"))
    cfiles = list(root.rglob("case_summary.csv"))
    afiles = list(root.rglob("carrier_audit.csv"))
    efiles = list(root.rglob("pair_contrast_evidence.csv"))
    expected = len(KNOWN_TRUTH_FAMILIES)
    if not all(len(x) == expected for x in (pfiles, cfiles, afiles, efiles)):
        raise ValueError("v11 aggregate requires one artifact per family")
    pairs = pd.concat([_read_csv(x, PAIR_COLUMNS) for x in pfiles], ignore_index=True)
    cases = pd.concat([_read_csv(x, CASE_COLUMNS) for x in cfiles], ignore_index=True)
    carriers = pd.concat([_read_csv(x) for x in afiles], ignore_index=True)
    evidence_parts = [frame for frame in (_read_csv(x) for x in efiles) if len(frame.columns)]
    evidence = pd.concat(evidence_parts, ignore_index=True) if evidence_parts else pd.DataFrame()

    shared = int(cases["n_shared_candidates"].sum())
    shared_with_carrier = int(cases["n_shared_candidates_with_carrier"].sum())
    result = {
        "purpose": "carrier_set_separation_v11_consumed_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(len(cases)),
        "n_shared_candidate_cells": shared,
        "n_shared_candidates_with_background_carrier": shared_with_carrier,
        "shared_candidate_carrier_coverage": float(shared_with_carrier / shared) if shared else 1.0,
        "n_eligible_carrier_pairs": int(carriers["eligible_carrier"].astype(bool).sum()) if len(carriers) else 0,
        "n_pair_audits": int(len(pairs)),
        "n_pairs_with_separator": int((pairs["status"].astype(str) == "separable_in_principle").sum()) if len(pairs) else 0,
        "n_target_favored_pairs": int((pairs["pair_decision"].astype(str) == "target_favored").sum()) if len(pairs) else 0,
        "n_competitor_favored_pairs": int((pairs["pair_decision"].astype(str) == "competitor_favored").sum()) if len(pairs) else 0,
        "carrier_selection_background_only": True,
        "competitor_outcome_status_used_for_carrier_selection": False,
        "separator_selection_outcome_blind": True,
        "fresh_known_truth_validation_authorized": False,
        "fresh_empirical_validation_authorized": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(out / "pair_audit.csv", index=False)
    cases.to_csv(out / "case_summary.csv", index=False)
    carriers.to_csv(out / "carrier_audit.csv", index=False)
    evidence.to_csv(out / "pair_contrast_evidence.csv", index=False)
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
