"""Deterministic source-decoding recovery for the fresh 46-layer feature bundle.

This module preserves the original v1 feature-gate failure and creates a new
v2 bundle by decoding only structural ecological states that were encoded as
raster NODATA.  No taxon, predictor, threshold, or answer-check data may change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.process_id.fresh.features import (
    EXPECTED_PREDICTORS,
    EXPECTED_TAXA,
    MIN_MODEL_POOL_COMPLETE_ROWS,
    MIN_MODEL_POOL_RETENTION_FRACTION,
    MIN_PRIMARY_BACKGROUND_COMPLETE_ROWS,
    evaluate_complete_case_gate,
)

PROGRAM = "sdmr-fresh-empirical-feature-source-decoding-v2"
EXPECTED_LOCATION_ROWS = 249_919
EXPECTED_SOURCE_ARTIFACT_DIGEST = (
    "sha256:0cf9df03c101ffa9fd22f903e795599de5ead38b31164e615b5c1e9510e79906"
)
EXPECTED_CORRECTION_COUNTS = {
    "fcf": 148_163,
    "swe": 186_897,
    "fgd": 91_166,
    "lgd": 91_166,
    "gdgfgd5": 130_488,
    "gdgfgd10": 77_774,
}


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require_columns(frame: pd.DataFrame, columns: set[str], *, name: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


def apply_frozen_source_decoding(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(features) != EXPECTED_LOCATION_ROWS:
        raise ValueError("frozen location denominator changed")
    required = {
        "location_id",
        "fcf",
        "bio6",
        "swe",
        "scd",
        "fgd",
        "lgd",
        "gsl",
        "gdgfgd5",
        "gdgfgd10",
        "ngd5",
        "ngd10",
    }
    _require_columns(features, required, name="location feature bundle")

    out = features.copy()
    ledger: list[dict[str, object]] = []

    rules = [
        ("fcf", out["fcf"].isna() & pd.to_numeric(out["bio6"], errors="coerce").gt(0), 0.0,
         "no_freezing_month_zero_freeze_thaw_transitions"),
        ("swe", out["swe"].isna() & pd.to_numeric(out["scd"], errors="coerce").eq(0), 0.0,
         "zero_snow_cover_days_zero_swe"),
        ("fgd", out["fgd"].isna() & pd.to_numeric(out["gsl"], errors="coerce").eq(365), 1.0,
         "all_year_growing_season_first_day_1"),
        ("lgd", out["lgd"].isna() & pd.to_numeric(out["gsl"], errors="coerce").eq(365), 365.0,
         "all_year_growing_season_last_day_365"),
        ("gdgfgd5", out["gdgfgd5"].isna() & pd.to_numeric(out["ngd5"], errors="coerce").eq(365), 1.0,
         "all_year_above_5C_first_qualifying_day_1"),
        ("gdgfgd10", out["gdgfgd10"].isna() & pd.to_numeric(out["ngd10"], errors="coerce").eq(365), 1.0,
         "all_year_above_10C_first_qualifying_day_1"),
    ]

    for predictor, mask, value, reason in rules:
        count = int(mask.sum())
        expected = EXPECTED_CORRECTION_COUNTS[predictor]
        if count != expected:
            raise RuntimeError(
                f"frozen source-decoding count changed for {predictor}: "
                f"{count} != {expected}"
            )
        before_nonmissing = int(out[predictor].notna().sum())
        out.loc[mask, predictor] = float(value)
        after_nonmissing = int(out[predictor].notna().sum())
        if after_nonmissing - before_nonmissing != count:
            raise RuntimeError(f"source decoding did not add exactly {count} rows for {predictor}")
        ledger.append(
            {
                "predictor": predictor,
                "corrected_rows": count,
                "set_to": float(value),
                "reason": reason,
                "rule_is_value_deterministic": True,
            }
        )

    return out, pd.DataFrame(ledger)


def rebuild_complete_case_gate(
    *,
    corrected_locations: pd.DataFrame,
    model_index: pd.DataFrame,
    background_index: pd.DataFrame,
    predictors: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if len(predictors) != EXPECTED_PREDICTORS or len(set(predictors)) != EXPECTED_PREDICTORS:
        raise ValueError("source decoding requires exact frozen 46-predictor universe")
    if "location_id" not in corrected_locations:
        raise KeyError("corrected locations lack location_id")
    if corrected_locations["location_id"].duplicated().any():
        raise ValueError("corrected location IDs must remain unique")

    location_features = corrected_locations[["location_id", *predictors]].copy()
    model = model_index.drop(columns=["complete_case"], errors="ignore").merge(
        location_features,
        on="location_id",
        how="left",
        validate="many_to_one",
    )
    background = background_index.drop(columns=["complete_case"], errors="ignore").merge(
        location_features,
        on="location_id",
        how="left",
        validate="many_to_one",
    )
    gate = evaluate_complete_case_gate(
        model_features=model,
        background_features=background,
        predictors=predictors,
    )

    complete_ids = set(
        location_features.loc[
            location_features[predictors].notna().all(axis=1),
            "location_id",
        ].astype(int)
    )
    model_out = model_index.drop(columns=["complete_case"], errors="ignore").copy()
    model_out["complete_case"] = model_out["location_id"].astype(int).isin(complete_ids)
    bg_out = background_index.drop(columns=["complete_case"], errors="ignore").copy()
    bg_out["complete_case"] = bg_out["location_id"].astype(int).isin(complete_ids)
    return gate, model_out, bg_out


def run_recovery(
    *,
    source_bundle_dir: str | Path,
    contract_path: str | Path,
    process_registry_path: str | Path,
    output_dir: str | Path,
) -> dict:
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if contract.get("program") != PROGRAM:
        raise ValueError("wrong source-decoding recovery contract")
    unchanged = contract.get("unchanged", {})
    expected = {
        "taxon_count": EXPECTED_TAXA,
        "predictor_count": EXPECTED_PREDICTORS,
        "minimum_model_pool_retention_fraction": MIN_MODEL_POOL_RETENTION_FRACTION,
        "minimum_model_pool_complete_rows": MIN_MODEL_POOL_COMPLETE_ROWS,
        "minimum_primary_background_complete_rows": MIN_PRIMARY_BACKGROUND_COMPLETE_ROWS,
        "predictor_deletion": False,
        "taxon_replacement": False,
        "threshold_relaxation": False,
    }
    for key, value in expected.items():
        if unchanged.get(key) != value:
            raise ValueError(f"frozen source-decoding invariant changed: {key}")

    registry = pd.read_csv(process_registry_path)
    predictors = registry["predictor"].astype(str).tolist()
    if len(predictors) != EXPECTED_PREDICTORS or len(set(predictors)) != EXPECTED_PREDICTORS:
        raise ValueError("process registry no longer contains exact 46 predictors")

    source = Path(source_bundle_dir)
    feature_path = source / "location_features.parquet"
    model_index_path = source / "model_pool_feature_index.csv"
    background_index_path = source / "background_300km_feature_index.csv"
    provenance_path = source / "raster_provenance.csv"
    missingness_path = source / "predictor_missingness.csv"
    result_path = source / "feature_extraction_result.json"
    for path in (
        feature_path,
        model_index_path,
        background_index_path,
        provenance_path,
        missingness_path,
        result_path,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    prior = json.loads(result_path.read_text(encoding="utf-8"))
    if prior.get("status") != "feature_extraction_unavailable_complete_case_gate_failed":
        raise ValueError("source v1 feature bundle is not the frozen gate failure")
    if prior.get("answer_check_accessed") is not False:
        raise ValueError("source bundle crossed answer-check boundary")
    if prior.get("model_fitting_performed") is not False:
        raise ValueError("source bundle fitted models before decoding recovery")

    features = pd.read_parquet(feature_path)
    model_index = pd.read_csv(model_index_path)
    background_index = pd.read_csv(background_index_path)
    corrected, ledger = apply_frozen_source_decoding(features)
    gate, model_out, bg_out = rebuild_complete_case_gate(
        corrected_locations=corrected,
        model_index=model_index,
        background_index=background_index,
        predictors=predictors,
    )

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    corrected_path = output / "location_features_source_decoded_v2.parquet"
    ledger_path = output / "source_decoding_ledger.csv"
    gate_path = output / "complete_case_gate_v2.csv"
    model_out_path = output / "model_pool_feature_index_v2.csv"
    bg_out_path = output / "background_300km_feature_index_v2.csv"

    corrected.to_parquet(corrected_path, index=False)
    ledger.to_csv(ledger_path, index=False)
    gate.to_csv(gate_path, index=False)
    model_out.to_csv(model_out_path, index=False)
    bg_out.to_csv(bg_out_path, index=False)

    all_passed = bool(gate["complete_case_gate_passed"].all())
    min_ret = gate.loc[gate["model_pool_retention_fraction"].astype(float).idxmin()]
    min_bg = gate.loc[gate["background_complete_rows"].astype(int).idxmin()]
    result = {
        "program": PROGRAM,
        "status": (
            "source_decoding_recovery_complete_case_gate_passed"
            if all_passed
            else "source_decoding_recovery_complete_case_gate_failed"
        ),
        "taxon_count": EXPECTED_TAXA,
        "predictor_count": EXPECTED_PREDICTORS,
        "corrected_predictors": ledger["predictor"].astype(str).tolist(),
        "total_structural_decoding_rows": int(ledger["corrected_rows"].sum()),
        "taxa_passing_complete_case_gate": int(gate["complete_case_gate_passed"].sum()),
        "all_taxa_complete_case_gate_passed": all_passed,
        "minimum_model_pool_retention_fraction": float(
            min_ret["model_pool_retention_fraction"]
        ),
        "minimum_model_pool_retention_taxon": str(min_ret["scientific_name"]),
        "minimum_background_complete_rows": int(min_bg["background_complete_rows"]),
        "minimum_background_complete_taxon": str(min_bg["scientific_name"]),
        "location_features_sha256": _sha256(corrected_path),
        "source_decoding_ledger_sha256": _sha256(ledger_path),
        "complete_case_gate_sha256": _sha256(gate_path),
        "model_pool_feature_index_sha256": _sha256(model_out_path),
        "background_300km_feature_index_sha256": _sha256(bg_out_path),
        "answer_check_accessed": False,
        "model_fitting_performed": False,
        "taxon_replacement_performed": False,
        "predictor_deletion_performed": False,
        "threshold_relaxation_performed": False,
        "next_gate": (
            "fit_frozen_process_first_and_flat_comparators_on_model_pool_only"
            if all_passed
            else "terminal_unavailable_true_coverage_after_source_decoding"
        ),
    }
    (output / "source_decoding_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-bundle-dir", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--process-registry", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = run_recovery(
        source_bundle_dir=args.source_bundle_dir,
        contract_path=args.contract,
        process_registry_path=args.process_registry,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
