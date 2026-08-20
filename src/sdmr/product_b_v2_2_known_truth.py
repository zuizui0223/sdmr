"""Product-B v2.2 known-truth pipeline using frozen-representation ablation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import benchmark_recovery_procedures
from .product_b_v2 import pair_process_knockout_losses, repeat_process_core_splits, summarize_taxon_process_support
from .product_b_v2_2_frozen_ablation import frozen_representation_process_ablation
from .product_b_v2_2_known_truth_contract import (
    FROZEN_METHOD_SOURCE,
    load_product_b_v2_2_known_truth_contract,
)
from .product_b_v2_known_truth_audit import audit_product_b_v2_known_truth
from .product_b_v2_known_truth_contract import M_SPECS
from .product_b_v2_known_truth_method_worker import _require_structurally_evaluable_outer_folds
from .v2_1_known_truth_gate_ablation import (
    CANDIDATE_ECOLOGICAL_PREDICTORS,
    SimulatedTaxonSpec,
    _model_only_frame,
    _nested_background_perturbations,
    _procedure_library,
    _simulate_taxon,
)
from .validation import make_spatial_partition

FORBIDDEN = {"true_suitability", "sampling_effort", "focal_recording_multiplier"}
PROCESS_SHARD_PURPOSE = "product_b_v2_2_known_truth_process_shard_pretruth"
PRETRUTH_PURPOSE = "product_b_v2_2_known_truth_process_core_pretruth_freeze"
DECISION_PURPOSE = "product_b_v2_2_fresh_known_truth_decision"


def _load_frozen_method(method_dir: str | Path, contract: dict) -> dict:
    method = json.loads((Path(method_dir) / "contract.json").read_text(encoding="utf-8"))
    source = contract["frozen_product_a_method_source"]
    if source != FROZEN_METHOD_SOURCE:
        raise ValueError("v2.2 frozen method source contract changed")
    if method.get("purpose") != source["expected_purpose"]:
        raise ValueError("v2.2 method artifact purpose mismatch")
    if method.get("source_contract_sha256") != source["source_contract_sha256"]:
        raise ValueError("v2.2 method artifact source contract mismatch")
    if str(method.get("frozen_candidate")) != source["frozen_candidate"]:
        raise ValueError("v2.2 frozen candidate mismatch")
    if method.get("candidate_frozen_before_product_b_evaluation_taxa") is not True:
        raise ValueError("v2.2 method was not frozen before evaluation taxa")
    if method.get("product_b_evaluation_taxa_simulated_or_read") is not False:
        raise ValueError("v2.2 method source had already read evaluation taxa")
    if method.get("generating_truth_read") is not False:
        raise ValueError("v2.2 method source used generating truth")
    return method


def run_process_shard(
    *,
    contract_path: str | Path,
    method_dir: str | Path,
    taxon_index: int,
    m_index: int,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_product_b_v2_2_known_truth_contract(contract_path)
    method = _load_frozen_method(method_dir, contract)
    specs = contract["product_b_evaluation_taxa"]
    if not 0 <= int(taxon_index) < len(specs):
        raise ValueError("Product-B v2.2 taxon_index out of range")
    if not 0 <= int(m_index) < len(M_SPECS):
        raise ValueError("Product-B v2.2 m_index out of range")
    raw = specs[int(taxon_index)]
    spec = SimulatedTaxonSpec(str(raw["family"]), int(raw["seed"]), "product_b_v2_2_evaluation")
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
            raise AssertionError("generating truth crossed Product-B v2.2 process barrier")

    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_SPECS},
        CANDIDATE_ECOLOGICAL_PREDICTORS,
        minimum_coverage=float(simc["minimum_predictor_coverage"]),
    )
    predictors = tuple(admissibility.predictors)
    if not predictors:
        raise ValueError("Product-B v2.2 has no admissible ecological predictors")
    procedures = {
        p.label: p
        for p in _procedure_library(
            inner_folds=int(simc["inner_folds"]),
            max_predictors=int(simc["max_predictors"]),
        )
    }
    frozen_candidate = str(method["frozen_candidate"])
    if frozen_candidate not in procedures:
        raise ValueError("Product-B v2.2 frozen candidate is absent from procedure library")
    procedure = procedures[frozen_candidate]

    m_name = M_SPECS[int(m_index)]
    background = backgrounds[m_name]
    partition_contract = contract["partition_contract"]
    random_state = int(partition_contract["process_partition_seed_base"]) + int(taxon_index) * 10 + int(m_index)
    n_blocks = int(partition_contract["fixed_n_spatial_blocks"])
    partition = make_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=n_blocks,
        holdout_fraction=0.20,
        random_state=random_state,
    )
    _require_structurally_evaluable_outer_folds(
        occurrence,
        background,
        partition.presence_blocks,
        partition.background_blocks,
        outer_folds=int(simc["outer_folds"]),
    )

    base = benchmark_recovery_procedures(
        occurrence,
        background,
        partition.presence_blocks,
        partition.background_blocks,
        predictors,
        tuple(simulation.audit_predictors),
        (procedure,),
        outer_folds=int(simc["outer_folds"]),
        chance_auc=0.50,
        minimum_auc_margin=0.01,
        auc_sem_multiplier=1.0,
    ).fold_metrics.copy()
    expected_folds = set(range(int(simc["outer_folds"])))
    observed_base = set(pd.to_numeric(base["fold"], errors="coerce").dropna().astype(int))
    if observed_base != expected_folds or len(base) != len(expected_folds):
        raise ValueError(
            f"Product-B v2.2 base procedure is incomplete: expected={sorted(expected_folds)}, observed={sorted(observed_base)}"
        )
    base["taxon"] = spec.taxon
    base["M"] = m_name
    base["family"] = spec.family
    base["simulation_seed"] = spec.seed

    knockout = frozen_representation_process_ablation(
        occurrence,
        background,
        partition.presence_blocks,
        partition.background_blocks,
        base,
        tuple(simulation.audit_predictors),
        procedure,
        tuple(contract["ecological_process_universe"]),
        contract["process_predictor_aliases"],
        outer_folds=int(simc["outer_folds"]),
        observation_correction_active=False,
    )
    knockout["taxon"] = spec.taxon
    knockout["M"] = m_name
    knockout["family"] = spec.family
    knockout["simulation_seed"] = spec.seed
    for process, group in knockout.groupby("excluded_process_domain", sort=False):
        observed = set(pd.to_numeric(group["fold"], errors="coerce").dropna().astype(int))
        if observed != expected_folds or len(group) != len(expected_folds):
            raise ValueError(
                f"Product-B v2.2 frozen ablation incomplete for {process}: expected={sorted(expected_folds)}, observed={sorted(observed)}"
            )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base.to_csv(out / "base_fold_metrics.csv", index=False)
    knockout.to_csv(out / "knockout_fold_metrics.csv", index=False)
    admissibility.ledger.to_csv(out / "predictor_coverage.csv", index=False)
    result = {
        "purpose": PROCESS_SHARD_PURPOSE,
        "source_contract_sha256": contract["contract_sha256"],
        "frozen_method_source_artifact_id": int(FROZEN_METHOD_SOURCE["artifact_id"]),
        "frozen_method_source_artifact_digest": FROZEN_METHOD_SOURCE["artifact_digest"],
        "frozen_candidate": frozen_candidate,
        "taxon": spec.taxon,
        "family": spec.family,
        "simulation_seed": spec.seed,
        "taxon_index": int(taxon_index),
        "M": m_name,
        "m_index": int(m_index),
        "partition_seed": random_state,
        "n_spatial_blocks": n_blocks,
        "requested_outer_folds": int(simc["outer_folds"]),
        "all_requested_outer_folds_evaluable": True,
        "base_selected_predictors_frozen_before_process_drop": True,
        "predictor_reselection_after_process_drop": False,
        "same_outer_fold_partition_for_base_and_all_ablations": True,
        "admissibility_computed_across_all_frozen_M": True,
        "generating_truth_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def freeze_process_core(
    *, contract_path: str | Path, method_dir: str | Path, worker_root: str | Path, output_dir: str | Path
) -> dict[str, object]:
    contract = load_product_b_v2_2_known_truth_contract(contract_path)
    method = _load_frozen_method(method_dir, contract)
    frozen_candidate = str(method["frozen_candidate"])
    contracts: list[dict[str, object]] = []
    base_frames: list[pd.DataFrame] = []
    knockout_frames: list[pd.DataFrame] = []
    for path in sorted(Path(worker_root).rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != PROCESS_SHARD_PURPOSE:
            continue
        if row.get("source_contract_sha256") != contract["contract_sha256"]:
            raise ValueError("Product-B v2.2 process shard contract mismatch")
        if str(row.get("frozen_candidate")) != frozen_candidate:
            raise ValueError("Product-B v2.2 process shards mixed frozen candidates")
        for key in ("generating_truth_read", "real_empirical_data_read", "empirical_sealed_outcomes_read", "scientific_threshold_tuning_performed", "predictor_reselection_after_process_drop"):
            if row.get(key) is not False:
                raise ValueError(f"Product-B v2.2 pretruth barrier violated: {key}")
        for key in ("base_selected_predictors_frozen_before_process_drop", "same_outer_fold_partition_for_base_and_all_ablations", "all_requested_outer_folds_evaluable"):
            if row.get(key) is not True:
                raise ValueError(f"Product-B v2.2 frozen-ablation invariant failed: {key}")
        base = pd.read_csv(path.parent / "base_fold_metrics.csv")
        knockout = pd.read_csv(path.parent / "knockout_fold_metrics.csv")
        if base.empty or knockout.empty:
            raise ValueError(f"empty Product-B v2.2 shard metrics: {path.parent}")
        if not knockout["predictor_reselection_after_process_drop"].eq(False).all():
            raise ValueError("Product-B v2.2 knockout unexpectedly reselected predictors")
        if not knockout["frozen_representation_ablation"].eq(True).all():
            raise ValueError("Product-B v2.2 knockout lost frozen-representation semantics")
        contracts.append(row)
        base_frames.append(base)
        knockout_frames.append(knockout)

    taxa = tuple(contract["product_b_evaluation_taxon_names"])
    expected_keys = {(taxon, m) for taxon in taxa for m in M_SPECS}
    observed_keys = {(str(x["taxon"]), str(x["M"])) for x in contracts}
    if observed_keys != expected_keys or len(contracts) != len(expected_keys):
        raise ValueError("Product-B v2.2 taxon x M denominator is incomplete")
    base = pd.concat(base_frames, ignore_index=True)
    knockout = pd.concat(knockout_frames, ignore_index=True)
    outer_folds = int(contract["simulation_contract"]["outer_folds"])
    expected_folds = tuple(range(outer_folds))
    paired = pair_process_knockout_losses(
        base,
        knockout,
        frozen_candidate=frozen_candidate,
        expected_taxa=taxa,
        expected_M=M_SPECS,
        expected_folds=expected_folds,
    )
    rule = contract["process_constraint_rule"]
    taxon_process = summarize_taxon_process_support(
        paired,
        expected_M=M_SPECS,
        expected_folds=expected_folds,
        min_pareto_worsening_fraction=float(rule["min_pareto_worsening_fraction"]),
        max_pareto_improvement_fraction=float(rule["max_pareto_improvement_fraction"]),
    )
    expected_rows = len(taxa) * len(contract["ecological_process_universe"])
    if len(taxon_process) != expected_rows or not taxon_process["complete_M_fold_evidence"].astype(bool).all():
        raise ValueError("Product-B v2.2 process inference lacks complete M x fold evidence")

    universality = contract["universality_rule"]
    repeated = repeat_process_core_splits(
        taxon_process,
        seeds=tuple(int(x) for x in universality["split_seeds"]),
        validation_fraction=float(universality["validation_fraction"]),
        min_taxon_support_fraction=float(universality["min_taxon_support_fraction"]),
    )
    stability = repeated.process_stability.copy()
    stable_threshold = float(universality["stable_core_min_validation_confirmation_fraction"])
    stability["stable_universal_core"] = (
        pd.to_numeric(stability["validation_confirmation_stability"], errors="coerce")
        >= stable_threshold - 1e-12
    )
    stable_core = tuple(sorted(stability.loc[stability["stable_universal_core"], "process_domain"].astype(str)))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paired.to_csv(out / "paired_process_losses.csv", index=False)
    taxon_process.to_csv(out / "taxon_process_summary.csv", index=False)
    repeated.split_summary.to_csv(out / "universality_split_summary.csv", index=False)
    stability.to_csv(out / "process_stability.csv", index=False)
    result = {
        "purpose": PRETRUTH_PURPOSE,
        "source_contract_sha256": contract["contract_sha256"],
        "frozen_candidate": frozen_candidate,
        "frozen_method_source_artifact_id": int(FROZEN_METHOD_SOURCE["artifact_id"]),
        "n_process_shards": len(contracts),
        "n_taxa": len(taxa),
        "n_processes": len(contract["ecological_process_universe"]),
        "M_specs": list(M_SPECS),
        "outer_folds": outer_folds,
        "stable_core_threshold": stable_threshold,
        "stable_universal_core": list(stable_core),
        "all_M_x_fold_evidence_complete": True,
        "frozen_representation_ablation": True,
        "predictor_reselection_after_process_drop": False,
        "process_losses_frozen_before_generating_truth_audit": True,
        "generating_truth_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Product-B v2.2 known-truth stages.")
    sub = parser.add_subparsers(dest="stage", required=True)
    process = sub.add_parser("process-shard")
    process.add_argument("--contract", required=True)
    process.add_argument("--method-dir", required=True)
    process.add_argument("--taxon-index", type=int, required=True)
    process.add_argument("--m-index", type=int, required=True)
    process.add_argument("--output-dir", required=True)
    pretruth = sub.add_parser("pretruth-freeze")
    pretruth.add_argument("--contract", required=True)
    pretruth.add_argument("--method-dir", required=True)
    pretruth.add_argument("--worker-root", required=True)
    pretruth.add_argument("--output-dir", required=True)
    audit = sub.add_parser("truth-audit")
    audit.add_argument("--contract", required=True)
    audit.add_argument("--pretruth-dir", required=True)
    audit.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.stage == "process-shard":
        run_process_shard(
            contract_path=args.contract,
            method_dir=args.method_dir,
            taxon_index=args.taxon_index,
            m_index=args.m_index,
            output_dir=args.output_dir,
        )
    elif args.stage == "pretruth-freeze":
        freeze_process_core(
            contract_path=args.contract,
            method_dir=args.method_dir,
            worker_root=args.worker_root,
            output_dir=args.output_dir,
        )
    else:
        audit_product_b_v2_known_truth(
            contract_path=args.contract,
            pretruth_dir=args.pretruth_dir,
            output_dir=args.output_dir,
            contract_loader=load_product_b_v2_2_known_truth_contract,
            expected_pretruth_purpose=PRETRUTH_PURPOSE,
            result_purpose=DECISION_PURPOSE,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
