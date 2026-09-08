"""Development-only separator-availability diagnostic for v10.

Uses the already-consumed 15001-15010 denominator.  v9 shared candidates are
identified from frozen v5 total evidence plus v8 unique evidence; separator
selection itself uses background environments and spatial block labels only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .conditional_shared_knockout_v8_development import _load as _load_v8, _specs
from .conditional_shared_knockout_process_challenge import fit_conditional_shared_knockout_process_challenge
from .environmental_decorrelation_audit import audit_environmental_decorrelation
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .process_challenge_learner import CONTRIBUTORY
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "decorrelation_contrast_v10_development.json"


def _config() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "decorrelation_contrast_v10_development_only":
        raise ValueError("wrong v10 development contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v10 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001, 15011)):
        raise ValueError("v10 must use exactly consumed 15001-15010")
    if cfg.get("separator_selection_uses_occurrence_or_truth") is not False:
        raise ValueError("separator selection must remain outcome-blind")
    if cfg.get("post_outcome_threshold_relaxation_allowed") is not False:
        raise ValueError("post-outcome threshold relaxation forbidden")
    return cfg


def fit_family(family: str, output_dir: str | Path) -> dict[str, object]:
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    cfg = _config(); dev, v6 = _load_v8()
    sim = v6["simulation"]; learner = v6["learner"]
    ecological = tuple(v6["ecological_predictors"]); observation = tuple(v6["observation_predictors"])
    processes = tuple(v6["process_universe"])
    registry = pd.DataFrame(v6["process_registry"])[["predictor", "process", "role"]]
    closures = {p: tuple(process_information_closure(registry, p)) for p in processes}
    rows: list[dict[str, object]] = []
    case_rows: list[dict[str, object]] = []
    for seed in cfg["consumed_seed_denominator"]:
        seed = int(seed)
        simulation = simulate_known_truth_plant_niche(family, seed=seed, n_cells=int(sim["n_cells"]), n_occurrences=int(sim["n_occurrences"]), n_target_group=int(sim["n_target_group"]))
        occurrences, background = _selection_frames(simulation, family=family, seed=seed)
        split = freeze_occurrence_answer_check_split(occurrences, id_col="occurrence_id", lon_col="longitude", lat_col="latitude", n_blocks=int(sim["outer_n_blocks"]), holdout_fraction=float(sim["answer_check_fraction"]), random_state=int(sim["outer_random_state_offset"]) + seed)
        model_presence = split.model_pool(occurrences)
        inner = make_spatial_partition(model_presence["longitude"].to_numpy(float), model_presence["latitude"].to_numpy(float), background["longitude"].to_numpy(float), background["latitude"].to_numpy(float), n_blocks=int(sim["inner_n_blocks"]), holdout_fraction=0.20, random_state=int(sim["inner_random_state_offset"]) + seed)
        fit = fit_conditional_shared_knockout_process_challenge(
            model_presence, background, inner.presence_blocks, inner.background_blocks,
            ecological_predictors=ecological, observation_predictors=observation,
            process_registry=registry, process_universe=processes, model_specs=_specs(v6),
            n_splits=int(sim["inner_n_splits"]), chance_score=float(learner["chance_score"]), minimum_margin=float(learner["minimum_margin"]), sem_multiplier=float(learner["sem_multiplier"]),
            relative_noninferiority_margin=float(learner["relative_noninferiority_margin"]), relative_sem_multiplier=float(learner["relative_sem_multiplier"]), density_noninferiority_margin=float(learner["density_noninferiority_margin"]), density_sem_multiplier=float(learner["density_sem_multiplier"]), density_probability_epsilon=float(learner["density_probability_epsilon"]), knockout_degree=int(dev["knockout_degree"]), knockout_ridge_alpha=float(dev["knockout_ridge_alpha"]),
            observation_signal_chance=float(learner["observation_signal_chance"]), observation_signal_margin=float(learner["observation_signal_margin"]), observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]), observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]), observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]), occurrence_split=split, occurrence_id_col="occurrence_id",
        )
        summary = fit.process_summary.copy()
        summary["shared_candidate"] = summary["v5_status"].astype(str).eq(CONTRIBUTORY) & ~summary["status"].astype(str).eq(CONTRIBUTORY)
        shared = summary.loc[summary["shared_candidate"].astype(bool), "process"].astype(str).tolist()
        n_pair = 0; n_sep = 0
        for p in shared:
            for q in processes:
                if q == p:
                    continue
                n_pair += 1
                record = {"family": family, "seed": seed, "target_process": p, "competitor_process": q, "status": "insufficient", "n_separating_blocks": 0, "separating_blocks": ""}
                try:
                    result = audit_environmental_decorrelation(
                        background, inner.background_blocks,
                        target_process=p, competitor_process=q,
                        target_predictors=closures[p], competitor_predictors=closures[q],
                        degree=int(cfg["degree"]), ridge_alpha=float(cfg["ridge_alpha"]), material_r2_drop=float(cfg["material_r2_drop"]), sem_multiplier=float(cfg["sem_multiplier"]), minimum_complete_rows_per_block=int(cfg["minimum_complete_rows_per_block"]),
                    )
                    if result.separating_blocks:
                        record["status"] = "separable_in_principle"; record["n_separating_blocks"] = len(result.separating_blocks); record["separating_blocks"] = ",".join(str(x) for x in result.separating_blocks); n_sep += 1
                    else:
                        record["status"] = "no_separator"
                except ValueError as exc:
                    record["status"] = "structural_overlap" if "structurally disjoint" in str(exc) else "insufficient"
                rows.append(record)
        case_rows.append({"family": family, "seed": seed, "n_shared_candidates": len(shared), "n_pair_audits": n_pair, "n_pairs_with_separator": n_sep})
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pair = pd.DataFrame(rows); cases = pd.DataFrame(case_rows)
    pair.to_csv(out / "pair_audit.csv", index=False); cases.to_csv(out / "case_summary.csv", index=False)
    return {"family": family, "n_cases": int(len(cases)), "n_pair_audits": int(len(pair)), "n_pairs_with_separator": int((pair.get("status", pd.Series(dtype=str)).astype(str) == "separable_in_principle").sum())}


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(input_dir)
    pfiles = list(root.rglob("pair_audit.csv")); cfiles = list(root.rglob("case_summary.csv"))
    if len(pfiles) != len(KNOWN_TRUTH_FAMILIES) or len(cfiles) != len(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v10 aggregate requires one artifact per family")
    pairs = pd.concat([pd.read_csv(x) for x in pfiles], ignore_index=True)
    cases = pd.concat([pd.read_csv(x) for x in cfiles], ignore_index=True)
    status_counts = pairs["status"].value_counts().to_dict() if len(pairs) else {}
    shared_cells = int(cases["n_shared_candidates"].sum())
    case_with_any_separator = int((cases["n_pairs_with_separator"] > 0).sum())
    decision = {
        "purpose": "decorrelation_contrast_v10_separator_availability",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_cases": int(len(cases)),
        "n_shared_candidate_cells": shared_cells,
        "n_pair_audits": int(len(pairs)),
        "pair_status_counts": {str(k): int(v) for k, v in status_counts.items()},
        "n_cases_with_any_separator_pair": case_with_any_separator,
        "separator_selection_outcome_blind": True,
        "contrast_outcome_not_yet_evaluated": True,
        "fresh_known_truth_validation_authorized": False,
        "fresh_empirical_validation_authorized": False
    }
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(out / "pair_audit.csv", index=False); cases.to_csv(out / "case_summary.csv", index=False)
    (out / "development_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def main(argv=None):
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit-family"); f.add_argument("--family", required=True); f.add_argument("--output-dir", required=True)
    a = sub.add_parser("aggregate"); a.add_argument("--input-dir", required=True); a.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    result = fit_family(args.family, args.output_dir) if args.cmd == "fit-family" else aggregate(args.input_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
