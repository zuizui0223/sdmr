import pandas as pd
import pytest

from sdmr.drivers import (
    aggregate_process_evidence,
    annotate_predictor_metadata,
    equivalence_group_process_map,
    validate_candidate_manifest,
)


def _manifest():
    return pd.DataFrame(
        {
            "predictor": ["t1", "t2", "w1"],
            "source": ["x", "x", "x"],
            "version": ["1", "1", "1"],
            "candidate_class": ["core", "core", "core"],
            "process": ["temperature", "temperature", "water"],
            "mechanism": ["mean", "extreme", "drought"],
        }
    )


def test_manifest_rejects_duplicate_predictor_names():
    manifest = pd.concat([_manifest(), _manifest().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        validate_candidate_manifest(manifest)


def test_process_aggregation_uses_absent_species_as_selection_zero():
    selection = pd.DataFrame(
        {
            "species": ["a", "a", "b"],
            "predictor": ["t1", "t2", "w1"],
            "gain": [0.08, 0.02, 0.05],
        }
    )
    drop = pd.DataFrame(
        {
            "species": ["a", "b"],
            "predictor": ["t1", "w1"],
            "loss": [0.07, 0.04],
        }
    )
    out = aggregate_process_evidence(
        selection, drop, _manifest(), species_universe=["a", "b", "c"]
    ).set_index("process")
    assert out.loc["temperature", "selection_fraction"] == pytest.approx(1 / 3)
    assert out.loc["temperature", "mean_incremental_gain"] == pytest.approx(0.10 / 3)
    assert out.loc["water", "selection_fraction"] == pytest.approx(1 / 3)
    assert out.loc["temperature", "drop_one_coverage_fraction"] == pytest.approx(1 / 3)


def test_equivalence_group_map_flags_cross_process_substitution():
    eq = pd.DataFrame(
        {
            "predictor": ["t1", "w1", "t2"],
            "equivalence_group": ["eq1", "eq1", "eq2"],
        }
    )
    out = equivalence_group_process_map(eq, _manifest()).set_index("equivalence_group")
    assert bool(out.loc["eq1", "cross_process_substitution"])
    assert not bool(out.loc["eq2", "cross_process_substitution"])
    annotated = annotate_predictor_metadata(pd.DataFrame({"predictor": ["w1"]}), _manifest())
    assert annotated.loc[0, "process"] == "water"
