from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from sdmr.model import ModelSpec
from sdmr.niche_recovery_procedure import RecoveryProcedure
from sdmr.product_b_v2_2_frozen_ablation import frozen_representation_process_ablation
from sdmr.product_b_v2_2_known_truth_contract import (
    EVALUATION_SEEDS,
    EXCLUDED_MODEL_ONLY_SEEDS,
    FROZEN_METHOD_SOURCE,
    load_product_b_v2_2_known_truth_contract,
)
from sdmr.product_b_v2_2_known_truth import DECISION_PURPOSE, PRETRUTH_PURPOSE
from sdmr.product_b_v2_known_truth_audit import audit_product_b_v2_known_truth

CONFIG = Path("configs/product_b_v2_2_known_truth_contract.json")


def test_v22_contract_freezes_method_and_uses_fresh_taxa_without_relaxing_thresholds():
    c = load_product_b_v2_2_known_truth_contract(CONFIG)
    assert tuple(x["seed"] for x in c["product_b_evaluation_taxa"]) == EVALUATION_SEEDS
    assert set(EVALUATION_SEEDS).isdisjoint(EXCLUDED_MODEL_ONLY_SEEDS)
    assert c["frozen_product_a_method_source"] == FROZEN_METHOD_SOURCE
    assert all(x["generating_process_truth_opened"] is False for x in c["successor_history"])
    semantics = c["process_ablation_semantics"]
    assert semantics["base_selected_predictors_are_frozen_within_outer_fold"] is True
    assert semantics["predictor_reselection_after_process_drop"] is False
    assert semantics["compensated_reoptimization_is_not_used_for_core_process_support"] is True
    assert c["process_constraint_rule"]["min_pareto_worsening_fraction"] == pytest.approx(2 / 3)
    assert c["process_constraint_rule"]["max_pareto_improvement_fraction"] == pytest.approx(1 / 3)
    assert c["supported_result_requires"]["mean_taxon_process_recall_minimum"] == 0.9
    assert c["supported_result_requires"]["mean_taxon_process_precision_minimum"] == 0.8


def _toy_frames():
    rng = np.random.default_rng(17)
    p_groups = np.repeat(np.arange(4), 10)
    b_groups = np.repeat(np.arange(4), 20)
    p = pd.DataFrame({
        "temperature": rng.normal(1.0, 0.7, len(p_groups)),
        "water": rng.normal(0.8, 0.8, len(p_groups)),
        "recording_bias": rng.normal(0.2, 1.0, len(p_groups)),
    })
    b = pd.DataFrame({
        "temperature": rng.normal(0.0, 1.0, len(b_groups)),
        "water": rng.normal(0.0, 1.0, len(b_groups)),
        "recording_bias": rng.normal(0.0, 1.0, len(b_groups)),
    })
    return p, b, p_groups, b_groups


def test_frozen_ablation_removes_process_from_base_selection_without_reselection():
    p, b, pg, bg = _toy_frames()
    procedure = RecoveryProcedure(
        "all",
        ModelSpec(C=1.0, degree=1, penalty="l2"),
        inner_folds=2,
        max_predictors=3,
        predictive_min_gain=0.0,
        observation_predictors=("recording_bias",),
    )
    base = pd.DataFrame([
        {"fold": 0, "candidate": procedure.label, "selected_predictors": "temperature,water,recording_bias"},
        {"fold": 1, "candidate": procedure.label, "selected_predictors": "temperature,water,recording_bias"},
    ])
    result = frozen_representation_process_ablation(
        p,
        b,
        pg,
        bg,
        base,
        ("temperature", "water"),
        procedure,
        ("temperature", "water", "soil"),
        {"temperature": "temperature", "water": "water", "recording_bias": "observation_process"},
        outer_folds=2,
    )
    assert len(result) == 6
    assert result["predictor_reselection_after_process_drop"].eq(False).all()
    assert result["frozen_representation_ablation"].eq(True).all()
    for _, group in result.groupby("excluded_process_domain"):
        assert set(group["fold"].astype(int)) == {0, 1}
    temp = result.loc[result["excluded_process_domain"].eq("temperature")]
    assert temp["excluded_predictors"].eq("temperature").all()
    assert temp["selected_predictors"].eq("water,recording_bias").all()
    water = result.loc[result["excluded_process_domain"].eq("water")]
    assert water["selected_predictors"].eq("temperature,recording_bias").all()
    soil = result.loc[result["excluded_process_domain"].eq("soil")]
    assert soil["excluded_predictors"].eq("").all()
    assert soil["selected_predictors"].eq("temperature,water,recording_bias").all()


def _write_pretruth(tmp_path: Path, *, false_stable: bool = False) -> Path:
    c = load_product_b_v2_2_known_truth_contract(CONFIG)
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


def test_v22_truth_audit_keeps_empirical_b_blocked_even_when_known_truth_supported(tmp_path):
    root = _write_pretruth(tmp_path)
    out = tmp_path / "out"
    result = audit_product_b_v2_known_truth(
        contract_path=CONFIG,
        pretruth_dir=root,
        output_dir=out,
        contract_loader=load_product_b_v2_2_known_truth_contract,
        expected_pretruth_purpose=PRETRUTH_PURPOSE,
        result_purpose=DECISION_PURPOSE,
    )
    decision = pd.read_csv(out / "decision.csv").iloc[0]
    assert result["purpose"] == DECISION_PURPOSE
    assert result["decision"] == "product_b_v2_known_truth_supported"
    assert decision["universal_process_recall"] == 1.0
    assert decision["mean_taxon_process_precision"] == 1.0
    assert result["product_b_formally_unblocked"] is False


def test_v22_truth_audit_rejects_false_stable_process(tmp_path):
    root = _write_pretruth(tmp_path, false_stable=True)
    out = tmp_path / "out"
    result = audit_product_b_v2_known_truth(
        contract_path=CONFIG,
        pretruth_dir=root,
        output_dir=out,
        contract_loader=load_product_b_v2_2_known_truth_contract,
        expected_pretruth_purpose=PRETRUTH_PURPOSE,
        result_purpose=DECISION_PURPOSE,
    )
    decision = pd.read_csv(out / "decision.csv").iloc[0]
    assert result["decision"] == "product_b_v2_known_truth_not_supported"
    assert decision["false_stable_universal_processes"] == 1
