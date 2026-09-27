"""Diagnose true predictor coverage after frozen structural source decoding.

Diagnostic only: no predictor deletion, threshold relaxation, taxon replacement,
answer-check access, or model fitting is performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROGRAM = "sdmr-fresh-empirical-postdecode-coverage-audit-v1"
EXPECTED_TAXA = 50
EXPECTED_PREDICTORS = 46


def audit_coverage(
    *,
    decoded_bundle_dir: str | Path,
    process_registry_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    root = Path(decoded_bundle_dir)
    features = pd.read_parquet(root / "location_features_source_decoded_v2.parquet")
    model_idx = pd.read_csv(root / "model_pool_feature_index_v2.csv")
    bg_idx = pd.read_csv(root / "background_300km_feature_index_v2.csv")
    gate = pd.read_csv(root / "complete_case_gate_v2.csv")
    registry = pd.read_csv(process_registry_path)
    predictors = registry["predictor"].astype(str).tolist()
    if len(predictors) != EXPECTED_PREDICTORS or len(set(predictors)) != EXPECTED_PREDICTORS:
        raise ValueError("predictor universe changed")
    if gate["scientific_name"].astype(str).nunique() != EXPECTED_TAXA:
        raise ValueError("taxon denominator changed")

    location = features.set_index("location_id")
    rows = []
    loo_rows = []
    failing_taxa = gate.loc[
        ~gate["complete_case_gate_passed"].astype(bool),
        "scientific_name",
    ].astype(str).tolist()

    for taxon in failing_taxa:
        m_idx = model_idx.loc[model_idx["scientific_name"].astype(str).eq(taxon)].copy()
        b_idx = bg_idx.loc[bg_idx["scientific_name"].astype(str).eq(taxon)].copy()
        m = location.reindex(m_idx["location_id"].astype(int).tolist())
        b = location.reindex(b_idx["location_id"].astype(int).tolist())
        for predictor in predictors:
            m_finite = pd.to_numeric(m[predictor], errors="coerce").notna()
            b_finite = pd.to_numeric(b[predictor], errors="coerce").notna()
            rows.append(
                {
                    "scientific_name": taxon,
                    "predictor": predictor,
                    "process": str(
                        registry.loc[
                            registry["predictor"].astype(str).eq(predictor),
                            "process",
                        ].iloc[0]
                    ),
                    "model_pool_rows": int(len(m)),
                    "model_pool_finite_rows": int(m_finite.sum()),
                    "model_pool_finite_fraction": float(m_finite.mean()),
                    "background_rows": int(len(b)),
                    "background_finite_rows": int(b_finite.sum()),
                    "background_finite_fraction": float(b_finite.mean()),
                    "individual_predictor_below_model_080": bool(m_finite.mean() < 0.8),
                    "individual_predictor_below_background_4000": bool(b_finite.sum() < 4000),
                }
            )

        # Diagnostic leave-one-predictor-out completeness. This is NOT permission
        # to delete a predictor; it only identifies the coverage bottleneck for a
        # future independent design.
        for omitted in predictors:
            kept = [p for p in predictors if p != omitted]
            m_complete = m[kept].notna().all(axis=1)
            b_complete = b[kept].notna().all(axis=1)
            retention = float(m_complete.mean()) if len(m) else 0.0
            gate_pass = (
                retention >= 0.8
                and int(m_complete.sum()) >= 50
                and int(b_complete.sum()) >= 4000
            )
            loo_rows.append(
                {
                    "scientific_name": taxon,
                    "omitted_predictor_diagnostic_only": omitted,
                    "model_pool_complete_rows_without": int(m_complete.sum()),
                    "model_pool_retention_without": retention,
                    "background_complete_rows_without": int(b_complete.sum()),
                    "would_pass_complete_case_gate_without": bool(gate_pass),
                }
            )

    coverage = pd.DataFrame(rows)
    loo = pd.DataFrame(loo_rows)
    blockers = coverage.loc[
        coverage["individual_predictor_below_model_080"]
        | coverage["individual_predictor_below_background_4000"]
    ]
    result = {
        "program": PROGRAM,
        "status": "diagnostic_complete",
        "failing_taxa": len(failing_taxa),
        "taxa_with_individual_predictor_blockers": int(
            blockers["scientific_name"].nunique()
        ),
        "individual_blocker_predictors": sorted(
            blockers["predictor"].astype(str).unique().tolist()
        ),
        "individual_blocker_processes": sorted(
            blockers["process"].astype(str).unique().tolist()
        ),
        "taxa_rescued_by_single_predictor_omission_diagnostic_only": int(
            loo.loc[loo["would_pass_complete_case_gate_without"], "scientific_name"]
            .astype(str)
            .nunique()
        ),
        "answer_check_accessed": False,
        "model_fitting_performed": False,
        "predictor_deletion_performed": False,
        "threshold_relaxation_performed": False,
        "taxon_replacement_performed": False,
    }
    return coverage, loo, result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decoded-bundle-dir", required=True)
    parser.add_argument("--process-registry", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    coverage, loo, result = audit_coverage(
        decoded_bundle_dir=args.decoded_bundle_dir,
        process_registry_path=args.process_registry,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(out / "failing_taxon_predictor_coverage.csv", index=False)
    loo.to_csv(out / "leave_one_predictor_out_coverage_diagnostic.csv", index=False)
    (out / "coverage_audit_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
