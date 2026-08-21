"""Product-B v3: A-conditioned universal process validation on fresh known truth.

Product B consumes Product A's *selection algorithm*, not one candidate frozen on
an unrelated cohort.  The fresh cohort is first benchmarked with the frozen
Product-A candidate pool while generating process truth remains hidden.  A single
complete prediction-adequate niche-recovery representative is then frozen across
all taxa and M specifications.  Only after that freeze does Product B ablate
process domains from the already selected outer-fold representations without
predictor reselection.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import benchmark_recovery_procedures
from .niche_recovery_selection import RECOVERY_DIRECTIONS, select_generalization_gated_niche_recovery_protocol
from .product_b_v2 import pair_process_knockout_losses, repeat_process_core_splits, summarize_taxon_process_support
from .product_b_v2_2_frozen_ablation import frozen_representation_process_ablation
from .product_b_v2_known_truth_audit import audit_product_b_v2_known_truth
from .product_b_v2_known_truth_contract import M_SPECS
from .product_b_v2_known_truth_method_worker import _require_structurally_evaluable_outer_folds
from .product_b_v3_known_truth_contract import load_product_b_v3_known_truth_contract
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
A_SHARD_PURPOSE = "product_b_v3_product_a_model_pool_shard_pretruth"
A_FREEZE_PURPOSE = "product_b_v3_product_a_representative_pretruth_freeze"
B_SHARD_PURPOSE = "product_b_v3_process_shard_pretruth"
B_PRETRUTH_PURPOSE = "product_b_v3_process_core_pretruth_freeze"
DECISION_PURPOSE = "product_b_v3_fresh_known_truth_decision"


def _simulation_and_partition(contract: dict, taxon_index: int, m_index: int):
    specs = contract["product_b_evaluation_taxa"]
    if not 0 <= int(taxon_index) < len(specs):
        raise ValueError("Product-B v3 taxon_index out of range")
    if not 0 <= int(m_index) < len(M_SPECS):
        raise ValueError("Product-B v3 m_index out of range")
    raw = specs[int(taxon_index)]
    spec = SimulatedTaxonSpec(str(raw["family"]), int(raw["seed"]), "product_b_v3_evaluation")
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
            raise AssertionError("generating truth crossed Product-B v3 model barrier")
    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_SPECS},
        CANDIDATE_ECOLOGICAL_PREDICTORS,
        minimum_coverage=float(simc["minimum_predictor_coverage"]),
    )
    predictors = tuple(admissibility.predictors)
    if not predictors:
        raise ValueError("Product-B v3 has no admissible ecological predictors")
    m_name = M_SPECS[int(m_index)]
    background = backgrounds[m_name]
    pc = contract["partition_contract"]
    random_state = int(pc["partition_seed_base"]) + int(taxon_index) * 10 + int(m_index)
    partition = make_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=int(pc["fixed_n_spatial_blocks"]),
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
    return spec, simulation, occurrence, backgrounds, predictors, admissibility, m_name, background, partition, random_state


def run_product_a_shard(*, contract_path: str | Path, taxon_index: int, m_index: int, output_dir: str | Path) -> dict[str, object]:
    contract = load_product_b_v3_known_truth_contract(contract_path)
    spec, simulation, occurrence, _, predictors, admissibility, m_name, background, partition, random_state = _simulation_and_partition(
        contract, taxon_index, m_index
    )
    simc = contract["simulation_contract"]
    selector = contract["product_a_selector"]
    procedures = _procedure_library(
        inner_folds=int(simc["inner_folds"]),
        max_predictors=int(simc["max_predictors"]),
    )
    benchmark = benchmark_recovery_procedures(
        occurrence,
        background,
        partition.presence_blocks,
        partition.background_blocks,
        predictors,
        tuple(simulation.audit_predictors),
        procedures,
        outer_folds=int(simc["outer_folds"]),
        chance_auc=float(selector["chance_auc"]),
        minimum_auc_margin=float(selector["minimum_auc_margin"]),
        auc_sem_multiplier=float(selector["auc_sem_multiplier"]),
    )
    metrics = benchmark.fold_metrics.copy()
    if metrics.empty:
        raise ValueError("Product-B v3 Product-A benchmark produced no fold metrics")
    metrics["taxon"] = spec.taxon
    metrics["M"] = m_name
    metrics["family"] = spec.family
    metrics["simulation_seed"] = spec.seed

    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(out / "base_fold_metrics.csv", index=False)
    benchmark.selection_trace.to_csv(out / "selection_trace.csv", index=False)
    admissibility.ledger.to_csv(out / "predictor_coverage.csv", index=False)
    result = {
        "purpose": A_SHARD_PURPOSE,
        "source_contract_sha256": contract["contract_sha256"],
        "taxon": spec.taxon,
        "family": spec.family,
        "simulation_seed": spec.seed,
        "taxon_index": int(taxon_index),
        "M": m_name,
        "m_index": int(m_index),
        "partition_seed": random_state,
        "n_spatial_blocks": int(contract["partition_contract"]["fixed_n_spatial_blocks"]),
        "requested_outer_folds": int(simc["outer_folds"]),
        "admissible_predictors": list(predictors),
        "n_candidate_procedures": len(procedures),
        "product_a_representative_selected": False,
        "product_b_process_ablation_outcomes_read": False,
        "generating_truth_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def freeze_product_a_representative(*, contract_path: str | Path, worker_root: str | Path, output_dir: str | Path) -> dict[str, object]:
    contract = load_product_b_v3_known_truth_contract(contract_path)
    taxa = tuple(contract["product_b_evaluation_taxon_names"])
    contracts: list[dict] = []
    frames: list[pd.DataFrame] = []
    for path in sorted(Path(worker_root).rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != A_SHARD_PURPOSE:
            continue
        if row.get("source_contract_sha256") != contract["contract_sha256"]:
            raise ValueError("Product-B v3 Product-A shard contract mismatch")
        for key in ("product_b_process_ablation_outcomes_read", "generating_truth_read", "real_empirical_data_read", "empirical_sealed_outcomes_read", "scientific_threshold_tuning_performed"):
            if row.get(key) is not False:
                raise ValueError(f"Product-B v3 Product-A information barrier violated: {key}")
        frame = pd.read_csv(path.parent / "base_fold_metrics.csv")
        if frame.empty:
            raise ValueError(f"empty Product-A shard: {path.parent}")
        contracts.append(row); frames.append(frame)
    expected = {(taxon, m) for taxon in taxa for m in M_SPECS}
    observed = {(str(x["taxon"]), str(x["M"])) for x in contracts}
    if observed != expected or len(contracts) != len(expected):
        raise ValueError("Product-B v3 Product-A taxon x M denominator is incomplete")
    base = pd.concat(frames, ignore_index=True)
    decorated = base.copy()
    decorated["species"] = decorated["taxon"].astype(str)
    decorated["perturbation"] = decorated["M"].astype(str)
    outer_folds = int(contract["simulation_contract"]["outer_folds"])
    complete = require_complete_outer_fold_evidence(
        decorated,
        discovery_taxa=taxa,
        perturbations=M_SPECS,
        required_columns=("presence_rank", *tuple(RECOVERY_DIRECTIONS)),
        expected_outer_folds=outer_folds,
    )
    if not complete.eligible_candidates:
        raise ValueError("Product-B v3 upstream Product-A selector has no complete candidate across the fresh cohort")
    complete_metrics = base.loc[base["candidate"].astype(str).isin(complete.eligible_candidates)].copy()
    selector = contract["product_a_selector"]
    ecological = select_generalization_gated_niche_recovery_protocol(
        complete_metrics,
        chance_auc=float(selector["chance_auc"]),
        minimum_auc_margin=float(selector["minimum_auc_margin"]),
        auc_sem_multiplier=float(selector["auc_sem_multiplier"]),
    )
    candidate = str(ecological.candidate)
    if candidate not in set(complete.eligible_candidates):
        raise AssertionError("Product-A selector returned a candidate outside complete evidence")

    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    complete.cell_ledger.to_csv(out / "product_a_complete_cell_ledger.csv", index=False)
    complete.candidate_summary.to_csv(out / "product_a_complete_candidate_summary.csv", index=False)
    ecological.gate_summary.to_csv(out / "product_a_prediction_adequacy_gate.csv", index=False)
    ecological.recovery_selection.summary.to_csv(out / "product_a_ecological_selection.csv", index=False)
    pd.DataFrame(contracts).to_csv(out / "product_a_shard_contracts.csv", index=False)
    result = {
        "purpose": A_FREEZE_PURPOSE,
        "source_contract_sha256": contract["contract_sha256"],
        "n_product_a_shards": len(contracts),
        "n_taxa": len(taxa),
        "M_specs": list(M_SPECS),
        "outer_folds": outer_folds,
        "complete_candidates": list(complete.eligible_candidates),
        "product_a_representative": candidate,
        "product_a_representative_frozen_before_any_product_b_process_ablation": True,
        "product_b_process_ablation_outcomes_read": False,
        "generating_truth_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_process_shard(*, contract_path: str | Path, product_a_freeze_dir: str | Path, product_a_shard_dir: str | Path, taxon_index: int, m_index: int, output_dir: str | Path) -> dict[str, object]:
    contract = load_product_b_v3_known_truth_contract(contract_path)
    freeze = json.loads((Path(product_a_freeze_dir) / "contract.json").read_text(encoding="utf-8"))
    if freeze.get("purpose") != A_FREEZE_PURPOSE or freeze.get("source_contract_sha256") != contract["contract_sha256"]:
        raise ValueError("Product-B v3 requires the frozen Product-A representative")
    if freeze.get("product_a_representative_frozen_before_any_product_b_process_ablation") is not True:
        raise ValueError("Product-A representative was not frozen before Product-B")
    if freeze.get("product_b_process_ablation_outcomes_read") is not False or freeze.get("generating_truth_read") is not False:
        raise ValueError("Product-A representative freeze crossed a Product-B/truth barrier")
    frozen_candidate = str(freeze["product_a_representative"])

    base_contract = json.loads((Path(product_a_shard_dir) / "contract.json").read_text(encoding="utf-8"))
    if base_contract.get("purpose") != A_SHARD_PURPOSE or base_contract.get("source_contract_sha256") != contract["contract_sha256"]:
        raise ValueError("Product-B v3 base shard mismatch")
    if int(base_contract.get("taxon_index", -1)) != int(taxon_index) or int(base_contract.get("m_index", -1)) != int(m_index):
        raise ValueError("Product-B v3 base shard cell mismatch")

    spec, simulation, occurrence, _, _, _, m_name, background, partition, random_state = _simulation_and_partition(contract, taxon_index, m_index)
    if str(base_contract.get("taxon")) != spec.taxon or str(base_contract.get("M")) != m_name or int(base_contract.get("partition_seed", -1)) != random_state:
        raise ValueError("Product-B v3 base shard provenance mismatch")
    simc = contract["simulation_contract"]
    procedures = {p.label: p for p in _procedure_library(inner_folds=int(simc["inner_folds"]), max_predictors=int(simc["max_predictors"]))}
    if frozen_candidate not in procedures:
        raise ValueError("frozen Product-A representative is absent from candidate library")
    procedure = procedures[frozen_candidate]
    all_base = pd.read_csv(Path(product_a_shard_dir) / "base_fold_metrics.csv")
    base = all_base.loc[all_base["candidate"].astype(str).eq(frozen_candidate)].copy()
    expected_folds = set(range(int(simc["outer_folds"])))
    observed_folds = set(pd.to_numeric(base["fold"], errors="coerce").dropna().astype(int))
    if observed_folds != expected_folds or len(base) != len(expected_folds):
        raise ValueError("frozen Product-A representative lost complete fold evidence after freeze")

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
    base["taxon"] = spec.taxon; base["M"] = m_name; base["family"] = spec.family; base["simulation_seed"] = spec.seed
    knockout["taxon"] = spec.taxon; knockout["M"] = m_name; knockout["family"] = spec.family; knockout["simulation_seed"] = spec.seed
    for process, group in knockout.groupby("excluded_process_domain", sort=False):
        observed = set(pd.to_numeric(group["fold"], errors="coerce").dropna().astype(int))
        if observed != expected_folds or len(group) != len(expected_folds):
            raise ValueError(f"Product-B v3 ablation denominator incomplete for {process}")

    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    base.to_csv(out / "base_fold_metrics.csv", index=False)
    knockout.to_csv(out / "knockout_fold_metrics.csv", index=False)
    result = {
        "purpose": B_SHARD_PURPOSE,
        "source_contract_sha256": contract["contract_sha256"],
        "frozen_product_a_representative": frozen_candidate,
        "taxon": spec.taxon,
        "family": spec.family,
        "simulation_seed": spec.seed,
        "taxon_index": int(taxon_index),
        "M": m_name,
        "m_index": int(m_index),
        "partition_seed": random_state,
        "product_a_base_fold_representation_reused": True,
        "predictor_reselection_after_process_drop": False,
        "same_outer_fold_partition_as_product_a_base_evidence": True,
        "all_requested_outer_folds_evaluable": True,
        "generating_truth_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def freeze_process_core(*, contract_path: str | Path, product_a_freeze_dir: str | Path, worker_root: str | Path, output_dir: str | Path) -> dict[str, object]:
    contract = load_product_b_v3_known_truth_contract(contract_path)
    freeze = json.loads((Path(product_a_freeze_dir) / "contract.json").read_text(encoding="utf-8"))
    if freeze.get("purpose") != A_FREEZE_PURPOSE or freeze.get("source_contract_sha256") != contract["contract_sha256"]:
        raise ValueError("Product-B v3 process freeze requires matching Product-A freeze")
    frozen_candidate = str(freeze["product_a_representative"])
    taxa = tuple(contract["product_b_evaluation_taxon_names"])
    contracts: list[dict] = []; base_frames: list[pd.DataFrame] = []; knockout_frames: list[pd.DataFrame] = []
    for path in sorted(Path(worker_root).rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != B_SHARD_PURPOSE:
            continue
        if row.get("source_contract_sha256") != contract["contract_sha256"] or str(row.get("frozen_product_a_representative")) != frozen_candidate:
            raise ValueError("Product-B v3 process shard mismatch")
        for key in ("predictor_reselection_after_process_drop", "generating_truth_read", "real_empirical_data_read", "empirical_sealed_outcomes_read", "scientific_threshold_tuning_performed"):
            if row.get(key) is not False:
                raise ValueError(f"Product-B v3 process barrier violated: {key}")
        for key in ("product_a_base_fold_representation_reused", "same_outer_fold_partition_as_product_a_base_evidence", "all_requested_outer_folds_evaluable"):
            if row.get(key) is not True:
                raise ValueError(f"Product-B v3 process invariant failed: {key}")
        contracts.append(row)
        base_frames.append(pd.read_csv(path.parent / "base_fold_metrics.csv"))
        knockout_frames.append(pd.read_csv(path.parent / "knockout_fold_metrics.csv"))
    expected = {(taxon, m) for taxon in taxa for m in M_SPECS}
    observed = {(str(x["taxon"]), str(x["M"])) for x in contracts}
    if observed != expected or len(contracts) != len(expected):
        raise ValueError("Product-B v3 process taxon x M denominator is incomplete")
    base = pd.concat(base_frames, ignore_index=True); knockout = pd.concat(knockout_frames, ignore_index=True)
    outer_folds = int(contract["simulation_contract"]["outer_folds"])
    expected_folds = tuple(range(outer_folds))
    paired = pair_process_knockout_losses(base, knockout, frozen_candidate=frozen_candidate, expected_taxa=taxa, expected_M=M_SPECS, expected_folds=expected_folds)
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
        raise ValueError("Product-B v3 process inference lacks complete M x fold evidence")
    u = contract["universality_rule"]
    repeated = repeat_process_core_splits(
        taxon_process,
        seeds=tuple(int(x) for x in u["split_seeds"]),
        validation_fraction=float(u["validation_fraction"]),
        min_taxon_support_fraction=float(u["min_taxon_support_fraction"]),
    )
    stability = repeated.process_stability.copy()
    threshold = float(u["stable_core_min_validation_confirmation_fraction"])
    stability["stable_universal_core"] = pd.to_numeric(stability["validation_confirmation_stability"], errors="coerce") >= threshold - 1e-12
    stable_core = tuple(sorted(stability.loc[stability["stable_universal_core"], "process_domain"].astype(str)))

    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    paired.to_csv(out / "paired_process_losses.csv", index=False)
    taxon_process.to_csv(out / "taxon_process_summary.csv", index=False)
    repeated.split_summary.to_csv(out / "universality_split_summary.csv", index=False)
    stability.to_csv(out / "process_stability.csv", index=False)
    result = {
        "purpose": B_PRETRUTH_PURPOSE,
        "source_contract_sha256": contract["contract_sha256"],
        "product_a_representative_available": True,
        "frozen_product_a_representative": frozen_candidate,
        "n_process_shards": len(contracts),
        "n_taxa": len(taxa),
        "M_specs": list(M_SPECS),
        "outer_folds": outer_folds,
        "stable_core_threshold": threshold,
        "stable_universal_core": list(stable_core),
        "all_M_x_fold_evidence_complete": True,
        "product_a_candidate_frozen_before_process_ablation": True,
        "predictor_reselection_after_process_drop": False,
        "process_losses_frozen_before_generating_truth_audit": True,
        "generating_truth_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_truth_audit(*, contract_path: str | Path, pretruth_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    contract = load_product_b_v3_known_truth_contract(contract_path)
    frozen = json.loads((Path(pretruth_dir) / "contract.json").read_text(encoding="utf-8"))
    if frozen.get("purpose") != B_PRETRUTH_PURPOSE or frozen.get("source_contract_sha256") != contract["contract_sha256"]:
        raise ValueError("Product-B v3 truth audit requires matching pretruth core")
    if frozen.get("product_a_representative_available") is not True or frozen.get("product_a_candidate_frozen_before_process_ablation") is not True:
        raise ValueError("Product-B v3 truth audit lacks frozen upstream Product-A representation")
    result = audit_product_b_v2_known_truth(
        contract_path=contract_path,
        pretruth_dir=pretruth_dir,
        output_dir=output_dir,
        contract_loader=load_product_b_v3_known_truth_contract,
        expected_pretruth_purpose=B_PRETRUTH_PURPOSE,
        result_purpose=DECISION_PURPOSE,
    )
    out = Path(output_dir)
    decision = pd.read_csv(out / "decision.csv")
    if len(decision) != 1:
        raise ValueError("Product-B v3 truth audit expected one decision row")
    old = str(decision.loc[0, "decision"])
    mapping = {
        "product_b_v2_known_truth_supported": "product_b_v3_known_truth_supported",
        "product_b_v2_known_truth_not_supported": "product_b_v3_known_truth_not_supported",
    }
    if old not in mapping:
        raise ValueError(f"unexpected inherited Product-B decision: {old}")
    new = mapping[old]
    decision.loc[0, "decision"] = new
    decision.to_csv(out / "decision.csv", index=False)
    contract_out = json.loads((out / "contract.json").read_text(encoding="utf-8"))
    contract_out["purpose"] = DECISION_PURPOSE
    contract_out["decision"] = new
    contract_out["product_a_representative_available_before_process_audit"] = True
    (out / "contract.json").write_text(json.dumps(contract_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["purpose"] = DECISION_PURPOSE; result["decision"] = new
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Product-B v3 known-truth stages")
    sub = parser.add_subparsers(dest="stage", required=True)
    a = sub.add_parser("product-a-shard"); a.add_argument("--contract", required=True); a.add_argument("--taxon-index", type=int, required=True); a.add_argument("--m-index", type=int, required=True); a.add_argument("--output-dir", required=True)
    f = sub.add_parser("product-a-freeze"); f.add_argument("--contract", required=True); f.add_argument("--worker-root", required=True); f.add_argument("--output-dir", required=True)
    p = sub.add_parser("process-shard"); p.add_argument("--contract", required=True); p.add_argument("--product-a-freeze-dir", required=True); p.add_argument("--product-a-shard-dir", required=True); p.add_argument("--taxon-index", type=int, required=True); p.add_argument("--m-index", type=int, required=True); p.add_argument("--output-dir", required=True)
    c = sub.add_parser("pretruth-freeze"); c.add_argument("--contract", required=True); c.add_argument("--product-a-freeze-dir", required=True); c.add_argument("--worker-root", required=True); c.add_argument("--output-dir", required=True)
    t = sub.add_parser("truth-audit"); t.add_argument("--contract", required=True); t.add_argument("--pretruth-dir", required=True); t.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.stage == "product-a-shard":
        run_product_a_shard(contract_path=args.contract, taxon_index=args.taxon_index, m_index=args.m_index, output_dir=args.output_dir)
    elif args.stage == "product-a-freeze":
        freeze_product_a_representative(contract_path=args.contract, worker_root=args.worker_root, output_dir=args.output_dir)
    elif args.stage == "process-shard":
        run_process_shard(contract_path=args.contract, product_a_freeze_dir=args.product_a_freeze_dir, product_a_shard_dir=args.product_a_shard_dir, taxon_index=args.taxon_index, m_index=args.m_index, output_dir=args.output_dir)
    elif args.stage == "pretruth-freeze":
        freeze_process_core(contract_path=args.contract, product_a_freeze_dir=args.product_a_freeze_dir, worker_root=args.worker_root, output_dir=args.output_dir)
    else:
        run_truth_audit(contract_path=args.contract, pretruth_dir=args.pretruth_dir, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
