import numpy as np
import pandas as pd

from sdmr.process_id.fresh.background import (
    BACKGROUND_POINTS,
    M_KM,
    _target_where_sql,
    build_backgrounds,
    validate_background_contract,
)


FINAL = "configs/sdmr_fresh_empirical_final_freeze_v1.json"
SOURCE = "configs/sdmr_fresh_empirical_source_freeze_v1.json"
OCCURRENCE_RECEIPT = "configs/sdmr_fresh_empirical_occurrence_split_artifact_receipt_v1.json"
SELECTED = "configs/sdmr_fresh_empirical_selected_taxa_v1.csv"


def _target_grid():
    rows = []
    gid = 1000
    for i, lon in enumerate(np.linspace(-5, 5, 81)):
        for j, lat in enumerate(np.linspace(-2, 2, 33)):
            rows.append(
                {
                    "gx": i,
                    "gy": j,
                    "gbifid": str(gid),
                    "longitude": float(lon),
                    "latitude": float(lat),
                }
            )
            gid += 1
    return pd.DataFrame(rows)


def _model_pool():
    return pd.DataFrame(
        {
            "scientific_name": ["Taxon A", "Taxon A", "Taxon B", "Taxon B"],
            "occurrence_id": ["A1", "A2", "B1", "B2"],
            "longitude": [0.0, 0.5, 3.0, 3.5],
            "latitude": [0.0, 0.2, 0.0, 0.2],
        }
    )


def test_background_contract_remains_pre_environment_and_model_pool_only():
    final, source, receipt, selected = validate_background_contract(
        final_contract_path=FINAL,
        source_contract_path=SOURCE,
        occurrence_receipt_path=OCCURRENCE_RECEIPT,
        selected_taxa_path=SELECTED,
    )
    assert len(selected) == 50
    assert final["fresh_outcomes_opened"] is False
    assert final["final_freeze_evidence"]["environmental_features_opened"] is False
    assert receipt["answer_check_coordinates_persisted_for_M"] is False
    assert source["accessible_area"]["focal_coordinates_allowed"] == "model_pool_only"
    assert source["accessible_area"]["answer_check_coordinates_for_M_allowed"] is False


def test_target_query_uses_exact_frozen_taxonomic_and_qc_scope():
    names = [f"Species {i}" for i in range(50)]
    sql = _target_where_sql(names)
    assert "phylum = 'Tracheophyta'" in sql
    assert "year BETWEEN 2010 AND 2025" in sql
    assert "FOSSIL_SPECIMEN" in sql
    assert "coordinateuncertaintyinmeters <= 10000" in sql
    assert "NOT (decimallatitude = 0 AND decimallongitude = 0)" in sql
    for name in names:
        assert name in sql


def test_model_pool_only_background_is_deterministic_and_distance_nested():
    target = _target_grid()
    model = _model_pool()
    a_bg, a_summary = build_backgrounds(
        target_footprint=target,
        model_pool=model,
        taxa=["Taxon A", "Taxon B"],
    )
    b_bg, b_summary = build_backgrounds(
        target_footprint=target.sample(frac=1.0, random_state=13),
        model_pool=model.sample(frac=1.0, random_state=17),
        taxa=["Taxon A", "Taxon B"],
    )
    a_key = a_bg[["scientific_name", "m_km", "background_rank", "gbifid"]]
    b_key = b_bg[["scientific_name", "m_km", "background_rank", "gbifid"]]
    assert a_key.equals(b_key)
    assert a_summary.equals(b_summary)

    for taxon, group in a_summary.groupby("scientific_name"):
        counts = group.set_index("m_km")["candidate_target_cells"]
        assert counts.loc[150] <= counts.loc[300] <= counts.loc[500]
        assert set(group["m_km"]) == set(M_KM)
        assert (group["background_points"] <= BACKGROUND_POINTS).all()


def test_background_rows_never_exceed_frozen_5000_per_taxon_and_M():
    backgrounds, summary = build_backgrounds(
        target_footprint=_target_grid(),
        model_pool=_model_pool(),
        taxa=["Taxon A", "Taxon B"],
    )
    counts = backgrounds.groupby(["scientific_name", "m_km"]).size()
    assert (counts <= BACKGROUND_POINTS).all()
    assert len(summary) == 2 * len(M_KM)
