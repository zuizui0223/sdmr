"""Prospective factorial process-identity recovery experiment for Product A.

This experiment exists to answer a concrete weakness in the v2.7.2 truth suite:
temperature and water were generating processes in every case, so only soil
provided a presence/absence identification test.  Here temperature, water and
soil are independently switched on/off across all seven non-empty process sets.

The contract is frozen in ``configs/product_a_factorial_process_recovery_contract.json``.
Hidden process truth is never used by candidate selection.  It is opened only
after canonical AUC, canonical ecological-recovery and perturbation-robust
ecological selectors have selected fitted candidates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .ecological_inference_certificate import build_ecological_inference_certificate
from .known_truth import KnownTruthSimulation, known_truth_niche_recovery_profile
from .known_truth_perturbation import (
    KnownTruthPerturbationResult,
    KnownTruthPerturbationSpec,
    _candidate_spatial_metrics,
)
from .known_truth_perturbation_experiment import _canonical_model_pool, _metric_winner
from .known_truth_response import (
    DEFAULT_PROCESS_ALIASES,
    known_truth_process_profile,
    known_truth_response_profile,
)
from .known_truth_scenarios import _base_landscape
from .model import ModelSpec, fit_relative_suitability_model, score_ecological_suitability
from .niche_recovery_cv import RecoveryCandidate
from .niche_recovery_perturbation import select_perturbation_robust_niche_recovery_protocol
from .niche_recovery_selection import select_generalization_gated_niche_recovery_protocol
from .v2_7_2_deterministic_procedure_library import seed_recovery_candidates

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "configs" / "product_a_factorial_process_recovery_contract.json"
CANONICAL_SELECTOR = "canonical_replicated_observation_niche_recovery"
ROBUST_SELECTOR = "replicated_observation_perturbation_robust_niche_recovery"
AUC_SELECTOR = "canonical_auc"
PROCESSES = ("temperature", "water", "soil")


def load_contract(path: str | Path = CONTRACT_PATH) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_factorial_process_recovery_preoutcome_contract":
        raise ValueError("wrong factorial process-recovery contract")
    if payload.get("frozen_before_factorial_outcome") is not True:
        raise ValueError("factorial contract was not frozen before outcome")
    sets = [tuple(str(x) for x in row) for row in payload["process_sets"]]
    expected = {
        ("temperature",),
        ("water",),
        ("soil",),
        ("temperature", "water"),
        ("temperature", "soil"),
        ("water", "soil"),
        ("temperature", "water", "soil"),
    }
    if set(sets) != expected or len(sets) != 7:
        raise ValueError("factorial process-set universe changed")
    seeds = tuple(int(x) for x in payload["seeds"])
    if seeds != (4201, 4202, 4203, 4204, 4205):
        raise ValueError("factorial seeds changed")
    if int(payload["n_cases"]) != 35:
        raise ValueError("factorial denominator changed")
    if payload["governance"].get("no_threshold_change_after_outcome") is not True:
        raise ValueError("post-outcome threshold changes are not prohibited")
    return payload


def process_set_label(processes: Sequence[str]) -> str:
    order = {"temperature": "T", "water": "W", "soil": "S"}
    return "+".join(order[p] for p in PROCESSES if p in set(processes))


def factorial_candidates(*, random_state: int = 0) -> dict[str, RecoveryCandidate]:
    base = {
        "temperature_quadratic": RecoveryCandidate(
            "temperature_quadratic", ("temperature",), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "temp_proxy_quadratic": RecoveryCandidate(
            "temp_proxy_quadratic", ("temp_proxy",), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "water_quadratic": RecoveryCandidate(
            "water_quadratic", ("water",), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "soil_quadratic": RecoveryCandidate(
            "soil_quadratic", ("soil",), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "temperature_water_quadratic": RecoveryCandidate(
            "temperature_water_quadratic", ("temperature", "water"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "temp_proxy_water_quadratic": RecoveryCandidate(
            "temp_proxy_water_quadratic", ("temp_proxy", "water"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "temperature_soil_quadratic": RecoveryCandidate(
            "temperature_soil_quadratic", ("temperature", "soil"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "temp_proxy_soil_quadratic": RecoveryCandidate(
            "temp_proxy_soil_quadratic", ("temp_proxy", "soil"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "water_soil_quadratic": RecoveryCandidate(
            "water_soil_quadratic", ("water", "soil"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "temperature_water_soil_quadratic": RecoveryCandidate(
            "temperature_water_soil_quadratic", ("temperature", "water", "soil"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "temp_proxy_water_soil_quadratic": RecoveryCandidate(
            "temp_proxy_water_soil_quadratic", ("temp_proxy", "water", "soil"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "broad_linear": RecoveryCandidate(
            "broad_linear",
            ("temperature", "water", "temp_proxy", "soil", "seasonality", "noise"),
            ModelSpec(C=1.0, degree=1, penalty="l2"),
        ),
    }
    return seed_recovery_candidates(base, random_state=int(random_state))


def simulate_factorial_process_niche(
    processes: Sequence[str],
    *,
    seed: int,
    n_cells: int,
    n_occurrences: int,
    n_target_group: int,
    sampling_bias_strength: float,
) -> KnownTruthSimulation:
    active = tuple(p for p in PROCESSES if p in set(str(x) for x in processes))
    if not active:
        raise ValueError("at least one ecological process must be active")
    unknown = sorted(set(processes) - set(PROCESSES))
    if unknown:
        raise ValueError(f"unknown processes: {unknown}")
    if n_occurrences >= n_cells or n_target_group >= n_cells:
        raise ValueError("sample sizes must be smaller than landscape size")

    rng, environment = _base_landscape(int(seed), int(n_cells))
    params = {
        "temperature": (0.55, 0.60),
        "water": (-0.35, 0.70),
        "soil": (0.20, 0.55),
    }
    log_truth = np.zeros(len(environment), dtype=float)
    for process in active:
        center, width = params[process]
        values = environment[process].to_numpy(float)
        log_truth += -0.5 * ((values - center) / width) ** 2
    log_truth -= float(np.nanmax(log_truth))
    true_suitability = np.exp(log_truth)

    axis = 0.65 * environment["longitude"].to_numpy(float) + 0.35 * environment["latitude"].to_numpy(float)
    axis_z = (axis - axis.mean()) / axis.std()
    sampling_effort = np.exp(float(sampling_bias_strength) * axis_z)
    sampling_effort /= sampling_effort.max()

    occurrence_prob = true_suitability * sampling_effort
    occurrence_prob /= occurrence_prob.sum()
    target_prob = sampling_effort / sampling_effort.sum()
    occurrence_idx = rng.choice(len(environment), size=int(n_occurrences), replace=False, p=occurrence_prob)
    target_idx = rng.choice(len(environment), size=int(n_target_group), replace=False, p=target_prob)

    environment = environment.copy()
    environment["true_suitability"] = true_suitability
    environment["sampling_effort"] = sampling_effort
    environment["scenario"] = f"factorial_{process_set_label(active)}"
    for process in PROCESSES:
        environment[f"truth_process_{process}"] = bool(process in active)

    occurrences = environment.iloc[np.sort(occurrence_idx)].copy().reset_index(drop=True)
    occurrences["species"] = f"simulated_factorial_{process_set_label(active)}"
    target_group = environment.iloc[np.sort(target_idx)].copy().reset_index(drop=True)
    target_group["species"] = "nonfocal_target_group"
    return KnownTruthSimulation(
        environment=environment,
        occurrences=occurrences,
        target_group=target_group,
        audit_predictors=("temperature", "water", "temp_proxy", "seasonality", "soil", "noise"),
    )


def evaluate_factorial_perturbations(
    processes: Sequence[str],
    seed: int,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    perturbations: Sequence[KnownTruthPerturbationSpec],
    n_cells: int,
    n_occurrences: int,
    n_target_group: int,
    n_spatial_blocks: int,
    inner_folds: int,
    outer_holdout_fraction: float,
    min_background: int,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
) -> KnownTruthPerturbationResult:
    frames = []
    label = process_set_label(processes)
    for spec in perturbations:
        if spec.is_domain_transfer:
            raise ValueError("factorial contract does not include domain-transfer perturbations")
        simulation = simulate_factorial_process_niche(
            processes,
            seed=int(seed),
            n_cells=int(n_cells),
            n_occurrences=int(n_occurrences),
            n_target_group=int(n_target_group),
            sampling_bias_strength=float(spec.sampling_bias_strength),
        )
        frame = _candidate_spatial_metrics(
            simulation,
            candidates,
            perturbation=spec.name,
            access_radius=float(spec.access_radius),
            n_spatial_blocks=int(n_spatial_blocks),
            inner_folds=int(inner_folds),
            random_state=int(seed),
            outer_holdout_fraction=float(outer_holdout_fraction),
            min_background=int(min_background),
            observation_correction=False,
            observation_weight_truncation_quantile=0.99,
            observation_signal_chance_auc=0.50,
            observation_signal_minimum_auc_margin=0.01,
            observation_signal_auc_sem_multiplier=1.0,
        )
        frame["process_set"] = label
        frame["seed"] = int(seed)
        frame["sampling_bias_strength"] = float(spec.sampling_bias_strength)
        frames.append(frame)
    metrics = pd.concat(frames, ignore_index=True)
    try:
        selection = select_perturbation_robust_niche_recovery_protocol(
            metrics,
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
        )
        error = None
    except ValueError as exc:
        selection = None
        error = str(exc)
    return KnownTruthPerturbationResult(metrics, selection, error)


def _candidate_processes(candidate: RecoveryCandidate) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(DEFAULT_PROCESS_ALIASES.get(str(p), str(p)))
                for p in candidate.predictors
                if p not in candidate.observation_predictors
            }
        )
    )


def _profile_selected_candidate(
    simulation: KnownTruthSimulation,
    candidate: RecoveryCandidate,
    model_occurrence: pd.DataFrame,
    background: pd.DataFrame,
    true_processes: Sequence[str],
) -> dict[str, float | int]:
    model = fit_relative_suitability_model(
        model_occurrence,
        background,
        candidate.predictors,
        model_spec=candidate.model_spec,
    )
    ecological = score_ecological_suitability(
        model,
        simulation.environment,
        candidate.predictors,
        observation_predictors=candidate.observation_predictors,
        observation_reference=background,
    )
    truth = simulation.environment[simulation.true_suitability_column].to_numpy(float)
    niche = known_truth_niche_recovery_profile(
        simulation.environment,
        ecological,
        truth,
        simulation.audit_predictors,
    )
    response = known_truth_response_profile(
        simulation.environment,
        ecological,
        truth,
        tuple(true_processes),
    )
    process = known_truth_process_profile(
        tuple(p for p in candidate.predictors if p not in candidate.observation_predictors),
        tuple(true_processes),
    )
    return {**niche.as_dict(), **response.as_dict(), **process.as_dict()}


def _process_metrics(selected: Sequence[str], truth: Sequence[str]) -> dict[str, float | bool]:
    s = set(selected)
    t = set(truth)
    tp = len(s & t)
    precision = tp / len(s) if s else 0.0
    recall = tp / len(t) if t else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "exact": bool(s == t),
    }


def run_experiment(output_dir: str | Path, *, contract_path: str | Path = CONTRACT_PATH) -> dict[str, object]:
    contract = load_contract(contract_path)
    sim_cfg = contract["simulation"]
    candidates = factorial_candidates(random_state=0)
    expected_candidates = set(contract["candidate_library"])
    if set(candidates) != expected_candidates:
        raise ValueError("factorial candidate library changed after contract freeze")
    perturbations = tuple(KnownTruthPerturbationSpec(**row) for row in contract["perturbations"])

    case_rows: list[dict[str, object]] = []
    selector_truth_rows: list[dict[str, object]] = []
    metric_frames: list[pd.DataFrame] = []

    for process_row in contract["process_sets"]:
        truth_processes = tuple(str(x) for x in process_row)
        label = process_set_label(truth_processes)
        for seed in tuple(int(x) for x in contract["seeds"]):
            result = evaluate_factorial_perturbations(
                truth_processes,
                seed,
                candidates,
                perturbations=perturbations,
                n_cells=int(sim_cfg["n_cells"]),
                n_occurrences=int(sim_cfg["n_occurrences"]),
                n_target_group=int(sim_cfg["n_target_group"]),
                n_spatial_blocks=int(sim_cfg["n_spatial_blocks"]),
                inner_folds=int(sim_cfg["inner_folds"]),
                outer_holdout_fraction=float(sim_cfg["outer_holdout_fraction"]),
                min_background=int(sim_cfg["minimum_background"]),
            )
            metrics = result.fold_metrics.assign(process_set=label, seed=seed)
            metric_frames.append(metrics)
            canonical = metrics.loc[metrics["perturbation"].astype(str).eq("sampling_standard")].copy()
            auc_name = _metric_winner(canonical, "presence_rank", ascending=False)
            canonical_name = select_generalization_gated_niche_recovery_protocol(canonical).candidate
            robust_name = result.selection.candidate if result.selection is not None else None

            certificate = build_ecological_inference_certificate(
                canonical_name,
                robust_name,
                candidates,
                process_groups=DEFAULT_PROCESS_ALIASES,
            )
            stable = tuple(certificate.stable_process_core)
            stable_metrics = _process_metrics(stable, truth_processes)
            canonical_processes = _candidate_processes(candidates[canonical_name])
            canonical_metrics = _process_metrics(canonical_processes, truth_processes)
            auc_processes = _candidate_processes(candidates[auc_name])
            auc_metrics = _process_metrics(auc_processes, truth_processes)
            robust_processes: tuple[str, ...] = ()
            robust_metrics = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "exact": False}
            if robust_name is not None:
                robust_processes = _candidate_processes(candidates[robust_name])
                robust_metrics = _process_metrics(robust_processes, truth_processes)

            case_rows.append(
                {
                    "process_set": label,
                    "seed": seed,
                    "true_processes": ",".join(truth_processes),
                    "canonical_candidate": canonical_name,
                    "robust_candidate": robust_name or "",
                    "auc_candidate": auc_name,
                    "canonical_processes": ",".join(canonical_processes),
                    "robust_processes": ",".join(robust_processes),
                    "auc_processes": ",".join(auc_processes),
                    "stable_process_core": ",".join(stable),
                    "contested_processes": ",".join(certificate.contested_processes),
                    "robust_available": robust_name is not None,
                    "model_consensus": certificate.model_consensus,
                    "process_set_consensus": certificate.process_set_consensus,
                    "stable_precision": stable_metrics["precision"],
                    "stable_recall": stable_metrics["recall"],
                    "stable_f1": stable_metrics["f1"],
                    "stable_exact": stable_metrics["exact"],
                    "canonical_exact": canonical_metrics["exact"],
                    "robust_exact": robust_metrics["exact"],
                    "auc_exact": auc_metrics["exact"],
                    "selection_error": result.selection_error or "",
                }
            )

            simulation = simulate_factorial_process_niche(
                truth_processes,
                seed=seed,
                n_cells=int(sim_cfg["n_cells"]),
                n_occurrences=int(sim_cfg["n_occurrences"]),
                n_target_group=int(sim_cfg["n_target_group"]),
                sampling_bias_strength=float(sim_cfg["sampling_bias_strength_canonical"]),
            )
            model_occurrence, background = _canonical_model_pool(
                simulation,
                access_radius=0.35,
                n_spatial_blocks=int(sim_cfg["n_spatial_blocks"]),
                random_state=seed,
                outer_holdout_fraction=float(sim_cfg["outer_holdout_fraction"]),
                min_background=int(sim_cfg["minimum_background"]),
            )
            selected = {
                AUC_SELECTOR: auc_name,
                CANONICAL_SELECTOR: canonical_name,
            }
            if robust_name is not None:
                selected[ROBUST_SELECTOR] = robust_name
            for selector, candidate_name in selected.items():
                selector_truth_rows.append(
                    {
                        "process_set": label,
                        "seed": seed,
                        "selector": selector,
                        "candidate": candidate_name,
                        "true_processes": ",".join(truth_processes),
                        "selected_processes": ",".join(_candidate_processes(candidates[candidate_name])),
                        **_profile_selected_candidate(
                            simulation,
                            candidates[candidate_name],
                            model_occurrence,
                            background,
                            truth_processes,
                        ),
                    }
                )

    cases = pd.DataFrame(case_rows)
    selector_truth = pd.DataFrame(selector_truth_rows)
    fold_metrics = pd.concat(metric_frames, ignore_index=True)
    if len(cases) != int(contract["n_cases"]):
        raise ValueError("factorial case denominator incomplete")

    process_rows = []
    for process in PROCESSES:
        truth = cases["true_processes"].map(lambda x: process in set(str(x).split(",")))
        stable = cases["stable_process_core"].map(
            lambda x: process in set(str(x).split(",")) if str(x) else False
        )
        auc = cases["auc_processes"].map(
            lambda x: process in set(str(x).split(",")) if str(x) else False
        )
        tp = int((truth & stable).sum())
        fn = int((truth & ~stable).sum())
        tn = int((~truth & ~stable).sum())
        fp = int((~truth & stable).sum())
        auc_tp = int((truth & auc).sum())
        auc_fn = int((truth & ~auc).sum())
        auc_tn = int((~truth & ~auc).sum())
        auc_fp = int((~truth & auc).sum())
        process_rows.append(
            {
                "process": process,
                "truth_present_n": int(truth.sum()),
                "truth_absent_n": int((~truth).sum()),
                "stable_tp": tp,
                "stable_fn": fn,
                "stable_tn": tn,
                "stable_fp": fp,
                "stable_sensitivity": tp / (tp + fn),
                "stable_specificity": tn / (tn + fp),
                "auc_sensitivity": auc_tp / (auc_tp + auc_fn),
                "auc_specificity": auc_tn / (auc_tn + auc_fp),
            }
        )
    process_summary = pd.DataFrame(process_rows)

    set_summary = (
        cases.groupby("process_set", as_index=False)
        .agg(
            n=("seed", "size"),
            robust_available=("robust_available", "mean"),
            stable_exact=("stable_exact", "mean"),
            canonical_exact=("canonical_exact", "mean"),
            robust_exact=("robust_exact", "mean"),
            auc_exact=("auc_exact", "mean"),
            model_consensus=("model_consensus", "mean"),
            process_set_consensus=("process_set_consensus", "mean"),
        )
    )

    robust_coverage = float(cases["robust_available"].mean())
    stable_exact_rate = float(cases["stable_exact"].mean())
    auc_exact_rate = float(cases["auc_exact"].mean())
    disagreement = cases.loc[~cases["model_consensus"].astype(bool)]
    exact_when_disagree = float(disagreement["stable_exact"].mean()) if len(disagreement) else float("nan")

    gate = contract["support_gate"]
    process_gate = bool(
        (process_summary["stable_sensitivity"] >= float(gate["per_process_sensitivity_min"])).all()
        and (process_summary["stable_specificity"] >= float(gate["per_process_specificity_min"])).all()
    )
    supported = bool(
        robust_coverage >= float(gate["robust_selector_coverage_min"])
        and stable_exact_rate >= float(gate["stable_exact_process_set_recovery_min"])
        and process_gate
    )
    comparison_delta = stable_exact_rate - auc_exact_rate
    comparison_supported = bool(
        comparison_delta >= float(contract["comparison_gate"]["stable_minus_auc_exact_recovery_min"])
    )
    decision = {
        "purpose": "product_a_factorial_process_recovery_decision",
        "supported": supported,
        "robust_selector_coverage": robust_coverage,
        "stable_exact_process_set_recovery": stable_exact_rate,
        "auc_exact_process_set_recovery": auc_exact_rate,
        "stable_minus_auc_exact_recovery": comparison_delta,
        "comparison_gate_supported": comparison_supported,
        "model_disagreement_n": int(len(disagreement)),
        "stable_exact_when_models_disagree": exact_when_disagree,
        "process_summary": process_summary.to_dict(orient="records"),
        "thresholds_frozen_before_outcome": True,
        "existing_v2_8_4_empirical_endpoint_unchanged": True,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases.to_csv(out / "factorial_case_results.csv", index=False)
    process_summary.to_csv(out / "factorial_process_summary.csv", index=False)
    set_summary.to_csv(out / "factorial_process_set_summary.csv", index=False)
    selector_truth.to_csv(out / "factorial_selector_truth.csv", index=False)
    fold_metrics.to_csv(out / "factorial_fold_metrics.csv", index=False)
    (out / "factorial_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract", default=str(CONTRACT_PATH))
    args = parser.parse_args(argv)
    decision = run_experiment(args.output_dir, contract_path=args.contract)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
