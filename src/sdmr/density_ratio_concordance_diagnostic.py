"""Development-only concordance diagnostic for v4 changed process cells.

This module does not define a new learner and does not alter any threshold. It
loads the already-completed v4 development artifact, selects all and only process
cells whose v4 status changed from v3, reruns those burned development cases with
the frozen v4 configuration, and exports every matched model/process route's
rank and density-score deltas.

The purpose is diagnostic: determine whether v4's added density signal agrees in
direction with the pre-existing rank evidence or behaves as a density-only
signal. No status is reclassified here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .density_ratio_process_challenge import fit_density_ratio_process_challenge
from .density_ratio_process_challenge_development import _load as _load_v4, _specs
from .known_truth_scenarios import simulate_known_truth_plant_niche
from .process_proxy_audit import audit_process_proxy_reconstructability
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .shared_carrier_attribution import attribute_shared_carrier_process_summary
from .validation import make_spatial_partition


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_CONFIG = ROOT / "configs" / "density_ratio_concordance_diagnostic.json"


def _load_diagnostic_config() -> dict:
    cfg = json.loads(DIAGNOSTIC_CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "density_ratio_v4_changed_cell_concordance_diagnostic":
        raise ValueError("wrong v4 concordance diagnostic config")
    if cfg.get("development_only") is not True:
        raise ValueError("v4 concordance diagnostic must remain development-only")
    if cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v4 concordance diagnostic cannot support prospective claims")
    if cfg.get("product_a_reopened") is not False:
        raise ValueError("Product A must remain closed")
    if cfg.get("selection_rule") != "all_and_only_rows_where_v4_changed_from_v3_is_true":
        raise ValueError("changed-cell selection rule drifted")
    if cfg.get("no_margin_retuning") is not True or cfg.get("no_status_reclassification_in_this_diagnostic") is not True:
        raise ValueError("diagnostic must not retune or reclassify")
    return cfg


def _literal_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    lowered = series.astype(str).str.strip().str.lower()
    valid = lowered.isin(["true", "false"])
    if not bool(valid.all()):
        raise ValueError("boolean diagnostic column contains malformed values")
    return lowered.eq("true")


def _changed_cells(process_file: str | Path, cfg: dict) -> pd.DataFrame:
    frame = pd.read_csv(process_file)
    required = {
        "family",
        "seed",
        "process",
        "status",
        "v3_status",
        "expected_true_process",
        "v4_changed_from_v3",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError("v4 process artifact missing columns: " + ", ".join(missing))
    changed = frame.loc[_literal_bool(frame["v4_changed_from_v3"])].copy()
    expected_n = int(cfg["source"]["expected_changed_cells"])
    if len(changed) != expected_n:
        raise ValueError(f"expected {expected_n} changed process cells, found {len(changed)}")
    if changed[["family", "seed", "process"]].duplicated().any():
        raise ValueError("changed-cell artifact contains duplicate family/seed/process keys")
    return changed.sort_values(["family", "seed", "process"], kind="mergesort").reset_index(drop=True)


def _fit_case(family: str, seed: int, dev: dict, base: dict):
    sim_cfg = base["simulation"]
    learner_cfg = base["learner"]
    density_cfg = dev["density_ratio"]
    attr_cfg = dev["shared_carrier_attribution"]
    ecological_predictors = tuple(str(x) for x in base["ecological_predictors"])
    observation_predictors = tuple(str(x) for x in base["observation_predictors"])
    processes = tuple(str(x) for x in base["process_universe"])
    registry = pd.DataFrame(base["process_registry"])[["predictor", "process", "role"]].copy()

    simulation = simulate_known_truth_plant_niche(
        family,
        seed=int(seed),
        n_cells=int(sim_cfg["n_cells"]),
        n_occurrences=int(sim_cfg["n_occurrences"]),
        n_target_group=int(sim_cfg["n_target_group"]),
    )
    occurrences, background = _selection_frames(simulation, family=family, seed=int(seed))
    split = freeze_occurrence_answer_check_split(
        occurrences,
        id_col="occurrence_id",
        lon_col="longitude",
        lat_col="latitude",
        n_blocks=int(sim_cfg["outer_n_blocks"]),
        holdout_fraction=float(sim_cfg["answer_check_fraction"]),
        random_state=int(sim_cfg["outer_random_state_offset"]) + int(seed),
    )
    model_presence = split.model_pool(occurrences)
    inner = make_spatial_partition(
        model_presence["longitude"].to_numpy(float),
        model_presence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=int(sim_cfg["inner_n_blocks"]),
        holdout_fraction=0.20,
        random_state=int(sim_cfg["inner_random_state_offset"]) + int(seed),
    )
    fit = fit_density_ratio_process_challenge(
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
        relative_noninferiority_margin=float(dev["rank_relative_noninferiority_margin"]),
        relative_sem_multiplier=float(dev["rank_relative_sem_multiplier"]),
        density_noninferiority_margin=float(density_cfg["noninferiority_margin_nats"]),
        density_sem_multiplier=float(density_cfg["sem_multiplier"]),
        density_probability_epsilon=float(density_cfg["probability_epsilon"]),
        observation_signal_chance=float(learner_cfg["observation_signal_chance"]),
        observation_signal_margin=float(learner_cfg["observation_signal_margin"]),
        observation_signal_sem_multiplier=float(learner_cfg["observation_signal_sem_multiplier"]),
        observation_weight_truncation_quantile=float(learner_cfg["observation_weight_truncation_quantile"]),
        observation_weight_probability_epsilon=float(learner_cfg["observation_weight_probability_epsilon"]),
        occurrence_split=split,
        occurrence_id_col="occurrence_id",
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
        fit.process_summary,
        registry,
        process_universe=processes,
        predictor_universe=ecological_predictors,
        proxy_candidate_summary=audit.candidate_summary,
        minimum_univariate_cv_r2=float(attr_cfg["minimum_univariate_cv_r2"]),
        minimum_abs_spearman=float(attr_cfg["minimum_abs_spearman"]),
        require_other_process_challenge_signal=bool(attr_cfg["require_other_process_challenge_signal"]),
    )
    return fit, attributed


def run(process_file: str | Path, output_dir: str | Path) -> dict[str, object]:
    cfg = _load_diagnostic_config()
    dev, base = _load_v4()
    changed = _changed_cells(process_file, cfg)

    route_rows: list[pd.DataFrame] = []
    cell_rows: list[dict[str, object]] = []
    cache: dict[tuple[str, int], tuple[object, object]] = {}

    for selected in changed.itertuples(index=False):
        key = (str(selected.family), int(selected.seed))
        if key not in cache:
            cache[key] = _fit_case(key[0], key[1], dev, base)
        fit, attributed = cache[key]
        process = str(selected.process)

        fit_status = str(
            fit.process_summary.loc[fit.process_summary["process"].astype(str).eq(process), "status"].iloc[0]
        )
        v3_status = str(
            fit.v3_fit.process_summary.loc[
                fit.v3_fit.process_summary["process"].astype(str).eq(process), "status"
            ].iloc[0]
        )
        attribution_status = str(
            attributed.process_summary.loc[
                attributed.process_summary["process"].astype(str).eq(process), "attribution_status"
            ].iloc[0]
        )
        if fit_status != str(selected.status) or v3_status != str(selected.v3_status):
            raise ValueError("rerun status does not reproduce fixed v4 artifact")

        group = fit.route_summary.loc[fit.route_summary["excluded_process"].astype(str).eq(process)].copy()
        if group.empty:
            raise ValueError("changed process has no v4 route evidence")
        group.insert(0, "expected_true_process", bool(selected.expected_true_process))
        group.insert(0, "process", process)
        group.insert(0, "seed", int(selected.seed))
        group.insert(0, "family", str(selected.family))
        group["v3_process_status"] = v3_status
        group["v4_process_status"] = fit_status
        group["v4_attribution_status"] = attribution_status
        group["prediction_delta_negative"] = pd.to_numeric(
            group["mean_prediction_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["ecological_rank_delta_negative"] = pd.to_numeric(
            group["mean_ecological_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["density_delta_negative"] = pd.to_numeric(
            group["mean_density_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["ecological_density_delta_negative"] = pd.to_numeric(
            group["mean_ecological_density_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["all_four_mean_deltas_negative"] = (
            group["prediction_delta_negative"]
            & group["ecological_rank_delta_negative"]
            & group["density_delta_negative"]
            & group["ecological_density_delta_negative"]
        )
        group["density_rejected_v3_witness"] = (
            group["relative_noninferior"].astype(bool)
            & ~group["multicriterion_noninferior"].astype(bool)
        )
        route_rows.append(group)

        rejected = group.loc[group["density_rejected_v3_witness"].astype(bool)].copy()
        cell_rows.append(
            {
                "family": str(selected.family),
                "seed": int(selected.seed),
                "process": process,
                "expected_true_process": bool(selected.expected_true_process),
                "v3_process_status": v3_status,
                "v4_process_status": fit_status,
                "v4_attribution_status": attribution_status,
                "n_routes": int(len(group)),
                "n_v3_relative_noninferior_routes": int(group["relative_noninferior"].astype(bool).sum()),
                "n_density_rejected_v3_witness_routes": int(len(rejected)),
                "n_rejected_routes_all_four_mean_deltas_negative": int(
                    rejected["all_four_mean_deltas_negative"].astype(bool).sum()
                ),
                "all_rejected_routes_rank_direction_negative": bool(
                    len(rejected)
                    and (
                        rejected["prediction_delta_negative"].astype(bool)
                        & rejected["ecological_rank_delta_negative"].astype(bool)
                    ).all()
                ),
                "any_rejected_route_rank_direction_negative": bool(
                    len(rejected)
                    and (
                        rejected["prediction_delta_negative"].astype(bool)
                        & rejected["ecological_rank_delta_negative"].astype(bool)
                    ).any()
                ),
            }
        )

    routes = pd.concat(route_rows, ignore_index=True)
    cells = pd.DataFrame(cell_rows).sort_values(["family", "seed", "process"], kind="mergesort")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    routes.sort_values(["family", "seed", "process", "model_label", "route"], kind="mergesort").to_csv(
        out / "changed_cell_route_deltas.csv", index=False
    )
    cells.to_csv(out / "changed_cell_concordance_summary.csv", index=False)

    true = cells.loc[cells["expected_true_process"].astype(bool)]
    false = cells.loc[~cells["expected_true_process"].astype(bool)]
    decision = {
        "purpose": "density_ratio_v4_changed_cell_concordance_diagnostic",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_changed_cells": int(len(cells)),
        "n_true_changed_cells": int(len(true)),
        "n_false_changed_cells": int(len(false)),
        "true_cells_all_rejected_routes_rank_direction_negative": int(
            true["all_rejected_routes_rank_direction_negative"].astype(bool).sum()
        ),
        "false_cells_all_rejected_routes_rank_direction_negative": int(
            false["all_rejected_routes_rank_direction_negative"].astype(bool).sum()
        ),
        "true_cells_any_rejected_route_rank_direction_negative": int(
            true["any_rejected_route_rank_direction_negative"].astype(bool).sum()
        ),
        "false_cells_any_rejected_route_rank_direction_negative": int(
            false["any_rejected_route_rank_direction_negative"].astype(bool).sum()
        ),
        "no_margin_retuning": True,
        "no_status_reclassification": True,
        "product_a_reopened": False,
    }
    (out / "concordance_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(decision, indent=2, sort_keys=True))
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-file", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run(args.process_file, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
