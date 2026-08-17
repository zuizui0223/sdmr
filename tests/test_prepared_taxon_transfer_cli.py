import json

import pandas as pd

from sdmr.prepared_taxon_transfer_cli import (
    _freeze_discovery_selectors,
    _load_taxon_role_config,
    _validate_outcome_blind_panel,
)


def test_stage1_panel_and_roles_are_recoverable_from_frozen_preoutcome_metadata(tmp_path):
    counts = {
        "Nothofagus pumilio": 4,
        "Rhizophora mangle": 6,
        "Picea mariana": 7,
        "Eucalyptus pauciflora": 8,
        "Larrea tridentata": 9,
        "Large taxon": 50,
    }
    rows = []
    for species, n_model in counts.items():
        rows.extend(
            {"species": species, "__sdmr_outer_role": "model"}
            for _ in range(n_model)
        )
        rows.extend(
            {"species": species, "__sdmr_outer_role": "sealed"}
            for _ in range(2)
        )
    pd.DataFrame(rows).to_csv(tmp_path / "pilot_occurrences.csv", index=False)

    roles = pd.DataFrame(
        {
            "scientific_name": [
                "Nothofagus pumilio",
                "Eucalyptus pauciflora",
                "Picea mariana",
                "Rhizophora mangle",
                "Larrea tridentata",
            ],
            "role": ["discovery", "discovery", "discovery", "validation", "validation"],
            "model_presence_count": [4, 8, 7, 6, 9],
        }
    )
    path = tmp_path / "roles.csv"
    roles.to_csv(path, index=False)
    loaded = _load_taxon_role_config(path)
    contract = {"seed": 20260814, "taxon_validation_fraction_for_future_search": 0.25}
    result = _validate_outcome_blind_panel(tmp_path, loaded, contract)

    assert result["panel_selection"] == "smallest_model_pool_occurrence_counts_only"
    assert result["expected_validation_taxa"] == ["Larrea tridentata", "Rhizophora mangle"]
    assert result["observed_model_presence_counts"]["Nothofagus pumilio"] == 4
    assert "Large taxon" not in result["expected_panel"]


def _discovery_metrics():
    rows = []
    for species in ("sp1", "sp2"):
        for perturbation in ("buffer_150km", "buffer_300km", "buffer_500km"):
            for fold in (0, 1):
                rows.append(
                    {
                        "species": species,
                        "candidate": "auc_method",
                        "strategy": "predictive_forward",
                        "perturbation": perturbation,
                        "perturbation_type": "sampling_or_background",
                        "fold": fold,
                        "presence_rank": 0.80,
                        "n_predictors": 2,
                        "niche_overlap_schoener_d_pc12": 0.60,
                        "centroid_distance": 0.40,
                        "breadth_log_sd_error": 0.30,
                        "quantile_profile_error": 0.35,
                    }
                )
                rows.append(
                    {
                        "species": species,
                        "candidate": "eco_method",
                        "strategy": "niche_forward",
                        "perturbation": perturbation,
                        "perturbation_type": "sampling_or_background",
                        "fold": fold,
                        "presence_rank": 0.70,
                        "n_predictors": 2,
                        "niche_overlap_schoener_d_pc12": 0.90,
                        "centroid_distance": 0.10,
                        "breadth_log_sd_error": 0.08,
                        "quantile_profile_error": 0.09,
                    }
                )
    return pd.DataFrame(rows)


def test_discovery_freeze_separates_auc_and_ecological_procedures():
    winners, errors, robust_selection, robust_cert = _freeze_discovery_selectors(
        _discovery_metrics(), canonical_spec="buffer_300km"
    )
    assert winners["canonical_auc"] == "auc_method"
    assert winners["canonical_ecology"] == "eco_method"
    assert winners["robust_ecology"] == "eco_method"
    assert errors == {
        "canonical_auc": None,
        "canonical_ecology": None,
        "robust_ecology": None,
    }
    assert robust_selection is not None
    assert robust_cert.status == "selected"


def test_taxon_role_loader_rejects_single_validation_taxon(tmp_path):
    path = tmp_path / "roles.csv"
    pd.DataFrame(
        {
            "scientific_name": ["a", "b", "c"],
            "role": ["discovery", "discovery", "validation"],
        }
    ).to_csv(path, index=False)
    try:
        _load_taxon_role_config(path)
    except SystemExit as exc:
        assert "at least two validation taxa" in str(exc)
    else:
        raise AssertionError("single validation taxon should be rejected")
