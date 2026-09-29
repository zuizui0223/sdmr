"""Audit structural missingness in the frozen fresh feature bundle.

This audit is diagnostic only.  It never fits a model, opens answer-check
occurrences, changes the 50-taxon cohort, or changes the frozen predictor
universe.  Its purpose is to distinguish true raster coverage gaps from
source-encoding collisions such as a GeoTIFF NODATA value of zero for
ecological variables whose valid domain includes zero.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROGRAM = "sdmr-fresh-empirical-feature-missingness-audit-v1"

ZERO_DOMAIN_PREDICTORS = (
    "fcf",
    "ngd0",
    "ngd5",
    "ngd10",
    "gsl",
)
EVENT_DATE_PAIRS = (
    ("fgd", "gsl"),
    ("lgd", "gsl"),
    ("gdgfgd5", "ngd5"),
    ("gdgfgd10", "ngd10"),
)


def _as_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        raise KeyError(f"missing diagnostic column: {column}")
    return pd.to_numeric(frame[column], errors="coerce")


def audit_feature_missingness(
    *,
    location_features_path: str | Path,
    predictor_missingness_path: str | Path,
    raster_provenance_path: str | Path,
) -> dict:
    features = pd.read_parquet(location_features_path)
    missingness = pd.read_csv(predictor_missingness_path)
    provenance = pd.read_csv(raster_provenance_path)

    if len(features) != 249_919:
        raise ValueError("frozen location denominator changed")
    if len(missingness) != 46 or missingness["predictor"].astype(str).nunique() != 46:
        raise ValueError("frozen predictor denominator changed")
    if provenance["predictor"].astype(str).nunique() != 46:
        raise ValueError("raster provenance predictor denominator changed")

    prov = provenance.drop_duplicates("predictor").set_index("predictor")
    miss = missingness.set_index("predictor")
    rows: list[dict[str, object]] = []

    for predictor in ZERO_DOMAIN_PREDICTORS:
        nodata = float(prov.loc[predictor, "nodata"])
        missing_rows = int(miss.loc[predictor, "missing_rows"])
        rows.append(
            {
                "audit_type": "zero_domain_nodata_collision",
                "predictor": predictor,
                "companion": "",
                "nodata": nodata,
                "missing_rows": missing_rows,
                "condition_rows": missing_rows if nodata == 0 else 0,
                "condition_fraction_of_missing": (
                    1.0 if missing_rows and nodata == 0 else 0.0
                ),
                "interpretation": (
                    "source_nodata_equals_valid_domain_zero"
                    if nodata == 0
                    else "no_zero_nodata_collision"
                ),
            }
        )

    for predictor, companion in EVENT_DATE_PAIRS:
        p = _as_numeric(features, predictor)
        c = _as_numeric(features, companion)
        missing = p.isna()
        missing_n = int(missing.sum())
        positive = c > 0
        rows.append(
            {
                "audit_type": "event_date_missing_with_positive_companion",
                "predictor": predictor,
                "companion": companion,
                "nodata": float(prov.loc[predictor, "nodata"]),
                "missing_rows": missing_n,
                "condition_rows": int((missing & positive).sum()),
                "condition_fraction_of_missing": (
                    float((missing & positive).sum() / missing_n)
                    if missing_n
                    else 0.0
                ),
                "interpretation": "missing_event_date_despite_positive_companion",
            }
        )
        if companion.startswith("ngd") or companion == "gsl":
            rows.append(
                {
                    "audit_type": "event_date_missing_with_full_year_companion",
                    "predictor": predictor,
                    "companion": companion,
                    "nodata": float(prov.loc[predictor, "nodata"]),
                    "missing_rows": missing_n,
                    "condition_rows": int((missing & c.eq(365)).sum()),
                    "condition_fraction_of_missing": (
                        float((missing & c.eq(365)).sum() / missing_n)
                        if missing_n
                        else 0.0
                    ),
                    "interpretation": "missing_event_date_where_companion_holds_all_year",
                }
            )

    swe = _as_numeric(features, "swe")
    scd = _as_numeric(features, "scd")
    swe_missing = swe.isna()
    swe_missing_n = int(swe_missing.sum())
    for label, condition in (
        ("scd_zero", scd.eq(0)),
        ("scd_positive", scd.gt(0)),
        ("scd_missing", scd.isna()),
    ):
        rows.append(
            {
                "audit_type": "swe_missingness_by_snow_cover_days",
                "predictor": "swe",
                "companion": "scd",
                "nodata": float(prov.loc["swe", "nodata"]),
                "missing_rows": swe_missing_n,
                "condition_rows": int((swe_missing & condition).sum()),
                "condition_fraction_of_missing": (
                    float((swe_missing & condition).sum() / swe_missing_n)
                    if swe_missing_n
                    else 0.0
                ),
                "interpretation": label,
            }
        )

    fcf = _as_numeric(features, "fcf")
    bio6 = _as_numeric(features, "bio6")
    fcf_missing = fcf.isna()
    fcf_missing_n = int(fcf_missing.sum())
    for label, condition in (
        ("coldest_month_above_zero", bio6.gt(0)),
        ("coldest_month_at_or_below_zero", bio6.le(0)),
    ):
        rows.append(
            {
                "audit_type": "fcf_missingness_by_winter_temperature",
                "predictor": "fcf",
                "companion": "bio6",
                "nodata": float(prov.loc["fcf", "nodata"]),
                "missing_rows": fcf_missing_n,
                "condition_rows": int((fcf_missing & condition).sum()),
                "condition_fraction_of_missing": (
                    float((fcf_missing & condition).sum() / fcf_missing_n)
                    if fcf_missing_n
                    else 0.0
                ),
                "interpretation": label,
            }
        )

    audit = pd.DataFrame(rows)
    zero_collision_predictors = sorted(
        audit.loc[
            audit["audit_type"].eq("zero_domain_nodata_collision")
            & audit["interpretation"].eq("source_nodata_equals_valid_domain_zero"),
            "predictor",
        ].astype(str)
    )
    swe_zero_row = audit.loc[
        audit["audit_type"].eq("swe_missingness_by_snow_cover_days")
        & audit["interpretation"].eq("scd_zero")
    ].iloc[0]
    result = {
        "program": PROGRAM,
        "status": "diagnostic_complete",
        "location_rows": int(len(features)),
        "predictor_count": 46,
        "zero_domain_nodata_collision_predictors": zero_collision_predictors,
        "zero_domain_nodata_collision_count": len(zero_collision_predictors),
        "swe_missing_rows": swe_missing_n,
        "swe_missing_with_scd_zero": int(swe_zero_row["condition_rows"]),
        "swe_missing_with_scd_zero_fraction": float(
            swe_zero_row["condition_fraction_of_missing"]
        ),
        "answer_check_accessed": False,
        "model_fitting_performed": False,
        "taxon_replacement_performed": False,
        "predictor_deletion_performed": False,
    }
    return {"result": result, "audit": audit}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--location-features", required=True)
    parser.add_argument("--predictor-missingness", required=True)
    parser.add_argument("--raster-provenance", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    out = audit_feature_missingness(
        location_features_path=args.location_features,
        predictor_missingness_path=args.predictor_missingness,
        raster_provenance_path=args.raster_provenance,
    )
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    out["audit"].to_csv(output / "structural_missingness_audit.csv", index=False)
    (output / "structural_missingness_result.json").write_text(
        json.dumps(out["result"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(out["result"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
