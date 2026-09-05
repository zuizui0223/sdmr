"""Prospective known-truth validation runner for ecological identification.

Family jobs fit/select models using only model-pool evidence and never evaluate
true generating processes. The terminal evaluator opens generating-process labels
only after all independently repeated family jobs have completed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .known_truth_response import DEFAULT_PROCESS_ALIASES, infer_true_processes
from .known_truth_scenarios import (
    KNOWN_TRUTH_FAMILIES,
    simulate_known_truth_plant_niche,
    standard_known_truth_candidates,
)
from .metrics import presence_rank_score
from .model import ModelSpec, fit_relative_suitability_model, score_relative_suitability
from .niche_recovery_cv import RecoveryCandidate, benchmark_niche_recovery_candidates
from .observation_aware_identification import fit_observation_aware_identification
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .transport_parity import assert_transport_frame_parity
from .v2_7_2_deterministic_procedure_library import seed_recovery_candidates
from .validation import make_spatial_partition


EXECUTION_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "ecological_identification_learner_validation_execution.json"
)


def load_execution(path: str | Path = EXECUTION_PATH) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "prospective_ecological_identification_learner_validation_execution":
        raise ValueError("wrong prospective validation execution receipt")
    if payload.get("scientific_run_authorized") is not True:
        raise ValueError("prospective validation scientific run is not authorized")
    families = tuple(str(x) for x in payload.get("families", ()))
    if families != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("prospective validation family denominator changed")
    seeds = tuple(int(x) for x in payload.get("seeds", ()))
    if seeds != tuple(range(4101, 4121)):
        raise ValueError("prospective validation seed denominator changed")
    if int(payload.get("n_cases", -1)) != len(families) * len(seeds):
        raise ValueError("prospective validation case denominator changed")
    if payload.get("post_outcome_changes_allowed") is not False:
        raise ValueError("post-outcome changes must remain forbidden")
    if payload.get("threshold_relaxation_allowed") is not False:
        raise ValueError("threshold relaxation must remain forbidden")
    return payload


def _model_specs(cfg: dict) -> tuple[ModelSpec, ...]:
    specs = tuple(
        ModelSpec(
            C=float(row["C"]),
            degree=int(row["degree"]),
            penalty=str(row["penalty"]),
            random_state=int(row["random_state"]),
        )
        for row in cfg["learner"]["model_specs"]
    )
    if len(specs) != 6 or len({s.label for s in specs}) != 6:
        raise ValueError("prospective learner must contain six frozen unique model specs")
    expected = {(0.1, 1), (1.0, 1), (10.0, 1), (0.1, 2), (1.0, 2), (10.0, 2)}
    if {(float(s.C), int(s.degree)) for s in specs} != expected:
        raise ValueError("prospective learner capacity grid changed")
    return specs


def _process_registry(cfg: dict) -> pd.DataFrame:
    return pd.DataFrame(cfg["process_registry"])[["predictor", "process", "role"]].copy()


def _selection_frames(simulation, *, family: str, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    forbidden = {
        "true_suitability",
        "sampling_effort",
        "focal_recording_multiplier",
        "scenario",
    }
    occurrences = simulation.occurrences.drop(columns=list(forbidden), errors="ignore").copy()
    background = simulation.target_group.drop(columns=list(forbidden), errors="ignore").copy()
    occurrences["occurrence_id"] = [
        f"{family}-{seed}-occ-{index:04d}" for index in range(len(occurrences))
    ]
    leaked = forbidden.intersection(occurrences.columns) | forbidden.intersection(background.columns)
    if leaked:
        raise RuntimeError("hidden simulation columns leaked into selection frames: " + ", ".join(sorted(leaked)))
    return occurrences, background


def _candidate_processes(
    candidate: RecoveryCandidate,
    process_universe: Sequence[str],
) -> tuple[str, ...]:
    allowed = set(str(x) for x in process_universe)
    observation = set(str(x) for x in candidate.observation_predictors)
    processes = []
    for predictor in candidate.predictors:
        if predictor in observation:
            continue
        process = str(DEFAULT_PROCESS_ALIASES.get(str(predictor), str(predictor)))
        if process in allowed and process not in processes:
            processes.append(process)
    return tuple(sorted(processes))


def _canonical_prediction_winner(metrics: pd.DataFrame) -> str:
    summary = (
        metrics.groupby("candidate", as_index=False)["presence_rank"]
        .mean()
        .rename(columns={"presence_rank": "mean_presence_rank"})
    )
    summary["mean_presence_rank"] = pd.to_numeric(summary["mean_presence_rank"], errors="coerce")
    summary = summary.loc[np.isfinite(summary["mean_presence_rank"])].copy()
    if summary.empty:
        raise ValueError("canonical prediction comparator has no finite candidate")
    summary = summary.sort_values(
        ["mean_presence_rank", "candidate"],
        ascending=[False, True],
        kind="mergesort",
    )
    return str(summary.iloc[0]["candidate"])


def _candidate_sealed_presence_rank(
    candidate: RecoveryCandidate,
    model_presence: pd.DataFrame,
    background: pd.DataFrame,
    answer_presence: pd.DataFrame,
) -> float:
    model = fit_relative_suitability_model(
        model_presence,
        background,
        candidate.predictors,
        model_spec=candidate.model_spec,
    )
    p_scores = score_relative_suitability(model, answer_presence, candidate.predictors)
    b_scores = score_relative_suitability(model, background, candidate.predictors)
    return float(presence_rank_score(p_scores, b_scores))


def _case_failure_rows(
    *,
    family: str,
    seed: int,
    replicate: int,
    process_universe: Sequence[str],
    error: BaseException,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    case = {
        "replicate": int(replicate),
        "family": str(family),
        "seed": int(seed),
        "case_available": False,
        "failure_class": type(error).__name__,
        "selection_receipt": "",
        "admissible_model_labels": "",
        "canonical_candidate": "",
        "canonical_processes": "",
        "ecological_candidate": "",
        "ecological_processes": "",
        "learner_presence_rank": float("nan"),
        "canonical_presence_rank": float("nan"),
        "ecological_presence_rank": float("nan"),
        "learner_minus_canonical_presence_rank": float("nan"),
        "n_model_pool_occurrences": 0,
        "n_answer_check_occurrences": 0,
    }
    process_rows = [
        {
            "replicate": int(replicate),
            "family": str(family),
            "seed": int(seed),
            "process": str(process),
            "status": "unresolved",
            "n_admitted_baseline_models": 0,
            "n_complete_knockout_routes": 0,
            "n_adequate_witness_routes": 0,
            "adequate_witness_routes": "",
        }
        for process in process_universe
    ]
    return case, process_rows


def fit_case_nontruth(
    family: str,
    seed: int,
    *,
    replicate: int,
    execution: dict,
) -> dict[str, pd.DataFrame]:
    """Fit one case without ever evaluating its true generating process labels."""

    sim_cfg = execution["simulation"]
    learner_cfg = execution["learner"]
    ecological_predictors = tuple(str(x) for x in execution["ecological_predictors"])
    observation_predictors = tuple(str(x) for x in execution["observation_predictors"])
    process_universe = tuple(str(x) for x in execution["process_universe"])
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

    fit = fit_observation_aware_identification(
        model_presence,
        background,
        inner.presence_blocks,
        inner.background_blocks,
        ecological_predictors=ecological_predictors,
        observation_predictors=observation_predictors,
        process_registry=_process_registry(execution),
        process_universe=process_universe,
        model_specs=_model_specs(execution),
        n_splits=int(sim_cfg["inner_n_splits"]),
        chance_score=float(learner_cfg["chance_score"]),
        minimum_margin=float(learner_cfg["minimum_margin"]),
        sem_multiplier=float(learner_cfg["sem_multiplier"]),
        observation_signal_chance=float(learner_cfg["observation_signal_chance"]),
        observation_signal_margin=float(learner_cfg["observation_signal_margin"]),
        observation_signal_sem_multiplier=float(learner_cfg["observation_signal_sem_multiplier"]),
        observation_weight_truncation_quantile=float(learner_cfg["observation_weight_truncation_quantile"]),
        observation_weight_probability_epsilon=float(learner_cfg["observation_weight_probability_epsilon"]),
        occurrence_split=split,
        occurrence_id_col="occurrence_id",
    )

    candidates = seed_recovery_candidates(standard_known_truth_candidates(), random_state=0)
    comparator_metrics, ecological_selection = benchmark_niche_recovery_candidates(
        model_presence,
        background,
        inner.presence_blocks,
        inner.background_blocks,
        candidates,
        simulation.audit_predictors,
        n_splits=int(sim_cfg["inner_n_splits"]),
    )
    canonical_candidate = _canonical_prediction_winner(comparator_metrics)
    ecological_candidate = str(ecological_selection.candidate)
    canonical_processes = _candidate_processes(candidates[canonical_candidate], process_universe)
    ecological_processes = _candidate_processes(candidates[ecological_candidate], process_universe)

    receipt_payload = "\n".join(
        [
            f"learner={fit.selection_receipt}",
            f"canonical={canonical_candidate}",
            f"canonical_processes={','.join(canonical_processes)}",
            f"ecological={ecological_candidate}",
            f"ecological_processes={','.join(ecological_processes)}",
            f"outer_split={split.split_digest}",
        ]
    )
    selection_receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    answer_presence = split.open_answer_check(
        occurrences,
        selection_receipt=selection_receipt,
        id_col="occurrence_id",
    )

    learner_presence_rank = presence_rank_score(
        fit.predict_relative_suitability(answer_presence),
        fit.predict_relative_suitability(background),
    )
    canonical_presence_rank = _candidate_sealed_presence_rank(
        candidates[canonical_candidate],
        model_presence,
        background,
        answer_presence,
    )
    ecological_presence_rank = _candidate_sealed_presence_rank(
        candidates[ecological_candidate],
        model_presence,
        background,
        answer_presence,
    )

    case_summary = pd.DataFrame(
        [
            {
                "replicate": int(replicate),
                "family": str(family),
                "seed": int(seed),
                "case_available": True,
                "failure_class": "",
                "selection_receipt": selection_receipt,
                "admissible_model_labels": ",".join(fit.admissible_model_labels),
                "canonical_candidate": canonical_candidate,
                "canonical_processes": ",".join(canonical_processes),
                "ecological_candidate": ecological_candidate,
                "ecological_processes": ",".join(ecological_processes),
                "learner_presence_rank": float(learner_presence_rank),
                "canonical_presence_rank": float(canonical_presence_rank),
                "ecological_presence_rank": float(ecological_presence_rank),
                "learner_minus_canonical_presence_rank": float(
                    learner_presence_rank - canonical_presence_rank
                ),
                "n_model_pool_occurrences": int(len(model_presence)),
                "n_answer_check_occurrences": int(len(answer_presence)),
            }
        ]
    )
    process_status = fit.process_summary.copy()
    process_status.insert(0, "seed", int(seed))
    process_status.insert(0, "family", str(family))
    process_status.insert(0, "replicate", int(replicate))

    baseline = fit.baseline_summary.copy()
    baseline.insert(0, "seed", int(seed))
    baseline.insert(0, "family", str(family))
    baseline.insert(0, "replicate", int(replicate))
    knockout = fit.knockout_summary.copy()
    knockout.insert(0, "seed", int(seed))
    knockout.insert(0, "family", str(family))
    knockout.insert(0, "replicate", int(replicate))
    folds = fit.fold_evidence.copy()
    folds.insert(0, "seed", int(seed))
    folds.insert(0, "family", str(family))
    folds.insert(0, "replicate", int(replicate))
    comparator_metrics = comparator_metrics.copy()
    comparator_metrics.insert(0, "seed", int(seed))
    comparator_metrics.insert(0, "family", str(family))
    comparator_metrics.insert(0, "replicate", int(replicate))
    return {
        "case_summary": case_summary,
        "process_status": process_status,
        "baseline_summary": baseline,
        "knockout_summary": knockout,
        "fold_evidence": folds,
        "comparator_metrics": comparator_metrics,
    }


def fit_family(
    family: str,
    replicate: int,
    output_dir: str | Path,
    *,
    execution_path: str | Path = EXECUTION_PATH,
) -> None:
    execution = load_execution(execution_path)
    if family not in execution["families"]:
        raise ValueError(f"family is outside frozen denominator: {family}")
    if int(replicate) not in (1, 2):
        raise ValueError("replicate must be 1 or 2")
    process_universe = tuple(str(x) for x in execution["process_universe"])

    accumulated: dict[str, list[pd.DataFrame]] = {
        "case_summary": [],
        "process_status": [],
        "baseline_summary": [],
        "knockout_summary": [],
        "fold_evidence": [],
        "comparator_metrics": [],
    }
    for seed in tuple(int(x) for x in execution["seeds"]):
        try:
            frames = fit_case_nontruth(
                family,
                seed,
                replicate=int(replicate),
                execution=execution,
            )
        except Exception as error:  # denominator-preserving scientific failure state
            case, process_rows = _case_failure_rows(
                family=family,
                seed=seed,
                replicate=int(replicate),
                process_universe=process_universe,
                error=error,
            )
            frames = {
                "case_summary": pd.DataFrame([case]),
                "process_status": pd.DataFrame(process_rows),
                "baseline_summary": pd.DataFrame(),
                "knockout_summary": pd.DataFrame(),
                "fold_evidence": pd.DataFrame(),
                "comparator_metrics": pd.DataFrame(),
            }
        for name, frame in frames.items():
            if len(frame):
                accumulated[name].append(frame)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, frames in accumulated.items():
        result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if len(result):
            sort_cols = [x for x in ("replicate", "family", "seed", "process", "model_label", "candidate", "route", "fold") if x in result.columns]
            result = result.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
        result.to_csv(out / f"{name}.csv", index=False)
    receipt = {
        "purpose": "prospective_ecological_identification_family_nontruth_fit",
        "family": str(family),
        "replicate": int(replicate),
        "seeds": list(execution["seeds"]),
        "n_expected_cases": len(execution["seeds"]),
        "hidden_true_process_labels_used_during_fit_or_selection": False,
        "hidden_true_suitability_used_during_fit_or_selection": False,
        "post_outcome_changes_allowed": False,
    }
    (out / "run_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _split_processes(value: object) -> set[str]:
    text = "" if pd.isna(value) else str(value)
    return {x for x in text.split(",") if x}


def _process_metrics_from_labels(frame: pd.DataFrame, predicted_col: str) -> dict[str, float | int]:
    expected = frame["expected_required"].astype(bool).to_numpy()
    predicted = frame[predicted_col].astype(str).to_numpy()
    is_required = predicted == "required"
    is_nonrequired = predicted == "nonrequired"
    true_required_n = int(expected.sum())
    false_process_n = int((~expected).sum())
    required_tp = int(np.sum(expected & is_required))
    false_required = int(np.sum((~expected) & is_required))
    nonrequired_tp = int(np.sum((~expected) & is_nonrequired))
    required_fn = int(np.sum(expected & (~is_required)))
    nonrequired_fn = int(np.sum((~expected) & (~is_nonrequired)))
    nonrequired_fp = int(np.sum(expected & is_nonrequired))

    def f1(tp: int, fp: int, fn: int) -> float:
        denom = 2 * tp + fp + fn
        return float(2 * tp / denom) if denom else float("nan")

    required_f1 = f1(required_tp, false_required, required_fn)
    nonrequired_f1 = f1(nonrequired_tp, nonrequired_fp, nonrequired_fn)
    return {
        "true_process_recall": float(required_tp / true_required_n) if true_required_n else float("nan"),
        "false_required_rate": float(false_required / false_process_n) if false_process_n else float("nan"),
        "required_f1": required_f1,
        "nonrequired_f1": nonrequired_f1,
        "macro_f1": float(np.nanmean([required_f1, nonrequired_f1])),
        "n_true_processes": true_required_n,
        "n_false_processes": false_process_n,
        "n_required_true_positive": required_tp,
        "n_false_required": false_required,
        "n_unresolved": int(np.sum(predicted == "unresolved")),
    }


def _discover_runs(root: Path) -> dict[tuple[int, str], Path]:
    runs: dict[tuple[int, str], Path] = {}
    for receipt_path in root.rglob("run_receipt.json"):
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        if payload.get("purpose") != "prospective_ecological_identification_family_nontruth_fit":
            continue
        key = (int(payload["replicate"]), str(payload["family"]))
        if key in runs:
            raise ValueError(f"duplicate family replicate artifact: {key}")
        runs[key] = receipt_path.parent
    return runs


def _load_frame(path: Path, filename: str) -> pd.DataFrame:
    file_path = path / filename
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path)


def evaluate_terminal(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    execution_path: str | Path = EXECUTION_PATH,
) -> dict[str, object]:
    """Open process truth only after every nontruth family/replicate result exists."""

    execution = load_execution(execution_path)
    root = Path(input_dir)
    runs = _discover_runs(root)
    expected_keys = {
        (replicate, family)
        for replicate in (1, 2)
        for family in tuple(execution["families"])
    }
    if set(runs) != expected_keys:
        missing = sorted(expected_keys - set(runs))
        extra = sorted(set(runs) - expected_keys)
        raise ValueError(f"terminal evaluator requires all frozen family replicates; missing={missing}, extra={extra}")

    det_cfg = execution["determinism"]
    rtol = float(det_cfg["numeric_relative_tolerance"])
    atol = float(det_cfg["numeric_absolute_tolerance"])
    determinism_frames: dict[str, dict[str, object]] = {}
    for family in tuple(execution["families"]):
        for filename in (
            "case_summary.csv",
            "process_status.csv",
            "baseline_summary.csv",
            "knockout_summary.csv",
            "fold_evidence.csv",
            "comparator_metrics.csv",
        ):
            a = _load_frame(runs[(1, family)], filename).drop(columns="replicate", errors="ignore")
            b = _load_frame(runs[(2, family)], filename).drop(columns="replicate", errors="ignore")
            result = assert_transport_frame_parity(a, b, rtol=rtol, atol=atol)
            determinism_frames[f"{family}/{filename}"] = result.as_dict()
    determinism_passed = True

    case_frames = [_load_frame(runs[(1, family)], "case_summary.csv") for family in execution["families"]]
    process_frames = [_load_frame(runs[(1, family)], "process_status.csv") for family in execution["families"]]
    cases = pd.concat(case_frames, ignore_index=True).sort_values(["family", "seed"], kind="mergesort").reset_index(drop=True)
    process = pd.concat(process_frames, ignore_index=True).sort_values(["family", "seed", "process"], kind="mergesort").reset_index(drop=True)
    expected_case_n = int(execution["n_cases"])
    if len(cases) != expected_case_n:
        raise ValueError(f"terminal case denominator changed: {len(cases)} != {expected_case_n}")

    truth_rows = []
    process_universe = tuple(str(x) for x in execution["process_universe"])
    for row in cases[["family", "seed"]].itertuples(index=False):
        # Truth labels are opened here, after all fit/selection artifacts already exist.
        truth_frame = pd.DataFrame(
            {
                "scenario": [str(row.family)],
                "temperature": [0.0],
                "water": [0.0],
                "soil": [0.0],
            }
        )
        true_processes = set(infer_true_processes(truth_frame))
        case_row = cases.loc[
            cases["family"].astype(str).eq(str(row.family))
            & cases["seed"].astype(int).eq(int(row.seed))
        ].iloc[0]
        canonical = _split_processes(case_row["canonical_processes"])
        ecological = _split_processes(case_row["ecological_processes"])
        for process_name in process_universe:
            status_rows = process.loc[
                process["family"].astype(str).eq(str(row.family))
                & process["seed"].astype(int).eq(int(row.seed))
                & process["process"].astype(str).eq(process_name)
            ]
            if len(status_rows) != 1:
                status = "unresolved"
                n_admitted = 0
                n_complete = 0
            else:
                status = str(status_rows.iloc[0]["status"])
                n_admitted = int(status_rows.iloc[0]["n_admitted_baseline_models"])
                n_complete = int(status_rows.iloc[0]["n_complete_knockout_routes"])
            if status == "required_by_evidence_contract":
                new_label = "required"
            elif status == "refuted_as_necessary":
                new_label = "nonrequired"
            else:
                new_label = "unresolved"
            truth_rows.append(
                {
                    "family": str(row.family),
                    "seed": int(row.seed),
                    "process": process_name,
                    "expected_required": process_name in true_processes,
                    "new_status": status,
                    "new_label": new_label,
                    "canonical_label": "required" if process_name in canonical else "nonrequired",
                    "ecological_winner_label": "required" if process_name in ecological else "nonrequired",
                    "n_admitted_baseline_models": n_admitted,
                    "n_complete_knockout_routes": n_complete,
                }
            )
    truth = pd.DataFrame(truth_rows)

    method_rows = []
    for method, column in (
        ("new_identification_learner", "new_label"),
        ("canonical_prediction_winner", "canonical_label"),
        ("single_ecological_recovery_winner", "ecological_winner_label"),
    ):
        metrics = _process_metrics_from_labels(truth, column)
        method_rows.append({"method": method, **metrics})
    method_metrics = pd.DataFrame(method_rows)

    family_rows = []
    for family, group in truth.groupby("family", sort=True):
        metrics = _process_metrics_from_labels(group, "new_label")
        family_rows.append({"family": str(family), **metrics})
    family_metrics = pd.DataFrame(family_rows)

    new_metrics = method_metrics.loc[
        method_metrics["method"].eq("new_identification_learner")
    ].iloc[0]
    primary_cfg = execution["primary_process_thresholds"]
    required_rows = truth.loc[truth["new_label"].eq("required")]
    required_complete = bool(
        len(required_rows) == 0
        or (
            required_rows["n_admitted_baseline_models"].astype(int).gt(0)
            & required_rows["n_complete_knockout_routes"].astype(int).eq(
                required_rows["n_admitted_baseline_models"].astype(int)
            )
        ).all()
    )
    family_recall_pass = bool(
        np.isfinite(family_metrics["true_process_recall"]).all()
        and (
            family_metrics["true_process_recall"]
            >= float(primary_cfg["family_true_process_recall_min"])
        ).all()
    )
    process_checks = {
        "false_required_rate": float(new_metrics["false_required_rate"])
        <= float(primary_cfg["false_required_rate_max"]),
        "true_process_recall": float(new_metrics["true_process_recall"])
        >= float(primary_cfg["true_process_recall_min"]),
        "process_status_macro_f1": float(new_metrics["macro_f1"])
        >= float(primary_cfg["process_status_macro_f1_min"]),
        "all_family_true_process_recall": family_recall_pass,
        "required_claim_evidence_complete": required_complete,
    }

    learner_scores = pd.to_numeric(cases["learner_presence_rank"], errors="coerce")
    canonical_scores = pd.to_numeric(cases["canonical_presence_rank"], errors="coerce")
    prediction_complete = bool(
        len(cases) == expected_case_n
        and np.isfinite(learner_scores).all()
        and np.isfinite(canonical_scores).all()
    )
    delta = learner_scores - canonical_scores
    mean_delta = float(delta.mean()) if prediction_complete else float("nan")
    family_prediction = (
        cases.assign(delta=delta)
        .groupby("family", as_index=False)["delta"]
        .mean()
        .rename(columns={"delta": "mean_learner_minus_canonical_presence_rank"})
    )
    guard = execution["prediction_guardrails"]
    family_guard_pass = bool(
        prediction_complete
        and np.isfinite(family_prediction["mean_learner_minus_canonical_presence_rank"]).all()
        and (
            family_prediction["mean_learner_minus_canonical_presence_rank"]
            >= float(guard["family_mean_delta_min"])
        ).all()
    )
    prediction_checks = {
        "complete_full_denominator": prediction_complete,
        "mean_delta_guardrail": bool(
            prediction_complete
            and mean_delta >= float(guard["mean_sealed_presence_rank_delta_vs_canonical_min"])
        ),
        "family_delta_guardrail": family_guard_pass,
    }

    known_truth_supported = bool(
        determinism_passed
        and all(process_checks.values())
        and all(prediction_checks.values())
    )
    canonical_metrics = method_metrics.loc[
        method_metrics["method"].eq("canonical_prediction_winner")
    ].iloc[0]
    ecological_metrics = method_metrics.loc[
        method_metrics["method"].eq("single_ecological_recovery_winner")
    ].iloc[0]
    decision = {
        "purpose": "prospective_ecological_identification_known_truth_decision",
        "known_truth_supported": known_truth_supported,
        "determinism_passed": determinism_passed,
        "process_checks": process_checks,
        "prediction_checks": prediction_checks,
        "mean_learner_minus_canonical_presence_rank": mean_delta,
        "new_learner_process_metrics": {k: (float(v) if isinstance(v, (float, np.floating)) else int(v)) for k, v in new_metrics.items() if k != "method"},
        "canonical_prediction_winner_process_metrics": {k: (float(v) if isinstance(v, (float, np.floating)) else int(v)) for k, v in canonical_metrics.items() if k != "method"},
        "single_ecological_recovery_winner_process_metrics": {k: (float(v) if isinstance(v, (float, np.floating)) else int(v)) for k, v in ecological_metrics.items() if k != "method"},
        "comparative_superiority_threshold_was_predeclared": False,
        "comparators_are_descriptive_not_posthoc_promotion_gates": True,
        "fresh_empirical_validation_pending": True,
        "nature_family_promotion_allowed_now": False,
        "product_a_reopened": False,
        "post_outcome_changes_allowed": False,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases.to_csv(out / "case_summary.csv", index=False)
    process.to_csv(out / "process_status_pretruth.csv", index=False)
    truth.to_csv(out / "truth_evaluation.csv", index=False)
    method_metrics.to_csv(out / "method_process_metrics.csv", index=False)
    family_metrics.to_csv(out / "family_process_metrics.csv", index=False)
    family_prediction.to_csv(out / "family_prediction_guardrail.csv", index=False)
    (out / "determinism_decision.json").write_text(
        json.dumps(
            {
                "determinism_passed": determinism_passed,
                "numeric_relative_tolerance": rtol,
                "numeric_absolute_tolerance": atol,
                "frame_summaries": determinism_frames,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "scientific_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    fit = sub.add_parser("fit-family")
    fit.add_argument("--family", required=True, choices=KNOWN_TRUTH_FAMILIES)
    fit.add_argument("--replicate", required=True, type=int, choices=(1, 2))
    fit.add_argument("--output-dir", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--input-dir", required=True)
    evaluate.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "fit-family":
        fit_family(args.family, args.replicate, args.output_dir)
    else:
        evaluate_terminal(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
