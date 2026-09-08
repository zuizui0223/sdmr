#!/usr/bin/env python3
"""Development-only v6 diagnosis on already consumed real positive controls.

The script computes temperature and water challenges for *every* taxon before it
reads any external expected-process label.  Each challenge uses two matched
routes with the same frozen logistic ModelSpec.  The baseline carries the process;
the paired counterfactual removes the declared process variables and residualizes
all retained ecological predictors against those variables using model-background
environments only.

The outer-sealed rows already frozen in the consumed artifacts are then used once
to measure raw Schoener-D recovery loss.  These eight taxa are development data
and can never become fresh validation for the successor.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.metrics import presence_rank_score
from sdmr.model import (
    ModelSpec,
    fit_relative_suitability_model,
    score_relative_suitability,
)
from sdmr.niche_recovery_cv import heldout_niche_recovery_profile
from sdmr.pilot import MODEL_ROLE, OUTER_ROLE_COL, SEALED_ROLE
from sdmr.process_information_purge import fit_process_information_purge


M_SPECS = ("buffer_150km", "buffer_300km", "buffer_500km")
PROCESSES = ("temperature", "water")
MODEL_SPEC = ModelSpec(C=0.1, degree=1, penalty="l2", random_state=0)

LANE_GROUPS = {
    "plant": {
        "temperature": ("bio1", "bio10", "bio11", "gst"),
        "water": ("bio12", "bio14", "bio17", "gsp"),
        "neutral": ("rsds", "sfcWind"),
    },
    "nonplant": {
        "temperature": ("bio1", "bio5", "bio6", "bio7"),
        "water": ("bio12", "bio13", "bio14", "bio17"),
        "neutral": ("rsds", "sfcWind"),
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--plant-root", type=Path, required=True)
    p.add_argument("--nonplant-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--purge-degree", type=int, default=2)
    p.add_argument("--purge-ridge-alpha", type=float, default=1.0)
    return p.parse_args()


def _required_paths(root: Path) -> None:
    required = [root / "feature_cache" / "pilot_occurrences.csv", root / "result" / "real_positive_control_taxon_results.csv"]
    required.extend(root / "feature_cache" / "specifications" / m / "background.csv" for m in M_SPECS)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("consumed positive-control artifact is incomplete: " + "; ".join(missing))


def _score(model, frame: pd.DataFrame, predictors: tuple[str, ...]) -> np.ndarray:
    return score_relative_suitability(model, frame, predictors)


def _complete_count(frame: pd.DataFrame, predictors: tuple[str, ...]) -> int:
    values = frame[list(predictors)].apply(pd.to_numeric, errors="coerce")
    return int(values.notna().all(axis=1).sum())


def _matched_route_definitions(process: str, groups: dict[str, tuple[str, ...]]):
    temperature = groups["temperature"]
    water = groups["water"]
    neutral = groups["neutral"]
    if process == "temperature":
        return (
            ("temperature_only", temperature + neutral, neutral),
            ("temperature_water", temperature + water + neutral, water + neutral),
        )
    if process == "water":
        return (
            ("water_only", water + neutral, neutral),
            ("temperature_water", temperature + water + neutral, temperature + neutral),
        )
    raise KeyError(process)


def _outer_d(
    *,
    fit_background: pd.DataFrame,
    sealed_background: pd.DataFrame,
    sealed_presence: pd.DataFrame,
    suitability: np.ndarray,
    audit_predictors: tuple[str, ...],
) -> float:
    profile = heldout_niche_recovery_profile(
        fit_background,
        sealed_background,
        sealed_presence,
        suitability,
        audit_predictors,
    )
    return float(profile.niche_overlap_schoener_d_pc12)


def _one_lane(
    root: Path,
    lane: str,
    *,
    purge_degree: int,
    purge_ridge_alpha: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    _required_paths(root)
    groups = LANE_GROUPS[lane]
    audit_predictors = groups["temperature"] + groups["water"] + groups["neutral"]
    occurrence = pd.read_csv(root / "feature_cache" / "pilot_occurrences.csv", low_memory=False)
    species_names = tuple(sorted(occurrence["species"].dropna().astype(str).unique()))
    route_rows: list[dict[str, object]] = []

    # IMPORTANT: expected_process labels are not read anywhere in this loop.
    for m_spec in M_SPECS:
        background = pd.read_csv(
            root / "feature_cache" / "specifications" / m_spec / "background.csv",
            low_memory=False,
        )
        for species in species_names:
            p = occurrence.loc[occurrence["species"].astype(str).eq(species)].copy()
            b = background.loc[background["species"].astype(str).eq(species)].copy()
            p_model = p.loc[p[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)].reset_index(drop=True)
            p_sealed = p.loc[p[OUTER_ROLE_COL].astype(str).eq(SEALED_ROLE)].reset_index(drop=True)
            b_model = b.loc[b[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)].reset_index(drop=True)
            b_sealed = b.loc[b[OUTER_ROLE_COL].astype(str).eq(SEALED_ROLE)].reset_index(drop=True)
            sealed_complete = _complete_count(p_sealed, audit_predictors)

            for process in PROCESSES:
                process_predictors = groups[process]
                for carrier, baseline_predictors, retained_predictors in _matched_route_definitions(process, groups):
                    row: dict[str, object] = {
                        "lane": lane,
                        "species": species,
                        "m_spec": m_spec,
                        "process": process,
                        "carrier": carrier,
                        "baseline_predictors": ",".join(baseline_predictors),
                        "process_predictors": ",".join(process_predictors),
                        "retained_predictors": ",".join(retained_predictors),
                        "n_model_presence": int(len(p_model)),
                        "n_sealed_presence": int(len(p_sealed)),
                        "n_complete_sealed_occurrences": sealed_complete,
                        "complete": False,
                        "status": "unavailable",
                        "baseline_outer_presence_rank": np.nan,
                        "purged_outer_presence_rank": np.nan,
                        "outer_presence_rank_delta": np.nan,
                        "baseline_outer_schoener_d": np.nan,
                        "purged_outer_schoener_d": np.nan,
                        "outer_schoener_d_loss": np.nan,
                    }
                    try:
                        if sealed_complete < 2:
                            raise ValueError("fewer than two complete outer-sealed occurrences")
                        if min(len(p_model), len(b_model), len(p_sealed), len(b_sealed)) < 2:
                            raise ValueError("outer/model role lacks sufficient rows")

                        baseline = fit_relative_suitability_model(
                            p_model,
                            b_model,
                            baseline_predictors,
                            model_spec=MODEL_SPEC,
                        )
                        baseline_p = _score(baseline, p_sealed, baseline_predictors)
                        baseline_b = _score(baseline, b_sealed, baseline_predictors)
                        baseline_rank = presence_rank_score(baseline_p, baseline_b)
                        baseline_d = _outer_d(
                            fit_background=b_model,
                            sealed_background=b_sealed,
                            sealed_presence=p_sealed,
                            suitability=baseline_b,
                            audit_predictors=audit_predictors,
                        )

                        purge = fit_process_information_purge(
                            b_model,
                            process=process,
                            process_predictors=process_predictors,
                            retained_predictors=retained_predictors,
                            degree=int(purge_degree),
                            ridge_alpha=float(purge_ridge_alpha),
                            minimum_complete_rows=10,
                        )
                        p_model_purged = purge.transform(p_model)
                        b_model_purged = purge.transform(b_model)
                        p_sealed_purged = purge.transform(p_sealed)
                        b_sealed_purged = purge.transform(b_sealed)
                        purged = fit_relative_suitability_model(
                            p_model_purged,
                            b_model_purged,
                            retained_predictors,
                            model_spec=MODEL_SPEC,
                        )
                        purged_p = _score(purged, p_sealed_purged, retained_predictors)
                        purged_b = _score(purged, b_sealed_purged, retained_predictors)
                        purged_rank = presence_rank_score(purged_p, purged_b)
                        # Keep the audit environmental space on the original
                        # frozen variables; only the suitability weights come
                        # from the information-purged model.
                        purged_d = _outer_d(
                            fit_background=b_model,
                            sealed_background=b_sealed,
                            sealed_presence=p_sealed,
                            suitability=purged_b,
                            audit_predictors=audit_predictors,
                        )
                        values = (baseline_rank, purged_rank, baseline_d, purged_d)
                        if not all(np.isfinite(float(x)) for x in values):
                            raise ValueError("outer matched route produced non-finite evidence")
                        row.update(
                            {
                                "complete": True,
                                "status": "compared",
                                "baseline_outer_presence_rank": float(baseline_rank),
                                "purged_outer_presence_rank": float(purged_rank),
                                "outer_presence_rank_delta": float(purged_rank - baseline_rank),
                                "baseline_outer_schoener_d": float(baseline_d),
                                "purged_outer_schoener_d": float(purged_d),
                                "outer_schoener_d_loss": float(baseline_d - purged_d),
                            }
                        )
                    except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                        row["status"] = str(exc)
                    route_rows.append(row)

    routes = pd.DataFrame(route_rows)
    score_rows: list[dict[str, object]] = []
    for (species, process, m_spec), frame in routes.groupby(["species", "process", "m_spec"], sort=True):
        complete = bool(len(frame) == 2 and frame["complete"].astype(bool).all())
        loss = pd.to_numeric(frame["outer_schoener_d_loss"], errors="coerce")
        rank_delta = pd.to_numeric(frame["outer_presence_rank_delta"], errors="coerce")
        score_rows.append(
            {
                "lane": lane,
                "species": species,
                "process": process,
                "m_spec": m_spec,
                "matched_routes_complete": complete,
                "mean_outer_schoener_d_loss": float(loss.mean()) if complete else np.nan,
                "mean_outer_presence_rank_delta": float(rank_delta.mean()) if complete else np.nan,
                "n_positive_loss_routes": int((loss > 0).sum()) if complete else 0,
                "n_complete_sealed_occurrences": int(frame["n_complete_sealed_occurrences"].min()),
            }
        )
    return routes, pd.DataFrame(score_rows)


def main() -> None:
    args = parse_args()
    for root in (args.plant_root, args.nonplant_root):
        _required_paths(root)

    route_frames: list[pd.DataFrame] = []
    m_frames: list[pd.DataFrame] = []
    for lane, root in (("plant", args.plant_root), ("nonplant", args.nonplant_root)):
        routes, m_scores = _one_lane(
            root,
            lane,
            purge_degree=int(args.purge_degree),
            purge_ridge_alpha=float(args.purge_ridge_alpha),
        )
        route_frames.append(routes)
        m_frames.append(m_scores)

    routes = pd.concat(route_frames, ignore_index=True)
    m_scores = pd.concat(m_frames, ignore_index=True)

    # Aggregate truth-blind T/W scores first.
    aggregate_rows: list[dict[str, object]] = []
    for (lane, species, process), frame in m_scores.groupby(["lane", "species", "process"], sort=True):
        values = pd.to_numeric(frame["mean_outer_schoener_d_loss"], errors="coerce")
        complete = bool(len(frame) == len(M_SPECS) and np.isfinite(values).all())
        aggregate_rows.append(
            {
                "lane": lane,
                "species": species,
                "process": process,
                "m_complete": complete,
                "mean_outer_schoener_d_loss": float(values.mean()) if complete else np.nan,
                "positive_m_count": int((values > 0).sum()) if complete else 0,
                "minimum_complete_sealed_occurrences": int(frame["n_complete_sealed_occurrences"].min()),
            }
        )
    process_scores = pd.DataFrame(aggregate_rows)

    # Only now open the already-consumed external positive labels for diagnostic
    # scoring. They are never passed to a purge or SDM fit.
    label_frames = []
    for lane, root in (("plant", args.plant_root), ("nonplant", args.nonplant_root)):
        labels = pd.read_csv(root / "result" / "real_positive_control_taxon_results.csv")
        labels = labels[["species", "expected_process"]].copy()
        labels["lane"] = lane
        label_frames.append(labels)
    labels = pd.concat(label_frames, ignore_index=True)

    expected = labels.merge(
        process_scores,
        left_on=["lane", "species", "expected_process"],
        right_on=["lane", "species", "process"],
        how="left",
        validate="one_to_one",
    )
    expected["descriptive_directional_recovery"] = (
        expected["m_complete"].fillna(False).astype(bool)
        & (pd.to_numeric(expected["mean_outer_schoener_d_loss"], errors="coerce") > 0)
        & (pd.to_numeric(expected["positive_m_count"], errors="coerce") >= 2)
    )
    expected["future_outer_coverage_floor_10_met"] = (
        pd.to_numeric(expected["minimum_complete_sealed_occurrences"], errors="coerce") >= 10
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    routes.to_csv(args.output_dir / "proxy_closed_outer_route_evidence.csv", index=False)
    m_scores.to_csv(args.output_dir / "proxy_closed_outer_process_m_scores.csv", index=False)
    process_scores.to_csv(args.output_dir / "proxy_closed_outer_process_scores.csv", index=False)
    expected.to_csv(args.output_dir / "proxy_closed_expected_process_development_readout.csv", index=False)

    decision = {
        "purpose": "proxy_closed_positive_control_v6_consumed_development_diagnostic",
        "development_only": True,
        "eligible_for_empirical_validation_claim": False,
        "consumed_controls_n": int(len(expected)),
        "truth_blind_process_scores_completed_before_labels_opened": True,
        "purge_fit_uses_background_environment_only": True,
        "matched_route_model_spec": MODEL_SPEC.label,
        "purge_degree": int(args.purge_degree),
        "purge_ridge_alpha": float(args.purge_ridge_alpha),
        "descriptive_directional_recovery_n": int(expected["descriptive_directional_recovery"].sum()),
        "unavailable_expected_process_n": int((~expected["m_complete"].fillna(False).astype(bool)).sum()),
        "future_outer_coverage_floor_10_met_n": int(expected["future_outer_coverage_floor_10_met"].sum()),
        "fresh_validation_required": True,
        "current_eight_labels_must_not_be_reused_as_fresh_validation": True,
    }
    (args.output_dir / "development_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(decision, indent=2, sort_keys=True))
    print(expected.to_string(index=False))


if __name__ == "__main__":
    main()
