import pandas as pd
import pytest

from sdmr.predictor_process_registry import (
    PredictorProcessEntry,
    PredictorProcessRegistry,
)


def _registry():
    return PredictorProcessRegistry(
        (
            PredictorProcessEntry(
                "bio5",
                "thermal_regime",
                "warm_extreme_temperature",
                source_family="CHELSA",
                units="degC",
                rationale="predeclared warm-season thermal constraint",
            ),
            PredictorProcessEntry(
                "gdd5",
                "thermal_regime",
                "growing_season_energy",
                source_family="CHELSA",
                units="degree_days",
            ),
            PredictorProcessEntry(
                "collector_access",
                "observation_process",
                "collector_accessibility",
                role="observation",
                source_family="sampling_bias",
            ),
        )
    )


def test_registry_keeps_process_and_equivalence_group_distinct():
    registry = _registry()
    assert registry.process_aliases() == {
        "bio5": "thermal_regime",
        "gdd5": "thermal_regime",
    }
    assert registry.equivalence_aliases() == {
        "bio5": "warm_extreme_temperature",
        "gdd5": "growing_season_energy",
    }
    assert registry.observation_predictors == ("collector_access",)
    assert "collector_access" not in registry.process_aliases()


def test_registry_can_be_loaded_from_explicit_table():
    frame = pd.DataFrame(
        [
            {
                "predictor": "bio12",
                "process": "water_input",
                "equivalence_group": "annual_precipitation",
                "role": "ecological",
                "source_family": "CHELSA",
            },
            {
                "predictor": "effort",
                "process": "observation_process",
                "equivalence_group": "sampling_effort",
                "role": "observation",
            },
        ]
    )
    registry = PredictorProcessRegistry.from_frame(frame)
    assert registry.ecological_predictors == ("bio12",)
    assert registry.observation_predictors == ("effort",)
    assert set(registry.as_frame()["predictor"]) == {"bio12", "effort"}


def test_duplicate_or_unknown_predictors_fail_loudly():
    with pytest.raises(ValueError, match="duplicate predictor"):
        PredictorProcessRegistry(
            (
                PredictorProcessEntry("bio5", "thermal", "warm"),
                PredictorProcessEntry("bio5", "thermal", "warm"),
            )
        )
    registry = _registry()
    with pytest.raises(KeyError, match="absent from predeclared registry"):
        registry.validate_candidate_predictors(["bio5", "posthoc_variable"])


def test_registry_does_not_ship_a_posthoc_universal_flag():
    registry = _registry()
    assert "universal" not in registry.as_frame().columns
    assert "importance" not in registry.as_frame().columns
