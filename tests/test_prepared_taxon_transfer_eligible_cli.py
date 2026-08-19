import json

import pandas as pd

from sdmr.prepared_recovery_procedure_cli import _sha256
from sdmr.prepared_taxon_transfer_eligible_cli import _load_and_validate_eligibility


def _write_fixture(tmp_path):
    candidate = tmp_path / "candidate.csv"
    candidate.write_text(
        "scientific_name,role\n"
        "Nothofagus pumilio,discovery\n"
        "Eucalyptus pauciflora,discovery\n"
        "Picea mariana,discovery\n"
        "Rhizophora mangle,validation\n"
        "Larrea tridentata,validation\n",
        encoding="utf-8",
    )
    eligibility = tmp_path / "eligibility"
    eligibility.mkdir()
    roles = pd.DataFrame(
        {
            "scientific_name": [
                "Nothofagus pumilio",
                "Eucalyptus pauciflora",
                "Rhizophora mangle",
                "Larrea tridentata",
            ],
            "role": ["discovery", "discovery", "validation", "validation"],
            "model_presence_count": [406, 2794, 2433, 5803],
            "original_panel_index": [0, 1, 3, 4],
        }
    )
    roles.to_csv(eligibility / "eligible_taxon_roles.csv", index=False)
    contract = {
        "scientific_promotion_run": False,
        "model_scores_used": False,
        "environmental_predictor_values_used": False,
        "hidden_truth_used": False,
        "sealed_rows_used_for_eligibility": False,
        "eligibility_uses_model_pool_coordinates_and_row_counts_only": True,
        "source_feature_cache_contract": {"featured_occurrence_csv_sha256": "occ-sha"},
        "candidate_taxa_config_sha256": _sha256(candidate),
        "outer_folds": 2,
        "spatial_partition_seed": 20260814,
        "n_spatial_blocks": 4,
        "eligible_taxa": list(roles["scientific_name"]),
        "ineligible_taxa": ["Picea mariana"],
        "role_assignments": dict(zip(roles["scientific_name"], roles["role"])),
        "panel_index_by_species": {
            "Nothofagus pumilio": 0,
            "Eucalyptus pauciflora": 1,
            "Picea mariana": 2,
            "Rhizophora mangle": 3,
            "Larrea tridentata": 4,
        },
        "candidate_panel_taxa": [
            "Nothofagus pumilio",
            "Eucalyptus pauciflora",
            "Picea mariana",
            "Rhizophora mangle",
            "Larrea tridentata",
        ],
    }
    (eligibility / "taxon_transfer_spatial_eligibility_contract.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )
    return candidate, eligibility


def test_eligibility_provenance_preserves_original_panel_indices(tmp_path):
    candidate, eligibility = _write_fixture(tmp_path)
    roles, contract, panel_index = _load_and_validate_eligibility(
        eligibility,
        {"featured_occurrence_csv_sha256": "occ-sha"},
        candidate,
        outer_folds=2,
        seed=20260814,
    )
    assert set(roles.loc[roles["role"].eq("discovery"), "scientific_name"]) == {
        "Nothofagus pumilio",
        "Eucalyptus pauciflora",
    }
    assert set(roles.loc[roles["role"].eq("validation"), "scientific_name"]) == {
        "Rhizophora mangle",
        "Larrea tridentata",
    }
    assert panel_index["Rhizophora mangle"] == 3
    assert panel_index["Larrea tridentata"] == 4
    assert contract["ineligible_taxa"] == ["Picea mariana"]


def test_eligibility_provenance_rejects_reindexed_roles(tmp_path):
    candidate, eligibility = _write_fixture(tmp_path)
    roles_path = eligibility / "eligible_taxon_roles.csv"
    roles = pd.read_csv(roles_path)
    roles.loc[roles["scientific_name"].eq("Rhizophora mangle"), "original_panel_index"] = 2
    roles.to_csv(roles_path, index=False)
    try:
        _load_and_validate_eligibility(
            eligibility,
            {"featured_occurrence_csv_sha256": "occ-sha"},
            candidate,
            outer_folds=2,
            seed=20260814,
        )
    except SystemExit as exc:
        assert "original candidate-panel indices" in str(exc)
    else:
        raise AssertionError("reindexed eligible roles should be rejected")


def test_eligibility_provenance_rejects_model_outcome_screen(tmp_path):
    candidate, eligibility = _write_fixture(tmp_path)
    contract_path = eligibility / "taxon_transfer_spatial_eligibility_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["model_scores_used"] = True
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    try:
        _load_and_validate_eligibility(
            eligibility,
            {"featured_occurrence_csv_sha256": "occ-sha"},
            candidate,
            outer_folds=2,
            seed=20260814,
        )
    except SystemExit as exc:
        assert "pre-model contract" in str(exc)
    else:
        raise AssertionError("model-outcome eligibility artifact should be rejected")
