import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.fresh.contract import validate_final_freeze_contract
from sdmr.process_information_closure import normalize_process_information_registry


FINAL = Path("configs/sdmr_fresh_empirical_final_freeze_v1.json")
SOURCE = Path("configs/sdmr_fresh_empirical_source_freeze_v1.json")
REGISTRY = Path("configs/sdmr_fresh_empirical_process_registry_v1.csv")
SELECTED = Path("configs/sdmr_fresh_empirical_selected_taxa_v1.csv")
CHELSA = Path("configs/chelsa_v2_1_plant_candidates.csv")

EXPECTED_PROCESSES = (
    "thermal",
    "water",
    "seasonality",
    "radiation_energy",
    "soil_substrate",
    "productivity",
)
EXPECTED_SOIL = {
    "sg_phh2o_0_5": ("https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt", "divide_by_10"),
    "sg_clay_0_5": ("https://files.isric.org/soilgrids/latest/data/clay/clay_0-5cm_mean.vrt", "divide_by_10"),
    "sg_soc_0_5": ("https://files.isric.org/soilgrids/latest/data/soc/soc_0-5cm_mean.vrt", "divide_by_10"),
    "sg_nitrogen_0_5": ("https://files.isric.org/soilgrids/latest/data/nitrogen/nitrogen_0-5cm_mean.vrt", "divide_by_100"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_final_contract_is_complete_and_hash_pins_all_preoutcome_manifests():
    c = json.loads(FINAL.read_text(encoding="utf-8"))
    validate_final_freeze_contract(c)
    assert c["fresh_outcomes_opened"] is False
    assert c["cohort"]["exact_denominator"] == 50
    assert c["cohort"]["taxon_identity_manifest_sha256"] == "sha256:" + _sha256(SELECTED)
    assert c["cohort"]["source_manifest_sha256"] == "sha256:" + _sha256(SOURCE)
    assert c["process_registry"]["registry_manifest_sha256"] == "sha256:" + _sha256(REGISTRY)
    assert c["final_freeze_evidence"]["environmental_features_opened"] is False
    assert c["final_freeze_evidence"]["answer_check_features_opened"] is False


def test_process_registry_has_exactly_46_unique_predictors_and_all_six_processes():
    registry = pd.read_csv(REGISTRY)
    assert len(registry) == 46
    assert registry["predictor"].nunique() == 46
    normalized = normalize_process_information_registry(
        registry[["predictor", "process", "role"]],
        process_universe=EXPECTED_PROCESSES,
        predictor_universe=tuple(registry["predictor"].astype(str)),
    )
    assert set(normalized["process"]) == set(EXPECTED_PROCESSES)
    counts = normalized.groupby("process")["predictor"].nunique()
    assert (counts > 0).all()


def test_chelsa_universe_is_all_declared_candidates_except_wind():
    registry = pd.read_csv(REGISTRY)
    chelsa = pd.read_csv(CHELSA)
    expected = set(chelsa["predictor"].astype(str)) - {"sfcWind"}
    observed = set(
        registry.loc[registry["source_family"].eq("CHELSA"), "predictor"].astype(str)
    )
    assert len(expected) == 42
    assert observed == expected
    assert "sfcWind" not in observed


def test_soilgrids_is_frozen_to_four_topsoil_webdav_vrts():
    registry = pd.read_csv(REGISTRY)
    soil = registry.loc[registry["source_family"].eq("SoilGrids")].copy()
    assert set(soil["predictor"]) == set(EXPECTED_SOIL)
    assert soil["process"].eq("soil_substrate").all()
    assert soil["role"].eq("direct").all()
    for row in soil.itertuples(index=False):
        expected_url, expected_transform = EXPECTED_SOIL[row.predictor]
        assert row.source_locator == expected_url
        assert row.transform == expected_transform


def test_source_freeze_forbids_answer_check_coordinates_from_M_and_replacement():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert source["selected_taxa"]["post_selection_replacement_allowed"] is False
    assert source["accessible_area"]["focal_coordinates_allowed"] == "model_pool_only"
    assert source["accessible_area"]["answer_check_coordinates_for_M_allowed"] is False
    assert source["outer_split"]["answer_check_environmental_features_opened"] is False
    assert source["predictor_count"] == 46
    assert source["process_universe"] == list(EXPECTED_PROCESSES)
