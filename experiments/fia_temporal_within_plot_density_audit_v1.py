"""Postoutcome temporal within-plot FIA density audit, archive-only.

Question: after earlier plot-chain growth and covariate differences are known,
does the change in prior stand basal area predict later plot-averaged
conditional-survivor growth in county-heldout geographic folds?

Only source-qualified training T-P-time bins from PREVIOUS source-only records
are used to select both period records. No new FIA/NOAA downloads or tree
response access. This is NOT a panel of the same individually linked trees.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from fia_density_vs_county_climate_replay_v1 import (
    SOURCE_RUN, SOURCE_ARTIFACT, ZIP_SHA256, INPUT_SHA256,
    SOURCE_SHA256, RESULT_SHA256, PRIMARY, STATES, FOLDS,
    prepare_inputs, county_fold,
)

PROGRAM = "fia_archived_temporal_within_plot_BA_next_growth_v1"
BOOTSTRAP_DRAWS = 999
MIN_EVENT_SURVIVOR_GROWTH_ROWS = 3
MIN_PAIR_GAP_YEARS = 4.0
MAX_PAIR_GAP_YEARS = 15.0
MIN_TRAIN_COUNTIES_PER_STATE = 10
MIN_TEST_COUNTIES_PER_STATE = 3
MIN_TRAIN_PLOT_PAIRS_PER_STATE = 40
MIN_TEST_PLOT_PAIRS_PER_STATE = 5
SOURCE_MIN_COUNTIES_PER_CELL = 2
SOURCE_MIN_PLOTS_PER_CELL = 5
SOURCE_MIN_SHARED_CELLS = 2
EXPECTED_ALL_SOURCE_TAXA = ("68","129","261","316","318","371","531","541","743","762","802","833","837")
EXPECTED_CANDIDATE_PAIRS = {"129":519,"316":2448,"802":767,"833":741,"837":269}
BASELINE_FEATURES = ("d_ln_dia","d_age","d_interval","d_temp","d_rain",
                     "elapsed_decades","first_year_centered","ba_0","growth_0")
OUTCOMES = ("lagged_baseline", "lagged_plus_density_change")


def source_cells(source: pd.DataFrame) -> pd.DataFrame:
    x = source.copy()
    if set(x.state.unique()) != set(STATES) or set(x.species_code.unique()) != set(EXPECTED_ALL_SOURCE_TAXA):
        raise ValueError("source identity missing fixed states or primary species")
    x["source_cell"] = list(zip(
        np.floor(x.temperature_anomaly_c.to_numpy(float)).astype(int),
        np.floor(x.precipitation_anomaly_mm.to_numpy(float)/100).astype(int),
        np.floor((x.interval_end_year.to_numpy(float)-1990)/5).astype(int),
    ))
    x["fold"] = x.county_fips.map(county_fold)
    return x


def aggregate_events(growth: pd.DataFrame, source: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    """Exactly one species x plot chain x current source-PLOT interval event.

    No tree/individual identity is available to ensure the same individuals
    recur. Exclude events where BA changes across sampled source conditions.
    """
    g = ["sp","state","county","plot_chain_sha256","plot"]
    event = (growth.groupby(g,sort=False).agg(
        n_tree_growth_rows=("growth","size"),
        distinct_BA_values=("ba100","nunique"),
        growth=("growth","mean"),
        ba=("ba100","mean"),
        yr=("year_centered","first"),
        yr_nunique=("year_centered","nunique"),
        ln_dia=("ln_dia10","mean"),
        age=("age60","mean"),
        interval=("interval","mean"),
        temp=("tanom3","first"), rain=("panom200","first")
    ).reset_index())
    source_keys = source[["species_code","state","county_fips","interval_id",
                          "plot_chain_id","interval_end_year","source_cell",
                          "temperature_anomaly_c","precipitation_anomaly_mm"]].rename(
        columns={"species_code":"sp","county_fips":"src_county",
                 "interval_id":"plot"})
    if source_keys.duplicated(["sp","state","plot"]).any():
        raise ValueError("source-only duplicate taxon-current PLOT event")
    event = event.merge(source_keys,on=["sp","state","plot"],how="left",
                        validate="one_to_one")
    if event.src_county.isna().any() or event["source_cell"].isna().any():
        raise ValueError("growth event missing frozen prior-visit taxon source")
    if not (event.county == event.src_county).all():
        raise ValueError("county drift between growth and source event")
    source_chain_hash = event.plot_chain_id.map(
        lambda z: hashlib.sha256(str(z).encode()).hexdigest())
    if not (source_chain_hash == event.plot_chain_sha256).all():
        raise ValueError("source original chain identity differs from growth chain SHA")
    if not (abs(event.yr*20+2005-event.interval_end_year) < 1e-7).all():
        raise ValueError("measurement-year mismatch")
    if ((abs(event.temp*3 - event.temperature_anomaly_c)>1e-5) |
        (abs(event.rain*200-event.precipitation_anomaly_mm)>1e-4)).any():
        raise ValueError("NOAA exposure differs between biological and source-only record")
    if (event.yr_nunique != 1).any():
        raise ValueError("multiple dates in one biological PLOT event")
    candidate = event[(event.n_tree_growth_rows >= MIN_EVENT_SURVIVOR_GROWTH_ROWS) &
                      (event.distinct_BA_values == 1)].copy()
    candidate = candidate.sort_values(
        ["sp","state","county","plot_chain_sha256","yr","plot"])
    candidate["observed_event_index"] = candidate.groupby(
        ["sp","state","county","plot_chain_sha256"],sort=False).cumcount()
    a = candidate[candidate.observed_event_index == 0].copy()
    b = candidate[candidate.observed_event_index == 1].copy()
    keys = ["sp","state","county","plot_chain_sha256"]
    pair = a.merge(b,on=keys,how="inner",suffixes=("_0","_1"),
                   validate="one_to_one")
    pair["elapsed_years"] = (pair.yr_1 - pair.yr_0)*20
    pair = pair.loc[pair.elapsed_years.between(
        MIN_PAIR_GAP_YEARS,MAX_PAIR_GAP_YEARS)].copy()
    pair["elapsed_decades"]=pair.elapsed_years/10
    pair["first_year_centered"]=pair.yr_0
    for col in ("growth","ba","ln_dia","age","interval","temp","rain"):
        pair["d_"+col] = pair[col+"_1"]-pair[col+"_0"]
    pair["fold"] = pair.county.map(county_fold)
    observed = {str(sp):int(n) for sp,n in pair.groupby("sp",sort=False).size().items()}
    if observed != EXPECTED_CANDIDATE_PAIRS:
        raise ValueError("complete first-pair candidate denominator changed: "+str(observed))
    if pair.duplicated(keys).any():
        raise ValueError("repeated plot chain in first-pair unit")
    audit = {
        "first_open_growth_rows":len(growth),
        "all_source_matched_plot_events":len(event),
        "events_survivor_rows_ge_three_with_single_BA":len(candidate),
        "unqualified_event_count":len(event)-len(candidate),
        "first_two_eligible_event_candidates":len(pair),
        "first_two_eligible_pairs_by_taxon":dict(sorted(observed.items())),
        "one_temporal_pair_per_plot_chain":True,
        "first_two_observed_eligible_events_not_proven_uninterrupted_censuses":True,
        "same_individual_trees_not_verified":True,
    }
    return pair,audit


def train_support(source: pd.DataFrame, sp: str, fold: int) -> set:
    """Common cells defined before testing by VA/WI TRAINING source-only records."""
    supported=[]
    for state in STATES:
        rows = source.loc[
            (source.species_code==sp)&(source.state==state)&(source.fold!=fold)]
        bins = (rows.groupby("source_cell").agg(
            n_counties=("county_fips","nunique"),
            n_plots=("plot_chain_id","nunique")))
        supported.append(set(bins.index[
            (bins.n_counties>=SOURCE_MIN_COUNTIES_PER_CELL)&
            (bins.n_plots>=SOURCE_MIN_PLOTS_PER_CELL)]))
    return supported[0]&supported[1]


def model_matrix(df: pd.DataFrame, include_density_change: bool) -> np.ndarray:
    cols=[np.ones(len(df)),(df.state=="WI").to_numpy(float)]
    cols.extend(df[name].to_numpy(float) for name in BASELINE_FEATURES)
    if include_density_change:
        cols.append(df.d_ba.to_numpy(float))
    return np.column_stack(cols)


def predict(train: pd.DataFrame, test: pd.DataFrame,
            include_density_change: bool) -> np.ndarray:
    x = model_matrix(train,include_density_change)
    xt = model_matrix(test,include_density_change)
    nrows=train.groupby(["state","county"]).county.transform("size").to_numpy(float)
    ncounty=train.groupby("state").county.transform("nunique").to_numpy(float)
    if np.any(nrows<=0) or np.any(ncounty<=0):
        raise ValueError("missing county or state model weights")
    w=np.sqrt(1/(len(STATES)*nrows*ncounty))
    theta,_,rank,_ = np.linalg.lstsq(
        x*w[:,None],train.growth_1.to_numpy(float)*w,rcond=None)
    if rank!=x.shape[1] or not np.isfinite(theta).all():
        raise ValueError("unestimable fixed linear model under county split")
    return xt@theta


def county_score(counties: list[dict], model: str) -> float:
    scores=[]
    for state in STATES:
        vals=[x[model+"_mse"] for x in counties if x["state"]==state]
        if not vals:
            raise ValueError("missing regional holdout in county score")
        scores.append(float(np.mean(vals)))
    return math.sqrt(float(np.mean(scores)))


def improvement(counties: list[dict]) -> float:
    base=county_score(counties,"lagged_baseline")
    enriched=county_score(counties,"lagged_plus_density_change")
    return 100*(base-enriched)/base if base>0 else float("nan")


def evaluate(pairs: pd.DataFrame, source: pd.DataFrame,
             audit: dict) -> tuple[dict,pd.DataFrame,pd.DataFrame]:
    per_species=[]
    ledger=[]
    kept_pairs=[]
    for sp in PRIMARY:
        rows=pairs[pairs.sp==sp]
        fold_results=[]
        for fold in range(FOLDS):
            common=train_support(source,sp,fold)
            target=rows.loc[rows.source_cell_0.isin(common)&
                            rows.source_cell_1.isin(common)]
            train=target.loc[target.fold!=fold]
            test=target.loc[target.fold==fold]
            failed=[]
            if len(common)<SOURCE_MIN_SHARED_CELLS:
                failed.append("insufficient_common_T_P_year_source_cells")
            for state in STATES:
                tr=train.loc[train.state==state]
                te=test.loc[test.state==state]
                if tr.county.nunique()<MIN_TRAIN_COUNTIES_PER_STATE or len(tr)<MIN_TRAIN_PLOT_PAIRS_PER_STATE:
                    failed.append(state+":too_few_train_counties_or_eligible_plot_pairs")
                if te.county.nunique()<MIN_TEST_COUNTIES_PER_STATE or len(te)<MIN_TEST_PLOT_PAIRS_PER_STATE:
                    failed.append(state+":too_few_test_counties_or_eligible_plot_pairs")
                if set(tr.county)&set(te.county):
                    raise ValueError("county leaked across training and test")
            record={"fold":fold,"n_train_pairs":len(train),"n_test_pairs":len(test),
                    "n_source_common_train_cells":len(common),
                    "n_test_counties_by_state":{
                        state:int(test.loc[test.state==state,"county"].nunique()) for state in STATES},
                    "status":"evaluated" if not failed else "nonestimable",
                    "reasons":failed}
            fold_results.append(record)
            if failed:
                continue
            base=predict(train,test,False)
            enriched=predict(train,test,True)
            target_growth=test.growth_1.to_numpy(float)
            for (state,county),indices in test.groupby(["state","county"]).indices.items():
                ledger.append({"species_code":sp,"state":state,"county_fips":county,
                               "fold":fold,"n_test_plot_pairs":len(indices),
                               "lagged_baseline_mse":float(np.mean((target_growth[indices]-base[indices])**2)),
                               "lagged_plus_density_change_mse":float(np.mean((target_growth[indices]-enriched[indices])**2))})
            kept_pairs.append(test)
        result={"species_code":sp,"n_candidate_plot_chains":len(rows),
                "n_complete_folds":sum(x["status"]=="evaluated" for x in fold_results),
                "folds":fold_results}
        if result["n_complete_folds"]==FOLDS:
            counties=[x for x in ledger if x["species_code"]==sp]
            if len({x["county_fips"] for x in counties})!=len(counties):
                raise ValueError("one county was in more than one heldout fold")
            gain=improvement(counties)
            rng=np.random.default_rng(20261117+int(sp))
            by_region={s:[x for x in counties if x["state"]==s] for s in STATES}
            bootstrap=[]
            for _ in range(BOOTSTRAP_DRAWS):
                sampled=[]
                for state in STATES:
                    pool=by_region[state]
                    indices=rng.integers(len(pool),size=len(pool))
                    sampled.extend(pool[int(i)] for i in indices)
                bootstrap.append(improvement(sampled))
            b=np.quantile(bootstrap,[.025,.975])
            result.update({"status":"postoutcome_exploratory_complete",
                "n_heldout_scored_counties":len(counties),
                "n_heldout_scored_plot_pairs":int(sum(x["n_test_plot_pairs"] for x in counties)),
                "rmse_next_growth_by_model_equal_state_county":{
                    model:county_score(counties,model) for model in OUTCOMES},
                "incremental_density_change_relative_RMSE_gain_percent":gain,
                "county_postfit_bootstrap95_percent":[float(b[0]),float(b[1])],
                "county_postfit_bootstrap_iterations":BOOTSTRAP_DRAWS,
                "bootstrap_refits_models":False,
                "within_plot_density_change_temporally_precedes_later_growth_window":True,
                "earlier_growth_0_adjusted":True})
        else:
            result.update({"status":"full_five_fold_result_not_available",
                           "no_success_claim_from_partial_folds":True})
        per_species.append(result)
    return ({
        "program":PROGRAM,
        "prior_source_run":SOURCE_RUN,
        "prior_source_artifact":SOURCE_ARTIFACT,
        "prior_source_ZIP_SHA256":ZIP_SHA256,
        "prior_growth_input_SHA256":INPUT_SHA256,
        "prior_source_only_input_SHA256":SOURCE_SHA256,
        "prior_original_response_SHA256":RESULT_SHA256,
        "original_source_rows":int(len(source)),
        "original_growth_rows":audit["first_open_growth_rows"],
        "n_declared_prior_taxa":len(EXPECTED_ALL_SOURCE_TAXA),
        "fixed_source_taxa":list(EXPECTED_ALL_SOURCE_TAXA),
        "secondary_taxa_not_modelled":[sp for sp in EXPECTED_ALL_SOURCE_TAXA if sp not in PRIMARY],
        "primary_taxa":list(PRIMARY),
        "n_primary_taxa":len(PRIMARY),
        "source_selection_uses_training_counties_only":True,
        "first_pair_selection":"first_two_events_with_at_least_3_surviving_growth_records_and_unique_BA_each_with_4_to_15_year_gap",
        "county_fold":"first4bytes_sha256_FIPS_mod_5",
        "comparison":"predict_later_plot_event_survivor_growth_given_earlier_growth_and_baseline_BA",
        "n_candidate_temporal_pairs":audit["first_two_eligible_event_candidates"],
        "n_source_supported_heldout_pairs":int(sum(x["n_test_plot_pairs"] for x in ledger)),
        "n_primary_complete":sum(r["status"]=="postoutcome_exploratory_complete" for r in per_species),
        "n_positive_density_change_gains":sum(r.get("incremental_density_change_relative_RMSE_gain_percent",0)>0 for r in per_species),
        "n_postfit_county95_intervals_lower_positive":sum(r.get("county_postfit_bootstrap95_percent",[float("-inf")])[0]>0 for r in per_species),
        "source_and_pair_audit":audit,
        "species":per_species,
        "no_new_RAW_FIA_or_NOAA_network_fetch":True,
        "no_new_response_outcome_opened":True,
        "prior_survivor_cohort_not_independent":True,
        "same_tree_individuals_across_windows_not_verified":True,
        "calendar_and_time_varying_management_confounding_remain":True,
        "post_prior_response_outcome_selection_and_gates_exploratory":True,
        "not_independent_prospective_or_causal_niche_result":True,
        "biological_promotion_authorized":False
    },pd.DataFrame(ledger),pd.concat(kept_pairs,ignore_index=True) if kept_pairs else pairs.iloc[0:0].copy())


def run(source_dir: Path) -> tuple[dict,pd.DataFrame,pd.DataFrame]:
    growth,raw_source,old=prepare_inputs(source_dir)
    if old.get("n_primary_complete")!=5 or len(growth)!=170994 or len(raw_source)!=88145:
        raise ValueError("original previously opened growth/source denominator changed")
    src=source_cells(raw_source)
    pairs,audit=aggregate_events(growth,src)
    result,counties,supported_pairs=evaluate(pairs,src,audit)
    return result,counties,supported_pairs


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",type=Path,required=True)
    parser.add_argument("--out-dir",type=Path,required=True)
    args=parser.parse_args()
    result,ledger,supported=run(args.source_dir)
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/"temporal_within_plot_density_audit_v1.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    ledger.to_csv(args.out_dir/"temporal_within_plot_county_ledger_v1.csv",index=False)
    cols=["sp","state","county","plot_chain_sha256","fold",
          "growth_0","growth_1","ba_0","ba_1","d_ba",
          "source_cell_0","source_cell_1","elapsed_years",
          *BASELINE_FEATURES]
    supported.loc[:,list(dict.fromkeys(cols))].to_csv(
        args.out_dir/"temporal_plot_pair_numeric_inputs_v1.csv",index=False)
    print("temporal plot pairs",result["n_candidate_temporal_pairs"],
          "source-heldout",result["n_source_supported_heldout_pairs"],
          "full species",result["n_primary_complete"],
          "positive density-change gain",result["n_positive_density_change_gains"])


if __name__=="__main__":
    main()
