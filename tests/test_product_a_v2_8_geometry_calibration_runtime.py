import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_8_geometry_calibration import (
    EXPECTED_FRACTIONS,
    EXPECTED_SEEDS,
    _admit_geometry_rows,
    _load_raw_geometry_columns,
    aggregate_parts,
    wilson_lower_bound,
)
from sdmr.data import OccurrenceAdmissionConfig, admit_occurrences


DESIGN = Path("configs/product_a_v2_8_geometry_only_validation_calibration_contract.json")
EXECUTION = Path("configs/product_a_v2_8_geometry_only_validation_calibration_execution.json")
REGISTRY = Path("configs/product_a_v2_7_1_fresh_taxon_candidates.csv")
SOURCE_PIN = Path("configs/product_a_v2_8_geometry_calibration_source_pin.json")
MODULE = Path("src/sdmr/v2_8_geometry_calibration.py")
WORKFLOW = Path(".github/workflows/product-a-v2-8-geometry-calibration.yml")
LAUNCHER = Path(".github/workflows/product-a-v2-8-geometry-calibration-pr-launch.yml")
TRIGGER = Path("configs/product_a_v2_8_geometry_calibration_pr_trigger.txt")


def _barrier():
    return {
        "environmental_values_read": False,
        "CHELSA_values_read": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_read": False,
        "sealed_ecological_outcomes_read": False,
        "scientific_confirmation_allowed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }


def _write_parts(root: Path, *, failures_by_fraction=None):
    failures_by_fraction = failures_by_fraction or {}
    registry = pd.read_csv(REGISTRY)
    for seed in EXPECTED_SEEDS:
        for fraction in EXPECTED_FRACTIONS:
            part = root / f"{seed}-{fraction:.2f}"
            part.mkdir(parents=True)
            rows = []
            for taxon_index, row in enumerate(registry.itertuples(index=False)):
                rows.append(
                    {
                        "seed": seed,
                        "sealed_fraction": fraction,
                        "taxon_index": taxon_index,
                        "taxon": row.scientific_name,
                        "validation_stratum": row.validation_stratum,
                        "candidate_rank": row.candidate_rank,
                        "partition_seed": seed + taxon_index * 100 + 271,
                        "structurally_feasible": True,
                        "selected_assignment_attempt": 0,
                        "n_occurrences_model_pool": 100,
                        "n_unique_cells_model_pool": 80,
                        "unavailable_stage": None,
                        "unavailable_reason": None,
                    }
                )
            # Failure quotas apply independently within each fraction's 180 cells.
            fraction_rows_seen = sum(
                36
                for prior_seed in EXPECTED_SEEDS
                if prior_seed < seed
            )
            quota = int(failures_by_fraction.get(fraction, 0))
            for offset, row in enumerate(rows):
                row["structurally_feasible"] = fraction_rows_seen + offset >= quota
                if not row["structurally_feasible"]:
                    row["selected_assignment_attempt"] = None
                    row["unavailable_stage"] = "evidence_balanced_partition"
                    row["unavailable_reason"] = "synthetic structural failure"
            pd.DataFrame(rows).to_csv(part / "taxon_feasibility.csv", index=False)
            contract = {
                "purpose": "product_a_v2_8_geometry_calibration_part",
                "seed": seed,
                "sealed_fraction": fraction,
                "source_run_id": 32936391197,
                "focal_sha256": "f" * 64,
                "target_sha256": "e" * 64,
                "calibration_corpus_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
                "n_taxa": 36,
                "n_feasible_taxa": int(sum(bool(row["structurally_feasible"]) for row in rows)),
                "M_specs": ["buffer_150km", "buffer_300km", "buffer_500km"],
                "outer_sealed_before_M": True,
                "M_built_from_model_pool_only": True,
                "sealed_rows_used_for_partition_assignment": False,
                **_barrier(),
            }
            (part / "contract.json").write_text(json.dumps(contract))


def test_wilson_rule_boundary_is_applied_to_all_180_taxon_seed_cells():
    assert wilson_lower_bound(177, 180) >= 0.95
    assert wilson_lower_bound(176, 180) < 0.95


def test_column_pruned_transport_preserves_default_geometry_admission(tmp_path):
    raw = pd.DataFrame(
        {
            "gbifid": ["3", "2", "1", "4", "5", "6"],
            "species": ["a", "a", "a", "b", "b", "b"],
            "decimallongitude": [1.0, 1.0, 2.0, 1.0, 181.0, None],
            "decimallatitude": [2.0, 2.0, 3.0, 2.0, 4.0, 5.0],
            "occurrencestatus": ["PRESENT", "PRESENT", "ABSENT", "", "PRESENT", "PRESENT"],
            "unused_large_payload": ["x"] * 6,
        }
    )
    source = tmp_path / "raw.parquet"
    raw.to_parquet(source, index=False)
    geometry = _load_raw_geometry_columns(source)
    assert "unused_large_payload" not in geometry
    assert {"gbifID", "species", "longitude", "latitude", "occurrenceStatus"} <= set(
        geometry.columns
    )
    expected = admit_occurrences(
        geometry, config=OccurrenceAdmissionConfig()
    ).accepted.reset_index(drop=True)
    actual = _admit_geometry_rows(geometry)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)


