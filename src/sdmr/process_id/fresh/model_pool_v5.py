"""Model-pool-only process and comparator freeze for fresh empirical v5.

This module is deliberately downstream of a terminally passing v5 numeric
feature gate and upstream of every sealed answer-check operation.

It uses only:
- frozen final50 identities;
- model-pool occurrences;
- frozen 300-km background rows with background_rank % 5 != 0;
- frozen complete-case environmental features;
- the frozen 46-predictor / six-process registry.

It freezes process states, stable states, SDMR retained predictors, flat
comparator predictor sets, and final model specifications.  It never reads
answer-check occurrence coordinates/features or evaluates EMP outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from sdmr.process_id.evidence import (
    _balanced_log_score,
    _hgb_balanced_sample_weight,
    evaluate_occurrence_processes,
)
from sdmr.process_id.hgb_profiles import get_hgb_profile
from sdmr.process_id.known_truth.integration_v5 import apply_permutation_authorization
from sdmr.process_id.known_truth.permutation_gate import evaluate_full_system_permutation_gate
from sdmr.process_id.known_truth.worlds import KnownTruthWorld
from sdmr.process_id.taxonomy import DEFAULT_PLANT_PROCESSES
from sdmr.process_information_closure import normalize_process_information_registry
from sdmr.validation import lonlat_to_unit_xyz


PROGRAM = "sdmr-fresh-empirical-v5-model-pool-freeze"
EXPECTED_TAXA = 50
EXPECTED_PREDICTORS = 46
EXPECTED_PROCESSES = 6
BACKGROUND_TRAIN_MODULUS = 5
BACKGROUND_TRAIN_REMAINDERS = (1, 2, 3, 4)
BACKGROUND_EVAL_REMAINDER = 0
INNER_SPLITS = 3
PROCESS_MARGIN = 0.01
ADEQUACY_FLOOR = -0.75
SEM_MULTIPLIER = 1.0
PERMUTATIONS = 999
PERMUTATION_ALPHA = 0.001
PERMUTATION_SEED = 0
MIN_GAIN_OVER_NULL = 0.01
MAX_FORWARD_PREDICTORS = 8
VIF_THRESHOLD = 5.0
SHARP_STATES = ("replaceable", "contributory", "required")


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_model_design(path: str | Path) -> dict:
    c = json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("schema") != "sdmr.fresh_empirical_v5_model_design.v1":
        raise ValueError("wrong v5 model-design schema")
    if c.get("status") != "model_design_frozen_before_final50_numeric_features_and_model_fit":
        raise ValueError("v5 model design status changed")
    if int(c["cohort_binding"]["exact_taxa"]) != EXPECTED_TAXA:
        raise ValueError("v5 model taxon denominator changed")
    if int(c["predictor_and_process_universe"]["predictor_count"]) != EXPECTED_PREDICTORS:
        raise ValueError("v5 model predictor denominator changed")
    if int(c["predictor_and_process_universe"]["process_count"]) != EXPECTED_PROCESSES:
        raise ValueError("v5 model process denominator changed")

    stage = c["process_identification"]["stage_p"]
    expected = {
        "n_inner_splits": INNER_SPLITS,
        "score": "balanced_presence_background_log_score",
        "margin": PROCESS_MARGIN,
        "adequacy_floor": ADEQUACY_FLOOR,
        "sem_multiplier": SEM_MULTIPLIER,
        "split_mode": "spatial",
    }
    for key, value in expected.items():
        if stage.get(key) != value:
            raise ValueError(f"v5 model Stage-P rule changed: {key}")
    auth = stage["full_system_authorization"]
    if int(auth["n_permutations"]) != PERMUTATIONS:
        raise ValueError("v5 model permutation denominator changed")
    if float(auth["alpha"]) != PERMUTATION_ALPHA:
        raise ValueError("v5 model permutation alpha changed")
    if int(auth["permutation_seed"]) != PERMUTATION_SEED:
        raise ValueError("v5 model permutation seed changed")
    if float(auth["minimum_gain_over_null"]) != MIN_GAIN_OVER_NULL:
        raise ValueError("v5 model minimum full-system gain changed")

    bg = c["model_pool_background_split"]
    if bg["training_rule"] != "background_rank modulo 5 != 0":
        raise ValueError("v5 background training split changed")
    if bg["sealed_evaluation_rule"] != "background_rank modulo 5 == 0":
        raise ValueError("v5 background evaluation split changed")
    if int(bg["training_rows_per_taxon"]) != 4000 or int(bg["evaluation_rows_per_taxon"]) != 1000:
        raise ValueError("v5 background train/evaluation denominator changed")

    flat = c["flat_comparators"]
    if int(flat["matched_learner_flat_predictive_selector"]["maximum_predictors"]) != MAX_FORWARD_PREDICTORS:
        raise ValueError("v5 matched comparator max predictor count changed")
    if int(flat["auc_oriented_flat_selector"]["maximum_predictors"]) != MAX_FORWARD_PREDICTORS:
        raise ValueError("v5 AUC comparator max predictor count changed")
    if float(flat["correlation_vif_flat_filter"]["vif_threshold"]) != VIF_THRESHOLD:
        raise ValueError("v5 VIF threshold changed")
    return c


def _load_feature_bundle(
    *,
    feature_root: str | Path,
    selected_path: str | Path,
    process_registry_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, tuple[str, ...], pd.DataFrame]:
    root = Path(feature_root)
    result = json.loads((root / "feature_gate_result_v5.json").read_text(encoding="utf-8"))
    if result.get("program") != "sdmr-fresh-empirical-v5-feature-gate":
        raise ValueError("wrong v5 feature artifact")
    if result.get("status") != "v5_feature_gate_passed":
        raise ValueError("v5 model fitting requires terminally passing feature gate")
    if result.get("all_taxa_complete_case_gate_passed") is not True:
        raise ValueError("v5 model fitting requires all 50 feature gates to pass")
    if result.get("answer_check_accessed") is not False or result.get("model_fitting_performed") is not False:
        raise ValueError("v5 feature artifact crossed answer-check/model boundary")

    selected = pd.read_csv(selected_path)
    required_selected = {"selection_rank", "scientific_name"}
    if required_selected - set(selected.columns):
        raise ValueError("v5 final50 manifest columns changed")
    if len(selected) != EXPECTED_TAXA or selected["scientific_name"].astype(str).nunique() != EXPECTED_TAXA:
        raise ValueError("v5 model fitting requires exact final50")
    ranks = sorted(pd.to_numeric(selected["selection_rank"], errors="raise").astype(int))
    if ranks != list(range(1, EXPECTED_TAXA + 1)):
        raise ValueError("v5 final50 selection ranks changed")

    registry = pd.read_csv(process_registry_path)
    registry = normalize_process_information_registry(
        registry[["predictor", "process", "role"]],
        process_universe=DEFAULT_PLANT_PROCESSES,
    )
    predictors = tuple(dict.fromkeys(registry["predictor"].astype(str)))
    if len(predictors) != EXPECTED_PREDICTORS:
        raise ValueError("v5 process registry predictor denominator changed")

    locations = pd.read_parquet(root / "location_features_v5.parquet")
    model_index = pd.read_csv(root / "model_pool_feature_index_v5.csv")
    background_index = pd.read_csv(root / "background_300km_feature_index_v5.csv")
    gate = pd.read_csv(root / "complete_case_gate_v5.csv")
    if len(gate) != EXPECTED_TAXA or not gate["complete_case_gate_passed"].astype(bool).all():
        raise ValueError("v5 feature gate table is not exact 50/50 PASS")
    return selected, locations, model_index, background_index, predictors, registry


def _nearest_occurrence_blocks(
    occurrence: pd.DataFrame,
    background: pd.DataFrame,
) -> np.ndarray:
    """Assign each background row to nearest occurrence's frozen spatial block.

    Occurrences are sorted by occurrence_id before tree construction.  Exact
    distance ties are then resolved lexicographically by occurrence_id.
    """
    required_o = {"occurrence_id", "longitude", "latitude", "spatial_block"}
    required_b = {"longitude", "latitude"}
    if required_o - set(occurrence.columns):
        raise ValueError("occurrence table lacks frozen spatial-block columns")
    if required_b - set(background.columns):
        raise ValueError("background table lacks coordinates")
    occ = occurrence.copy()
    occ["occurrence_id"] = occ["occurrence_id"].astype(str)
    occ = occ.sort_values("occurrence_id", kind="mergesort").reset_index(drop=True)
    if occ.empty or background.empty:
        raise ValueError("nearest block assignment requires non-empty inputs")

    occ_xyz = lonlat_to_unit_xyz(
        pd.to_numeric(occ["longitude"], errors="raise").to_numpy(float),
        pd.to_numeric(occ["latitude"], errors="raise").to_numpy(float),
    )
    bg_xyz = lonlat_to_unit_xyz(
        pd.to_numeric(background["longitude"], errors="raise").to_numpy(float),
        pd.to_numeric(background["latitude"], errors="raise").to_numpy(float),
    )
    tree = cKDTree(occ_xyz)
    distance, nearest = tree.query(bg_xyz, k=1)
    out = np.empty(len(background), dtype=int)

    # Resolve rare exact/near-exact nearest-neighbour ties deterministically.
    for i, (point, dist, idx) in enumerate(zip(bg_xyz, distance, nearest, strict=True)):
        candidate_idx = tree.query_ball_point(point, r=float(dist) + 1e-12)
        if len(candidate_idx) <= 1:
            chosen = int(idx)
        else:
            candidate_idx = np.asarray(candidate_idx, dtype=int)
            delta = occ_xyz[candidate_idx] - point
            d2 = np.einsum("ij,ij->i", delta, delta)
            best = float(np.min(d2))
            tied = candidate_idx[np.isclose(d2, best, rtol=0.0, atol=1e-15)]
            chosen = int(np.min(tied))  # lexical occurrence order
        out[i] = int(pd.to_numeric(occ.loc[chosen, "spatial_block"], errors="raise"))
    return out


def _taxon_training_tables(
    *,
    taxon: str,
    locations: pd.DataFrame,
    model_index: pd.DataFrame,
    background_index: pd.DataFrame,
    predictors: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    taxon = str(taxon)
    all_model = model_index.loc[model_index["scientific_name"].astype(str).eq(taxon)].copy()
    all_bg = background_index.loc[background_index["scientific_name"].astype(str).eq(taxon)].copy()
    if all_model.empty or all_bg.empty:
        raise ValueError(f"missing v5 feature rows for {taxon}")

    if "complete_case" not in all_model or "complete_case" not in all_bg:
        raise ValueError("v5 model input requires complete_case flags")
    # Frozen background grouping is defined against every model-pool occurrence,
    # before complete-case filtering.  Missing environmental values must not
    # change the spatial CV groups.
    all_bg["spatial_block"] = _nearest_occurrence_blocks(all_model, all_bg)
    model = all_model.loc[all_model["complete_case"].astype(bool)].copy()
    bg = all_bg.loc[
        all_bg["complete_case"].astype(bool)
        & pd.to_numeric(all_bg["background_rank"], errors="raise").astype(int).mod(BACKGROUND_TRAIN_MODULUS).ne(BACKGROUND_EVAL_REMAINDER)
    ].copy()
    if len(model) < 50:
        raise ValueError(f"insufficient complete model-pool occurrences for {taxon}")
    if len(bg) < 50:
        raise ValueError(f"insufficient complete training background for {taxon}")

    feature_cols = ["location_id", *predictors]
    env = locations.loc[:, feature_cols].copy()
    model = model.merge(env, on="location_id", how="left", validate="many_to_one")
    bg = bg.merge(env, on="location_id", how="left", validate="many_to_one")
    if not np.isfinite(model.loc[:, predictors].to_numpy(float)).all():
        raise ValueError(f"non-finite model-pool feature survived complete-case gate: {taxon}")
    if not np.isfinite(bg.loc[:, predictors].to_numpy(float)).all():
        raise ValueError(f"non-finite training background survived complete-case gate: {taxon}")
    return model, bg


def _empirical_world(
    *,
    taxon: str,
    model: pd.DataFrame,
    background: pd.DataFrame,
    predictors: Sequence[str],
    registry: pd.DataFrame,
) -> KnownTruthWorld:
    bg = background.copy()
    if "spatial_block" not in bg:
        bg["spatial_block"] = _nearest_occurrence_blocks(model, bg)

    occurrence_rows = model.copy().reset_index(drop=True)
    background_rows = bg.copy().reset_index(drop=True)
    n_occ = len(occurrence_rows)
    n_bg = len(background_rows)
    occurrence_rows["cell_id"] = np.arange(n_occ, dtype=int)
    background_rows["cell_id"] = np.arange(n_occ, n_occ + n_bg, dtype=int)
    environment = pd.concat(
        [occurrence_rows, background_rows],
        ignore_index=True,
        sort=False,
    )[["cell_id", "longitude", "latitude", *predictors]].copy()
    spatial_groups = np.concatenate([
        pd.to_numeric(occurrence_rows["spatial_block"], errors="raise").to_numpy(int),
        pd.to_numeric(background_rows["spatial_block"], errors="raise").to_numpy(int),
    ])
    return KnownTruthWorld(
        name=f"empirical::{taxon}",
        environment=environment,
        true_suitability=np.full(len(environment), np.nan, dtype=float),
        occurrences=occurrence_rows[["cell_id", "longitude", "latitude", *predictors]].copy(),
        background=background_rows[["cell_id", "longitude", "latitude", *predictors]].copy(),
        process_registry=registry.copy(),
        predictor_universe=tuple(predictors),
        process_universe=tuple(DEFAULT_PLANT_PROCESSES),
        spatial_groups=spatial_groups,
        generating_processes=(),
        observation_unresolved_processes=(),
        model_pool_mask=np.ones(len(environment), dtype=bool),
    )


def _learner_process_states(world: KnownTruthWorld, *, learner: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if learner == "penalized_logistic":
        evidence_learner = "linear"
        hgb_profile = "current"
    elif learner == "shallow3_hgb":
        evidence_learner = "hgb"
        hgb_profile = "shallow3"
    else:
        raise ValueError("unknown frozen v5 learner route")

    try:
        authorization = evaluate_full_system_permutation_gate(
            world,
            n_splits=INNER_SPLITS,
            split_mode="spatial",
            learner=evidence_learner,
            hgb_profile=hgb_profile,
            C=1.0,
            adequacy_floor=ADEQUACY_FLOOR,
            n_permutations=PERMUTATIONS,
            alpha=PERMUTATION_ALPHA,
            permutation_seed=PERMUTATION_SEED,
            minimum_gain_over_null=MIN_GAIN_OVER_NULL,
        )
        evaluation = evaluate_occurrence_processes(
            world,
            n_splits=INNER_SPLITS,
            margin=PROCESS_MARGIN,
            adequacy_floor=ADEQUACY_FLOOR,
            sem_multiplier=SEM_MULTIPLIER,
            C=1.0,
            learner=evidence_learner,
            split_mode="spatial",
            hgb_profile=hgb_profile,
            require_full_system_information=False,
        )
    except ValueError as exc:
        # Expected finite-data failures (for example insufficient surviving
        # spatial groups) are scientific unavailability, not permission to
        # delete the taxon from the declared denominator.
        states = pd.DataFrame([
            {
                "learner_route": learner,
                "process": process,
                "state": "unavailable",
                "reason": f"finite_route_unavailable:{type(exc).__name__}",
                "closure_predictors": "",
                "complete": False,
                "full_system_information_adequate": False,
            }
            for process in DEFAULT_PLANT_PROCESSES
        ])
        evidence = pd.DataFrame(columns=[
            "learner_route","process","fold","route","split_mode","hgb_profile",
            "complete","full_log_score","knockout_log_score","delta",
            "excluded_predictors","retained_predictors",
        ])
        auth = {
            "authorized": False,
            "reason": f"finite_route_unavailable:{type(exc).__name__}",
            "observed_mean_score": float("nan"),
            "mean_gain_over_null": float("nan"),
            "p_value": float("nan"),
            "n_permutations": PERMUTATIONS,
            "permutation_seed": PERMUTATION_SEED,
        }
        return states, evidence, auth

    states = apply_permutation_authorization(
        evaluation.states,
        authorized=bool(authorization.summary["authorized"]),
        observed_mean_score=float(authorization.summary["observed_mean_score"]),
        mean_gain_over_null=float(authorization.summary["mean_gain_over_null"]),
        p_value=float(authorization.summary["p_value"]),
    )
    states.insert(0, "learner_route", learner)
    evidence = evaluation.evidence.copy()
    evidence.insert(0, "learner_route", learner)
    return states, evidence, dict(authorization.summary)


def stable_process_states(route_states: pd.DataFrame) -> pd.DataFrame:
    required = {"learner_route", "process", "state"}
    if required - set(route_states.columns):
        raise ValueError("route state table missing columns")
    routes = set(route_states["learner_route"].astype(str))
    if routes != {"penalized_logistic", "shallow3_hgb"}:
        raise ValueError("stable-state table requires both frozen learner routes")
    rows = []
    for process in DEFAULT_PLANT_PROCESSES:
        g = route_states.loc[route_states["process"].astype(str).eq(process)]
        if len(g) != 2:
            raise ValueError(f"process route denominator changed: {process}")
        state_map = dict(zip(g["learner_route"].astype(str), g["state"].astype(str), strict=True))
        a = state_map["penalized_logistic"]
        b = state_map["shallow3_hgb"]
        if "unavailable" in {a, b}:
            stable = "unavailable"
        elif a == b and a in SHARP_STATES:
            stable = a
        else:
            stable = "unresolved"
        rows.append({
            "process": process,
            "logistic_state": a,
            "hgb_state": b,
            "stable_state": stable,
            "stable_sharp": bool(stable in SHARP_STATES),
        })
    return pd.DataFrame(rows)


def sdmr_retained_predictors(
    *,
    registry: pd.DataFrame,
    stable_states: pd.DataFrame,
    predictors: Sequence[str],
) -> tuple[str, ...]:
    state = dict(zip(stable_states["process"].astype(str), stable_states["stable_state"].astype(str), strict=True))
    retained = []
    for predictor in predictors:
        mapped = tuple(
            dict.fromkeys(
                registry.loc[registry["predictor"].astype(str).eq(str(predictor)), "process"].astype(str)
            )
        )
        if not mapped:
            raise ValueError(f"predictor lacks process mapping: {predictor}")
        if all(state[p] == "replaceable" for p in mapped):
            continue
        retained.append(str(predictor))
    return tuple(retained)


def _fit_hgb_probability(train: pd.DataFrame, test: pd.DataFrame, predictors: Sequence[str]) -> np.ndarray:
    if not predictors:
        return np.full(len(test), np.nan, dtype=float)
    x_train = train.loc[:, list(predictors)].to_numpy(float)
    x_test = test.loc[:, list(predictors)].to_numpy(float)
    y_train = train["label"].to_numpy(int)
    if len(np.unique(y_train)) != 2:
        return np.full(len(test), np.nan, dtype=float)
    model = HistGradientBoostingClassifier(
        loss="log_loss",
        random_state=0,
        **get_hgb_profile("shallow3"),
    )
    model.fit(x_train, y_train, sample_weight=_hgb_balanced_sample_weight(y_train))
    return np.asarray(model.predict_proba(x_test)[:, 1], dtype=float)


def _inner_sample_and_groups(model: pd.DataFrame, background: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    occ = model.copy()
    bg = background.copy()
    if "spatial_block" not in bg:
        bg["spatial_block"] = _nearest_occurrence_blocks(occ, bg)
    occ["label"] = 1
    bg["label"] = 0
    sample = pd.concat([occ, bg], ignore_index=True, sort=False)
    groups = pd.concat(
        [
            pd.to_numeric(occ["spatial_block"], errors="raise"),
            pd.to_numeric(bg["spatial_block"], errors="raise"),
        ],
        ignore_index=True,
    ).to_numpy(int)
    if len(np.unique(groups)) < INNER_SPLITS:
        raise ValueError("insufficient spatial groups for v5 selector")
    return sample, groups


def _mean_cv_metric(
    sample: pd.DataFrame,
    groups: np.ndarray,
    predictors: Sequence[str],
    *,
    metric: str,
) -> float:
    splitter = GroupKFold(n_splits=INNER_SPLITS)
    values = []
    for train_idx, test_idx in splitter.split(np.arange(len(sample)), sample["label"], groups):
        train = sample.iloc[train_idx].reset_index(drop=True)
        test = sample.iloc[test_idx].reset_index(drop=True)
        p = _fit_hgb_probability(train, test, predictors)
        if not np.isfinite(p).all():
            return float("-inf")
        if metric == "balanced_log_score":
            score = _balanced_log_score(test["label"].to_numpy(int), p)
        elif metric == "roc_auc":
            if test["label"].nunique() != 2:
                return float("-inf")
            score = float(roc_auc_score(test["label"].to_numpy(int), p))
        else:
            raise ValueError("unknown selector metric")
        if not math.isfinite(score):
            return float("-inf")
        values.append(float(score))
    return float(np.mean(values))


def sequential_forward_selection(
    *,
    model: pd.DataFrame,
    background: pd.DataFrame,
    predictors: Sequence[str],
    metric: str,
    max_predictors: int = MAX_FORWARD_PREDICTORS,
) -> dict:
    predictors = tuple(sorted(str(p) for p in predictors))
    sample, groups = _inner_sample_and_groups(model, background)
    chosen: list[str] = []
    prefixes: list[dict[str, object]] = []

    for step in range(1, min(int(max_predictors), len(predictors)) + 1):
        rows = []
        for candidate in predictors:
            if candidate in chosen:
                continue
            seq = tuple(chosen + [candidate])
            score = _mean_cv_metric(sample, groups, seq, metric=metric)
            rows.append((float(score), candidate, seq))
        if not rows:
            break
        # maximum score; lexical candidate tie-break.
        best_score = max(x[0] for x in rows)
        best_candidates = [x for x in rows if np.isclose(x[0], best_score, rtol=0.0, atol=1e-12)]
        best = sorted(best_candidates, key=lambda x: x[1])[0]
        chosen.append(best[1])
        prefixes.append({
            "n_predictors": step,
            "predictors": tuple(chosen),
            "mean_score": float(best[0]),
        })

    if not prefixes:
        raise RuntimeError("forward selection produced no evaluable prefix")
    best_score = max(float(x["mean_score"]) for x in prefixes)
    tied = [
        x for x in prefixes
        if np.isclose(float(x["mean_score"]), best_score, rtol=0.0, atol=1e-12)
    ]
    best_prefix = sorted(
        tied,
        key=lambda x: (int(x["n_predictors"]), tuple(x["predictors"])),
    )[0]
    return {
        "metric": metric,
        "selected_predictors": tuple(best_prefix["predictors"]),
        "selected_count": int(best_prefix["n_predictors"]),
        "selected_mean_score": float(best_prefix["mean_score"]),
        "prefixes": prefixes,
    }


def vif_prune(background: pd.DataFrame, predictors: Sequence[str], *, threshold: float = VIF_THRESHOLD) -> tuple[str, ...]:
    """Deterministic iterative VIF pruning on training-background rows only."""
    retained = list(sorted(str(p) for p in predictors))
    threshold = float(threshold)
    if not math.isfinite(threshold) or threshold <= 1.0:
        raise ValueError("VIF threshold must be finite and > 1")

    def current_vif(columns: list[str]) -> np.ndarray:
        x = background.loc[:, columns].to_numpy(float)
        if not np.isfinite(x).all():
            raise ValueError("VIF input must be complete finite training background")
        values = np.empty(len(columns), dtype=float)
        for i in range(len(columns)):
            y = x[:, i]
            others = np.delete(x, i, axis=1)
            y_centered = y - float(np.mean(y))
            sst = float(np.dot(y_centered, y_centered))
            if not math.isfinite(sst) or sst <= 1e-15:
                values[i] = float("inf")
                continue
            if others.shape[1] == 0:
                values[i] = 1.0
                continue
            design = np.column_stack([np.ones(len(others)), others])
            try:
                coef, *_ = np.linalg.lstsq(design, y, rcond=None)
                residual = y - design @ coef
                sse = float(np.dot(residual, residual))
                r2 = 1.0 - sse / sst
                if r2 >= 1.0 - 1e-12:
                    values[i] = float("inf")
                else:
                    values[i] = 1.0 / max(1.0 - r2, 1e-12)
            except np.linalg.LinAlgError:
                values[i] = float("inf")
        return values

    while len(retained) > 1:
        vif = current_vif(retained)
        max_vif = float(np.max(vif))
        if math.isfinite(max_vif) and max_vif <= threshold:
            break
        if math.isfinite(max_vif):
            candidates = [
                retained[i] for i, value in enumerate(vif)
                if np.isclose(float(value), max_vif, rtol=0.0, atol=1e-10)
            ]
        else:
            candidates = [retained[i] for i, value in enumerate(vif) if not math.isfinite(float(value))]
        retained.remove(sorted(candidates)[0])
    return tuple(retained)


@dataclass(frozen=True)
class TaxonModelFreeze:
    taxon: str
    route_states: pd.DataFrame
    stable_states: pd.DataFrame
    process_evidence: pd.DataFrame
    authorization: pd.DataFrame
    sdmr_predictors: tuple[str, ...]
    flat_balanced_predictors: tuple[str, ...]
    flat_auc_predictors: tuple[str, ...]
    vif_predictors: tuple[str, ...]
    selector_audit: pd.DataFrame


def freeze_taxon_model_pool(
    *,
    taxon: str,
    locations: pd.DataFrame,
    model_index: pd.DataFrame,
    background_index: pd.DataFrame,
    predictors: Sequence[str],
    registry: pd.DataFrame,
) -> TaxonModelFreeze:
    model, background = _taxon_training_tables(
        taxon=taxon,
        locations=locations,
        model_index=model_index,
        background_index=background_index,
        predictors=predictors,
    )
    world = _empirical_world(
        taxon=taxon,
        model=model,
        background=background,
        predictors=predictors,
        registry=registry,
    )

    route_states = []
    evidence = []
    auth_rows = []
    for route in ("penalized_logistic", "shallow3_hgb"):
        states, ev, auth = _learner_process_states(world, learner=route)
        route_states.append(states)
        evidence.append(ev)
        auth_rows.append({"learner_route": route, **auth})
    route_states_df = pd.concat(route_states, ignore_index=True)
    evidence_df = pd.concat(evidence, ignore_index=True)
    stable = stable_process_states(route_states_df)
    sdmr_predictors = sdmr_retained_predictors(
        registry=registry,
        stable_states=stable,
        predictors=predictors,
    )

    selector_errors = {}
    try:
        flat_balanced = sequential_forward_selection(
            model=model,
            background=background,
            predictors=predictors,
            metric="balanced_log_score",
        )
    except (ValueError, RuntimeError) as exc:
        flat_balanced = {
            "metric": "balanced_log_score",
            "selected_predictors": (),
            "selected_count": 0,
            "selected_mean_score": float("nan"),
            "prefixes": [],
        }
        selector_errors["matched_learner_flat_predictive_selector"] = type(exc).__name__
    try:
        flat_auc = sequential_forward_selection(
            model=model,
            background=background,
            predictors=predictors,
            metric="roc_auc",
        )
    except (ValueError, RuntimeError) as exc:
        flat_auc = {
            "metric": "roc_auc",
            "selected_predictors": (),
            "selected_count": 0,
            "selected_mean_score": float("nan"),
            "prefixes": [],
        }
        selector_errors["auc_oriented_flat_selector"] = type(exc).__name__
    try:
        vif = vif_prune(background, predictors, threshold=VIF_THRESHOLD)
    except (ValueError, RuntimeError) as exc:
        vif = ()
        selector_errors["correlation_vif_flat_filter"] = type(exc).__name__

    audit_rows = []
    for label, result in (
        ("matched_learner_flat_predictive_selector", flat_balanced),
        ("auc_oriented_flat_selector", flat_auc),
    ):
        for prefix in result["prefixes"]:
            audit_rows.append({
                "selector": label,
                "metric": result["metric"],
                "n_predictors": prefix["n_predictors"],
                "predictors": ",".join(prefix["predictors"]),
                "mean_score": prefix["mean_score"],
                "selected": tuple(prefix["predictors"]) == tuple(result["selected_predictors"]),
                "available": True,
                "failure_reason": "",
            })
        if not result["prefixes"]:
            audit_rows.append({
                "selector": label,
                "metric": result["metric"],
                "n_predictors": 0,
                "predictors": "",
                "mean_score": np.nan,
                "selected": False,
                "available": False,
                "failure_reason": selector_errors.get(label, "unavailable"),
            })
    audit_rows.append({
        "selector": "correlation_vif_flat_filter",
        "metric": "VIF",
        "n_predictors": len(vif),
        "predictors": ",".join(vif),
        "mean_score": np.nan,
        "selected": bool(vif),
        "available": bool(vif),
        "failure_reason": selector_errors.get("correlation_vif_flat_filter", ""),
    })
    return TaxonModelFreeze(
        taxon=str(taxon),
        route_states=route_states_df,
        stable_states=stable,
        process_evidence=evidence_df,
        authorization=pd.DataFrame(auth_rows),
        sdmr_predictors=tuple(sdmr_predictors),
        flat_balanced_predictors=tuple(flat_balanced["selected_predictors"]),
        flat_auc_predictors=tuple(flat_auc["selected_predictors"]),
        vif_predictors=tuple(vif),
        selector_audit=pd.DataFrame(audit_rows),
    )


def attach_occurrence_spatial_blocks(
    model_index: pd.DataFrame,
    *,
    occurrence_model_pool_path: str | Path,
) -> pd.DataFrame:
    """Restore the pre-feature frozen occurrence block labels by occurrence_id."""
    source = pd.read_csv(occurrence_model_pool_path)
    required = {"scientific_name", "occurrence_id", "spatial_block"}
    missing = required - set(source.columns)
    if missing:
        raise ValueError(f"v5 occurrence artifact missing spatial-block columns: {sorted(missing)}")
    source = source.loc[:, ["scientific_name", "occurrence_id", "spatial_block"]].copy()
    source["scientific_name"] = source["scientific_name"].astype(str)
    source["occurrence_id"] = source["occurrence_id"].astype(str)
    if source["occurrence_id"].duplicated().any():
        raise ValueError("v5 occurrence artifact occurrence_id must be unique")
    out = model_index.copy()
    out["scientific_name"] = out["scientific_name"].astype(str)
    out["occurrence_id"] = out["occurrence_id"].astype(str)
    out = out.merge(
        source,
        on=["scientific_name", "occurrence_id"],
        how="left",
        validate="one_to_one",
    )
    if out["spatial_block"].isna().any():
        raise ValueError("v5 feature model index does not map completely to frozen spatial blocks")
    out["spatial_block"] = pd.to_numeric(out["spatial_block"], errors="raise").astype(int)
    return out


def load_inputs(
    *,
    feature_root: str | Path,
    selected_path: str | Path,
    process_registry_path: str | Path,
    model_design_path: str | Path,
    occurrence_model_pool_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, tuple[str, ...], pd.DataFrame]:
    validate_model_design(model_design_path)
    selected, locations, model_index, background_index, predictors, registry = _load_feature_bundle(
        feature_root=feature_root,
        selected_path=selected_path,
        process_registry_path=process_registry_path,
    )
    model_index = attach_occurrence_spatial_blocks(
        model_index,
        occurrence_model_pool_path=occurrence_model_pool_path,
    )
    return selected, locations, model_index, background_index, predictors, registry


def declared_predictor_sets(
    frozen: TaxonModelFreeze,
    predictors: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    """Return every pre-outcome frozen prediction route for one taxon."""
    universe=tuple(str(p) for p in predictors)
    if not universe or len(universe)!=len(set(universe)):
        raise ValueError("v5 predictor universe must be non-empty and unique")
    return {
        "sdmr_process_first":tuple(frozen.sdmr_predictors),
        "matched_learner_flat_predictive_selector":tuple(frozen.flat_balanced_predictors),
        "auc_oriented_flat_selector":tuple(frozen.flat_auc_predictors),
        "correlation_vif_flat_filter":tuple(frozen.vif_predictors),
        "full_46_flat_hgb":universe,
    }


def _fit_final_hgb(
    model: pd.DataFrame,
    background: pd.DataFrame,
    predictors: Sequence[str],
):
    if not predictors:
        raise ValueError("final HGB fit requires at least one predictor")
    occ=model.copy(); bg=background.copy()
    occ["label"]=1; bg["label"]=0
    sample=pd.concat([occ,bg],ignore_index=True,sort=False)
    x=sample.loc[:,list(predictors)].to_numpy(float)
    y=sample["label"].to_numpy(int)
    if not np.isfinite(x).all() or len(np.unique(y))!=2:
        raise ValueError("final HGB fit requires finite two-class training data")
    fitted=HistGradientBoostingClassifier(
        loss="log_loss",random_state=0,**get_hgb_profile("shallow3")
    )
    fitted.fit(x,y,sample_weight=_hgb_balanced_sample_weight(y))
    return fitted


def run_taxon_freeze(
    *,
    selection_rank: int,
    feature_root: str | Path,
    selected_path: str | Path,
    occurrence_model_pool_path: str | Path,
    process_registry_path: str | Path,
    model_design_path: str | Path,
    output_dir: str | Path,
) -> dict:
    import joblib

    selected,locations,model_index,background_index,predictors,registry=load_inputs(
        feature_root=feature_root,
        selected_path=selected_path,
        process_registry_path=process_registry_path,
        model_design_path=model_design_path,
        occurrence_model_pool_path=occurrence_model_pool_path,
    )
    rank=int(selection_rank)
    if not 1<=rank<=EXPECTED_TAXA:
        raise ValueError("selection_rank must be in 1..50")
    row=selected.loc[pd.to_numeric(selected["selection_rank"],errors="raise").astype(int).eq(rank)]
    if len(row)!=1:
        raise ValueError("selection_rank does not map to exactly one frozen taxon")
    taxon=str(row.iloc[0]["scientific_name"])

    frozen=freeze_taxon_model_pool(
        taxon=taxon,
        locations=locations,
        model_index=model_index,
        background_index=background_index,
        predictors=predictors,
        registry=registry,
    )
    model,background=_taxon_training_tables(
        taxon=taxon,
        locations=locations,
        model_index=model_index,
        background_index=background_index,
        predictors=predictors,
    )
    auth_map=dict(zip(
        frozen.authorization["learner_route"].astype(str),
        frozen.authorization["authorized"].astype(bool),
        strict=True,
    ))
    sdmr_available=bool(
        auth_map.get("penalized_logistic",False)
        and auth_map.get("shallow3_hgb",False)
        and len(frozen.sdmr_predictors)>0
    )

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    route_path=out/"route_states.csv"
    stable_path=out/"stable_states.csv"
    evidence_path=out/"process_evidence.csv"
    auth_path=out/"full_system_authorization.csv"
    selector_path=out/"selector_audit.csv"
    frozen.route_states.to_csv(route_path,index=False)
    frozen.stable_states.to_csv(stable_path,index=False)
    frozen.process_evidence.to_csv(evidence_path,index=False)
    frozen.authorization.to_csv(auth_path,index=False)
    frozen.selector_audit.to_csv(selector_path,index=False)

    model_specs={}
    predictor_sets=declared_predictor_sets(frozen,predictors)
    for name,predictor_set in predictor_sets.items():
        available=bool(predictor_set) and (name!="sdmr_process_first" or sdmr_available)
        model_path=None
        if available:
            fitted=_fit_final_hgb(model,background,predictor_set)
            model_path=out/f"{name}.joblib"
            joblib.dump(fitted,model_path,compress=3)
        model_specs[name]={
            "available":available,
            "learner":"shallow3_hgb",
            "predictors":list(predictor_set),
            "predictor_count":len(predictor_set),
            "model_file":model_path.name if model_path is not None else None,
            "model_sha256":_sha256(model_path) if model_path is not None else None,
        }

    result={
        "program":PROGRAM,
        "status":"taxon_model_pool_frozen",
        "selection_rank":rank,
        "scientific_name":taxon,
        "predictor_count":len(predictors),
        "process_count":len(DEFAULT_PLANT_PROCESSES),
        "model_pool_complete_occurrences":int(len(model)),
        "training_background_complete_rows":int(len(background)),
        "full_system_authorized_logistic":bool(auth_map["penalized_logistic"]),
        "full_system_authorized_hgb":bool(auth_map["shallow3_hgb"]),
        "sdmr_primary_available":sdmr_available,
        "stable_sharp_processes":int(frozen.stable_states["stable_sharp"].astype(bool).sum()),
        "stable_process_denominator":EXPECTED_PROCESSES,
        "predictor_sets":model_specs,
        "route_states_sha256":_sha256(route_path),
        "stable_states_sha256":_sha256(stable_path),
        "process_evidence_sha256":_sha256(evidence_path),
        "authorization_sha256":_sha256(auth_path),
        "selector_audit_sha256":_sha256(selector_path),
        "answer_check_accessed":False,
        "answer_check_features_read":False,
        "model_pool_only":True,
    }
    (out/"taxon_model_freeze.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return result


def aggregate_taxon_freezes(
    *,
    taxon_root: str | Path,
    selected_path: str | Path,
    output_dir: str | Path,
) -> dict:
    selected=pd.read_csv(selected_path)
    if len(selected)!=EXPECTED_TAXA:
        raise ValueError("aggregate requires exact final50 manifest")
    expected=dict(zip(
        pd.to_numeric(selected["selection_rank"],errors="raise").astype(int),
        selected["scientific_name"].astype(str),
        strict=True,
    ))
    root=Path(taxon_root)
    receipts=sorted(root.rglob("taxon_model_freeze.json"))
    if len(receipts)!=EXPECTED_TAXA:
        raise RuntimeError(f"expected 50 taxon model receipts; found {len(receipts)}")

    rows=[]; route=[]; stable=[]; auth=[]; selector=[]
    for path in receipts:
        r=json.loads(path.read_text(encoding="utf-8"))
        rank=int(r["selection_rank"]); taxon=str(r["scientific_name"])
        if expected.get(rank)!=taxon:
            raise RuntimeError(f"taxon model receipt does not match frozen final50: {rank}/{taxon}")
        if r.get("answer_check_accessed") is not False or r.get("model_pool_only") is not True:
            raise RuntimeError(f"taxon model freeze crossed answer-check boundary: {taxon}")
        parent=path.parent
        checks={
            "route_states.csv":r["route_states_sha256"],
            "stable_states.csv":r["stable_states_sha256"],
            "process_evidence.csv":r["process_evidence_sha256"],
            "full_system_authorization.csv":r["authorization_sha256"],
            "selector_audit.csv":r["selector_audit_sha256"],
        }
        for filename,wanted in checks.items():
            if _sha256(parent/filename)!=wanted:
                raise RuntimeError(f"taxon model artifact SHA mismatch: {taxon}/{filename}")
        declared_routes={
            "sdmr_process_first",
            "matched_learner_flat_predictive_selector",
            "auc_oriented_flat_selector",
            "correlation_vif_flat_filter",
            "full_46_flat_hgb",
        }
        predictor_sets=r.get("predictor_sets",{})
        if set(predictor_sets)!=declared_routes:
            raise RuntimeError(f"v5 frozen route set changed: {taxon}")
        capacity=predictor_sets["full_46_flat_hgb"]
        if (
            capacity.get("available") is not True
            or capacity.get("learner")!="shallow3_hgb"
            or int(capacity.get("predictor_count",-1))!=EXPECTED_PREDICTORS
            or len(capacity.get("predictors",[]))!=EXPECTED_PREDICTORS
        ):
            raise RuntimeError(f"v5 full46 capacity route not frozen exactly: {taxon}")
        for spec in predictor_sets.values():
            if spec["available"]:
                mp=parent/spec["model_file"]
                if _sha256(mp)!=spec["model_sha256"]:
                    raise RuntimeError(f"serialized model SHA mismatch: {taxon}/{spec['model_file']}")
        rows.append(r)
        x=pd.read_csv(parent/"route_states.csv");x.insert(0,"scientific_name",taxon);x.insert(0,"selection_rank",rank);route.append(x)
        x=pd.read_csv(parent/"stable_states.csv");x.insert(0,"scientific_name",taxon);x.insert(0,"selection_rank",rank);stable.append(x)
        x=pd.read_csv(parent/"full_system_authorization.csv");x.insert(0,"scientific_name",taxon);x.insert(0,"selection_rank",rank);auth.append(x)
        x=pd.read_csv(parent/"selector_audit.csv");x.insert(0,"scientific_name",taxon);x.insert(0,"selection_rank",rank);selector.append(x)

    if sorted(int(r["selection_rank"]) for r in rows)!=list(range(1,EXPECTED_TAXA+1)):
        raise RuntimeError("taxon model freeze ranks are not exactly 1..50")
    stable_df=pd.concat(stable,ignore_index=True)
    denominator=EXPECTED_TAXA*EXPECTED_PROCESSES
    stable_sharp=int(stable_df["stable_sharp"].astype(bool).sum())
    available_taxa=int(sum(bool(r["sdmr_primary_available"]) for r in rows))

    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    summary_path=out/"taxon_model_freeze_summary.csv"
    route_path=out/"route_states_all_taxa.csv"
    stable_path=out/"stable_states_all_taxa.csv"
    auth_path=out/"full_system_authorization_all_taxa.csv"
    selector_path=out/"selector_audit_all_taxa.csv"
    pd.DataFrame(rows).drop(columns="predictor_sets").to_csv(summary_path,index=False)
    pd.concat(route,ignore_index=True).to_csv(route_path,index=False)
    stable_df.to_csv(stable_path,index=False)
    pd.concat(auth,ignore_index=True).to_csv(auth_path,index=False)
    pd.concat(selector,ignore_index=True).to_csv(selector_path,index=False)

    result={
        "program":PROGRAM,
        "status":"model_pool_states_and_comparator_sets_frozen",
        "taxon_count":EXPECTED_TAXA,
        "selected_manifest_sha256":_sha256(selected_path),
        "process_cells":denominator,
        "stable_sharp_process_cells":stable_sharp,
        "stable_process_fraction":float(stable_sharp/denominator),
        "sdmr_primary_available_taxa":available_taxa,
        "sdmr_primary_unavailable_taxa":EXPECTED_TAXA-available_taxa,
        "full46_capacity_control_frozen_taxa":EXPECTED_TAXA,
        "capacity_control_affects_emp_promotion":False,
        "taxon_summary_sha256":_sha256(summary_path),
        "route_states_sha256":_sha256(route_path),
        "stable_states_sha256":_sha256(stable_path),
        "authorization_sha256":_sha256(auth_path),
        "selector_audit_sha256":_sha256(selector_path),
        "answer_check_accessed":False,
        "answer_check_features_read":False,
        "model_pool_only":True,
        "next_gate":"freeze_model_pool_artifact_provenance_then_open_answer_check_once",
    }
    (out/"model_pool_freeze_result.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return result


def main() -> None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    taxon=sub.add_parser("taxon")
    taxon.add_argument("--selection-rank",type=int,required=True)
    taxon.add_argument("--feature-root",required=True)
    taxon.add_argument("--selected",required=True)
    taxon.add_argument("--occurrence-model-pool",required=True)
    taxon.add_argument("--process-registry",required=True)
    taxon.add_argument("--model-design",required=True)
    taxon.add_argument("--output-dir",required=True)

    agg=sub.add_parser("aggregate")
    agg.add_argument("--taxon-root",required=True)
    agg.add_argument("--selected",required=True)
    agg.add_argument("--output-dir",required=True)

    args=parser.parse_args()
    if args.command=="taxon":
        result=run_taxon_freeze(
            selection_rank=args.selection_rank,
            feature_root=args.feature_root,
            selected_path=args.selected,
            occurrence_model_pool_path=args.occurrence_model_pool,
            process_registry_path=args.process_registry,
            model_design_path=args.model_design,
            output_dir=args.output_dir,
        )
    else:
        result=aggregate_taxon_freezes(
            taxon_root=args.taxon_root,
            selected_path=args.selected,
            output_dir=args.output_dir,
        )
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
