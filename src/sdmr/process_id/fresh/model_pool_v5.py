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
    model = model_index.loc[model_index["scientific_name"].astype(str).eq(taxon)].copy()
    bg = background_index.loc[background_index["scientific_name"].astype(str).eq(taxon)].copy()
    if model.empty or bg.empty:
        raise ValueError(f"missing v5 feature rows for {taxon}")

    if "complete_case" not in model or "complete_case" not in bg:
        raise ValueError("v5 model input requires complete_case flags")
    model = model.loc[model["complete_case"].astype(bool)].copy()
    bg = bg.loc[
        bg["complete_case"].astype(bool)
        & pd.to_numeric(bg["background_rank"], errors="raise").astype(int).mod(BACKGROUND_TRAIN_MODULUS).ne(BACKGROUND_EVAL_REMAINDER)
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
    retained = list(sorted(str(p) for p in predictors))
    x = background.loc[:, retained].to_numpy(float)
    if not np.isfinite(x).all():
        raise ValueError("VIF input must be complete finite training background")
    while len(retained) > 1:
        x = background.loc[:, retained].to_numpy(float)
        sd = np.std(x, axis=0)
        constant = [retained[i] for i, value in enumerate(sd) if not np.isfinite(value) or value <= 0]
        if constant:
            # deterministic removal; a constant predictor has infinite VIF.
            retained.remove(sorted(constant)[0])
            continue
        z = (x - np.mean(x, axis=0)) / sd
        corr = np.corrcoef(z, rowvar=False)
        try:
            inv = np.linalg.pinv(corr, hermitian=True)
            vif = np.diag(inv)
        except np.linalg.LinAlgError:
            vif = np.full(len(retained), np.inf)
        max_vif = float(np.max(vif))
        if math.isfinite(max_vif) and max_vif <= float(threshold):
            break
        candidates = [
            retained[i]
            for i, value in enumerate(vif)
            if (not math.isfinite(max_vif) and not math.isfinite(float(value)))
            or np.isclose(float(value), max_vif, rtol=0.0, atol=1e-10)
        ]
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

    flat_balanced = sequential_forward_selection(
        model=model,
        background=background,
        predictors=predictors,
        metric="balanced_log_score",
    )
    flat_auc = sequential_forward_selection(
        model=model,
        background=background,
        predictors=predictors,
        metric="roc_auc",
    )
    vif = vif_prune(background, predictors, threshold=VIF_THRESHOLD)

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
            })
    audit_rows.append({
        "selector": "correlation_vif_flat_filter",
        "metric": "VIF",
        "n_predictors": len(vif),
        "predictors": ",".join(vif),
        "mean_score": np.nan,
        "selected": True,
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


def load_inputs(
    *,
    feature_root: str | Path,
    selected_path: str | Path,
    process_registry_path: str | Path,
    model_design_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, tuple[str, ...], pd.DataFrame]:
    validate_model_design(model_design_path)
    return _load_feature_bundle(
        feature_root=feature_root,
        selected_path=selected_path,
        process_registry_path=process_registry_path,
    )
