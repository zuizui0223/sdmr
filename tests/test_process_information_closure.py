import pandas as pd
import pytest

from sdmr.process_information_closure import (
    build_process_stability_certificate,
    classify_process_necessity,
    freeze_process_information_knockout_registry,
    normalize_process_information_registry,
    process_information_closure,
    summarize_process_information_closures,
)


def _registry() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"predictor": "bio1", "process": "thermal", "role": "direct"},
            {"predictor": "gdd5", "process": "thermal", "role": "derived"},
            {"predictor": "elevation", "process": "thermal", "role": "proxy"},
            {"predictor": "pet", "process": "thermal", "role": "composite"},
            {"predictor": "bio12", "process": "water", "role": "direct"},
            {"predictor": "cmi", "process": "water", "role": "derived"},
            {"predictor": "pet", "process": "water", "role": "composite"},
            {"predictor": "soil_n", "process": "soil", "role": "direct"},
        ]
    )


def test_many_to_many_closure_includes_composite_and_proxy() -> None:
    registry = _registry()

    assert process_information_closure(registry, "thermal") == (
        "bio1",
        "gdd5",
        "elevation",
        "pet",
    )
    assert process_information_closure(registry, "water") == (
        "bio12",
        "cmi",
        "pet",
    )

    summary = summarize_process_information_closures(
        registry,
        process_universe=("thermal", "water", "soil"),
    ).set_index("process")
    assert summary.loc["thermal", "proxy_predictors"] == "elevation"
    assert summary.loc["water", "composite_predictors"] == "pet"
    assert summary.loc["water", "n_closure_predictors"] == 3


def test_closure_aware_knockout_removes_shared_composite_from_both_processes() -> None:
    ecological = ("bio1", "gdd5", "elevation", "pet", "bio12", "cmi", "soil_n")
    frozen = freeze_process_information_knockout_registry(
        base_candidates=("glm", "gam"),
        ecological_predictors=ecological,
        process_registry=_registry(),
        process_universe=("thermal", "water", "soil"),
        observation_predictors=("recording_bias",),
    )

    thermal = frozen.loc[
        (frozen["base_candidate"] == "glm")
        & (frozen["excluded_process"] == "thermal")
    ].iloc[0]
    water = frozen.loc[
        (frozen["base_candidate"] == "glm")
        & (frozen["excluded_process"] == "water")
    ].iloc[0]

    assert set(thermal["excluded_predictors"].split(",")) == {
        "bio1",
        "gdd5",
        "elevation",
        "pet",
    }
    assert set(water["excluded_predictors"].split(",")) == {
        "bio12",
        "cmi",
        "pet",
    }
    assert "pet" not in thermal["retained_ecological_predictors"].split(",")
    assert "pet" not in water["retained_ecological_predictors"].split(",")
    assert thermal["observation_predictors"] == "recording_bias"
    assert len(frozen) == 6


def test_registry_fails_closed_for_unknown_role_and_uncovered_predictor() -> None:
    bad = _registry().copy()
    bad.loc[0, "role"] = "mystery"
    with pytest.raises(ValueError, match="unknown roles"):
        normalize_process_information_registry(bad)

    with pytest.raises(ValueError, match="requires at least one process-information link"):
        normalize_process_information_registry(
            _registry(),
            predictor_universe=(
                "bio1",
                "gdd5",
                "elevation",
                "pet",
                "bio12",
                "cmi",
                "soil_n",
                "unregistered_predictor",
            ),
        )


def test_necessity_states_are_refuted_required_or_unresolved() -> None:
    ecological = ("bio1", "gdd5", "elevation", "pet", "bio12", "cmi", "soil_n")
    frozen = freeze_process_information_knockout_registry(
        base_candidates=("glm", "gam"),
        ecological_predictors=ecological,
        process_registry=_registry(),
        process_universe=("thermal", "water", "soil"),
    )

    rows = []
    for row in frozen.itertuples(index=False):
        for context in ("split_a", "split_b"):
            complete = True
            adequate = False
            if row.excluded_process == "water" and row.base_candidate == "glm":
                adequate = True
            if row.excluded_process == "soil" and row.base_candidate == "gam" and context == "split_b":
                complete = False
            rows.append(
                {
                    "candidate": row.candidate,
                    "context": context,
                    "complete": complete,
                    "adequate": adequate,
                }
            )

    result = classify_process_necessity(
        pd.DataFrame(rows),
        frozen,
        expected_contexts=("split_a", "split_b"),
    ).set_index("process")

    assert result.loc["water", "status"] == "refuted_as_necessary"
    assert result.loc["thermal", "status"] == "required_by_evidence_contract"
    assert result.loc["soil", "status"] == "unresolved"
    assert result.loc["water", "n_adequate_witness_routes"] == 1
    assert result.loc["soil", "n_complete_routes"] == 1


def test_duplicate_context_is_not_treated_as_complete_evidence() -> None:
    ecological = ("bio1", "gdd5", "elevation", "pet", "bio12", "cmi", "soil_n")
    frozen = freeze_process_information_knockout_registry(
        base_candidates=("glm",),
        ecological_predictors=ecological,
        process_registry=_registry(),
        process_universe=("thermal", "water", "soil"),
    )
    water_candidate = frozen.loc[frozen["excluded_process"] == "water", "candidate"].iloc[0]
    evidence = pd.DataFrame(
        [
            {"candidate": water_candidate, "context": "a", "complete": True, "adequate": True},
            {"candidate": water_candidate, "context": "a", "complete": True, "adequate": True},
        ]
    )

    result = classify_process_necessity(
        evidence,
        frozen,
        expected_contexts=("a", "b"),
    ).set_index("process")
    assert result.loc["water", "status"] == "unresolved"


def test_process_stability_is_separate_from_necessity() -> None:
    certificate = build_process_stability_certificate(
        {
            "canonical": ("thermal", "water"),
            "robust": ("water", "soil"),
        }
    )

    assert certificate.stable_process_core == ("water",)
    assert certificate.process_union == ("soil", "thermal", "water")
    assert certificate.contested_processes == ("soil", "thermal")
    assert certificate.exact_process_consensus is False
