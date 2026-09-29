import numpy as np
import pandas as pd

from sdmr.data import raster as raster_mod
from sdmr.process_id.fresh.features import (
    EXPECTED_PREDICTORS,
    build_frozen_layer_specs,
    evaluate_complete_case_gate,
    validate_feature_contract,
)


FEATURE_CONTRACT = "configs/sdmr_fresh_empirical_feature_extraction_v1.json"
REGISTRY = "configs/sdmr_fresh_empirical_process_registry_v1.csv"
SELECTED = "configs/sdmr_fresh_empirical_selected_taxa_v1.csv"
OCCURRENCE_RECEIPT = "configs/sdmr_fresh_empirical_occurrence_split_artifact_receipt_v1.json"
BACKGROUND_RECEIPT = "configs/sdmr_fresh_empirical_background_artifact_receipt_v1.json"
CHELSA = "configs/chelsa_v2_1_plant_candidates.csv"


def test_feature_contract_is_frozen_before_environmental_value_read():
    contract, registry, selected = validate_feature_contract(
        feature_contract_path=FEATURE_CONTRACT,
        process_registry_path=REGISTRY,
        selected_taxa_path=SELECTED,
        occurrence_receipt_path=OCCURRENCE_RECEIPT,
        background_receipt_path=BACKGROUND_RECEIPT,
    )
    assert contract["status"] == "frozen_before_environmental_value_read"
    assert contract["extraction_scope"]["answer_check_occurrences"] is False
    assert contract["extraction_scope"]["answer_check_features"] is False
    assert contract["missingness"]["imputation"] == "none"
    assert contract["missingness"]["predictor_deletion_after_value_read"] is False
    assert contract["missingness"]["taxon_replacement"] is False
    assert len(registry) == EXPECTED_PREDICTORS == 46
    assert len(selected) == 50


def test_layer_specs_are_exactly_42_chelsa_plus_4_soilgrids():
    specs, resolved = build_frozen_layer_specs(
        process_registry_path=REGISTRY,
        chelsa_manifest_path=CHELSA,
    )
    assert len(specs) == 46
    assert len({spec.predictor for spec in specs}) == 46
    assert sum(spec.source == "SoilGrids" for spec in specs) == 4
    assert sum(spec.source != "SoilGrids" for spec in specs) == 42
    assert len(resolved) == 42
    assert resolved["resolution_status"].eq("resolved").all()
    soil = {spec.predictor: spec for spec in specs if spec.source == "SoilGrids"}
    assert soil["sg_phh2o_0_5"].scale == 0.1
    assert soil["sg_clay_0_5"].scale == 0.1
    assert soil["sg_soc_0_5"].scale == 0.1
    assert soil["sg_nitrogen_0_5"].scale == 0.01
    assert all(spec.uri.endswith(".vrt") for spec in soil.values())


def test_http_raster_environment_allows_vrt_and_overviews():
    class FakeRasterio:
        @staticmethod
        def Env(**kwargs):
            return kwargs

    env = raster_mod._raster_env(
        FakeRasterio,
        "https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt",
    )
    assert ".vrt" in env["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"]
    assert ".ovr" in env["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"]


def test_complete_case_gate_is_frozen_and_taxon_level():
    predictors = [f"x{i}" for i in range(46)]
    model_rows = []
    bg_rows = []
    for t in range(50):
        taxon = f"Taxon {t:02d}"
        for i in range(100):
            row = {"scientific_name": taxon}
            row.update({p: float(i) for p in predictors})
            model_rows.append(row)
        for i in range(5000):
            row = {"scientific_name": taxon}
            row.update({p: float(i) for p in predictors})
            bg_rows.append(row)
    model = pd.DataFrame(model_rows)
    bg = pd.DataFrame(bg_rows)
    gate = evaluate_complete_case_gate(
        model_features=model,
        background_features=bg,
        predictors=predictors,
    )
    assert len(gate) == 50
    assert gate["complete_case_gate_passed"].all()

    taxon = "Taxon 00"
    idx = model.index[model["scientific_name"].eq(taxon)][:21]
    model.loc[idx, predictors[0]] = np.nan
    gate2 = evaluate_complete_case_gate(
        model_features=model,
        background_features=bg,
        predictors=predictors,
    )
    failed = gate2.loc[gate2["scientific_name"].eq(taxon)].iloc[0]
    assert failed["model_pool_retention_fraction"] == 0.79
    assert not bool(failed["complete_case_gate_passed"])
