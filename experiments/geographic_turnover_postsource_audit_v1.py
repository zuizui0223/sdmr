"""Post-source Quercus real-record diagnostic; never a process/niche claim.

This is a *retrospective sensitivity study*: the source regions and climate cells
were frozen before observation extraction, but effort exponent, adequacy review
and this retrospective audit were designed after the first source opening.
It is therefore scientifically inappropriate to present any p value or ranking
as a prospective biological finding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp

from experiments import geographic_driver_turnover_v0 as model

# Sensitivity alternatives, NOT estimators of true collection effort.
EFFORT_EXPONENTS = (0.0, 0.5, 1.0)
REQUIRED_SOURCE_FIELDS = (
    "region", "cell_id", "spatial_block", "temperature", "moisture",
    "n_focal_records_diagnostic", "n_independent_target_group_records_diagnostic",
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_checks(frame: pd.DataFrame, receipt: dict, config: dict, taxon: str) -> tuple[pd.DataFrame, dict]:
    """Fail closed on eligibility; report all source status, including controls."""
    if receipt.get("macro_inference_blocked") is not True:
        raise ValueError("Source must remain macro-inference-blocked")
    if receipt.get("analysis") != "geographic_turnover_native_window_source_diagnostic_v1":
        raise ValueError("Wrong source receipt lineage")
    if config.get("study_status") != "source_and_geometry_diagnostic_only":
        raise ValueError("Study status was not source-only")
    if receipt.get("window_count") != len(config.get("windows", [])):
        raise ValueError("Incomplete source-window denominator")
    expected_regions = {w["region"] for w in config["windows"]}
    if set(frame.region) != expected_regions:
        raise ValueError("Available-climate source table missing/adding fixed regions")
    if frame.duplicated(["region", "cell_id"]).any():
        raise ValueError("Duplicate region/cell source rows")
    for field in REQUIRED_SOURCE_FIELDS:
        if field not in frame.columns:
            raise ValueError("Missing source field: " + field)
    statuses = {}
    for w in config["windows"]:
        candidates = [r for r in receipt.get("windows", []) if r.get("region") == w["region"]]
        if len(candidates) != 1:
            raise ValueError("Missing/duplicated source receipt window: " + w["region"])
        row = candidates[0]
        if row.get("focal_taxon") != w["focal_taxon"] or row.get("country") != w["country"]:
            raise ValueError("Source taxon/country identity drift")
        subset = frame.loc[frame.region == w["region"]]
        if int(row.get("n_climate_complete_cells", -1)) != len(subset):
            raise ValueError("Climate cell count disagrees with source receipt")
        statuses[w["region"]] = {
            "taxon": row["focal_taxon"],
            "focal_source_status": row.get("focal_source", {}).get("status"),
            "effort_source_status": row.get("target_group_effort_status"),
            "n_climate_cells": len(subset),
        }
    eligible = []
    for w in config["windows"]:
        if w["focal_taxon"] != taxon:
            continue
        s = statuses[w["region"]]
        if s["focal_source_status"] != "complete_diagnostic_search_archive":
            raise ValueError("Focal full-search archive incomplete in " + w["region"])
        if s["effort_source_status"] != "candidate_proxy_only_not_calibrated":
            raise ValueError("Target-group proxy source incomplete in " + w["region"])
        g = frame.loc[frame.region == w["region"]].copy()
        if g[list(REQUIRED_SOURCE_FIELDS[3:])].isna().any().any():
            raise ValueError("Missing ecological values or record counts")
        if (g.n_independent_target_group_records_diagnostic <= 0).any():
            raise ValueError("Zero sentinel count; cannot impute effort")
        if (g.n_focal_records_diagnostic < 0).any():
            raise ValueError("Invalid focal count")
        original = next(x for x in receipt["windows"] if x["region"] == w["region"])
        if int(g.n_focal_records_diagnostic.sum()) != int(original["n_admitted_focal_records_in_climate_cells"]):
            raise ValueError("Focal record total mismatch against authoritative source")
        if int((g.n_focal_records_diagnostic > 0).sum()) != int(original["n_climate_cells_with_focal_records"]):
            raise ValueError("Focal occupied-cell total mismatch")
        eligible.append(g)
    if len(eligible) != 2 or len({g.region.iloc[0] for g in eligible}) != 2:
        raise ValueError("Fixed two-region focal source panel not complete")
    a = pd.concat(eligible, ignore_index=True)
    a["taxon"] = taxon
    a["effort"] = a.n_independent_target_group_records_diagnostic.astype(float)
    a["n_occ"] = a.n_focal_records_diagnostic.astype(int)
    return model._check_frame(a), statuses


def _effective_n(v: np.ndarray) -> float:
    v = np.asarray(v, float)
    total = float(v.sum())
    if total <= 0:
        return 0.0
    p = v / total
    return float(1.0 / np.sum(p * p))


def region_source_descriptives(a: pd.DataFrame) -> dict[str, dict]:
    regions = {}
    for r, g in a.groupby("region", sort=True):
        y = g.n_occ.to_numpy(float)
        q = g.effort.to_numpy(float)
        regions[r] = {
            "n_available_cells": len(g),
            "n_recorded_cells": int((y > 0).sum()),
            "fraction_cells_with_any_record": float((y > 0).mean()),
            "n_focal_records": int(y.sum()),
            "n_target_group_records": int(q.sum()),
            "effective_focal_record_cells": _effective_n(y),
            "effective_target_group_record_cells": _effective_n(q),
            "temperature_min": float(g.temperature.min()),
            "temperature_max": float(g.temperature.max()),
            "precipitation_min": float(g.moisture.min()),
            "precipitation_max": float(g.moisture.max()),
        }
    return regions


def _heldout_scores(a: pd.DataFrame, effort_exponent: float, ridge: float) -> dict:
    """Held-out conditional multinomial scoring, including effort-only baseline."""
    if effort_exponent < 0 or not np.isfinite(effort_exponent):
        raise ValueError("Invalid diagnostic effort exponent")
    df = a.copy()
    df["effort"] = df.effort.astype(float).pow(effort_exponent)
    x = model._features(df)
    folds = model._spatial_folds(df, min_test_records=5)
    out = {}
    for region, part in df.groupby("region", sort=True):
        idx = part.index.to_numpy()
        xx = x[idx]
        yy = part.n_occ.to_numpy(float)
        qq = part.effort.to_numpy(float)
        classes = folds[region]
        fold_results = []
        score_sum = {**{k: 0.0 for k in model.FEATURE_SETS}, "effort_only": 0.0}
        ntest_sum = 0.0
        for held in (0, 1):
            train, test = classes != held, classes == held
            ntest = float(yy[test].sum())
            ntest_sum += ntest
            scores = {}
            for name, cols in model.FEATURE_SETS.items():
                beta = model._fit(xx[train], qq[train], yy[train], np.zeros(sum(train)), cols, ridge)
                scores[name] = model._test_logscore(xx[test], qq[test], yy[test], beta, cols)
            log_q = np.log(qq[test])
            scores["effort_only"] = float(yy[test] @ (log_q - logsumexp(log_q)) / ntest)
            for key in score_sum:
                score_sum[key] += ntest * scores[key]
            fold_results.append({"fold": held, "n_test_records": int(ntest),
                                 "n_test_cells": int(test.sum()),
                                 "full_minus_effort_only": scores["full"] - scores["effort_only"],
                                 "temperature_gain": scores["full"] - scores["without_temperature"],
                                 "moisture_gain": scores["full"] - scores["without_moisture"]})
        scores = {k: v / ntest_sum for k, v in score_sum.items()}
        gain_temp = scores["full"] - scores["without_temperature"]
        gain_wet = scores["full"] - scores["without_moisture"]
        gain_full = scores["full"] - scores["effort_only"]
        score_contrast = gain_temp - gain_wet
        candidate_winner = "temperature" if score_contrast > 0 else "moisture" if score_contrast < 0 else "tie"
        # The candidate ranking is UNINTERPRETABLE if either route provides no
        # positive ecological heldout information or full system cannot beat
        # the target-group-effort baseline under the same heldout folds.
        interpretable = gain_full > 0 and max(gain_temp, gain_wet) > 0
        out[region] = {
            "full_mean_heldout_log_score": scores["full"],
            "effort_only_mean_heldout_log_score": scores["effort_only"],
            "full_minus_effort_only": gain_full,
            "temperature_gain_vs_knockout": gain_temp,
            "moisture_gain_vs_knockout": gain_wet,
            "temperature_minus_moisture_gain": score_contrast,
            "rank_only_ignoring_adequacy": candidate_winner,
            "process_inference_status": "blocked_effort_proxy_and_M" if interpretable else "blocked_full_or_knockout_adequacy",
            "ecological_process_claim_allowed": False,
            "spatial_folds": fold_results,
        }
    return out


def audit(data: pd.DataFrame, source_receipt: dict, config: dict, *, taxon: str = "Quercus robur",
          ridge: float = 0.02) -> dict:
    a, statuses = source_checks(data, source_receipt, config, taxon)
    efforts = {}
    for alpha in EFFORT_EXPONENTS:
        reg = _heldout_scores(a, alpha, ridge)
        labels = [v["rank_only_ignoring_adequacy"] for v in reg.values()]
        efforts[str(alpha)] = {
            "assumption": "diagnostic_target_group_record_intensity_power_not_validated_effort",
            "by_region": reg,
            "apparent_rank_reversal_ignoring_adequacy": len(set(labels)) > 1,
            "any_ecological_process_claim_allowed": False,
        }
    return {
        "analysis": "quercus_postsource_effort_sensitivity_v1",
        "status": "POST_SOURCE_EXPLORATORY_NOT_PROSPECTIVE",
        "source_window_statuses": statuses,
        "taxon": taxon,
        "region_sources": region_source_descriptives(a),
        "pairwise_environment_overlap_coarse": model._availability_overlap(a),
        "effort_power_sensitivity": efforts,
        "model": "regionwise_heldout_conditional_multinomial_quadratic_temperature_precipitation",
        "all_effect_sizes_are_diagnostic": True,
        "publication_claim_allowed": False,
        "process_turnover_test_authorized": False,
        "reason": [
            "full_environmental_model_inadequate_under_fixed_effort_proxy",
            "records_do_not_estimate_true_population_abundance",
            "very_high_cell_occupancy_and_low_common_environmental_support",
            "unvalidated_target_group_detection_effort_and_species_accessible_M",
            "small_spatial_holdout_sample_with_two_folds",
            "retrospective_effort_sensitivity_not_independent_confirmation",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-cells", type=Path, required=True)
    ap.add_argument("--source-receipt", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=Path("configs/geographic_turnover_native_windows_v1.json"))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    frame = pd.read_csv(args.source_cells)
    rec = json.loads(args.source_receipt.read_text())
    conf = json.loads(args.config.read_text())
    result = audit(frame, rec, conf)
    result["input_sha256"] = {"source_cells": _sha(args.source_cells),
                              "source_receipt": _sha(args.source_receipt), "config": _sha(args.config)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    print("source_status=post_source_exploratory, taxa=1, regions=2, process_claim_allowed=False")
    for alpha, v in result["effort_power_sensitivity"].items():
        print("effort_exponent", alpha, "apparent_rank_reversal=", v["apparent_rank_reversal_ignoring_adequacy"])


if __name__ == "__main__":
    main()
