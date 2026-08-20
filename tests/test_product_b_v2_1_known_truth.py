from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from sdmr.product_b_v2_1_known_truth import DECISION_PURPOSE, PRETRUTH_PURPOSE
from sdmr.product_b_v2_1_known_truth_contract import (
    EVALUATION_SEEDS,
    EXCLUDED_V20_EVALUATION_SEEDS,
    METHOD_SEEDS,
    load_product_b_v2_1_known_truth_contract,
)
from sdmr.product_b_v2_known_truth_audit import audit_product_b_v2_known_truth
from sdmr.product_b_v2_known_truth_contract import load_product_b_v2_known_truth_contract
from sdmr.product_b_v2_known_truth_method_worker import _require_structurally_evaluable_outer_folds

CONFIG = Path("configs/product_b_v2_1_known_truth_contract.json")
OLD_CONFIG = Path("configs/product_b_v2_known_truth_contract.json")


def test_v21_contract_uses_new_unopened_taxa_and_preserves_scientific_gate():
    c = load_product_b_v2_1_known_truth_contract(CONFIG)
    assert tuple(x["seed"] for x in c["method_freeze_taxa"]) == METHOD_SEEDS
    assert tuple(x["seed"] for x in c["product_b_evaluation_taxa"]) == EVALUATION_SEEDS
    assert set(METHOD_SEEDS).isdisjoint(EVALUATION_SEEDS)
    assert set(EVALUATION_SEEDS).isdisjoint(EXCLUDED_V20_EVALUATION_SEEDS)
    assert min((*METHOD_SEEDS, *EVALUATION_SEEDS)) > max(EXCLUDED_V20_EVALUATION_SEEDS)
    assert c["successor_to_failed_pretruth_run"]["generating_process_truth_opened"] is False
    p = c["partition_contract"]
    assert p["fixed_n_spatial_blocks"] == 8
    assert p["partition_search_or_reselection"] is False
    assert p["partition_uses_coordinates_only"] is True
    assert p["partition_uses_generating_truth"] is False
    assert p["partition_uses_niche_recovery_scores"] is False
    assert p["all_requested_outer_folds_must_be_evaluable"] is True
    assert c["process_constraint_rule"]["min_pareto_worsening_fraction"] == pytest.approx(2 / 3)
    assert c["process_constraint_rule"]["max_pareto_improvement_fraction"] == pytest.approx(1 / 3)
    assert c["supported_result_requires"]["mean_taxon_process_recall_minimum"] == 0.9
    assert c["supported_result_requires"]["mean_taxon_process_precision_minimum"] == 0.8


def test_structural_outer_fold_guard_requires_background_in_both_folds():
    occurrence = pd.DataFrame({"x": range(8)})
    presence_groups = np.repeat(np.arange(4), 2)
    background = pd.DataFrame({"x": range(20)})
    background_groups = np.repeat(np.arange(4), 5)
    _require_structurally_evaluable_outer_folds(
        occurrence,
        background,
        presence_groups,
        background_groups,
        outer_folds=2,
    )

    bad_background = pd.DataFrame({"x": range(10)})
    bad_groups = np.zeros(10, dtype=int)
    with pytest.raises(ValueError, match="partition cannot support"):
        _require_structurally_evaluable_outer_folds(
            occurrence,
            bad_background,
            presence_groups,
            bad_groups,
            outer_folds=2,
        )


def test_old_v20_contract_still_loads_unchanged():
    old = load_product_b_v2_known_truth_contract(OLD_CONFIG)
    assert old["purpose"] == "product_b_v2_predeclared_fresh_known_truth_validation"
    assert tuple(x["seed"] for x in old["product_b_evaluation_taxa"]) == tuple(range(611, 623))


def _write_pretruth(tmp_path: Path, *, false_stable: bool = False) -> Path:
    c = load_product_b_v2_1_known_truth_contract(CONFIG)
    root = tmp_path / "pretruth"
    root.mkdir()
    (root / "contract.json").write_text(json.dumps({
        "purpose": PRETRUTH_PURPOSE,
        "source_contract_sha256": c["contract_sha256"],
        "process_losses_frozen_before_generating_truth_audit": True,
        "generating_truth_read": False,
        "scientific_threshold_tuning_performed": False,
        "all_M_x_fold_evidence_complete": True,
    }) + "\n", encoding="utf-8")
    rows = []
    for spec in c["product_b_evaluation_taxa"]:
        taxon = f"{spec['family']}__seed{int(spec['seed'])}"
        true = {"temperature", "water"}
        if spec["family"] == "omitted_driver":
            true.add("soil")
        for process in c["ecological_process_universe"]:
            rows.append({
                "taxon": taxon,
                "process_domain": process,
                "status": "supported_process_constraint" if process in true else "refuted_process_constraint",
                "complete_M_fold_evidence": True,
            })
    pd.DataFrame(rows).to_csv(root / "taxon_process_summary.csv", index=False)
    stability = []
    for process in c["ecological_process_universe"]:
        value = 1.0 if process in {"temperature", "water"} else 0.0
        if false_stable and process == "seasonality":
            value = 1.0
        stability.append({
            "process_domain": process,
            "n_splits": 5,
            "discovery_core_stability": value,
            "validation_confirmation_stability": value,
            "mean_validation_support_fraction": value,
            "mean_validation_refuted_fraction": 1.0 - value,
        })
    pd.DataFrame(stability).to_csv(root / "process_stability.csv", index=False)
    return root


def test_v21_truth_audit_supports_exact_recovery_without_unblocking_empirical_b(tmp_path):
    root = _write_pretruth(tmp_path)
    out = tmp_path / "out"
    result = audit_product_b_v2_known_truth(
        contract_path=CONFIG,
        pretruth_dir=root,
        output_dir=out,
        contract_loader=load_product_b_v2_1_known_truth_contract,
        expected_pretruth_purpose=PRETRUTH_PURPOSE,
        result_purpose=DECISION_PURPOSE,
    )
    decision = pd.read_csv(out / "decision.csv").iloc[0]
    assert result["purpose"] == DECISION_PURPOSE
    assert result["decision"] == "product_b_v2_known_truth_supported"
    assert decision["universal_process_recall"] == 1.0
    assert decision["false_stable_universal_processes"] == 0
    assert decision["mean_taxon_process_recall"] == 1.0
    assert decision["mean_taxon_process_precision"] == 1.0
    assert result["product_b_formally_unblocked"] is False


def test_v21_truth_audit_rejects_false_stable_universal_process(tmp_path):
    root = _write_pretruth(tmp_path, false_stable=True)
    out = tmp_path / "out"
    result = audit_product_b_v2_known_truth(
        contract_path=CONFIG,
        pretruth_dir=root,
        output_dir=out,
        contract_loader=load_product_b_v2_1_known_truth_contract,
        expected_pretruth_purpose=PRETRUTH_PURPOSE,
        result_purpose=DECISION_PURPOSE,
    )
    decision = pd.read_csv(out / "decision.csv").iloc[0]
    assert result["decision"] == "product_b_v2_known_truth_not_supported"
    assert decision["false_stable_universal_processes"] == 1
