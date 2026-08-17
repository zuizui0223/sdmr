import numpy as np
import pandas as pd

from sdmr.candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from sdmr.known_truth import KnownTruthSimulation
from sdmr.v2_1_known_truth_gate_ablation import (
    _add_structured_sparse_predictors,
    _available_candidates,
    _decision_ledger,
    _nested_background_perturbations,
    _procedure_library,
)


def _frame(n=100):
    x = np.linspace(-2.0, 2.0, n)
    return pd.DataFrame(
        {
            "longitude": x,
            "latitude": np.sin(x),
            "temperature": 0.4 * x,
            "water": -0.3 * x,
            "temp_proxy": 0.38 * x,
            "seasonality": np.cos(x),
            "soil": np.sin(2 * x),
            "noise": np.linspace(1.0, -1.0, n),
            "recording_bias": np.cos(2 * x),
            "true_suitability": np.exp(-(x**2)),
            "sampling_effort": np.ones(n),
        }
    )


def test_structured_sparse_predictors_are_deterministic_and_fail_095_coverage():
    first = _add_structured_sparse_predictors(_frame())
    second = _add_structured_sparse_predictors(_frame())
    pd.testing.assert_series_equal(first["sparse_temp_proxy"], second["sparse_temp_proxy"])
    pd.testing.assert_series_equal(first["sparse_noise"], second["sparse_noise"])
    assert first["sparse_temp_proxy"].notna().mean() < 0.95
    assert first["sparse_noise"].notna().mean() < 0.95
    assert first["temperature"].notna().all()


def test_background_perturbations_are_nested_and_canonical_is_intermediate():
    environment = _frame(140)
    occurrence = environment.iloc[50:70].copy().reset_index(drop=True)
    occurrence["species"] = "simulated"
    background = environment.copy().reset_index(drop=True)
    background["species"] = "target"
    simulation = KnownTruthSimulation(
        environment=environment,
        occurrences=occurrence,
        target_group=background,
        audit_predictors=("temperature", "water"),
    )
    perturbations = _nested_background_perturbations(simulation)
    assert list(perturbations) == ["m_core", "m_mid", "m_wide"]
    assert len(perturbations["m_core"]) < len(perturbations["m_mid"])
    assert len(perturbations["m_mid"]) < len(perturbations["m_wide"])


def test_available_gate_keeps_one_fold_but_complete_gate_rejects_it():
    rows = []
    for species in ("d1", "d2"):
        for perturbation in ("m_core", "m_mid", "m_wide"):
            rows.append(
                {
                    "candidate": "one_fold",
                    "species": species,
                    "perturbation": perturbation,
                    "fold": 0,
                    "presence_rank": 0.7,
                    "niche_overlap_schoener_d_pc12": 0.6,
                    "centroid_distance": 0.2,
                    "breadth_log_sd_error": 0.2,
                    "quantile_profile_error": 0.2,
                }
            )
    metrics = pd.DataFrame(rows)
    available, _ = _available_candidates(
        metrics,
        taxa=("d1", "d2"),
        perturbations=("m_core", "m_mid", "m_wide"),
        required_columns=("presence_rank",),
    )
    assert available == ("one_fold",)
    complete = require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=("d1", "d2"),
        perturbations=("m_core", "m_mid", "m_wide"),
        required_columns=("presence_rank",),
        expected_outer_folds=2,
    )
    assert complete.eligible_candidates == ()


def test_decision_support_requires_complete_validation_and_ecology_not_worse_than_auc():
    selectors = pd.DataFrame(
        [
            {
                "regime": regime,
                "selector": selector,
                "candidate": "p",
                "status": "selected",
                "n_evidence_eligible_candidates": (
                    0 if regime == "raw_complete" else 2
                ),
            }
            for regime in ("raw_complete", "coverage_complete")
            for selector in ("canonical_auc", "canonical_ecology", "robust_ecology")
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "regime": "coverage_complete",
                "selector": "canonical_auc",
                "n_truth_evaluable": 3,
                "mean_truth_worst_rank": 2.0,
                "mean_truth_mean_rank": 2.0,
            },
            {
                "regime": "coverage_complete",
                "selector": "canonical_ecology",
                "n_truth_evaluable": 3,
                "mean_truth_worst_rank": 1.5,
                "mean_truth_mean_rank": 1.5,
            },
            {
                "regime": "coverage_complete",
                "selector": "robust_ecology",
                "n_truth_evaluable": 3,
                "mean_truth_worst_rank": 2.5,
                "mean_truth_mean_rank": 2.5,
            },
        ]
    )
    decision = _decision_ledger(selectors, summary, n_validation_taxa=3)
    assert decision.loc[0, "decision"] == "supported"
    assert bool(decision.loc[0, "evidence_restored_or_preserved"])
    assert not bool(decision.loc[0, "scientific_promotion_allowed"])


def test_procedure_library_is_small_predeclared_and_observation_aware():
    procedures = _procedure_library(inner_folds=2, max_predictors=4)
    assert len(procedures) == 8
    assert {p.strategy for p in procedures} == {
        "all",
        "vif",
        "predictive_forward",
        "niche_forward",
    }
    assert all(p.observation_predictors == ("recording_bias",) for p in procedures)
