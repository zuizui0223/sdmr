import pandas as pd
import pytest

from sdmr.process_registry_proposal import (
    freeze_process_registry_proposal,
    normalize_process_classification_rules,
    propose_process_information_registry,
)


def _predictors() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"predictor": "bio1", "source_family": "CHELSA", "units": "degC"},
            {"predictor": "gdd5", "source_family": "CHELSA", "units": "degree_days"},
            {"predictor": "pet", "source_family": "CHELSA", "units": "mm"},
            {"predictor": "bio12", "source_family": "CHELSA", "units": "mm"},
            {"predictor": "soil_n", "source_family": "SoilGrids", "units": "cg/kg"},
        ]
    )


def _rules() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "rule_id": "thermal_bio1",
                "process": "thermal",
                "role": "direct",
                "predictor_exact": "bio1",
            },
            {
                "rule_id": "thermal_gdd",
                "process": "thermal",
                "role": "derived",
                "predictor_pattern": r"^gdd",
                "source_family": "CHELSA",
            },
            {
                "rule_id": "thermal_pet",
                "process": "thermal",
                "role": "composite",
                "predictor_exact": "pet",
            },
            {
                "rule_id": "water_pet",
                "process": "water",
                "role": "composite",
                "predictor_exact": "pet",
            },
            {
                "rule_id": "water_precip",
                "process": "water",
                "role": "direct",
                "predictor_exact": "bio12",
                "units_pattern": r"^mm$",
            },
            {
                "rule_id": "soil_source",
                "process": "soil",
                "role": "direct",
                "source_family": "SoilGrids",
            },
        ]
    )


def test_rule_based_proposal_expands_many_to_many_without_rowwise_labeling() -> None:
    proposal = propose_process_information_registry(_predictors(), _rules())

    assert not proposal["review_required"].any()
    pet = proposal.loc[proposal["predictor"] == "pet"]
    assert set(pet["process"]) == {"thermal", "water"}
    assert set(pet["role"]) == {"composite"}

    gdd = proposal.loc[proposal["predictor"] == "gdd5"].iloc[0]
    assert gdd["process"] == "thermal"
    assert gdd["role"] == "derived"
    assert set(gdd["match_basis"].split(",")) == {
        "predictor_pattern",
        "source_family",
    }

    frozen = freeze_process_registry_proposal(
        proposal,
        expected_predictors=tuple(_predictors()["predictor"]),
    )
    assert len(frozen) == 6
    assert set(frozen.loc[frozen["predictor"] == "pet", "process"]) == {
        "thermal",
        "water",
    }


def test_unmatched_predictor_is_flagged_and_blocks_freeze() -> None:
    predictors = pd.concat(
        [
            _predictors(),
            pd.DataFrame(
                [{"predictor": "mystery", "source_family": "unknown", "units": ""}]
            ),
        ],
        ignore_index=True,
    )
    proposal = propose_process_information_registry(predictors, _rules())

    mystery = proposal.loc[proposal["predictor"] == "mystery"].iloc[0]
    assert mystery["status"] == "unmatched"
    assert bool(mystery["review_required"]) is True

    with pytest.raises(ValueError, match="mystery:unmatched"):
        freeze_process_registry_proposal(proposal)


def test_conflicting_roles_for_same_predictor_process_are_flagged() -> None:
    rules = pd.concat(
        [
            _rules(),
            pd.DataFrame(
                [
                    {
                        "rule_id": "thermal_pet_conflict",
                        "process": "thermal",
                        "role": "proxy",
                        "predictor_exact": "pet",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    proposal = propose_process_information_registry(_predictors(), rules)

    pet_thermal = proposal.loc[
        (proposal["predictor"] == "pet") & (proposal["process"] == "thermal")
    ].iloc[0]
    assert pet_thermal["status"] == "conflict"
    assert set(pet_thermal["role"].split("|")) == {"composite", "proxy"}

    with pytest.raises(ValueError, match="pet:conflict"):
        freeze_process_registry_proposal(proposal)


def test_invalid_rule_regex_and_rule_without_matcher_fail_closed() -> None:
    bad_regex = pd.DataFrame(
        [
            {
                "rule_id": "bad",
                "process": "thermal",
                "role": "direct",
                "predictor_pattern": "[",
            }
        ]
    )
    with pytest.raises(ValueError, match="invalid regex"):
        normalize_process_classification_rules(bad_regex)

    no_matcher = pd.DataFrame(
        [{"rule_id": "empty", "process": "thermal", "role": "direct"}]
    )
    with pytest.raises(ValueError, match="requires at least one matcher"):
        normalize_process_classification_rules(no_matcher)


def test_freeze_requires_literal_boolean_review_flags() -> None:
    proposal = propose_process_information_registry(_predictors(), _rules())
    proposal["review_required"] = proposal["review_required"].astype(object)
    proposal.loc[0, "review_required"] = None
    with pytest.raises(ValueError, match="review_required contains missing values"):
        freeze_process_registry_proposal(proposal)
