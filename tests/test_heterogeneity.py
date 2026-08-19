import pandas as pd
import pytest

from sdmr.heterogeneity import (
    aggregate_process_evidence_across_strata,
    aggregate_process_evidence_by_stratum,
    summarize_process_heterogeneity,
    validate_species_metadata,
)


def _manifest():
    return pd.DataFrame({
        "predictor": ["temp", "water"],
        "source": ["synthetic", "synthetic"],
        "version": ["1", "1"],
        "candidate_class": ["core", "core"],
        "process": ["temperature", "water"],
        "mechanism": ["heat", "drought"],
    })


def _evidence():
    selection = pd.DataFrame({
        "species": ["a", "b", "c", "d"],
        "predictor": ["water", "water", "temp", "temp"],
        "gain": [0.08, 0.06, 0.07, 0.05],
    })
    drop = pd.DataFrame({
        "species": ["a", "b", "c", "d"],
        "predictor": ["water", "water", "temp", "temp"],
        "loss": [0.10, 0.08, 0.09, 0.07],
    })
    metadata = pd.DataFrame({
        "species": ["a", "b", "c", "d"],
        "biome": ["tropical", "tropical", "temperate", "temperate"],
        "growth_form": ["tree", "herb", "tree", "herb"],
    })
    return selection, drop, metadata


def test_stratum_aggregation_keeps_zero_selection_species_in_denominator():
    selection, drop, metadata = _evidence()
    out = aggregate_process_evidence_by_stratum(
        selection, drop, _manifest(), metadata,
        stratum_col="biome", modeled_species=list("abcd"), min_species=2,
    )
    table = out.set_index(["stratum", "process"])
    assert table.loc[("tropical", "water"), "selection_fraction"] == pytest.approx(1.0)
    assert table.loc[("tropical", "temperature"), "selection_fraction"] == pytest.approx(0.0)
    assert table.loc[("temperate", "temperature"), "selection_fraction"] == pytest.approx(1.0)


def test_heterogeneity_summary_reports_where_process_evidence_changes():
    selection, drop, metadata = _evidence()
    stratified = aggregate_process_evidence_across_strata(
        selection, drop, _manifest(), metadata,
        stratum_cols=["biome"], modeled_species=list("abcd"), min_species=2,
    )
    summary = summarize_process_heterogeneity(stratified).set_index("process")
    assert summary.loc["water", "selection_fraction_range"] == pytest.approx(1.0)
    assert summary.loc["water", "max_selection_stratum"] == "tropical"
    assert summary.loc["temperature", "max_selection_stratum"] == "temperate"


def test_species_metadata_must_be_unique_and_complete_for_modeled_species():
    selection, drop, metadata = _evidence()
    duplicated = pd.concat([metadata, metadata.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        validate_species_metadata(duplicated, required_strata=["biome"])

    incomplete = metadata.loc[metadata.species != "d"]
    with pytest.raises(ValueError):
        aggregate_process_evidence_by_stratum(
            selection, drop, _manifest(), incomplete,
            stratum_col="biome", modeled_species=list("abcd"), min_species=1,
        )
