import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.preoutcome_artifact_normalization import (
    normalize_preoutcome_model_pool_artifact,
)


def _write_contract(root: Path, **overrides):
    contract = {
        "development_evidence": "discovery_taxa_model_pool_only",
        "old_external_sealed_outcomes_read": False,
        "sealed_rows_returned_to_experiment": False,
        "scientific_promotion_run": False,
    }
    contract.update(overrides)
    (root / "product_a_v2_1_preoutcome_contract.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )


def _write_metrics(root: Path, **extra_columns):
    data = {
        "candidate": ["candidate_a"],
        "species": ["sp1"],
        "perturbation": ["m300"],
        "fold": [0],
        "presence_rank": [0.7],
        "n_sealed_occurrences": [12],
        "sealed_pc12_envelope_coverage90": [0.8],
    }
    data.update(extra_columns)
    pd.DataFrame(data).to_csv(root / "procedure_fold_metrics.csv", index=False)


def test_known_model_pool_outer_cv_labels_are_renamed(tmp_path):
    _write_contract(tmp_path)
    _write_metrics(tmp_path)

    result = normalize_preoutcome_model_pool_artifact(tmp_path)
    metrics = pd.read_csv(tmp_path / "procedure_fold_metrics.csv")

    assert result.model_pool_only_contract_verified
    assert result.renamed_columns == (
        "n_sealed_occurrences",
        "sealed_pc12_envelope_coverage90",
    )
    assert "n_sealed_occurrences" not in metrics.columns
    assert "sealed_pc12_envelope_coverage90" not in metrics.columns
    assert metrics.loc[0, "n_outer_heldout_occurrences"] == 12
    assert metrics.loc[0, "heldout_pc12_envelope_coverage90"] == 0.8


def test_normalization_rejects_contract_that_read_authoritative_sealed_rows(tmp_path):
    _write_contract(tmp_path, sealed_rows_returned_to_experiment=True)
    _write_metrics(tmp_path)

    with pytest.raises(ValueError, match="not a verified model-pool-only"):
        normalize_preoutcome_model_pool_artifact(tmp_path)


def test_unknown_sealed_metric_is_never_allowlisted(tmp_path):
    _write_contract(tmp_path)
    _write_metrics(tmp_path, sealed_presence_rank=[0.9])

    with pytest.raises(ValueError, match="unknown sealed-looking"):
        normalize_preoutcome_model_pool_artifact(tmp_path)
