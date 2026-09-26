import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.process_id.fresh.cohort import (
    EXACT_DENOMINATOR,
    HASH_SEED,
    MAX_PER_FAMILY,
    MAX_PER_GENUS,
    deterministic_rank,
    load_exclusion_manifest,
    select_cohort,
    validate_contract,
)


CONTRACT = Path("configs/sdmr_fresh_empirical_cohort_v1.json")
EXCLUSION = Path("configs/sdmr_fresh_empirical_historical_exclusion_v1.csv")


def _synthetic_summary(n=120):
    return pd.DataFrame(
        {
            "scientific_name": [f"Species {i:03d}" for i in range(n)],
            "family": [f"Family {i // 2:03d}" for i in range(n)],
            "genus": [f"Genus {i:03d}" for i in range(n)],
            "n_occurrences": [1000] * n,
            "n_unique_1_degree_cells": [50] * n,
        }
    )


def test_historical_exclusion_manifest_is_exactly_84_unique_taxa():
    df = load_exclusion_manifest(EXCLUSION)
    assert len(df) == 84
    assert df["scientific_name"].nunique() == 84
    assert not df["scientific_name"].str.strip().eq("").any()


def test_cohort_contract_preserves_metadata_only_information_barrier():
    c = validate_contract(CONTRACT)
    assert c["deterministic_selection"]["seed"] == HASH_SEED
    assert c["information_barrier"]["fresh_outcomes_opened"] is False
    forbidden = set(c["information_barrier"]["forbidden"])
    assert {"CHELSA", "AUC", "CBI", "OR10", "AICc", "sealed_answer_check"} <= forbidden


def test_selection_is_order_invariant_and_exactly_50():
    summary = _synthetic_summary()
    _, a = select_cohort(summary, excluded_names=[])
    _, b = select_cohort(summary.sample(frac=1.0, random_state=19), excluded_names=[])
    assert len(a) == EXACT_DENOMINATOR == 50
    assert a["scientific_name"].tolist() == b["scientific_name"].tolist()
    assert a["selection_hash"].tolist() == sorted(a["selection_hash"].tolist())


def test_selection_enforces_taxonomic_breadth_caps():
    _, selected = select_cohort(_synthetic_summary(), excluded_names=[])
    assert selected["genus"].value_counts().max() <= MAX_PER_GENUS
    assert selected["family"].value_counts().max() <= MAX_PER_FAMILY
    assert selected["family"].nunique() >= 25
    assert selected["genus"].nunique() == 50


def test_historical_taxa_are_never_selected():
    summary = _synthetic_summary()
    excluded = set(summary["scientific_name"].head(20))
    _, selected = select_cohort(summary, excluded_names=excluded)
    assert not (set(selected["scientific_name"]) & excluded)


def test_occurrence_and_grid_thresholds_fail_closed():
    summary = _synthetic_summary()
    summary.loc[:80, "n_occurrences"] = 499
    with pytest.raises(RuntimeError, match="cohort unavailable"):
        select_cohort(summary, excluded_names=[])


def test_hash_seed_is_scientific_name_specific():
    assert deterministic_rank("Species alpha") == deterministic_rank("Species alpha")
    assert deterministic_rank("Species alpha") != deterministic_rank("Species beta")
