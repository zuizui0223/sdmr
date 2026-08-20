"""Model-only Product-A method-freeze shard for Product-B known truth."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import benchmark_recovery_procedures
from .product_b_v2_known_truth_contract import load_product_b_v2_known_truth_contract
from .v2_1_known_truth_gate_ablation import (
    CANDIDATE_ECOLOGICAL_PREDICTORS,
    M_SPECS,
    SimulatedTaxonSpec,
    _model_only_frame,
    _nested_background_perturbations,
    _procedure_library,
    _simulate_taxon,
)
from .validation import make_spatial_partition

FORBIDDEN = {"true_suitability", "sampling_effort", "focal_recording_multiplier"}
ContractLoader = Callable[[str | Path], dict]


def _require_structurally_evaluable_outer_folds(
    occurrence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    *,
    outer_folds: int,
) -> None:
    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(np.unique(p_groups)) < int(outer_folds):
        raise ValueError("partition has fewer presence blocks than requested outer folds")
    splitter = GroupKFold(n_splits=int(outer_folds))
    dummy = np.zeros(len(occurrence), dtype=int)
    observed = 0
    for train_idx, test_idx in splitter.split(dummy, groups=p_groups):
        train_blocks = np.unique(p_groups[train_idx])
        test_blocks = np.unique(p_groups[test_idx])
        bg_train = np.isin(b_groups, train_blocks)
        bg_test = np.isin(b_groups, test_blocks)
        if bg_train.sum() < 5 or bg_test.sum() < 5 or len(test_idx) < 2:
            raise ValueError(
                "partition cannot support every requested outer fold with >=5 matched background rows and >=2 held-out presences"
            )
        observed += 1
    if observed != int(outer_folds):
        raise ValueError("partition did not yield the requested number of structurally evaluable outer folds")


def run_method_freeze_shard(
    *,
    contract_path: str | Path,
    taxon_index: int,
    m_index: int,
    output_dir: str | Path,
    contract_loader: ContractLoader = load_product_b_v2_known_truth_contract,
) -> dict[str, object]:
    contract = contract_loader(contract_path)
    specs = contract["method_freeze_taxa"]
    if not 0 <= int(taxon_index) < len(specs):
        raise ValueError("method-freeze taxon_index out of range")
    if not 0 <= int(m_index) < len(M_SPECS):
        raise ValueError("method-freeze m_index out of range")
    raw = specs[int(taxon_index)]
    spec = SimulatedTaxonSpec(str(raw["family"]), int(raw["seed"]), "method_freeze")
    simc = contract["simulation_contract"]
    simulation = _simulate_taxon(
        spec,
        n_cells=int(simc["n_cells"]),
        n_occurrences=int(simc["n_occurrences"]),
        n_target_group=int(simc["n_target_group"]),
    )
    occurrence = _model_only_frame(simulation.occurrences).reset_index(drop=True)
    backgrounds = {
        name: _model_only_frame(frame).reset_index(drop=True)
        for name, frame in _nested_background_perturbations(simulation).items()
    }
    for frame in (occurrence, *backgrounds.values()):
        if FORBIDDEN & set(frame.columns):
            raise AssertionError("generating truth crossed method-freeze barrier")
    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_SPECS},
        CANDIDATE_ECOLOGICAL_PREDICTORS,
        minimum_coverage=float(simc["minimum_predictor_coverage"]),
    )
    if not admissibility.predictors:
        raise ValueError("no admissible ecological predictors")
    procedures = _procedure_library(
        inner_folds=int(simc["inner_folds"]),
        max_predictors=int(simc["max_predictors"]),
    )
    m_name = M_SPECS[int(m_index)]
    background = backgrounds[m_name]
    partition_contract = contract.get("partition_contract", {})
    random_state = int(partition_contract.get("method_partition_seed_base", 720000)) + int(taxon_index) * 10 + int(m_index)
    n_blocks = int(partition_contract.get("fixed_n_spatial_blocks", max(4, int(simc["outer_folds"]) + 1)))
    partition = make_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=n_blocks,
        holdout_fraction=0.20,
        random_state=random_state,
    )
    if partition_contract.get("all_requested_outer_folds_must_be_evaluable") is True:
        _require_structurally_evaluable_outer_folds(
            occurrence,
            background,
            partition.presence_blocks,
            partition.background_blocks,
            outer_folds=int(simc["outer_folds"]),
        )
    benchmark = benchmark_recovery_procedures(
        occurrence,
        background,
        partition.presence_blocks,
        partition.background_blocks,
        tuple(admissibility.predictors),
        tuple(simulation.audit_predictors),
        procedures,
        outer_folds=int(simc["outer_folds"]),
        chance_auc=float(contract["method_freeze"]["prediction_adequacy"]["chance_auc"]),
        minimum_auc_margin=float(contract["method_freeze"]["prediction_adequacy"]["minimum_auc_margin"]),
        auc_sem_multiplier=float(contract["method_freeze"]["prediction_adequacy"]["auc_sem_multiplier"]),
    )
    metrics = benchmark.fold_metrics.copy()
    if metrics.empty:
        raise ValueError("method-freeze shard produced no fold metrics")
    metrics["taxon"] = spec.taxon
    metrics["species"] = spec.taxon
    metrics["M"] = m_name
    metrics["perturbation"] = m_name
    metrics["family"] = spec.family
    metrics["simulation_seed"] = spec.seed

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(out / "base_fold_metrics.csv", index=False)
    admissibility.ledger.to_csv(out / "predictor_coverage.csv", index=False)
    result = {
        "purpose": "product_b_v2_known_truth_method_freeze_shard",
        "contract_sha256": contract["contract_sha256"],
        "taxon": spec.taxon,
        "family": spec.family,
        "simulation_seed": spec.seed,
        "taxon_index": int(taxon_index),
        "M": m_name,
        "m_index": int(m_index),
        "n_procedures": len(procedures),
        "n_admissible_predictors": len(admissibility.predictors),
        "admissible_predictors": list(admissibility.predictors),
        "partition_seed": random_state,
        "n_spatial_blocks": n_blocks,
        "requested_outer_folds": int(simc["outer_folds"]),
        "partition_structurally_supports_all_requested_outer_folds": True,
        "generating_truth_read": False,
        "product_b_evaluation_taxa_simulated_or_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--taxon-index", type=int, required=True)
    parser.add_argument("--m-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_method_freeze_shard(
        contract_path=args.contract,
        taxon_index=args.taxon_index,
        m_index=args.m_index,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
