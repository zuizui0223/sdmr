import pandas as pd
import pytest

from sdmr.process_id.fresh.occurrence_split import (
    MIN_THINNED_CELLS,
    _freeze_taxon_split,
    validate_pre_feature_contract,
)


FINAL = "configs/sdmr_fresh_empirical_final_freeze_v1.json"
SOURCE = "configs/sdmr_fresh_empirical_source_freeze_v1.json"
SELECTED = "configs/sdmr_fresh_empirical_selected_taxa_v1.csv"


def _cells(n=60, taxon="Synthetic plant"):
    return pd.DataFrame(
        {
            "species": [taxon] * n,
            "cell_x": list(range(n)),
            "cell_y": list(range(n)),
            "n_occurrences_in_cell": [2] * n,
            "gbifid": [str(100000 + i) for i in range(n)],
            "gbifid_num": [100000 + i for i in range(n)],
            "longitude": [-120.0 + i * 0.2 for i in range(n)],
            "latitude": [30.0 + (i % 10) * 0.2 for i in range(n)],
        }
    )


def test_pre_feature_contract_is_complete_without_feature_access():
    final, source, selected = validate_pre_feature_contract(
        final_contract_path=FINAL,
        source_contract_path=SOURCE,
        selected_taxa_path=SELECTED,
    )
    assert len(selected) == 50
    assert final["fresh_outcomes_opened"] is False
    assert final["final_freeze_evidence"]["environmental_features_opened"] is False
    assert source["accessible_area"]["focal_coordinates_allowed"] == "model_pool_only"
    assert source["accessible_area"]["answer_check_coordinates_for_M_allowed"] is False


def test_taxon_split_uses_coordinates_but_exports_only_model_pool_coordinates():
    model, ledger, summary = _freeze_taxon_split(_cells(), "Synthetic plant")
    assert summary["raw_occurrences"] == 120
    assert summary["thinned_occurrences"] == 60
    assert summary["model_pool_occurrences"] + summary["answer_check_occurrences"] == 60
    assert set(ledger["outer_role"]) == {"model_pool", "answer_check"}
    answer_ids = set(
        ledger.loc[ledger["outer_role"].eq("answer_check"), "occurrence_id"].astype(str)
    )
    assert not (set(model["occurrence_id"].astype(str)) & answer_ids)
    assert {"longitude", "latitude"} <= set(model.columns)
    assert "longitude" not in ledger.columns
    assert "latitude" not in ledger.columns


def test_source_gate_fails_closed_without_taxon_replacement():
    too_few = _cells(n=MIN_THINNED_CELLS - 1)
    too_few["n_occurrences_in_cell"] = 10
    with pytest.raises(RuntimeError, match="failed source gate without replacement"):
        _freeze_taxon_split(too_few, "Synthetic plant")


def test_outer_split_is_row_order_invariant():
    cells = _cells()
    a_model, a_ledger, a_summary = _freeze_taxon_split(cells, "Synthetic plant")
    b_model, b_ledger, b_summary = _freeze_taxon_split(
        cells.sample(frac=1.0, random_state=17),
        "Synthetic plant",
    )
    assert a_summary["split_digest"] == b_summary["split_digest"]
    assert (
        a_ledger.sort_values("occurrence_id").reset_index(drop=True)
        .equals(b_ledger.sort_values("occurrence_id").reset_index(drop=True))
    )
    assert set(a_model["occurrence_id"]) == set(b_model["occurrence_id"])
