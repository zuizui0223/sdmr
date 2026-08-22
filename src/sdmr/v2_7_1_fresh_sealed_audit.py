"""Open fresh v2.7.1 sealed environments once, after the pretruth freeze and final fits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .data import raster_specs_from_chelsa_manifest
from .metrics import continuous_boyce_index, presence_rank_score
from .model import score_ecological_suitability, score_relative_suitability
from .model_criteria import or10
from .niche_recovery import empirical_niche_recovery_profile
from .niche_recovery_selection import RECOVERY_DIRECTIONS
from .pilot_grid_cli import extract_protocol_grid_rasters
from .v2_6_empirical_model_pool_worker import M_NAMES
from .v2_6_empirical_sealed_audit import _dominates
from .v2_7_1_fresh_contract import load_v2_7_1_fresh_confirmation_contract

PURPOSE = "product_a_v2_7_1_fresh_part_sealed_audit"
FINAL_PURPOSE = "product_a_v2_7_1_fresh_final_models_presealed"
REQUIRED_SEALED_METRICS = ("presence_rank", *tuple(RECOVERY_DIRECTIONS))


def _final_workers(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in sorted(root.rglob("contract.json")):
        c = json.loads(path.read_text(encoding="utf-8"))
        if c.get("purpose") != FINAL_PURPOSE:
            continue
        if c.get("sealed_occurrence_environment_read") is not False:
            raise ValueError("fresh final-fit artifact crossed sealed barrier")
        taxon = str(c.get("taxon", ""))
        if not taxon or taxon in found:
            raise ValueError("fresh final-fit taxon missing or duplicated")
        found[taxon] = path.parent
    if len(found) != 12:
        raise ValueError(f"fresh sealed audit requires exactly 12 final-fit artifacts, found {len(found)}")
    return found


def _unavailable_output(
    *, out: Path, materialization: dict, pretruth_root: Path, reason: str,
    sealed_environment_read: bool = False, audit: pd.DataFrame | None = None,
    role_summary: pd.DataFrame | None = None, model_rows: list[dict] | None = None,
    resolution: pd.DataFrame | None = None, raster_provenance: pd.DataFrame | None = None,
) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    part_id = f"seed{int(materialization['seed'])}_sealed{float(materialization['sealed_fraction']):.2f}"
    process = pd.read_csv(pretruth_root / "pretruth_process_status.csv")
    process["part_id"] = part_id
    part = pd.DataFrame([{
        "part_id": part_id,
        "seed": int(materialization["seed"]),
        "sealed_fraction": float(materialization["sealed_fraction"]),
        "all_12_taxa": False,
        "all_3_M_specs": False,
        "mean_presence_rank_delta_vs_auc": float("nan"),
        "ecologically_nondominated_vs_auc": False,
        "strict_ecological_improvement_vs_auc": False,
        "part_available": False,
        "unavailable_reason": str(reason),
    }])
    (audit if audit is not None else pd.DataFrame()).to_csv(out / "sealed_empirical_audit.csv", index=False)
    (role_summary if role_summary is not None else pd.DataFrame()).to_csv(out / "sealed_role_summary.csv", index=False)
    part.to_csv(out / "part_summary.csv", index=False)
    process.to_csv(out / "process_status.csv", index=False)
    pd.DataFrame(model_rows or []).to_csv(out / "frozen_models_audited.csv", index=False)
    (resolution if resolution is not None else pd.DataFrame()).to_csv(out / "sealed_chelsa_resolution_ledger.csv", index=False)
    (raster_provenance if raster_provenance is not None else pd.DataFrame()).to_csv(out / "sealed_raster_provenance.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "part_id": part_id,
        "available": False,
        "unavailable_reason": str(reason),
        "sealed_occurrence_environment_read": bool(sealed_environment_read),
        "sealed_occurrence_first_read_after_pretruth_freeze": bool(sealed_environment_read),
        "sealed_occurrence_used_for_candidate_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_or_threshold_retuning_after_sealed_read": False,
        "aicc_interpreted_as_niche_recovery_metric": False,
        "structural_or_audit_abstention_propagated_as_unavailable": not bool(sealed_environment_read),
        "undefined_sealed_ecological_evidence_propagated_as_unavailable": bool(sealed_environment_read),
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_fresh_sealed_audit(
    *, contract_path: str | Path, part_dir: str | Path, pretruth_dir: str | Path,
    final_fit_root: str | Path, manifest_path: str | Path, output_dir: str | Path,
) -> dict[str, object]:
    load_v2_7_1_fresh_confirmation_contract(contract_path)
    part = Path(part_dir)
    materialization = json.loads((part / "contract.json").read_text(encoding="utf-8"))
    if materialization.get("purpose") != "product_a_v2_7_1_fresh_part_model_pool_materialization":
        raise ValueError("fresh sealed audit received wrong materialization")
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False:
        raise ValueError("fresh sealed environments were opened before declared audit")
    pretruth_root = Path(pretruth_dir)
    pretruth = json.loads((pretruth_root / "contract.json").read_text(encoding="utf-8"))
    if pretruth.get("purpose") != "product_a_v2_7_1_fresh_part_pretruth_freeze":
        raise ValueError("fresh sealed audit requires frozen fresh pretruth")
    out = Path(output_dir)
    finals = _final_workers(Path(final_fit_root))
    if pretruth.get("available") is not True:
        return _unavailable_output(
            out=out, materialization=materialization, pretruth_root=pretruth_root,
            reason=str(pretruth.get("unavailable_reason", "pretruth_unavailable")),
        )
    if pretruth.get("sealed_audit_authorized") is not True:
        return _unavailable_output(
            out=out, materialization=materialization, pretruth_root=pretruth_root,
            reason="pretruth_did_not_authorize_sealed_audit",
        )

    required_predictors: set[str] = set()
    for taxon, root in finals.items():
        c = json.loads((root / "contract.json").read_text(encoding="utf-8"))
        if c.get("available") is not True or c.get("final_models_serialized_before_sealed_audit") is not True:
            return _unavailable_output(
                out=out, materialization=materialization, pretruth_root=pretruth_root,
                reason=f"final_fit_unavailable:{taxon}",
            )
        required_predictors.update(str(x) for x in c.get("audit_predictors", ()))
        frozen = pd.read_csv(root / "frozen_final_models.csv")
        for value in frozen["selected_predictors"].astype(str):
            required_predictors.update(x for x in value.split(",") if x)
    if not required_predictors:
        return _unavailable_output(
            out=out, materialization=materialization, pretruth_root=pretruth_root,
            reason="no_frozen_predictors_for_sealed_audit",
        )

    manifest = pd.read_csv(manifest_path)
    missing = sorted(required_predictors - set(manifest["predictor"].astype(str)))
    if missing:
        raise ValueError(f"fresh sealed audit manifest missing frozen predictors: {missing}")
    manifest = manifest.loc[manifest["predictor"].astype(str).isin(required_predictors)].copy()
    raster_specs, resolution = raster_specs_from_chelsa_manifest(
        manifest, include_availability=("current",), strict=True
    )
    if {spec.predictor for spec in raster_specs} != required_predictors:
        raise ValueError("fresh sealed raster resolution did not cover exactly the frozen predictor union")

    # First authoritative environmental read of sealed rows. No modelling choice changes after this line.
    sealed_occurrences_raw = pd.read_parquet(part / "sealed_occurrences_raw.parquet")
    sealed_backgrounds_raw = {
        name: pd.read_parquet(part / "M" / name / "sealed_background_raw.parquet") for name in M_NAMES
    }
    sealed_occurrences, sealed_backgrounds, raster_provenance = extract_protocol_grid_rasters(
        sealed_occurrences_raw, sealed_backgrounds_raw, raster_specs
    )

    audit_rows: list[dict] = []
    model_rows: list[dict] = []
    try:
        for taxon in sorted(finals):
            root = finals[taxon]
            frozen = pd.read_csv(root / "frozen_final_models.csv")
            audit_predictors = tuple(
                json.loads((root / "contract.json").read_text(encoding="utf-8"))["audit_predictors"]
            )
            model_occurrences_all = pd.read_parquet(part / "model_occurrences.parquet")
            model_occurrences = model_occurrences_all.loc[
                model_occurrences_all["species"].astype(str).eq(taxon)
            ].reset_index(drop=True)
            sealed_p = sealed_occurrences.loc[
                sealed_occurrences["species"].astype(str).eq(taxon)
            ].reset_index(drop=True)
            if sealed_p.empty:
                raise ValueError(f"fresh sealed audit missing focal occurrences for {taxon}")
            for name in M_NAMES:
                model_bg_all = pd.read_parquet(part / "M" / name / "model_background.parquet")
                model_bg = model_bg_all.loc[
                    model_bg_all["species"].astype(str).eq(taxon)
                ].reset_index(drop=True)
                sealed_bg = sealed_backgrounds[name].loc[
                    sealed_backgrounds[name]["species"].astype(str).eq(taxon)
                ].reset_index(drop=True)
                if sealed_bg.empty:
                    raise ValueError(f"fresh sealed audit missing reference background for {taxon} {name}")
                rows = frozen.loc[frozen["M"].astype(str).eq(name)]
                if set(rows["role"].astype(str)) != {"ecological", "auc"} or len(rows) != 2:
                    raise ValueError(f"fresh final representative denominator changed for {taxon} {name}")
                for row in rows.itertuples(index=False):
                    selected = tuple(x for x in str(row.selected_predictors).split(",") if x)
                    model = joblib.load(root / str(row.model_file))
                    train_p_scores = score_relative_suitability(model, model_occurrences, selected)
                    sealed_p_scores = score_relative_suitability(model, sealed_p, selected)
                    sealed_b_scores = score_relative_suitability(model, sealed_bg, selected)
                    reference_scores = score_ecological_suitability(
                        model, model_bg, selected, observation_predictors=()
                    )
                    profile = empirical_niche_recovery_profile(
                        model_bg, sealed_p, reference_scores, audit_predictors
                    )
                    audit_rows.append({
                        "taxon": taxon,
                        "M": name,
                        "role": str(row.role),
                        "candidate": str(row.candidate),
                        "presence_rank": presence_rank_score(sealed_p_scores, sealed_b_scores),
                        "continuous_boyce": continuous_boyce_index(sealed_p_scores, sealed_b_scores),
                        "or10": or10(train_p_scores, sealed_p_scores),
                        "aicc_status": "not_computed_no_valid_likelihood_mapping_for_penalized_class_weighted_logit",
                        **profile.as_dict(),
                    })
                    model_rows.append({
                        "taxon": taxon,
                        "M": name,
                        "role": str(row.role),
                        "candidate": str(row.candidate),
                        "selected_predictors": str(row.selected_predictors),
                        "audit_predictors": ",".join(audit_predictors),
                        "model_file": str(row.model_file),
                    })
    except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
        return _unavailable_output(
            out=out,
            materialization=materialization,
            pretruth_root=pretruth_root,
            reason=f"sealed_evidence_undefined:{exc}",
            sealed_environment_read=True,
            audit=pd.DataFrame(audit_rows),
            model_rows=model_rows,
            resolution=resolution,
            raster_provenance=raster_provenance,
        )

    audit = pd.DataFrame(audit_rows)
    if len(audit) != 12 * len(M_NAMES) * 2 or audit["taxon"].nunique() != 12 or audit["M"].nunique() != 3:
        return _unavailable_output(
            out=out,
            materialization=materialization,
            pretruth_root=pretruth_root,
            reason="sealed_audit_denominator_incomplete",
            sealed_environment_read=True,
            audit=audit,
            model_rows=model_rows,
            resolution=resolution,
            raster_provenance=raster_provenance,
        )
    required_values = audit.loc[:, list(REQUIRED_SEALED_METRICS)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(required_values).all():
        return _unavailable_output(
            out=out,
            materialization=materialization,
            pretruth_root=pretruth_root,
            reason="required_sealed_prediction_or_niche_recovery_metric_nonfinite",
            sealed_environment_read=True,
            audit=audit,
            model_rows=model_rows,
            resolution=resolution,
            raster_provenance=raster_provenance,
        )

    role_summary = audit.groupby("role", as_index=False).agg(
        mean_presence_rank=("presence_rank", "mean"),
        mean_continuous_boyce=("continuous_boyce", "mean"),
        mean_or10=("or10", "mean"),
        **{metric: (metric, "mean") for metric in RECOVERY_DIRECTIONS},
        mean_envelope_coverage90=("sealed_pc12_envelope_coverage90", "mean"),
    )
    eco = role_summary.loc[role_summary["role"].astype(str).eq("ecological")].iloc[0]
    auc = role_summary.loc[role_summary["role"].astype(str).eq("auc")].iloc[0]
    summary_required = np.asarray([
        float(eco["mean_presence_rank"]), float(auc["mean_presence_rank"]),
        *[float(eco[m]) for m in RECOVERY_DIRECTIONS],
        *[float(auc[m]) for m in RECOVERY_DIRECTIONS],
    ])
    if not np.isfinite(summary_required).all():
        return _unavailable_output(
            out=out,
            materialization=materialization,
            pretruth_root=pretruth_root,
            reason="sealed_role_summary_required_metric_nonfinite",
            sealed_environment_read=True,
            audit=audit,
            role_summary=role_summary,
            model_rows=model_rows,
            resolution=resolution,
            raster_provenance=raster_provenance,
        )

    auc_dominates_eco = _dominates(auc, eco)
    eco_dominates_auc = _dominates(eco, auc)
    part_id = f"seed{int(materialization['seed'])}_sealed{float(materialization['sealed_fraction']):.2f}"
    part_summary = pd.DataFrame([{
        "part_id": part_id,
        "seed": int(materialization["seed"]),
        "sealed_fraction": float(materialization["sealed_fraction"]),
        "all_12_taxa": True,
        "all_3_M_specs": True,
        "mean_presence_rank_delta_vs_auc": float(eco["mean_presence_rank"] - auc["mean_presence_rank"]),
        "ecologically_nondominated_vs_auc": not auc_dominates_eco,
        "strict_ecological_improvement_vs_auc": eco_dominates_auc,
        "part_available": True,
        "unavailable_reason": None,
    }])
    process_status = pd.read_csv(pretruth_root / "pretruth_process_status.csv")
    process_status["part_id"] = part_id
    out.mkdir(parents=True, exist_ok=True)
    audit.to_csv(out / "sealed_empirical_audit.csv", index=False)
    role_summary.to_csv(out / "sealed_role_summary.csv", index=False)
    part_summary.to_csv(out / "part_summary.csv", index=False)
    process_status.to_csv(out / "process_status.csv", index=False)
    pd.DataFrame(model_rows).to_csv(out / "frozen_models_audited.csv", index=False)
    resolution.to_csv(out / "sealed_chelsa_resolution_ledger.csv", index=False)
    raster_provenance.to_csv(out / "sealed_raster_provenance.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "part_id": part_id,
        "available": True,
        "unavailable_reason": None,
        "sealed_occurrence_environment_read": True,
        "sealed_occurrence_first_read_after_pretruth_freeze": True,
        "sealed_occurrence_used_for_candidate_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_or_threshold_retuning_after_sealed_read": False,
        "aicc_interpreted_as_niche_recovery_metric": False,
        "sealed_raster_predictors_were_frozen_union_only": True,
        "required_sealed_metrics_all_finite": True,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--part-dir", required=True)
    p.add_argument("--pretruth-dir", required=True)
    p.add_argument("--final-fit-root", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv)
    run_fresh_sealed_audit(
        contract_path=a.contract,
        part_dir=a.part_dir,
        pretruth_dir=a.pretruth_dir,
        final_fit_root=a.final_fit_root,
        manifest_path=a.manifest,
        output_dir=a.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
