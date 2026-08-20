from pathlib import Path
import json

import pandas as pd

from sdmr.product_b_v2_known_truth_audit import audit_product_b_v2_known_truth
from sdmr.product_b_v2_known_truth_contract import (
    EVALUATION_SEEDS,
    METHOD_SEEDS,
    PROCESS_UNIVERSE,
    load_product_b_v2_known_truth_contract,
)

CONFIG = Path("configs/product_b_v2_known_truth_contract.json")


def test_product_b_v2_known_truth_contract_uses_fresh_disjoint_seeds():
    c = load_product_b_v2_known_truth_contract(CONFIG)
    assert tuple(x["seed"] for x in c["method_freeze_taxa"]) == METHOD_SEEDS
    assert tuple(x["seed"] for x in c["product_b_evaluation_taxa"]) == EVALUATION_SEEDS
    assert set(METHOD_SEEDS).isdisjoint(EVALUATION_SEEDS)
    assert min((*METHOD_SEEDS, *EVALUATION_SEEDS)) > 523
    assert tuple(c["ecological_process_universe"]) == PROCESS_UNIVERSE
    assert c["method_freeze"]["product_b_evaluation_taxa_simulated_before_freeze"] is False
    assert c["truth_opening_order"]["process_losses_frozen_before_generating_truth_audit"] is True


def _write_pretruth(tmp_path: Path, *, add_false_universal: bool = False) -> Path:
    c = load_product_b_v2_known_truth_contract(CONFIG)
    root = tmp_path / "pretruth"
    root.mkdir()
    (root / "contract.json").write_text(
        json.dumps({
            "purpose": "product_b_v2_known_truth_process_core_pretruth_freeze",
            "source_contract_sha256": c["contract_sha256"],
            "process_losses_frozen_before_generating_truth_audit": True,
            "generating_truth_read": False,
            "scientific_threshold_tuning_performed": False,
            "all_M_x_fold_evidence_complete": True,
        }) + "\n"
    )
    rows = []
    for spec in c["product_b_evaluation_taxa"]:
        taxon = f"{spec['family']}__seed{int(spec['seed'])}"
        true = {"temperature", "water"}
        if spec["family"] == "omitted_driver":
            true.add("soil")
        for process in PROCESS_UNIVERSE:
            rows.append({
                "taxon": taxon,
                "process_domain": process,
                "status": "supported_process_constraint" if process in true else "refuted_process_constraint",
                "complete_M_fold_evidence": True,
            })
    pd.DataFrame(rows).to_csv(root / "taxon_process_summary.csv", index=False)
    stability = []
    for process in PROCESS_UNIVERSE:
        value = 1.0 if process in {"temperature", "water"} else 0.0
        if add_false_universal and process == "seasonality":
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


def test_product_b_v2_truth_audit_supports_exact_process_recovery(tmp_path):
    pretruth = _write_pretruth(tmp_path)
    out = tmp_path / "out"
    result = audit_product_b_v2_known_truth(
        contract_path=CONFIG, pretruth_dir=pretruth, output_dir=out
    )
    decision = pd.read_csv(out / "decision.csv").iloc[0]
    assert result["decision"] == "product_b_v2_known_truth_supported"
    assert decision["universal_process_recall"] == 1.0
    assert decision["false_stable_universal_processes"] == 0
    assert decision["mean_taxon_process_recall"] == 1.0
    assert decision["mean_taxon_process_precision"] == 1.0
    assert result["product_b_formally_unblocked"] is False


def test_product_b_v2_truth_audit_rejects_false_stable_universal_process(tmp_path):
    pretruth = _write_pretruth(tmp_path, add_false_universal=True)
    out = tmp_path / "out"
    result = audit_product_b_v2_known_truth(
        contract_path=CONFIG, pretruth_dir=pretruth, output_dir=out
    )
    decision = pd.read_csv(out / "decision.csv").iloc[0]
    assert result["decision"] == "product_b_v2_known_truth_not_supported"
    assert decision["false_stable_universal_processes"] == 1
