import numpy as np
import pandas as pd
import pytest

from sdmr.ecological_certificate import (
    audit_certificate_against_truth,
    audit_point_response_against_truth,
    build_ecological_certificate,
    response_point_estimates,
    select_ecological_candidate_sets,
)


def _candidate_metrics():
    rows = []
    for candidate in ("candidate_a", "candidate_b", "candidate_incomplete"):
        for species in ("sp1", "sp2"):
            for perturbation in ("m1", "m2"):
                for fold in (0, 1):
                    if (
                        candidate == "candidate_incomplete"
                        and species == "sp2"
                        and perturbation == "m2"
                        and fold == 1
                    ):
                        continue
                    if candidate == "candidate_a":
                        recovery = (0.90, 0.20, 0.20, 0.20)
                    elif candidate == "candidate_b":
                        recovery = (0.80, 0.10, 0.10, 0.10)
                    else:
                        recovery = (0.50, 0.50, 0.50, 0.50)
                    rows.append(
                        {
                            "candidate": candidate,
                            "species": species,
                            "perturbation": perturbation,
                            "fold": fold,
                            "presence_rank": 0.70,
                            "continuous_boyce": 0.50,
                            "or10": 0.10,
                            "n_predictors": 2,
                            "niche_overlap_schoener_d_pc12": recovery[0],
                            "centroid_distance": recovery[1],
                            "breadth_log_sd_error": recovery[2],
                            "quantile_profile_error": recovery[3],
                        }
                    )
    return pd.DataFrame(rows)


def _member_response():
    return pd.DataFrame(
        [
            {"member_id": "m1", "predictor": "temperature", "quantity": "optimum", "estimate": 1.0, "environment_span": 5.0},
            {"member_id": "m1", "predictor": "temperature", "quantity": "lower_limit", "estimate": 0.0, "environment_span": 5.0},
            {"member_id": "m1", "predictor": "temperature", "quantity": "upper_limit", "estimate": 3.0, "environment_span": 5.0},
            {"member_id": "m2", "predictor": "temperature", "quantity": "optimum", "estimate": 2.0, "environment_span": 5.0},
            {"member_id": "m2", "predictor": "temperature", "quantity": "lower_limit", "estimate": 0.5, "environment_span": 5.0},
            {"member_id": "m2", "predictor": "temperature", "quantity": "upper_limit", "estimate": 4.0, "environment_span": 5.0},
        ]
    )


def _truth_response():
    return pd.DataFrame(
        [
            {"member_id": "truth", "predictor": "temperature", "quantity": "optimum", "estimate": 1.5, "environment_span": 5.0},
            {"member_id": "truth", "predictor": "temperature", "quantity": "lower_limit", "estimate": 0.25, "environment_span": 5.0},
            {"member_id": "truth", "predictor": "temperature", "quantity": "upper_limit", "estimate": 3.5, "environment_span": 5.0},
        ]
    )


def test_candidate_set_retains_complete_adequate_recovery_pareto_front():
    result = select_ecological_candidate_sets(
        _candidate_metrics(),
        discovery_taxa=("sp1", "sp2"),
        perturbations=("m1", "m2"),
        expected_outer_folds=2,
    )

    assert result.complete_candidates == ("candidate_a", "candidate_b")
    assert result.adequate_candidates == ("candidate_a", "candidate_b")
    assert result.ecological_pareto_candidates == (
        "candidate_a",
        "candidate_b",
    )


def test_certificate_uses_exact_intersection_and_union_semantics():
    certificate = build_ecological_certificate(
        {
            "m1": ("temperature", "water"),
            "m2": ("temperature", "soil"),
        },
        _member_response(),
        process_universe=("temperature", "water", "soil", "seasonality"),
    )

    assert certificate.necessary_processes == ("temperature",)
    assert certificate.possible_processes == ("soil", "temperature", "water")
    assert certificate.contested_processes == ("soil", "water")
    assert certificate.unsupported_processes == ("seasonality",)
    optimum = certificate.boundary_intervals.loc[
        certificate.boundary_intervals["quantity"].eq("optimum")
    ].iloc[0]
    assert optimum["lower_bound"] == 1.0
    assert optimum["upper_bound"] == 2.0
    assert optimum["normalized_width"] == pytest.approx(0.2)


def test_certificate_truth_audit_reports_coverage_and_false_core():
    certificate = build_ecological_certificate(
        {
            "m1": ("temperature", "water"),
            "m2": ("temperature", "soil"),
        },
        _member_response(),
        process_universe=("temperature", "water", "soil", "seasonality"),
    )
    summary, boundary = audit_certificate_against_truth(
        certificate,
        true_processes=("temperature", "water"),
        truth_response_estimates=_truth_response(),
    )

    assert summary["n_false_necessary_processes"] == 0
    assert summary["possible_process_recall"] == 1.0
    assert summary["possible_process_precision"] == pytest.approx(2 / 3)
    assert summary["boundary_coverage_fraction"] == 1.0
    assert boundary["covered"].all()


def test_point_response_audit_is_normalized_by_environmental_span():
    point = _member_response().loc[lambda frame: frame["member_id"].eq("m1")]
    summary, audit = audit_point_response_against_truth(point, _truth_response())

    assert summary["n_point_boundaries_evaluable"] == 3
    expected_errors = np.array([0.10, 0.05, 0.10])
    assert summary["mean_normalized_absolute_error"] == pytest.approx(
        expected_errors.mean()
    )
    assert np.allclose(
        np.sort(audit["normalized_absolute_error"].to_numpy(float)),
        np.sort(expected_errors),
    )


def test_response_point_estimates_return_all_three_quantities():
    environment = pd.DataFrame({"temperature": np.linspace(-2, 2, 101)})
    suitability = np.exp(-0.5 * ((environment["temperature"] - 0.5) / 0.4) ** 2)
    result = response_point_estimates(
        environment,
        suitability,
        ("temperature",),
        member_id="member",
    )

    assert set(result["quantity"]) == {"optimum", "lower_limit", "upper_limit"}
    assert result["estimate"].notna().all()


def test_empty_certificate_is_explicitly_unavailable():
    with pytest.raises(ValueError, match="at least one retained member"):
        build_ecological_certificate(
            {},
            pd.DataFrame(
                columns=(
                    "member_id",
                    "predictor",
                    "quantity",
                    "estimate",
                    "environment_span",
                )
            ),
            process_universe=("temperature",),
        )