def test_successful_geometry_raw_source_is_pinned_before_calibration():
    pin = json.loads(SOURCE_PIN.read_text())
    assert pin["purpose"] == "product_a_v2_8_geometry_calibration_raw_source_pin"
    assert pin["workflow_run_id"] == 32936391197
    assert pin["workflow_conclusion"] == "success"
    assert pin["execution_sha"] == "e33a883ff0829b2c6b621b77ac295151de647a58"
    assert pin["execution_ref"] == "frozen/product-a-v2-8-geometry-source-e33a883f"
    assert pin["authorization_commit_sha"] == "8f426f0aa46ec648bf4b9332779b09fbb1f46133"
    assert pin["authorization_blob_sha"] == "230a670ba913e7bc1af5de141fca2ef1bdd604c1"
    assert pin["source_receipt_artifact"]["id"] == 9595593544
    assert pin["source_receipt_artifact"]["digest"] == (
        "sha256:852ee32958bd1081ac1ff03d363c6d552918314252d22dcd8f87380f7fe7a856"
    )
    assert pin["focal"]["artifact_id"] == 9595572912
    assert pin["focal"]["file_sha256"] == (
        "6633106cce2098860a0825de56b59eb42f52782b8167332bb0578c3d760e396d"
    )
    assert pin["focal"]["query_sha256"] == (
        "8da64e8453a13a4ea50f189a43ad5d5b17a51b795bb43a6a98b1afa800fffa2d"
    )
    assert pin["target_group"]["artifact_id"] == 9595280581
    assert pin["target_group"]["file_sha256"] == (
        "4825fa34e7a006ffd45f588a979973b8ba8e1b237f05577495509e2021f4e491"
    )
    assert pin["target_group"]["query_sha256"] == (
        "36884dfdfbd66480bcff92a82255a9c7c816ee11ed00609b1c7a37795eb6532d"
    )
    assert pin["snapshot_shard_catalog_sha256"] == (
        "47300bbeb7d7b10711e685cff20d7574737c3440228e9b0247efac40a3d0ca84"
    )
    assert pin["ready_for_geometry_calibration"] is True
    assert pin["ready_for_scientific_confirmation"] is False
    for value in pin["information_barrier"].values():
        assert value is False


def test_aggregate_selects_largest_qualifying_global_fraction(tmp_path):
    parts = tmp_path / "parts"
    _write_parts(parts, failures_by_fraction={0.30: 3, 0.35: 4})
    result = aggregate_parts(
        design_path=DESIGN,
        taxa_path=REGISTRY,
        parts_root=parts,
        output_dir=tmp_path / "decision",
    )
    assert result["decision"] == "geometry_calibration_fraction_selected"
    assert result["selected_global_sealed_fraction"] == 0.30
    assert result["n_taxon_seed_cells_per_fraction"] == 180
    assert result["taxon_specific_fraction_selection_allowed"] is False
    assert result["future_confirmation_must_use_taxa_outside_calibration_corpus"] is True
    assert result["geometry_calibration_result_is_ecological_support"] is False
    for key, value in _barrier().items():
        assert result[key] is value

    fractions = pd.read_csv(tmp_path / "decision" / "fraction_summary.csv")
    row30 = fractions.loc[fractions["sealed_fraction"].eq(0.30)].iloc[0]
    row35 = fractions.loc[fractions["sealed_fraction"].eq(0.35)].iloc[0]
    assert int(row30["n_structurally_feasible"]) == 177
    assert bool(row30["passes_predeclared_rule"])
    assert int(row35["n_structurally_feasible"]) == 176
    assert not bool(row35["passes_predeclared_rule"])


def test_aggregate_fail_closes_when_no_fraction_qualifies(tmp_path):
    parts = tmp_path / "parts"
    _write_parts(
        parts,
        failures_by_fraction={fraction: 4 for fraction in EXPECTED_FRACTIONS},
    )
    result = aggregate_parts(
        design_path=DESIGN,
        taxa_path=REGISTRY,
        parts_root=parts,
        output_dir=tmp_path / "decision",
    )
    assert result["decision"] == "geometry_calibration_no_fraction_qualifies"
    assert result["selected_global_sealed_fraction"] is None
    assert result["scientific_confirmation_allowed"] is False


