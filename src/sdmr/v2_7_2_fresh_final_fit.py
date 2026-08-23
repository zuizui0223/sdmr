"""Fit and serialize v2.7.2 representatives using model-pool rows only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .recovery_procedure_fit import fit_recovery_procedure
from .v2_6_empirical_model_pool_worker import M_NAMES
from .v2_7_2_deterministic_procedure_library import deterministic_procedure_library
from .v2_7_2_fresh_contract import load_v2_7_2_fresh_confirmation_contract

PURPOSE = "product_a_v2_7_2_fresh_final_models_presealed"


def _partition_values(
    worker_dir: Path, name: str, *, n_presence: int, n_background: int
) -> tuple[np.ndarray, np.ndarray]:
    p = pd.read_csv(worker_dir / "partition_presence.csv")
    b = pd.read_csv(worker_dir / f"partition_background__{name}.csv")
    if len(p) != n_presence or len(b) != n_background:
        raise ValueError(f"stored v2.7.2 partition does not align for {name}")
    if not np.array_equal(
        pd.to_numeric(p["row_index"]).to_numpy(int), np.arange(n_presence)
    ):
        raise ValueError("v2.7.2 stored presence partition row order changed")
    if not np.array_equal(
        pd.to_numeric(b["row_index"]).to_numpy(int), np.arange(n_background)
    ):
        raise ValueError(f"v2.7.2 stored background partition row order changed for {name}")
    return (
        pd.to_numeric(p["fold"]).to_numpy(int),
        pd.to_numeric(b["fold"]).to_numpy(int),
    )


def _write_unavailable(
    out: Path, *, taxon: str, taxon_index: int, part_seed: int, reason: str
) -> dict[str, object]:
    pd.DataFrame().to_csv(out / "frozen_final_models.csv", index=False)
    pd.DataFrame().to_csv(out / "final_selection_trace.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "available": False,
        "unavailable_reason": str(reason),
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_final_selection": False,
        "final_models_serialized_before_sealed_audit": False,
        "deterministic_successor": True,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def freeze_fresh_final_models(
    *, contract_path: str | Path, part_dir: str | Path, worker_dir: str | Path,
    pretruth_dir: str | Path, taxon: str, taxon_index: int, output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_7_2_fresh_confirmation_contract(contract_path)
    library_cfg = contract["fixed_design"]["procedure_library"]
    np.random.seed(int(library_cfg["selection_process_numpy_seed"]))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pretruth = json.loads(
        (Path(pretruth_dir) / "contract.json").read_text(encoding="utf-8")
    )
    if pretruth.get("purpose") != "product_a_v2_7_2_fresh_part_pretruth_freeze":
        raise ValueError("v2.7.2 final fitting requires a frozen v2.7.2 pretruth artifact")
    if pretruth.get("sealed_occurrence_environment_read") is not False:
        raise ValueError("v2.7.2 pretruth already crossed sealed environment barrier")
    if pretruth.get("deterministic_successor") is not True:
        raise ValueError("v2.7.2 final fitting received non-deterministic pretruth")
    if pretruth.get("available") is not True:
        return _write_unavailable(
            out,
            taxon=taxon,
            taxon_index=taxon_index,
            part_seed=int(pretruth["part_seed"]),
            reason=str(pretruth.get("unavailable_reason", "pretruth_unavailable")),
        )

    worker_root = Path(worker_dir)
    worker = json.loads((worker_root / "contract.json").read_text(encoding="utf-8"))
    if (
        worker.get("purpose") != "product_a_v2_7_2_fresh_model_pool_worker"
        or worker.get("available") is not True
    ):
        return _write_unavailable(
            out, taxon=taxon, taxon_index=taxon_index,
            part_seed=int(pretruth["part_seed"]),
            reason="v2.7.2_model_pool_worker_unavailable_after_available_pretruth",
        )
    if worker.get("taxon") != str(taxon) or int(worker.get("taxon_index", -1)) != int(taxon_index):
        raise ValueError("v2.7.2 worker identity differs from final-fit taxon")
    if worker.get("sealed_occurrence_environment_read") is not False:
        raise ValueError("v2.7.2 worker opened sealed environment")
    if worker.get("deterministic_successor") is not True:
        raise ValueError("v2.7.2 worker is not deterministic successor evidence")
    if int(worker.get("model_random_state", -1)) != 0 or int(worker.get("selection_process_numpy_seed", -1)) != 0:
        raise ValueError("v2.7.2 worker RNG identity changed")

    part = Path(part_dir)
    materialization = json.loads((part / "contract.json").read_text(encoding="utf-8"))
    if materialization.get("purpose") != "product_a_v2_7_2_fresh_part_model_pool_materialization":
        raise ValueError("v2.7.2 final fitting received wrong materialization")
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False:
        raise ValueError("v2.7.2 final fitting cannot consume opened sealed environments")

    part_seed = int(worker["part_seed"])
    ecological_predictors = tuple(str(x) for x in worker["admissible_predictors"])
    audit_predictors = tuple(str(x) for x in worker["audit_predictors"])
    if not ecological_predictors or not audit_predictors:
        return _write_unavailable(
            out, taxon=taxon, taxon_index=taxon_index, part_seed=part_seed,
            reason="frozen_model_or_audit_predictor_set_empty",
        )
    procedures = {p.label: p for p in deterministic_procedure_library(contract)}
    representatives = {
        "ecological": str(pretruth["ecological_representative"]),
        "auc": str(pretruth["auc_representative"]),
    }
    if any(label not in procedures for label in representatives.values()):
        raise ValueError("v2.7.2 representative not in deterministic procedure library")

    occurrence_all = pd.read_parquet(part / "model_occurrences.parquet")
    occurrence = occurrence_all.loc[
        occurrence_all["species"].astype(str).eq(str(taxon))
    ].reset_index(drop=True)
    selected_rows, trace_frames = [], []
    adequacy = contract["fixed_design"]["prediction_adequacy"]
    try:
        for name in M_NAMES:
            background_all = pd.read_parquet(part / "M" / name / "model_background.parquet")
            background = background_all.loc[
                background_all["species"].astype(str).eq(str(taxon))
            ].reset_index(drop=True)
            p_groups, b_groups = _partition_values(
                worker_root, name,
                n_presence=len(occurrence), n_background=len(background),
            )
            if set(np.unique(p_groups)) != set(range(4)):
                raise ValueError("v2.7.2 final fit requires all four frozen outer folds")
            m_out = out / "M" / name
            m_out.mkdir(parents=True, exist_ok=True)
            fitted_by_candidate = {}
            for role, candidate in representatives.items():
                if candidate not in fitted_by_candidate:
                    fitted_by_candidate[candidate] = fit_recovery_procedure(
                        occurrence, background, p_groups, b_groups,
                        ecological_predictors, audit_predictors,
                        procedures[candidate],
                        chance_auc=float(adequacy["chance_auc"]),
                        minimum_auc_margin=float(adequacy["minimum_auc_margin"]),
                        auc_sem_multiplier=float(adequacy["auc_sem_multiplier"]),
                    )
                fitted = fitted_by_candidate[candidate]
                model_file = f"{role}_model.joblib"
                joblib.dump(fitted.model, m_out / model_file)
                selected_rows.append({
                    "taxon": str(taxon),
                    "M": name,
                    "role": role,
                    "candidate": candidate,
                    "model": fitted.procedure.model_spec.label,
                    "selected_predictors": ",".join(fitted.selected_predictors),
                    "selected_ecological_predictors": ",".join(
                        fitted.selected_ecological_predictors
                    ),
                    "audit_predictors": ",".join(audit_predictors),
                    "n_predictors": len(fitted.selected_predictors),
                    "model_file": str(Path("M") / name / model_file),
                    "partition_seed": int(worker["partition_seed"]),
                    "model_random_state": int(fitted.procedure.model_spec.random_state),
                })
                if not fitted.selection_trace.empty:
                    trace = fitted.selection_trace.copy()
                    trace["taxon"] = str(taxon)
                    trace["M"] = name
                    trace["role"] = role
                    trace["candidate"] = candidate
                    trace_frames.append(trace)
    except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
        return _write_unavailable(
            out, taxon=taxon, taxon_index=taxon_index, part_seed=part_seed,
            reason=f"final_model_fit:{exc}",
        )

    selected = pd.DataFrame(selected_rows)
    if len(selected) != len(M_NAMES) * 2:
        return _write_unavailable(
            out, taxon=taxon, taxon_index=taxon_index, part_seed=part_seed,
            reason="v2.7.2 final-fit representative denominator incomplete",
        )
    if set(selected["model_random_state"].astype(int)) != {0}:
        raise ValueError("v2.7.2 final serialized models lost RNG identity")
    selected.to_csv(out / "frozen_final_models.csv", index=False)
    (
        pd.concat(trace_frames, ignore_index=True)
        if trace_frames else pd.DataFrame()
    ).to_csv(out / "final_selection_trace.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "available": True,
        "unavailable_reason": None,
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": part_seed,
        "n_M": len(M_NAMES),
        "representatives": representatives,
        "audit_predictors": list(audit_predictors),
        "model_random_state": 0,
        "selection_process_numpy_seed": 0,
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_final_selection": False,
        "final_models_serialized_before_sealed_audit": True,
        "stored_evidence_balanced_partition_reused_exactly": True,
        "deterministic_successor": True,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--part-dir", required=True)
    p.add_argument("--worker-dir", required=True)
    p.add_argument("--pretruth-dir", required=True)
    p.add_argument("--taxon", required=True)
    p.add_argument("--taxon-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv)
    freeze_fresh_final_models(
        contract_path=a.contract,
        part_dir=a.part_dir,
        worker_dir=a.worker_dir,
        pretruth_dir=a.pretruth_dir,
        taxon=a.taxon,
        taxon_index=a.taxon_index,
        output_dir=a.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
