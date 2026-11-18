"""Archived county-mean versus within-county basal-area predictor information.

Post-outcome exploratory diagnostic on the EXACT prior first-open VA/WI growth
input. No new TREE outcome or source acquisition; no causal competition claim.
Five species, five county folds, source-only environmental support, equal
counties within each state, equal states, all frozen from the first opening.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import fia_density_vs_county_climate_replay_v1 as prior

PROGRAM = "fia_archived_within_county_basal_area_information_v1"
MODES = ("without_density", "original_basal_area", "county_mean_basal_area",
         "within_county_basal_area", "between_and_within")
BOOTSTRAP = 999
SPECIES = prior.PRIMARY
STATES = prior.STATES


def add_predictors(growth: pd.DataFrame) -> pd.DataFrame:
    """County mean weights DISTINCT plot-chain means, never number of trees.

    This mean is transductively computed from the already selected, eventually
    surviving response cohort. It uses no response *values*, but is not an
    available unbiased prospective county baseline. Interpretation is limited.
    """
    keys = ["sp", "state", "county"]
    chain = ["sp", "state", "county", "plot_chain_sha256"]
    if growth.empty or growth[chain].isna().any().any():
        raise ValueError("missing source-identified plot-chain predictor units")
    means = (growth.groupby(chain, sort=False, as_index=False)["ba100"]
             .mean().rename(columns={"ba100": "plot_chain_mean_BA"}))
    county = (means.groupby(keys, sort=False, as_index=False)["plot_chain_mean_BA"]
              .mean().rename(columns={"plot_chain_mean_BA": "county_mean_BA"}))
    out = growth.merge(county, on=keys, how="left", validate="many_to_one")
    if len(out) != len(growth) or out["county_mean_BA"].isna().any():
        raise ValueError("predictor county mean join changed the fixed response cohort")
    out["within_county_BA"] = out.ba100 - out.county_mean_BA
    return out


def design(frame: pd.DataFrame, mode: str) -> np.ndarray:
    if mode not in MODES:
        raise ValueError("unknown fixed county-within predictor model")
    if mode == "without_density":
        return prior.design(frame, "without_density")
    if mode == "original_basal_area":
        return prior.design(frame, "baseline")
    bare = prior.design(frame, "without_density")
    more = {
        "county_mean_basal_area": ["county_mean_BA"],
        "within_county_basal_area": ["within_county_BA"],
        "between_and_within": ["county_mean_BA", "within_county_BA"],
    }[mode]
    return np.column_stack([bare] + [frame[k].to_numpy(float) for k in more])


def fit(train: pd.DataFrame, mode: str) -> np.ndarray:
    X = design(train, mode)
    y = train.growth.to_numpy(float)
    n = train.groupby(["state", "county"], sort=False)["county"].transform("size").to_numpy(float)
    c = train.groupby("state", sort=False)["county"].transform("nunique").to_numpy(float)
    if np.any(n <= 0) or np.any(c <= 0):
        raise ValueError("empty state or county in source-selected training data")
    w = np.sqrt(1/(2*n*c))
    coef, _, rank, _ = np.linalg.lstsq(X*w[:,None], y*w, rcond=None)
    if rank != X.shape[1] or not np.all(np.isfinite(coef)):
        raise ValueError("rank-deficient fixed county-decomposition model")
    return coef


def county_heldout_ledger(growth: pd.DataFrame, source: pd.DataFrame) -> list[dict]:
    ledger = []
    if set(growth.sp) != set(SPECIES) or set(growth.state) != set(STATES):
        raise ValueError("fixed five-taxon two-state response denominator changed")
    for sp in SPECIES:
        sg = growth.loc[growth.sp == sp]
        ss = source.loc[source.species_code == sp]
        for fold in range(prior.FOLDS):
            available = []
            for state in STATES:
                train_source = ss[(ss.state == state) & (ss.fold != fold)]
                available.append(prior.training_cells(train_source))
            common = available[0] & available[1]
            if len(common) < 2:
                raise ValueError("frozen out-of-county environmental support disappeared")
            panel = sg.loc[sg.cell.isin(common)]
            train = panel.loc[panel.fold != fold]
            test = panel.loc[panel.fold == fold]
            if not len(train) or not len(test) or set(train.county) & set(test.county):
                raise ValueError("empty fold or county leakage")
            predictions = {mode: design(test, mode) @ fit(train, mode) for mode in MODES}
            for state, county in test[["state", "county"]].drop_duplicates().itertuples(index=False, name=None):
                mask = ((test.state == state) & (test.county == county)).to_numpy()
                target = test.growth.to_numpy(float)[mask]
                row = {"species_code": sp, "state": state, "county_fips": county,
                       "fold": fold, "n_test_growth_pairs": len(target)}
                for mode in MODES:
                    row[mode + "_mse"] = float(np.mean((target - predictions[mode][mask])**2))
                ledger.append(row)
    return ledger


def score(ledger: list[dict], mode: str) -> float:
    values = []
    for state in STATES:
        items = [row[mode+"_mse"] for row in ledger if row["state"] == state]
        if not items:
            raise ValueError("missing state in county prediction score")
        values.append(float(np.mean(items)))
    return math.sqrt(float(np.mean(values)))


def gain(before: float, after: float) -> float:
    if before <= 0 or not math.isfinite(before + after):
        raise ValueError("invalid county-mean RMSE")
    return 100 * (before-after) / before


def plot_level_BA_partition(growth: pd.DataFrame) -> dict:
    # Variance across unique chains, rather than variance inflated by trees.
    plot_mean = (growth.groupby(["state", "county", "plot_chain_sha256"], sort=False)
                 .ba100.mean().reset_index(name="plot_ba100"))
    county_mean = plot_mean.groupby(["state", "county"]).plot_ba100.transform("mean")
    total = float(plot_mean.plot_ba100.var(ddof=0))
    between = float(county_mean.var(ddof=0))
    within = float((plot_mean.plot_ba100 - county_mean).var(ddof=0))
    if total <= 0 or abs((between + within) - total) > max(1e-10, total*1e-8):
        raise ValueError("county variation decomposition did not close")
    return {"n_distinct_plot_chains": len(plot_mean),
            "n_counties": int(plot_mean.groupby(["state", "county"]).ngroups),
            "between_county_variance_fraction": between/total,
            "within_county_variance_fraction": within/total,
            "between_and_within_variance_sum_verified": True}


def summarize_species(ledger: list[dict], sp: str, growth: pd.DataFrame,
                      original: dict) -> dict:
    rows = [r for r in ledger if r["species_code"] == sp]
    if len({r["county_fips"] for r in rows}) != len(rows):
        raise ValueError("repeated heldout county; all folds must be source-disjoint")
    scores = {mode: score(rows, mode) for mode in MODES}
    original_record = next(x for x in original["species"] if x["species_code"] == sp)
    original_baseline = original_record["rmse_by_model_equal_state_equal_county"]["baseline"]
    if original_record["status"] != "exploratory_five_fold_county_holdout_completed":
        raise ValueError("historical primary taxon was not fitted")
    if abs(scores["original_basal_area"] - original_baseline) > 1e-10:
        raise ValueError("original heldout growth endpoint not independently reproduced")
    contrasts = {
        "original_single_BA_vs_no_BA": ("without_density", "original_basal_area"),
        "county_mean_only_vs_no_BA": ("without_density", "county_mean_basal_area"),
        "within_county_only_vs_no_BA": ("without_density", "within_county_basal_area"),
        "within_county_increment_conditional_on_county_mean": ("county_mean_basal_area", "between_and_within"),
        "county_mean_increment_conditional_on_within": ("within_county_basal_area", "between_and_within"),
        "separate_slopes_vs_original_single_BA": ("original_basal_area", "between_and_within"),
    }
    effects = {k: gain(scores[a], scores[b]) for k,(a,b) in contrasts.items()}
    rng = np.random.default_rng(20261117 + int(sp))
    by_state = {state: [r for r in rows if r["state"] == state] for state in STATES}
    keys = ("original_single_BA_vs_no_BA","county_mean_only_vs_no_BA",
            "within_county_increment_conditional_on_county_mean",
            "separate_slopes_vs_original_single_BA")
    boot = {key: [] for key in keys}
    for _ in range(BOOTSTRAP):
        subset = []
        for state in STATES:
            data = by_state[state]
            indices = rng.integers(0,len(data),size=len(data))
            subset.extend(data[int(i)] for i in indices)
        errors = {mode: score(subset, mode) for mode in MODES}
        for key in keys:
            a,b = contrasts[key]
            boot[key].append(gain(errors[a], errors[b]))
    confidence = {k: [float(z) for z in np.quantile(v,[.025,.975])] for k,v in boot.items()}
    effects_by_state = {}
    for state, rows_by_state in by_state.items():
        mse = {mode: math.sqrt(float(np.mean([r[mode+"_mse"] for r in rows_by_state]))) for mode in MODES}
        effects_by_state[state] = {
            "within_county_increment_conditional_on_county_mean_percent":
                gain(mse["county_mean_basal_area"], mse["between_and_within"]),
            "county_mean_only_vs_no_BA_percent":
                gain(mse["without_density"], mse["county_mean_basal_area"]),
            "n_scored_counties": len(rows_by_state)}
    return {"species_code": sp, "n_scored_counties": len(rows),
            "original_baseline_RMSE_exactly_reproduced": True,
            "rmse_county_equal_state_equal": scores,
            "relative_rmse_gains_percent": effects,
            "county_postfit_bootstrap_95pct": confidence,
            "county_postfit_bootstrap_draws": BOOTSTRAP,
            "state_specific_descriptive_gains": effects_by_state,
            "plot_level_BA_variation": plot_level_BA_partition(growth),
            "county_mean_calculated_from_eventually_surviving_tree_cohort": True,
            "new_models_frozen_after_outcome_opening": True,
            "not_independent_biological_confirmation": True}


def run(source_dir: Path) -> tuple[dict,list[dict]]:
    growth, source, original = prior.prepare_inputs(source_dir)
    joined, source = prior.source_and_growth_cells(growth, source)
    observed = add_predictors(joined)
    ledger = county_heldout_ledger(observed,source)
    results = [summarize_species(ledger,sp,observed.loc[observed.sp==sp],original)
               for sp in SPECIES]
    return ({
        "program": PROGRAM,
        "first_open_run": prior.SOURCE_RUN,
        "first_open_artifact": prior.SOURCE_ARTIFACT,
        "first_open_archive_sha256": prior.ZIP_SHA256,
        "growth_input_sha256": prior.INPUT_SHA256,
        "source_input_sha256": prior.SOURCE_SHA256,
        "original_response_sha256": prior.RESULT_SHA256,
        "n_conditional_growth_rows": len(joined),
        "n_source_only_rows": len(source),
        "n_primary_species": len(SPECIES),
        "n_scored_counties": len(ledger),
        "n_species_with_positive_within_county_increment":
            sum(x["relative_rmse_gains_percent"]["within_county_increment_conditional_on_county_mean"]>0 for x in results),
        "n_species_with_postfit_95pct_interval_above_zero":
            sum(x["county_postfit_bootstrap_95pct"]["within_county_increment_conditional_on_county_mean"][0]>0 for x in results),
        "all_five_original_single_BA_scores_reproduced": True,
        "new_model_after_outcome_look": True,
        "posterior_selection_mean_from_conditional_survivor_cohort": True,
        "no_raw_FIA_retrieval_or_new_biological_outcome_opening": True,
        "not_an_estimate_of_competition_causality_or_niche_constraint": True,
        "postfit_bootstrap_not_model_refitting": True,
        "biological_promotion_authorized": False,
        "species": results,
    }, ledger)


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    args=p.parse_args()
    result,ledger=run(args.source_dir)
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/"within_county_BA_predictor_audit_v1.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    pd.DataFrame(ledger).to_csv(args.out_dir/"within_county_BA_county_scores_v1.csv",index=False)
    print("Source-frozen within-county BA predictor diagnostic:",
          result["n_species_with_positive_within_county_increment"],"/5;",
          result["n_species_with_postfit_95pct_interval_above_zero"],"postfit positive intervals")


if __name__ == "__main__":
    main()
