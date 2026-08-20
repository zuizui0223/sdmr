"""Run one fresh Product-B v2 taxon x M process-knockout shard without truth."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import benchmark_recovery_procedures
from .product_b_v2_known_truth_contract import M_SPECS, load_product_b_v2_known_truth_contract
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


def run_product_b_process_shard(
    *,
    contract_path: str | Path,
    method_dir: str | Path,
    taxon_index: int,
    m_index: int,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_product_b_v2_known_truth_contract(contract_path)
    method = json.loads((Path(method_dir) / "contract.json").read_text(encoding="utf-8"))
    if method.get("purpose") != "product_b_v2_frozen_product_a_method_pretruth":
        raise ValueError("Product-B process shard requires frozen Product-A method")
    if method.get("source_contract_sha256") != contract["contract_sha256"]:
        raise ValueError("Product-B method derives from a different contract")
    if method.get("candidate_frozen_before_product_b_evaluation_taxa") is not True:
        raise ValueError("Product-B method was not frozen before evaluation taxa")
    if method.get("product_b_evaluation_taxa_simulated_or_read") is not False:
        raise ValueError("method freeze already read Product-B evaluation taxa")
    if method.get("generating_truth_read") is not False:
        raise ValueError("method freeze used generating truth")

    specs = contract["product_b_evaluation_taxa"]
    if not 0 <= int(taxon_index) < len(specs):
        raise ValueError("Product-B taxon_index out of range")
    if not 0 <= int(m_index) < len(M_SPECS):
        raise ValueError("Product-B m_index out of range")
    raw = specs[int(taxon_index)]
    spec = SimulatedTaxonSpec(str(raw["family"]), int(raw["seed"]), "product_b_evaluation")
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
            raise AssertionError("generating truth crossed Product-B process barrier")

    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_SPECS},
        CANDIDATE_ECOLOGICAL_PREDICTORS,
        minimum_coverage=float(simc["minimum_predictor_coverage"]),
    )
    predictors = tuple(admissibility.predictors)
    if not predictors:
        raise ValueError("no admissible ecological predictors")
    procedures = {
        p.label: p
        for p in _procedure_library(
            inner_folds=int(simc["inner_folds"]),
            max_predictors=int(simc["max_predictors"]),
        )
    }
    frozen_candidate = str(method["frozen_candidate"])
    if frozen_candidate not in procedures:
        raise ValueError("frozen Product-A candidate is not in the procedure library")
    procedure = procedures[frozen_candidate]

    m_name = M_SPECS[int(m_index)]
    background = backgrounds[m_name]
    random_state = 830000 + int(taxon_index) * 10 + int(m_index)
    partition = make_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=max(4, int(simc["outer_folds"]) + 1),
        holdout_fraction=0.20,
        random_state=random_state,
    )

    common = dict(
        presence=occurrence,
        background=background,
        presence_groups=partition.presence_blocks,
        background_groups=partition.background_blocks,
        audit_predictors=tuple(simulation.audit_predictors),
        procedures=(procedure,),
        outer_folds=int(simc["outer_folds"]),
        chance_auc=float(contract["method_freeze"]["prediction_adequacy"]["chance_auc"]),
        minimum_auc_margin=float(contract["method_freeze"]["prediction_adequacy"]["minimum_auc_margin"]),
        auc_sem_multiplier=float(contract["method_freeze"]["prediction_adequacy"]["auc_sem_multiplier"]),
    )
    base = benchmark_recovery_procedures(ecological_predictors=predictors, **common).fold_metrics.copy()
    if base.empty:
        raise ValueError("Product-B base benchmark produced no metrics")
    base["taxon"] = spec.taxon
    base["M"] = m_name
    base["family"] = spec.family
    base["simulation_seed"] = spec.seed

    aliases = contract["process_predictor_aliases"]
    knockout_frames: list[pd.DataFrame] = []
    for process in contract["ecological_process_universe"]:
        excluded = {p for p in predictors if str(aliases.get(str(p), str(p))) == str(process)}
        retained = tuple(p for p in predictors if p not in excluded)
        if not retained:
            raise ValueError(f"process knockout leaves no predictors: {process}")
        result = benchmark_recovery_procedures(ecological_predictors=retained, **common).fold_metrics.copy()
        if result.empty:
            raise ValueError(f"Product-B knockout produced no metrics: {process}")
        result["base_candidate"] = frozen_candidate
        result["candidate"] = frozen_candidate + "::exclude::" + str(process)
        result["procedure"] = result["candidate"]
        result["excluded_process_domain"] = str(process)
        result["excluded_predictors"] = ",".join(sorted(excluded))
        result["taxon"] = spec.taxon
        result["M"] = m_name
        result["family"] = spec.family
        result["simulation_seed"] = spec.seed
        knockout_frames.append(result)
    knockout = pd.concat(knockout_frames, ignore_index=True)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base.to_csv(out / "base_fold_metrics.csv", index=False)
    knockout.to_csv(out / "knockout_fold_metrics.csv", index=False)
    admissibility.ledger.to_csv(out / "predictor_coverage.csv", index=False)
    result_contract = {
        "purpose": "product_b_v2_known_truth_process_shard_pretruth",
        "source_contract_sha256": contract["contract_sha256"],
        "frozen_candidate": frozen_candidate,
        "taxon": spec.taxon,
        "family": spec.family,
        "simulation_seed": spec.seed,
        "taxon_index": int(taxon_index),
        "M": m_name,
        "m_index": int(m_index),
        "n_processes": len(contract["ecological_process_universe"]),
        "same_spatial_partition_for_base_and_all_knockouts": True,
        "admissibility_computed_across_all_frozen_M": True,
        "generating_truth_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--method-dir", required=True)
    parser.add_argument("--taxon-index", type=int, required=True)
    parser.add_argument("--m-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_product_b_process_shard(
        contract_path=args.contract,
        method_dir=args.method_dir,
        taxon_index=args.taxon_index,
        m_index=args.m_index,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
