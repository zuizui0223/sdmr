import pandas as pd
import pytest


def _registry():
    return pd.DataFrame([
        {"predictor": "temp", "process": "thermal", "role": "direct"},
        {"predictor": "pet", "process": "thermal", "role": "composite"},
        {"predictor": "precip", "process": "water", "role": "direct"},
        {"predictor": "pet", "process": "water", "role": "composite"},
        {"predictor": "bio15", "process": "seasonality", "role": "direct"},
        {"predictor": "rsds", "process": "radiation_energy", "role": "direct"},
        {"predictor": "soil_n", "process": "soil_substrate", "role": "direct"},
        {"predictor": "ndvi", "process": "productivity", "role": "direct"},
    ])


def test_default_plant_process_order_is_frozen():
    from sdmr.process_id.taxonomy import DEFAULT_PLANT_PROCESSES

    assert DEFAULT_PLANT_PROCESSES == (
        "thermal",
        "water",
        "seasonality",
        "radiation_energy",
        "soil_substrate",
        "productivity",
    )


def test_shared_composite_can_link_to_multiple_processes():
    from sdmr.process_id.registry import freeze_process_registry

    frozen = freeze_process_registry(
        _registry(),
        predictor_universe=("temp", "pet", "precip", "bio15", "rsds", "soil_n", "ndvi"),
    )
    pet = frozen.table.loc[frozen.table["predictor"].eq("pet")]
    assert set(pet["process"]) == {"thermal", "water"}
    assert set(pet["role"]) == {"composite"}


def test_registry_digest_is_deterministic_under_row_permutation():
    from sdmr.process_id.registry import freeze_process_registry

    predictors = ("temp", "pet", "precip", "bio15", "rsds", "soil_n", "ndvi")
    first = freeze_process_registry(_registry(), predictor_universe=predictors)
    second = freeze_process_registry(
        _registry().sample(frac=1.0, random_state=8).reset_index(drop=True),
        predictor_universe=predictors,
    )
    assert first.digest == second.digest
    pd.testing.assert_frame_equal(first.table, second.table)


def test_registry_rejects_undeclared_process():
    from sdmr.process_id.registry import freeze_process_registry

    registry = pd.concat([
        _registry(),
        pd.DataFrame([{"predictor": "rogue", "process": "salinity", "role": "direct"}]),
    ], ignore_index=True)
    with pytest.raises(ValueError, match="outside process_universe"):
        freeze_process_registry(
            registry,
            predictor_universe=("temp", "pet", "precip", "bio15", "rsds", "soil_n", "ndvi", "rogue"),
        )


def test_registry_rejects_uncovered_predictor():
    from sdmr.process_id.registry import freeze_process_registry

    with pytest.raises(ValueError, match="requires at least one process-information link"):
        freeze_process_registry(
            _registry(),
            predictor_universe=("temp", "pet", "precip", "bio15", "rsds", "soil_n", "ndvi", "unmapped"),
        )
