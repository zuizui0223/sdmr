import numpy as np
import pandas as pd
import pytest

from sdmr.process_exclusion_certificate import (
    apply_discovery_interval_calibration,
    build_complete_refit_envelope,
    calibrate_discovery_interval_expansion,
    classify_validation_process_exclusion,
    freeze_process_knockout_registry,
    knockout_candidate_label,
    summarize_knockout_discovery_evidence,
)


ALIASES = {
    "temperature": "temperature",
    "temp_proxy": "temperature",
    "water": "water",
    "soil": "soil",
    "recording_bias": "observation_process",
}


def _registry():
    return freeze_process_knockout_registry(
        base_candidates=("base_a", "base_b"),
        ecological_predictors=("temperature", "temp_proxy", "water", "soil"),
        process_aliases=ALIASES,
        process_universe=("temperature", "water", "soil"),
        observation_predictors=("recording_bias",),
    )


def _discovery_metrics(registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for candidate in registry["candidate"]:
        process = candidate.rsplit("::exclude::", 1)[1]
        base = candidate.split("::exclude::", 1)[0]
        for species in ("sp1", "sp2"):
            for perturbation in ("m1", "m2"):
                for fold in (0, 1):
                    if (
                        process == "temperature"
                        and base == "base_b"
                        and species == "sp2"
                        and perturbation == "m2"
                        and fold == 1
                    ):
                        continue
                    rank = 0.70 if process == "temperature" else 0.50
                    rows.append(
                        {
                            "candidate": candidate,
                            "species": species,
                            "perturbation": perturbation,
                            "fold": fold,
                            "presence_rank": rank,
                        }
                    )
    return pd.DataFrame(rows)


def test_registry_is_complete_and_removes_every_frozen_proxy():
    registry = _registry()

    assert len(registry) == 2 * 3
    assert registry["candidate"].nunique() == len(registry)
    temperature = registry.loc[
        registry["candidate"].eq(
            knockout_candidate_label("base_a", "temperature")
        )
    ].iloc[0]
    assert temperature["excluded_predictors"] == "temperature,temp_proxy"
    assert temperature["retained_ecological_predictors"] == "water,soil"
    assert temperature["observation_predictors"] == "recording_bias"


def test_registry_fails_closed_on_unassigned_or_observational_predictors():
    with pytest.raises(KeyError, match="missing frozen process aliases"):
        freeze_process_knockout_registry(
            base_candidates=("base",),
            ecological_predictors=("temperature", "unknown"),
            process_aliases=ALIASES,
            process_universe=("temperature",),
        )

    with pytest.raises(ValueError, match="observation predictors must map"):
        freeze_process_knockout_registry(
            base_candidates=("base",),
            ecological_predictors=("temperature", "water"),
            process_aliases={
                "temperature": "temperature",
                "water": "water",
                "recording_bias": "temperature",
            },
            process_universe=("temperature", "water"),
            observation_predictors=("recording_bias",),
        )


def test_discovery_gate_separates_witness_required_and_missing_evidence():
    registry = _registry()
    result = summarize_knockout_discovery_evidence(
        _discovery_metrics(registry),
        registry,
        discovery_taxa=("sp1", "sp2"),
        perturbations=("m1", "m2"),
        expected_outer_folds=2,
    )
    process = result.process_summary.set_index("process")
    candidates = result.candidate_summary.set_index("candidate")

    assert (
        process.loc["temperature", "discovery_process_state"]
        == "exclusion_witness_frozen"
    )
    assert int(process.loc["temperature", "n_admitted_knockout_routes"]) == 1
    assert not bool(
        candidates.loc[
            knockout_candidate_label("base_b", "temperature"),
            "complete_outer_evidence",
        ]
    )

    for name in ("water", "soil"):
        assert (
            process.loc[name, "discovery_process_state"]
            == "required_by_frozen_discovery_contract"
        )
        assert bool(process.loc[name, "all_declared_routes_complete"])
        assert int(process.loc[name, "n_admitted_knockout_routes"]) == 0


def test_validation_status_never_turns_incomplete_transfer_into_requirement():
    registry = _registry()
    discovery = summarize_knockout_discovery_evidence(
        _discovery_metrics(registry),
        registry,
        discovery_taxa=("sp1", "sp2"),
        perturbations=("m1", "m2"),
        expected_outer_folds=2,
    )
    witness = knockout_candidate_label("base_a", "temperature")
    fits = pd.DataFrame(
        [
            {
                "candidate": witness,
                "species": "val1",
                "perturbation": "m1",
                "fit_status": "success",
            },
            {
                "candidate": witness,
                "species": "val1",
                "perturbation": "m2",
                "fit_status": "success",
            },
            {
                "candidate": witness,
                "species": "val2",
                "perturbation": "m1",
                "fit_status": "success",
            },
            {
                "candidate": witness,
                "species": "val2",
                "perturbation": "m2",
                "fit_status": "abstain_member_fit",
            },
        ]
    )
    status = classify_validation_process_exclusion(
        discovery,
        fits,
        validation_taxa=("val1", "val2"),
        perturbations=("m1", "m2"),
    ).set_index(["species", "process"])

    assert status.loc[("val1", "temperature"), "process_status"] == (
        "refuted_as_necessary"
    )
    assert status.loc[("val2", "temperature"), "process_status"] == "unresolved"
    assert status.loc[("val1", "water"), "process_status"] == (
        "required_by_frozen_evidence_contract"
    )


def _response_rows():
    return pd.DataFrame(
        [
            {
                "species": "sp1",
                "member_id": "member_1",
                "predictor": "temperature",
                "quantity": "optimum",
                "estimate": 1.0,
                "environment_span": 10.0,
            },
            {
                "species": "sp1",
                "member_id": "member_2",
                "predictor": "temperature",
                "quantity": "optimum",
                "estimate": 3.0,
                "environment_span": 10.0,
            },
            {
                "species": "sp1",
                "member_id": "member_1",
                "predictor": "temperature",
                "quantity": "lower_limit",
                "estimate": -2.0,
                "environment_span": 10.0,
            },
            {
                "species": "sp1",
                "member_id": "member_2",
                "predictor": "temperature",
                "quantity": "lower_limit",
                "estimate": -1.0,
                "environment_span": 10.0,
            },
        ]
    )


def test_refit_envelope_requires_every_predeclared_member():
    expected_members = pd.DataFrame(
        {
            "species": ["sp1", "sp1"],
            "member_id": ["member_1", "member_2"],
        }
    )
    expected_keys = pd.DataFrame(
        {
            "species": ["sp1", "sp1"],
            "predictor": ["temperature", "temperature"],
            "quantity": ["optimum", "lower_limit"],
        }
    )
    complete = build_complete_refit_envelope(
        _response_rows(),
        expected_members,
        expected_response_keys=expected_keys,
    ).set_index("quantity")

    assert complete.loc["optimum", "interval_status"] == "complete"
    assert complete.loc["optimum", "lower_bound"] == 1.0
    assert complete.loc["optimum", "upper_bound"] == 3.0
    assert complete.loc["optimum", "normalized_width"] == pytest.approx(0.2)

    incomplete_rows = _response_rows().loc[
        lambda frame: ~(
            frame["member_id"].eq("member_2")
            & frame["quantity"].eq("lower_limit")
        )
    ]
    incomplete = build_complete_refit_envelope(
        incomplete_rows,
        expected_members,
        expected_response_keys=expected_keys,
    ).set_index("quantity")
    assert (
        incomplete.loc["lower_limit", "interval_status"]
        == "unavailable_incomplete_refits"
    )
    assert incomplete.loc["lower_limit", "missing_member_ids"] == "member_2"
    assert np.isnan(incomplete.loc["lower_limit", "lower_bound"])


def test_discovery_only_calibration_expands_by_maximum_normalized_miss():
    envelopes = pd.DataFrame(
        [
            {
                "species": "d1",
                "predictor": "temperature",
                "quantity": "optimum",
                "interval_status": "complete",
                "lower_bound": 0.0,
                "upper_bound": 2.0,
                "environment_span": 10.0,
            },
            {
                "species": "d2",
                "predictor": "temperature",
                "quantity": "optimum",
                "interval_status": "complete",
                "lower_bound": 1.0,
                "upper_bound": 2.0,
                "environment_span": 10.0,
            },
        ]
    )
    truth = pd.DataFrame(
        [
            {
                "species": "d1",
                "predictor": "temperature",
                "quantity": "optimum",
                "estimate": 1.5,
            },
            {
                "species": "d2",
                "predictor": "temperature",
                "quantity": "optimum",
                "estimate": 4.0,
            },
        ]
    )
    calibration, audit = calibrate_discovery_interval_expansion(envelopes, truth)
    row = calibration.iloc[0]

    assert row["normalized_expansion_radius"] == pytest.approx(0.2)
    assert not bool(row["calibration_uses_validation_truth"])
    assert audit["raw_interval_covers_truth"].tolist() == [True, False]

    validation = pd.DataFrame(
        [
            {
                "species": "v1",
                "predictor": "temperature",
                "quantity": "optimum",
                "interval_status": "complete",
                "lower_bound": -1.0,
                "upper_bound": 1.0,
                "environment_span": 5.0,
            }
        ]
    )
    expanded = apply_discovery_interval_calibration(validation, calibration).iloc[0]
    assert expanded["calibrated_lower_bound"] == pytest.approx(-2.0)
    assert expanded["calibrated_upper_bound"] == pytest.approx(2.0)
    assert expanded["calibrated_normalized_width"] == pytest.approx(0.8)
    assert not bool(expanded["calibration_uses_validation_truth"])


def test_validation_truth_calibration_is_rejected():
    raw = pd.DataFrame(
        [
            {
                "species": "v1",
                "predictor": "temperature",
                "quantity": "optimum",
                "interval_status": "complete",
                "lower_bound": 0.0,
                "upper_bound": 1.0,
                "environment_span": 2.0,
            }
        ]
    )
    calibration = pd.DataFrame(
        [
            {
                "predictor": "temperature",
                "quantity": "optimum",
                "calibration_status": "complete",
                "normalized_expansion_radius": 0.1,
                "calibration_uses_validation_truth": True,
            }
        ]
    )
    with pytest.raises(ValueError, match="validation-truth calibration is forbidden"):
        apply_discovery_interval_calibration(raw, calibration)