def test_aggregate_rejects_incomplete_part_denominator(tmp_path):
    parts = tmp_path / "parts"
    _write_parts(parts)
    one_contract = next(parts.rglob("contract.json"))
    one_contract.unlink()
    with pytest.raises(ValueError, match="exactly 30"):
        aggregate_parts(
            design_path=DESIGN,
            taxa_path=REGISTRY,
            parts_root=parts,
            output_dir=tmp_path / "decision",
        )


def test_runtime_is_staged_closed_and_excludes_scientific_inputs():
    execution = json.loads(EXECUTION.read_text())
    assert execution["purpose"] == (
        "product_a_v2_8_geometry_only_validation_calibration_execution_authorization"
    )
    assert execution["geometry_only"] is True
    assert execution["execution_allowed"] is False
    assert execution["implementation_sha"] is None
    assert execution["frozen_ref"] is None
    assert execution["workflow_blob_sha"] == "87c13da7821e532fad812b65175454fed513451d"
    assert execution["module_blob_sha"] == "e235f49740aaa330d543c992919309b0a7566086"
    assert execution["contract_blob_sha"] == "6c3b74da06ac225ff6ef153761fd334ec1eb9d1c"
    assert execution["source_pin_blob_sha"] == "b53633cb56008df4e729c6326648c0532f4435e7"
    assert execution["candidate_registry_blob_sha"] == "ee43c9731eb8ad3673d2fa9271e0c3a8503bd0e0"
    assert execution["grid_blob_sha"] == "608ce63f4007406e2873e25267a1234933f0487e"
    assert execution["evidence_partition_blob_sha"] == "2109221ee796bee39093c0f9388d63761a62f4af"
    assert execution["eligibility_contract_blob_sha"] == "8933c270647daa612608a33f283f833074334656"
    assert execution["source_acquisition_run_id"] == 32936391197
    assert execution["run_all_30_parts"] is True
    assert execution["require_full_36_taxa_x_5_seed_per_fraction_denominator"] is True
    for key in (
        "environmental_values_allowed",
        "candidate_model_fitting_allowed",
        "sealed_ecological_outcomes_allowed",
        "scientific_confirmation_allowed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        assert execution[key] is False

    module = MODULE.read_text()
    assert "make_evidence_balanced_spatial_partitions" in module
    assert "raster_specs_from_chelsa_manifest" not in module
    assert "extract_protocol_grid_rasters" not in module
    assert "benchmark_recovery_procedures" not in module
    assert "select_model_pool_admissible_predictors" not in module


def test_workflow_runs_complete_geometry_denominator_and_stays_outcome_blind():
    workflow = WORKFLOW.read_text()
    assert "seed: [2026082201, 2026082202, 2026082203, 2026082204, 2026082205]" in workflow
    assert "sealed_fraction: ['0.10', '0.15', '0.20', '0.25', '0.30', '0.35']" in workflow
    assert "product-a-v2-8-geometry-calibration-focal-source-2026-08-01" in workflow
    assert "product-a-v2-8-geometry-calibration-target-source-2026-08-01" in workflow
    assert "v28-geometry-calibration-transport" in workflow
    assert "--transport-manifest transport/transport.json" in workflow
    assert "raw/focal.parquet\n            raw/target_group.parquet" not in workflow
    assert "v28-geometry-calibration-part-${{ matrix.seed }}-${{ matrix.sealed_fraction }}" in workflow
    assert "product-a-v2-8-geometry-calibration-decision" in workflow
    assert "configs/chelsa_v2_1_plant_candidates.csv" not in workflow
    assert "v2_7_2_fresh_model_pool" not in workflow
    assert "v2_7_2_fresh_sealed_audit" not in workflow


def test_launcher_is_external_one_shot_and_trigger_absent():
    launcher = LAUNCHER.read_text()
    assert "authorization_commit_sha=str(event['pull_request']['base']['sha'])" in launcher
    assert "auth.get('execution_allowed') is not True" in launcher
    assert "auth.get('run_all_30_parts') is not True" in launcher
    assert "multiple exact v2.8 geometry calibration runs exist" in launcher
    assert "verify_blob('src/sdmr/v2_8_geometry_calibration.py',auth['module_blob_sha'])" in launcher
    assert "verify_blob('configs/product_a_v2_8_geometry_calibration_source_pin.json',auth['source_pin_blob_sha'])" in launcher
    assert "'environmental_values_allowed':False" in launcher
    assert "'scientific_confirmation_allowed':False" in launcher
    assert "'scientific_promotion_allowed':False" in launcher
    assert "'product_b_unblocked':False" in launcher
    assert not TRIGGER.exists()
