"""Runtime-only successor for resumable Product-A v2.8.3 presealed computation.

This module deliberately reuses the frozen v2.8.3 scientific contract and the
v2.7.2 deterministic procedure library.  It changes only execution topology:
shared taxon-part preparation is computed once, and the base plus six process
knockout evaluations are independent logical units that can be retried without
repeating successful scientific work.

No sealed occurrence environments are read here.  The output of
``aggregate-groups`` intentionally preserves the historical v2.7.2 M-shard
contract purpose so the already-audited downstream M/taxon aggregation,
pretruth, and final-fit implementations can consume it unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import benchmark_recovery_procedures
from .v2_6_empirical_model_pool_worker import M_NAMES
from .v2_7_1_evidence_balanced_partition import make_evidence_balanced_spatial_partitions
from .v2_7_2_deterministic_procedure_library import deterministic_procedure_library
from .v2_7_empirical_audit_support import select_partition_aware_empirical_audit_space
from .v2_8_3_fresh_contract import load_v2_8_3_fresh_confirmation_contract

PRECOMPUTE_PURPOSE = "product_a_v2_8_4_taxon_part_precompute"
GROUP_PURPOSE = "product_a_v2_8_4_model_group_shard"
COMPAT_M_SHARD_PURPOSE = "product_a_v2_7_2_fresh_model_pool_M_shard"
RUNTIME_DESIGN_PURPOSE = "product_a_v2_8_4_runtime_only_successor_design"
BASE_GROUP = "base"


def _audit_manifest(registry: pd.DataFrame) -> pd.DataFrame:
    return registry[["predictor", "empirical_process_domain"]].rename(
        columns={"empirical_process_domain": "process"}
    )


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _logical_shard_id(
    *, scientific_execution_id: str, part_seed: int, taxon_index: int,
    M_name: str | None = None, evaluation_group: str | None = None,
) -> str:
    pieces = [
        str(scientific_execution_id),
        f"seed={int(part_seed)}",
        f"taxon_index={int(taxon_index)}",
    ]
    if M_name is not None:
        pieces.append(f"M={M_name}")
    if evaluation_group is not None:
        pieces.append(f"group={evaluation_group}")
    return "|".join(pieces)


def _load_runtime_design(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != RUNTIME_DESIGN_PURPOSE:
        raise ValueError("wrong v2.8.4 runtime successor design contract")
    predecessor = payload.get("predecessor_design_contract", {})
    if predecessor.get("blob_sha") != "1928de6d8f1289117415047c7a8d1ee894ca6bbe":
        raise ValueError("v2.8.4 predecessor scientific contract identity changed")
    if predecessor.get("scientific_semantics_inherited_without_change") is not True:
        raise ValueError("v2.8.4 scientific inheritance is not exact")
    invariants = payload.get("scientific_invariants", {})
    for key in (
        "candidate_predictor_universe_changed", "candidate_library_changed",
        "thresholds_changed", "taxa_changed", "M_changed", "seeds_changed",
        "fraction_changed", "denominator_changed", "decision_rule_changed",
        "scientific_promotion_allowed", "product_b_unblocked",
    ):
        if invariants.get(key) is not False:
            raise ValueError(f"v2.8.4 runtime design crossed scientific boundary: {key}")
    return payload


def _load_materialization(part_dir: Path, *, part_seed: int) -> dict:
    payload = json.loads((part_dir / "contract.json").read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_2_fresh_part_model_pool_materialization":
        raise ValueError("v2.8.4 presealed runtime received wrong materialization")
    if (
        payload.get("sealed_occurrence_raster_values_extracted") is not False
        or payload.get("sealed_background_raster_values_extracted") is not False
    ):
        raise ValueError("v2.8.4 presealed runtime received opened sealed environments")
    if int(payload.get("seed", -1)) != int(part_seed):
        raise ValueError("v2.8.4 part seed differs from materialization")
    return payload


def _validate_identity(contract: dict, *, part_seed: int, taxon_index: int) -> None:
    if int(part_seed) not in {int(x) for x in contract["fixed_design"]["split_seeds"]}:
        raise ValueError("v2.8.4 part seed is not frozen")
    if not 0 <= int(taxon_index) < 12:
        raise ValueError("v2.8.4 taxon_index must be 0..11")


def _empty_shared_files(out: Path) -> None:
    for filename in (
        "predictor_coverage.csv",
        "evidence_balanced_partition_support.csv",
        "evidence_balanced_partition_attempts.csv",
        "audit_support.csv",
        "audit_pruning.csv",
        "base_audit_space.csv",
        "partition_presence.csv",
        *[f"partition_background__{name}.csv" for name in M_NAMES],
    ):
        pd.DataFrame().to_csv(out / filename, index=False)


def _write_precompute_unavailable(
    out: Path, *, scientific_execution_id: str, taxon: str, taxon_index: int,
    part_seed: int, stage: str, error: str,
) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    _empty_shared_files(out)
    result = {
        "purpose": PRECOMPUTE_PURPOSE,
        "available": False,
        "unavailable_stage": str(stage),
        "unavailable_reason": str(error),
        "scientific_execution_id": str(scientific_execution_id),
        "logical_shard_id": _logical_shard_id(
            scientific_execution_id=scientific_execution_id,
            part_seed=part_seed,
            taxon_index=taxon_index,
        ),
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_used_for_partition_or_audit_selection": False,
        "v2_8_4_runtime_successor": True,
        "shared_across_all_three_M": True,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def prepare_taxon_part(
    *, runtime_design_path: str | Path, scientific_contract_path: str | Path,
    process_registry_path: str | Path, part_dir: str | Path,
    scientific_execution_id: str, taxon: str, taxon_index: int, part_seed: int,
    output_dir: str | Path,
) -> dict[str, object]:
    """Compute M-shared truth-blind admissibility, partition, and audit space once."""
    if not str(scientific_execution_id).strip():
        raise ValueError("scientific_execution_id must be non-empty")
    _load_runtime_design(runtime_design_path)
    contract = load_v2_8_3_fresh_confirmation_contract(scientific_contract_path)
    _validate_identity(contract, part_seed=part_seed, taxon_index=taxon_index)

    out = Path(output_dir)
    root = Path(part_dir)
    _load_materialization(root, part_seed=part_seed)

    occurrences_all = pd.read_parquet(root / "model_occurrences.parquet")
    occurrence = occurrences_all.loc[
        occurrences_all["species"].astype(str).eq(str(taxon))
    ].reset_index(drop=True)
    if occurrence.empty:
        raise ValueError(f"v2.8.4 model-pool occurrence data missing taxon: {taxon}")

    backgrounds: dict[str, pd.DataFrame] = {}
    for name in M_NAMES:
        frame = pd.read_parquet(root / "M" / name / "model_background.parquet")
        frame = frame.loc[frame["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
        if frame.empty:
            raise ValueError(f"v2.8.4 model-pool background missing {taxon} in {name}")
        backgrounds[name] = frame

    registry = pd.read_csv(process_registry_path)
    all_audit_predictors = tuple(registry["predictor"].astype(str))
    audit_cfg = contract["partition_aware_audit_space"]
    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_NAMES},
        all_audit_predictors,
        minimum_coverage=float(audit_cfg["minimum_predictor_coverage"]),
    )
    ecological_predictors = tuple(admissibility.predictors)
    if not ecological_predictors:
        return _write_precompute_unavailable(
            out,
            scientific_execution_id=scientific_execution_id,
            taxon=taxon,
            taxon_index=taxon_index,
            part_seed=part_seed,
            stage="predictor_admissibility",
            error="no predictor passed the frozen 0.95 model-pool coverage gate",
        )

    fold_cfg = contract["evidence_balanced_partition"]
    partition_seed = int(part_seed) + int(taxon_index) * 100 + 271
    try:
        partition = make_evidence_balanced_spatial_partitions(
            occurrence["longitude"].to_numpy(float),
            occurrence["latitude"].to_numpy(float),
            {
                name: (
                    backgrounds[name]["longitude"].to_numpy(float),
                    backgrounds[name]["latitude"].to_numpy(float),
                )
                for name in M_NAMES
            },
            n_microblocks=int(fold_cfg["spatial_microblocks"]),
            outer_folds=int(fold_cfg["outer_folds"]),
            minimum_evaluation_occurrences=int(
                fold_cfg["minimum_evaluation_occurrences_per_fold"]
            ),
            minimum_evaluation_background_rows=int(
                fold_cfg["minimum_evaluation_background_rows_per_M_fold"]
            ),
            minimum_training_background_rows=int(
                fold_cfg["minimum_training_background_rows_per_M_fold"]
            ),
            assignment_attempts=int(fold_cfg["assignment_attempts"]),
            random_state=partition_seed,
        )
    except ValueError as exc:
        return _write_precompute_unavailable(
            out,
            scientific_execution_id=scientific_execution_id,
            taxon=taxon,
            taxon_index=taxon_index,
            part_seed=part_seed,
            stage="structural_partition",
            error=str(exc),
        )

    partitions = {name: partition.for_M(name) for name in M_NAMES}
    try:
        selected_audit = select_partition_aware_empirical_audit_space(
            _audit_manifest(registry),
            occurrence,
            backgrounds,
            partitions,
            outer_folds=int(fold_cfg["outer_folds"]),
            minimum_predictor_coverage=float(audit_cfg["minimum_predictor_coverage"]),
            minimum_joint_coverage=float(audit_cfg["minimum_joint_coverage"]),
            minimum_processes=int(audit_cfg["minimum_processes"]),
            minimum_fit_background_rows=int(
                audit_cfg["minimum_complete_fit_background_rows_per_M_fold"]
            ),
            minimum_evaluation_background_rows=int(
                audit_cfg["minimum_complete_evaluation_background_rows_per_M_fold"]
            ),
            minimum_heldout_occurrence_rows=int(
                audit_cfg["minimum_complete_heldout_occurrence_rows_per_M_fold"]
            ),
        )
    except ValueError as exc:
        return _write_precompute_unavailable(
            out,
            scientific_execution_id=scientific_execution_id,
            taxon=taxon,
            taxon_index=taxon_index,
            part_seed=part_seed,
            stage="audit_space",
            error=str(exc),
        )

    out.mkdir(parents=True, exist_ok=True)
    admissibility.ledger.to_csv(out / "predictor_coverage.csv", index=False)
    partition.support_ledger.to_csv(
        out / "evidence_balanced_partition_support.csv", index=False
    )
    partition.attempt_ledger.to_csv(
        out / "evidence_balanced_partition_attempts.csv", index=False
    )
    selected_audit.support_ledger.to_csv(out / "audit_support.csv", index=False)
    selected_audit.pruning_ledger.to_csv(out / "audit_pruning.csv", index=False)
    selected_audit.base_audit_ledger.to_csv(out / "base_audit_space.csv", index=False)
    pd.DataFrame({
        "row_index": np.arange(len(occurrence)),
        "fold": partition.presence_folds,
        "microblock": partition.presence_microblocks,
    }).to_csv(out / "partition_presence.csv", index=False)
    for name in M_NAMES:
        pd.DataFrame({
            "row_index": np.arange(len(backgrounds[name])),
            "fold": partition.background_folds[name],
            "microblock": partition.background_microblocks[name],
        }).to_csv(out / f"partition_background__{name}.csv", index=False)

    library_cfg = contract["fixed_design"]["procedure_library"]
    result = {
        "purpose": PRECOMPUTE_PURPOSE,
        "available": True,
        "scientific_execution_id": str(scientific_execution_id),
        "logical_shard_id": _logical_shard_id(
            scientific_execution_id=scientific_execution_id,
            part_seed=part_seed,
            taxon_index=taxon_index,
        ),
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "partition_seed": int(partition_seed),
        "selected_assignment_attempt": int(partition.selected_attempt),
        "n_admissible_predictors": len(ecological_predictors),
        "admissible_predictors": list(ecological_predictors),
        "audit_predictors": list(selected_audit.predictors),
        "audit_processes": list(selected_audit.processes),
        "model_random_state": int(library_cfg["model_random_state"]),
        "selection_process_numpy_seed": int(
            library_cfg["selection_process_numpy_seed"]
        ),
        "process_registry_sha256": _sha256(process_registry_path),
        "scientific_contract_sha256": _sha256(scientific_contract_path),
        "runtime_design_sha256": _sha256(runtime_design_path),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_used_for_partition_or_audit_selection": False,
        "v2_8_4_runtime_successor": True,
        "shared_across_all_three_M": True,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def evaluate_group(
    *, runtime_design_path: str | Path, scientific_contract_path: str | Path,
    process_registry_path: str | Path, part_dir: str | Path,
    precompute_dir: str | Path, scientific_execution_id: str,
    taxon: str, taxon_index: int, part_seed: int, M_name: str,
    evaluation_group: str, output_dir: str | Path, attempt_ordinal: int = 0,
) -> dict[str, object]:
    """Evaluate exactly one base or process-knockout benchmark group."""
    if str(M_name) not in M_NAMES:
        raise ValueError(f"v2.8.4 M must be one of {M_NAMES}")
    _load_runtime_design(runtime_design_path)
    contract = load_v2_8_3_fresh_confirmation_contract(scientific_contract_path)
    _validate_identity(contract, part_seed=part_seed, taxon_index=taxon_index)
    domains = tuple(str(x) for x in contract["fixed_design"]["process_domains"])
    if str(evaluation_group) not in {BASE_GROUP, *domains}:
        raise ValueError("v2.8.4 evaluation group is not frozen")

    root = Path(part_dir)
    _load_materialization(root, part_seed=part_seed)
    pre_root = Path(precompute_dir)
    pre = json.loads((pre_root / "contract.json").read_text(encoding="utf-8"))
    if pre.get("purpose") != PRECOMPUTE_PURPOSE:
        raise ValueError("v2.8.4 group received wrong precompute artifact")
    for key, expected in (
        ("scientific_execution_id", str(scientific_execution_id)),
        ("taxon", str(taxon)),
        ("taxon_index", int(taxon_index)),
        ("part_seed", int(part_seed)),
    ):
        actual = pre.get(key)
        if isinstance(expected, int):
            actual = int(actual)
        if actual != expected:
            raise ValueError(f"v2.8.4 group/precompute identity mismatch: {key}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    logical_id = _logical_shard_id(
        scientific_execution_id=scientific_execution_id,
        part_seed=part_seed,
        taxon_index=taxon_index,
        M_name=M_name,
        evaluation_group=evaluation_group,
    )
    start = time.monotonic()

    if pre.get("available") is not True:
        pd.DataFrame().to_csv(out / "fold_metrics.csv", index=False)
        pd.DataFrame().to_csv(out / "selection_trace.csv", index=False)
        pd.DataFrame([{
            "taxon": taxon,
            "M": M_name,
            "group": evaluation_group,
            "status": "unavailable",
            "error": pre.get("unavailable_reason", "precompute_unavailable"),
            "partition_seed": None,
        }]).to_csv(out / "worker_status.csv", index=False)
        result = {
            "purpose": GROUP_PURPOSE,
            "available": False,
            "unavailable_stage": pre.get("unavailable_stage", "precompute"),
            "unavailable_reason": pre.get("unavailable_reason", "precompute_unavailable"),
            "scientific_execution_id": str(scientific_execution_id),
            "logical_shard_id": logical_id,
            "operational_attempt_ordinal": int(attempt_ordinal),
            "taxon": str(taxon),
            "taxon_index": int(taxon_index),
            "part_seed": int(part_seed),
            "M": str(M_name),
            "evaluation_group": str(evaluation_group),
            "sealed_occurrence_environment_read": False,
            "candidate_model_fitting_performed": False,
            "v2_8_4_runtime_successor": True,
        }
        (out / "contract.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return result

    occurrences_all = pd.read_parquet(root / "model_occurrences.parquet")
    occurrence = occurrences_all.loc[
        occurrences_all["species"].astype(str).eq(str(taxon))
    ].reset_index(drop=True)
    background_all = pd.read_parquet(root / "M" / str(M_name) / "model_background.parquet")
    background = background_all.loc[
        background_all["species"].astype(str).eq(str(taxon))
    ].reset_index(drop=True)
    if occurrence.empty or background.empty:
        raise ValueError("v2.8.4 group model-pool rows are missing")

    presence_groups = pd.read_csv(pre_root / "partition_presence.csv")["fold"].to_numpy()
    background_groups = pd.read_csv(
        pre_root / f"partition_background__{M_name}.csv"
    )["fold"].to_numpy()
    if len(presence_groups) != len(occurrence) or len(background_groups) != len(background):
        raise ValueError("v2.8.4 precomputed partition rows changed")

    registry = pd.read_csv(process_registry_path)
    ecological_predictors = tuple(str(x) for x in pre["admissible_predictors"])
    audit_predictors = tuple(str(x) for x in pre["audit_predictors"])
    procedures = deterministic_procedure_library(contract)
    library_cfg = contract["fixed_design"]["procedure_library"]
    adequacy = contract["fixed_design"]["prediction_adequacy"]
    common = dict(
        presence=occurrence,
        background=background,
        presence_groups=presence_groups,
        background_groups=background_groups,
        audit_predictors=audit_predictors,
        procedures=procedures,
        outer_folds=int(library_cfg["outer_folds"]),
        chance_auc=float(adequacy["chance_auc"]),
        minimum_auc_margin=float(adequacy["minimum_auc_margin"]),
        auc_sem_multiplier=float(adequacy["auc_sem_multiplier"]),
    )

    metrics = pd.DataFrame()
    trace = pd.DataFrame()
    fitting_performed = False
    partition_seed = int(pre["partition_seed"])
    status: dict[str, object]

    if evaluation_group == BASE_GROUP:
        retained = ecological_predictors
        excluded_predictors: Iterable[str] = ()
    else:
        excluded = set(
            registry.loc[
                registry["empirical_process_domain"].astype(str).eq(str(evaluation_group)),
                "predictor",
            ].astype(str)
        )
        retained = tuple(p for p in ecological_predictors if p not in excluded)
        excluded_predictors = sorted(excluded & set(ecological_predictors))

    if not retained:
        status = {
            "taxon": taxon,
            "M": M_name,
            "group": evaluation_group,
            "status": "failed_no_retained_predictors",
            "error": None,
            "partition_seed": partition_seed,
        }
    else:
        fitting_performed = True
        try:
            benchmark = benchmark_recovery_procedures(
                ecological_predictors=retained,
                **common,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
            status = {
                "taxon": taxon,
                "M": M_name,
                "group": evaluation_group,
                "status": "failed",
                "error": str(exc),
                "partition_seed": partition_seed,
            }
        else:
            metrics = benchmark.fold_metrics.copy()
            trace = benchmark.selection_trace.copy()
            if evaluation_group == BASE_GROUP:
                metrics["taxon"] = taxon
                metrics["M"] = M_name
                metrics["group"] = BASE_GROUP
                metrics["excluded_process_domain"] = None
                if not trace.empty:
                    trace["taxon"] = taxon
                    trace["M"] = M_name
                    trace["group"] = BASE_GROUP
            else:
                metrics["base_candidate"] = metrics["candidate"].astype(str)
                metrics["candidate"] = (
                    metrics["base_candidate"].astype(str)
                    + "::exclude::"
                    + str(evaluation_group)
                )
                metrics["procedure"] = metrics["candidate"]
                metrics["taxon"] = taxon
                metrics["M"] = M_name
                metrics["group"] = str(evaluation_group)
                metrics["excluded_process_domain"] = str(evaluation_group)
                metrics["excluded_predictors"] = ",".join(excluded_predictors)
                if not trace.empty:
                    trace["taxon"] = taxon
                    trace["M"] = M_name
                    trace["group"] = str(evaluation_group)
            status = {
                "taxon": taxon,
                "M": M_name,
                "group": evaluation_group,
                "status": "success",
                "error": None,
                "partition_seed": partition_seed,
            }

    metrics.to_csv(out / "fold_metrics.csv", index=False)
    trace.to_csv(out / "selection_trace.csv", index=False)
    pd.DataFrame([status]).to_csv(out / "worker_status.csv", index=False)
    elapsed = float(time.monotonic() - start)
    telemetry = {
        "logical_shard_id": logical_id,
        "phase": "deterministic_model_pool_group",
        "evaluation_group": str(evaluation_group),
        "candidate_model_fitting_performed": bool(fitting_performed),
        "elapsed_seconds": elapsed,
        "scientific_selection_input": False,
    }
    (out / "telemetry.json").write_text(
        json.dumps(telemetry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    result = {
        "purpose": GROUP_PURPOSE,
        "available": True,
        "scientific_execution_id": str(scientific_execution_id),
        "logical_shard_id": logical_id,
        "operational_attempt_ordinal": int(attempt_ordinal),
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "M": str(M_name),
        "evaluation_group": str(evaluation_group),
        "partition_seed": partition_seed,
        "selected_assignment_attempt": int(pre["selected_assignment_attempt"]),
        "n_admissible_predictors": int(pre["n_admissible_predictors"]),
        "admissible_predictors": list(pre["admissible_predictors"]),
        "audit_predictors": list(pre["audit_predictors"]),
        "audit_processes": list(pre["audit_processes"]),
        "model_random_state": int(pre["model_random_state"]),
        "selection_process_numpy_seed": int(pre["selection_process_numpy_seed"]),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_model_fitting_performed": bool(fitting_performed),
        "candidate_scores_used_for_partition_or_audit_selection": False,
        "v2_8_4_runtime_successor": True,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def aggregate_groups(
    *, runtime_design_path: str | Path, precompute_dir: str | Path,
    group_root: str | Path, scientific_execution_id: str, taxon: str,
    taxon_index: int, part_seed: int, M_name: str, output_dir: str | Path,
) -> dict[str, object]:
    """Assemble seven independent group shards into legacy-compatible M output."""
    _load_runtime_design(runtime_design_path)
    if str(M_name) not in M_NAMES:
        raise ValueError(f"v2.8.4 M must be one of {M_NAMES}")
    pre_root = Path(precompute_dir)
    pre = json.loads((pre_root / "contract.json").read_text(encoding="utf-8"))
    if pre.get("purpose") != PRECOMPUTE_PURPOSE:
        raise ValueError("v2.8.4 group aggregate received wrong precompute")

    expected_groups = {BASE_GROUP, "thermal", "water", "seasonality_phenology", "energy_productivity", "snow", "wind"}
    found: dict[str, tuple[dict, Path]] = {}
    for path in sorted(Path(group_root).rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != GROUP_PURPOSE:
            continue
        if payload.get("scientific_execution_id") != str(scientific_execution_id):
            continue
        if str(payload.get("taxon")) != str(taxon):
            continue
        if int(payload.get("taxon_index", -1)) != int(taxon_index):
            continue
        if int(payload.get("part_seed", -1)) != int(part_seed):
            continue
        if str(payload.get("M")) != str(M_name):
            continue
        group = str(payload.get("evaluation_group", ""))
        if group in found:
            raise ValueError(f"duplicate v2.8.4 evaluation group: {group}")
        found[group] = (payload, path.parent)
    if set(found) != expected_groups:
        raise ValueError(
            f"expected seven frozen v2.8.4 evaluation groups, found {sorted(found)}"
        )

    reference = found[BASE_GROUP][0]
    identity_keys = (
        "partition_seed", "selected_assignment_attempt", "n_admissible_predictors",
        "admissible_predictors", "audit_predictors", "audit_processes",
        "model_random_state", "selection_process_numpy_seed",
    )
    for group, (payload, _) in found.items():
        for key in identity_keys:
            if payload.get(key) != reference.get(key):
                raise ValueError(f"v2.8.4 group shards disagree on shared identity: {key}")
        for key in (
            "sealed_occurrence_environment_read",
            "sealed_occurrence_used_for_selection",
            "sealed_occurrence_used_for_process_status",
            "candidate_scores_used_for_partition_or_audit_selection",
        ):
            if payload.get(key) is not False:
                raise ValueError(f"v2.8.4 group crossed presealed barrier: {group}:{key}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    shared_files = [
        "predictor_coverage.csv",
        "evidence_balanced_partition_support.csv",
        "evidence_balanced_partition_attempts.csv",
        "audit_support.csv",
        "audit_pruning.csv",
        "base_audit_space.csv",
        "partition_presence.csv",
        *[f"partition_background__{name}.csv" for name in M_NAMES],
    ]
    for filename in shared_files:
        (out / filename).write_bytes((pre_root / filename).read_bytes())

    base_metrics = _read_csv_or_empty(found[BASE_GROUP][1] / "fold_metrics.csv")
    base_metrics.to_csv(out / "base_fold_metrics.csv", index=False)
    knockout_frames = [
        _read_csv_or_empty(found[group][1] / "fold_metrics.csv")
        for group in sorted(expected_groups - {BASE_GROUP})
    ]
    knockout_nonempty = [frame for frame in knockout_frames if not frame.empty]
    (
        pd.concat(knockout_nonempty, ignore_index=True)
        if knockout_nonempty
        else pd.DataFrame()
    ).to_csv(out / "knockout_fold_metrics.csv", index=False)

    trace_frames = [
        _read_csv_or_empty(found[group][1] / "selection_trace.csv")
        for group in sorted(expected_groups)
    ]
    trace_nonempty = [frame for frame in trace_frames if not frame.empty]
    (
        pd.concat(trace_nonempty, ignore_index=True)
        if trace_nonempty
        else pd.DataFrame()
    ).to_csv(out / "selection_trace.csv", index=False)
    status_frames = [
        _read_csv_or_empty(found[group][1] / "worker_status.csv")
        for group in sorted(expected_groups)
    ]
    status_nonempty = [frame for frame in status_frames if not frame.empty]
    (
        pd.concat(status_nonempty, ignore_index=True)
        if status_nonempty
        else pd.DataFrame()
    ).to_csv(out / "worker_status.csv", index=False)

    result = {
        "purpose": COMPAT_M_SHARD_PURPOSE,
        "available": True,
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "M": str(M_name),
        "partition_seed": int(reference["partition_seed"]),
        "selected_assignment_attempt": int(reference["selected_assignment_attempt"]),
        "n_admissible_predictors": int(reference["n_admissible_predictors"]),
        "admissible_predictors": list(reference["admissible_predictors"]),
        "audit_predictors": list(reference["audit_predictors"]),
        "audit_processes": list(reference["audit_processes"]),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_model_fitting_performed": any(
            payload.get("candidate_model_fitting_performed") is True
            for payload, _ in found.values()
        ),
        "candidate_scores_used_for_partition_or_audit_selection": False,
        "primary_M_shard": True,
        "deterministic_successor": True,
        "model_random_state": int(reference["model_random_state"]),
        "selection_process_numpy_seed": int(reference["selection_process_numpy_seed"]),
        "v2_8_4_runtime_successor": True,
        "scientific_execution_id": str(scientific_execution_id),
        "assembled_from_seven_independent_group_shards": True,
        "M_shared_precompute_reused": True,
        "telemetry_used_for_scientific_selection": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("precompute")
    q.add_argument("--runtime-design", required=True)
    q.add_argument("--scientific-contract", required=True)
    q.add_argument("--process-registry", required=True)
    q.add_argument("--part-dir", required=True)
    q.add_argument("--scientific-execution-id", required=True)
    q.add_argument("--taxon", required=True)
    q.add_argument("--taxon-index", type=int, required=True)
    q.add_argument("--part-seed", type=int, required=True)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=lambda a: prepare_taxon_part(
        runtime_design_path=a.runtime_design,
        scientific_contract_path=a.scientific_contract,
        process_registry_path=a.process_registry,
        part_dir=a.part_dir,
        scientific_execution_id=a.scientific_execution_id,
        taxon=a.taxon,
        taxon_index=a.taxon_index,
        part_seed=a.part_seed,
        output_dir=a.output_dir,
    ))

    q = sub.add_parser("evaluate-group")
    q.add_argument("--runtime-design", required=True)
    q.add_argument("--scientific-contract", required=True)
    q.add_argument("--process-registry", required=True)
    q.add_argument("--part-dir", required=True)
    q.add_argument("--precompute-dir", required=True)
    q.add_argument("--scientific-execution-id", required=True)
    q.add_argument("--taxon", required=True)
    q.add_argument("--taxon-index", type=int, required=True)
    q.add_argument("--part-seed", type=int, required=True)
    q.add_argument("--M", required=True)
    q.add_argument("--evaluation-group", required=True)
    q.add_argument("--attempt-ordinal", type=int, default=0)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=lambda a: evaluate_group(
        runtime_design_path=a.runtime_design,
        scientific_contract_path=a.scientific_contract,
        process_registry_path=a.process_registry,
        part_dir=a.part_dir,
        precompute_dir=a.precompute_dir,
        scientific_execution_id=a.scientific_execution_id,
        taxon=a.taxon,
        taxon_index=a.taxon_index,
        part_seed=a.part_seed,
        M_name=a.M,
        evaluation_group=a.evaluation_group,
        output_dir=a.output_dir,
        attempt_ordinal=a.attempt_ordinal,
    ))

    q = sub.add_parser("aggregate-groups")
    q.add_argument("--runtime-design", required=True)
    q.add_argument("--precompute-dir", required=True)
    q.add_argument("--group-root", required=True)
    q.add_argument("--scientific-execution-id", required=True)
    q.add_argument("--taxon", required=True)
    q.add_argument("--taxon-index", type=int, required=True)
    q.add_argument("--part-seed", type=int, required=True)
    q.add_argument("--M", required=True)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=lambda a: aggregate_groups(
        runtime_design_path=a.runtime_design,
        precompute_dir=a.precompute_dir,
        group_root=a.group_root,
        scientific_execution_id=a.scientific_execution_id,
        taxon=a.taxon,
        taxon_index=a.taxon_index,
        part_seed=a.part_seed,
        M_name=a.M,
        output_dir=a.output_dir,
    ))
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
