"""Open one empirical part's sealed environments only after all final models are frozen."""
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
from .v2_6_empirical_contract import load_v2_6_empirical_contract
from .v2_6_empirical_model_pool_worker import M_NAMES


def _load_final_fit_workers(root: Path) -> dict[str, Path]:
    found = {}
    for path in sorted(root.rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != "product_a_v2_6_empirical_final_models_presealed":
            continue
        if payload.get("sealed_occurrence_environment_read") is not False:
            raise ValueError("a final-fit artifact crossed the sealed environment barrier")
        if payload.get("final_models_serialized_before_sealed_audit") is not True:
            raise ValueError("final models were not serialized before sealed audit")
        taxon = str(payload["taxon"])
        if taxon in found:
            raise ValueError(f"duplicate final-fit artifact for {taxon}")
        found[taxon] = path.parent
    if len(found) != 12:
        raise ValueError(f"sealed audit requires exactly 12 final-fit artifacts, found {len(found)}")
    return found


def _dominates(a: pd.Series, b: pd.Series) -> bool:
    strict = False
    for metric, direction in RECOVERY_DIRECTIONS.items():
        av = float(a[metric]); bv = float(b[metric])
        if not np.isfinite(av) or not np.isfinite(bv):
            return False
        if direction == "max":
            if av < bv - 1e-12:
                return False
            strict |= av > bv + 1e-12
        else:
            if av > bv + 1e-12:
                return False
            strict |= av < bv - 1e-12
    return bool(strict)


def run_sealed_audit(
    *,
    contract_path: str | Path,
    part_dir: str | Path,
    pretruth_dir: str | Path,
    final_fit_root: str | Path,
    manifest_path: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_6_empirical_contract(contract_path)
    part = Path(part_dir)
    materialization = json.loads((part / "contract.json").read_text(encoding="utf-8"))
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False:
        raise ValueError("sealed environments were already opened before the declared audit")
    pretruth_root = Path(pretruth_dir)
    pretruth = json.loads((pretruth_root / "contract.json").read_text(encoding="utf-8"))
    if pretruth.get("purpose") != "product_a_v2_6_empirical_part_pretruth_freeze":
        raise ValueError("sealed audit requires the frozen pretruth aggregate")
    if pretruth.get("sealed_audit_authorized") is not True:
        raise ValueError("pretruth freeze did not authorize the sealed audit")
    final_workers = _load_final_fit_workers(Path(final_fit_root))

    # This is the first environmental-raster access for authoritative sealed rows.
    sealed_occurrences_raw = pd.read_parquet(part / "sealed_occurrences_raw.parquet")
    sealed_backgrounds_raw = {
        name: pd.read_parquet(part / "M" / name / "sealed_background_raw.parquet")
        for name in M_NAMES
    }
    manifest = pd.read_csv(manifest_path)
    raster_specs, resolution = raster_specs_from_chelsa_manifest(
        manifest, include_availability=("current",), strict=True
    )
    audit_predictors = tuple(spec.predictor for spec in raster_specs)
    sealed_occurrences, sealed_backgrounds, sealed_raster_provenance = extract_protocol_grid_rasters(
        sealed_occurrences_raw,
        sealed_backgrounds_raw,
        raster_specs,
    )

    audit_rows = []
    model_rows = []
    for taxon in sorted(final_workers):
        worker = final_workers[taxon]
        frozen = pd.read_csv(worker / "frozen_final_models.csv")
        model_occurrences_all = pd.read_parquet(part / "model_occurrences.parquet")
        model_occurrences = model_occurrences_all.loc[
            model_occurrences_all["species"].astype(str).eq(taxon)
        ].reset_index(drop=True)
        sealed_p = sealed_occurrences.loc[sealed_occurrences["species"].astype(str).eq(taxon)].reset_index(drop=True)
        if sealed_p.empty:
            raise ValueError(f"sealed audit missing focal occurrences for {taxon}")
        for name in M_NAMES:
            model_bg_all = pd.read_parquet(part / "M" / name / "model_background.parquet")
            model_bg = model_bg_all.loc[model_bg_all["species"].astype(str).eq(taxon)].reset_index(drop=True)
            sealed_bg_all = sealed_backgrounds[name]
            sealed_bg = sealed_bg_all.loc[sealed_bg_all["species"].astype(str).eq(taxon)].reset_index(drop=True)
            if sealed_bg.empty:
                raise ValueError(f"sealed audit missing reference background for {taxon} {name}")
            rows = frozen.loc[frozen["M"].astype(str).eq(name)]
            if set(rows["role"].astype(str)) != {"ecological", "auc"} or len(rows) != 2:
                raise ValueError(f"final-fit representative denominator changed for {taxon} {name}")
            for row in rows.itertuples(index=False):
                selected = tuple(x for x in str(row.selected_predictors).split(",") if x)
                model = joblib.load(worker / str(row.model_file))
                train_p_scores = score_relative_suitability(model, model_occurrences, selected)
                sealed_p_scores = score_relative_suitability(model, sealed_p, selected)
                sealed_b_scores = score_relative_suitability(model, sealed_bg, selected)
                ecological_reference_scores = score_ecological_suitability(
                    model, model_bg, selected, observation_predictors=(),
                )
                profile = empirical_niche_recovery_profile(
                    model_bg,
                    sealed_p,
                    ecological_reference_scores,
                    audit_predictors,
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
                    "taxon": taxon, "M": name, "role": str(row.role),
                    "candidate": str(row.candidate), "selected_predictors": str(row.selected_predictors),
                    "model_file": str(row.model_file),
                })

    audit = pd.DataFrame(audit_rows)
    if len(audit) != 12 * len(M_NAMES) * 2:
        raise ValueError("sealed audit did not produce the complete 12 x 3M x 2-representative table")
    role_summary = audit.groupby("role", as_index=False).agg(
        mean_presence_rank=("presence_rank", "mean"),
        mean_continuous_boyce=("continuous_boyce", "mean"),
        mean_or10=("or10", "mean"),
        **{metric: (metric, "mean") for metric in RECOVERY_DIRECTIONS},
        mean_envelope_coverage90=("sealed_pc12_envelope_coverage90", "mean"),
    )
    eco = role_summary.loc[role_summary["role"].astype(str).eq("ecological")].iloc[0]
    auc = role_summary.loc[role_summary["role"].astype(str).eq("auc")].iloc[0]
    auc_dominates_eco = _dominates(auc, eco)
    eco_dominates_auc = _dominates(eco, auc)
    part_id = f"seed{int(materialization['seed'])}_sealed{float(materialization['sealed_fraction']):.2f}"
    part_summary = pd.DataFrame([{
        "part_id": part_id,
        "seed": int(materialization["seed"]),
        "sealed_fraction": float(materialization["sealed_fraction"]),
        "all_12_taxa": audit["taxon"].nunique() == 12,
        "all_3_M_specs": audit["M"].nunique() == 3,
        "mean_presence_rank_delta_vs_auc": float(eco["mean_presence_rank"] - auc["mean_presence_rank"]),
        "ecologically_nondominated_vs_auc": not auc_dominates_eco,
        "strict_ecological_improvement_vs_auc": eco_dominates_auc,
    }])
    process_status = pd.read_csv(pretruth_root / "pretruth_process_status.csv")
    process_status["part_id"] = part_id

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit.to_csv(out / "sealed_empirical_audit.csv", index=False)
    role_summary.to_csv(out / "sealed_role_summary.csv", index=False)
    part_summary.to_csv(out / "part_summary.csv", index=False)
    process_status.to_csv(out / "process_status.csv", index=False)
    pd.DataFrame(model_rows).to_csv(out / "frozen_models_audited.csv", index=False)
    resolution.to_csv(out / "sealed_chelsa_resolution_ledger.csv", index=False)
    sealed_raster_provenance.to_csv(out / "sealed_raster_provenance.csv", index=False)
    result = {
        "purpose": "product_a_v2_6_empirical_part_sealed_audit",
        "part_id": part_id,
        "sealed_occurrence_environment_read": True,
        "sealed_occurrence_first_read_after_pretruth_freeze": True,
        "sealed_occurrence_used_for_candidate_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_or_threshold_retuning_after_sealed_read": False,
        "aicc_interpreted_as_niche_recovery_metric": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--part-dir", required=True)
    parser.add_argument("--pretruth-dir", required=True)
    parser.add_argument("--final-fit-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_sealed_audit(
        contract_path=args.contract,
        part_dir=args.part_dir,
        pretruth_dir=args.pretruth_dir,
        final_fit_root=args.final_fit_root,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
