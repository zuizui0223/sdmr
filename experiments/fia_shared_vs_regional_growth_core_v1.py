"""Frozen-design, postsource exploratory VA/WI growth-response model comparison.

Input growth rows are selected live->live trees, never raw source opportunity.
Heldout-county support comes exclusively from PRIOR source-only records in
training counties. A noncausal test of common vs region-modified associations,
NOT physiology, adaptation, process attribution or prospective replication.
"""
from __future__ import annotations
import hashlib
import math
from collections import defaultdict
import numpy as np
import pandas as pd

import fia_VA_WI_county_source_folds_v1 as source_preflight
import fia_joint_support_gate_v1 as gate

SPECIES = source_preflight.PRIMARY_SPECIES
STATES = ("VA", "WI")
FOLDS = 5
MIN_TEST_TREE_PAIRS_PER_STATE = 100
MIN_TRAIN_TREE_PAIRS_PER_STATE = 500
MIN_TRAIN_COUNTIES = 20
MIN_TEST_COUNTIES = 3
MIN_TEST_PLOTS = 20
BOOTSTRAP_ITERATIONS = 399
MIN_WORTHWHILE_RELATIVE_RMSE_GAIN_PERCENT = 1.0
MODELS = ("baseline", "stationary_climate", "state_varying_climate")
CLAIM_CEILING = "noncausal_county_heldout_conditional_survivor_growth_exploratory_only"


def design(frame: pd.DataFrame, kind: str) -> np.ndarray:
    if kind not in MODELS:
        raise ValueError("unknown frozen growth model")
    n = len(frame)
    wi = (frame.state.to_numpy() == "WI").astype(float)
    f = [np.ones(n), wi]
    for key in ("year_centered", "interval", "ln_dia10", "age60", "ba100"):
        f.append(frame[key].to_numpy(float))
    if kind != "baseline":
        t, p, ba = (frame[k].to_numpy(float) for k in ("tanom3", "panom200", "ba100"))
        f.extend((t,p,ba*t,ba*p))
        if kind == "state_varying_climate":
            f.extend((wi*t,wi*p,wi*ba*t,wi*ba*p))
    return np.column_stack(f)


def fit_county_equal_region_equal(x: np.ndarray, y: np.ndarray,
                                  train: pd.DataFrame) -> tuple[np.ndarray,int]:
    """Within each region each county contributes equal total fit weight."""
    if not len(x) or len(y) != len(train):
        raise ValueError("empty or mismatched model matrix")
    counts = train.groupby(["state","county"],sort=False)["county"].transform("size").to_numpy(float)
    per_region = train.groupby("state")["county"].transform("nunique").to_numpy(float)
    if np.any(counts <= 0) or np.any(per_region <= 0):
        raise ValueError("invalid county design weights")
    w = np.sqrt(1.0/(2.0*counts*per_region))
    beta, residuals, rank, singular = np.linalg.lstsq(x*w[:,None], y*w,rcond=None)
    if rank != x.shape[1] or not np.all(np.isfinite(beta)):
        raise ValueError("weighted model rank deficient or nonfinite")
    return beta,rank


def split_source_cells(source: list[dict], config: dict, sp: str, fold: int) -> set:
    """Every shared cell selected from VA & WI TRAINING ONLY."""
    if sp not in config["species_codes"] or fold not in range(FOLDS):
        raise ValueError("undeclared source split")
    by_region = {}
    for state in STATES:
        train = [r for r in source if r["species_code"] == sp and r["state"] == state
                 and source_preflight.county_fold(r["county_fips"]) != fold]
        by_region[state] = source_preflight.qualifying_cells(train,config)
    return by_region["VA"] & by_region["WI"]


def attach_source_to_growth(growth: pd.DataFrame, source: list[dict]) -> pd.DataFrame:
    """Map survivor responses to PREVIOUS visit species/plot source eligibility."""
    if growth.empty:
        return growth.copy()
    src={}
    for r in source:
        key=(r["species_code"],r["state"],r["interval_id"])
        if key in src:
            raise ValueError("duplicate source taxon-state-interval identity")
        src[key]=r
    rows=[]
    chain_hashes=[]
    for i, r in enumerate(growth.itertuples(index=False)):
        key=(str(r.sp), str(r.state), str(r.plot))
        s=src.get(key)
        if s is None:
            raise ValueError("growth response has no prior-visit species source")
        if r.county != s["county_fips"]:
            raise ValueError("growth county differs from source-only county")
        if not (abs(r.tanom3*3 - s["temperature_anomaly_c"]) < 1e-5 and
                abs(r.panom200*200 - s["precipitation_anomaly_mm"]) < 1e-4):
            raise ValueError("NOAA source and growth feature mismatch")
        chain_hashes.append(hashlib.sha256(s["plot_chain_id"].encode()).hexdigest())
        rows.append(source_preflight.source_cell(s, {
            "temperature_bin_c": 1, "precipitation_bin_mm": 100,
            "period_origin_year": 1990, "period_bin_years": 5
        }))
    new=growth.copy()
    new["source_cell"]=rows
    new["plot_chain_sha256"]=chain_hashes
    new["county_fold"]=new["county"].map(source_preflight.county_fold)
    return new


def county_mse(y: np.ndarray, yhats: dict[str,np.ndarray], test: pd.DataFrame) -> list[dict]:
    cells=defaultdict(lambda: {m: [] for m in MODELS})
    nobs=defaultdict(int)
    for row, target, *predicted in zip(
        test.itertuples(index=False), y, *(yhats[m] for m in MODELS), strict=True
    ):
        key=(str(row.state),str(row.county))
        nobs[key]+=1
        for model,pred in zip(MODELS,predicted,strict=True):
            cells[key][model].append(float((target-pred)**2))
    out=[]
    for (state,county), losses in sorted(cells.items()):
        out.append({"state":state,"county_fips":county,"n_test_growth_pairs":nobs[(state,county)],
                    **{m+"_mse":float(np.mean(v)) for m,v in losses.items()}})
    return out


def rmse_county_equal_state_equal(counties: list[dict], model: str) -> float:
    val=[]
    for state in STATES:
        values=[r[model+"_mse"] for r in counties if r["state"]==state]
        if not values:
            raise ValueError("missing state in heldout county-level score")
        val.append(np.mean(values))
    return math.sqrt(float(np.mean(val)))


def delta_percent(shared: float, alternative: float) -> float:
    return 100*(shared-alternative)/shared if shared>0 else float("nan")


def summarize_county_risk(counties: list[dict], species_code: str) -> dict:
    scores={m:rmse_county_equal_state_equal(counties,m) for m in MODELS}
    gain_shared=delta_percent(scores["baseline"],scores["stationary_climate"])
    gain_region=delta_percent(scores["stationary_climate"],scores["state_varying_climate"])
    if not all(math.isfinite(x) for x in [*scores.values(),gain_shared,gain_region]):
        raise ValueError("nonfinite completed county-level score")
    rng=np.random.default_rng(20261116+int(species_code))
    draws=[]
    by_state={s:[r for r in counties if r["state"]==s] for s in STATES}
    for _ in range(BOOTSTRAP_ITERATIONS):
        bootstrap=[]
        for state in STATES:
            available=by_state[state]
            indices=rng.integers(0,len(available),size=len(available))
            bootstrap.extend(available[i] for i in indices)
        a=rmse_county_equal_state_equal(bootstrap,"stationary_climate")
        b=rmse_county_equal_state_equal(bootstrap,"state_varying_climate")
        draws.append(delta_percent(a,b))
    ci=[float(x) for x in np.quantile(draws,[.025,.975])]
    return {"rmse_by_model_equal_state_equal_county":scores,
            "shared_climate_vs_baseline_rmse_gain_percent":gain_shared,
            "state_varying_vs_shared_rmse_gain_percent":gain_region,
            "bootstrap_county_pairing_refits_models":False,
            "state_stratified_county_resampling_iterations":BOOTSTRAP_ITERATIONS,
            "state_varying_gain_county_bootstrap_95pct_interval":ci,
            "meets_development_only_practical_threshold":
                (gain_shared >= MIN_WORTHWHILE_RELATIVE_RMSE_GAIN_PERCENT and gain_region >= MIN_WORTHWHILE_RELATIVE_RMSE_GAIN_PERCENT and ci[0]>0),
            "no_adaptive_model_selection_after_sealed_fold":True}


def evaluate(growth: pd.DataFrame, source: list[dict], cfg: dict) -> dict:
    gate.verify_config(cfg)
    if set(growth.state.unique())-set(STATES):
        raise ValueError("RI growth or undeclared state must not enter VA/WI comparison")
    source_gate=source_preflight.evaluate(source,cfg)
    by_fold={(r["species_code"],r["fixed_county_fold"]):r for r in source_gate["folds"]}
    annotated=attach_source_to_growth(growth,source)
    out=[]
    for sp in cfg["species_codes"]:
        if sp not in SPECIES:
            out.append({"species_code":sp,"status":"secondary_not_modelled_primary_five_fixed",
                        "n_available_folds":0,"not_a_zero_effect":True})
            continue
        part=annotated.loc[annotated.sp==sp]
        county_results=[]
        fold_results=[]
        for fold in range(FOLDS):
            before=by_fold[(sp,fold)]
            if before["status"]!="county_source_ready_for_response_design":
                fold_results.append({"fold":fold,"status":"source_not_evaluable",
                                     "source_reasons":before["reasons"]})
                continue
            allowed=split_source_cells(source,cfg,sp,fold)
            source_gated=part.loc[part.source_cell.map(lambda x:x in allowed)]
            train=source_gated.loc[source_gated.county_fold!=fold]
            test=source_gated.loc[source_gated.county_fold==fold]
            reasons=[]
            for state in STATES:
                tr=train[train.state==state]
                te=test[test.state==state]
                if len(tr)<MIN_TRAIN_TREE_PAIRS_PER_STATE or tr.county.nunique()<MIN_TRAIN_COUNTIES:
                    reasons.append(state+":insufficient_train_survivor_growth")
                if (len(te)<MIN_TEST_TREE_PAIRS_PER_STATE or te.county.nunique()<MIN_TEST_COUNTIES or
                    te["plot_chain_sha256"].nunique()<MIN_TEST_PLOTS):
                    reasons.append(state+":insufficient_heldout_survivor_growth")
                if set(tr.county)&set(te.county):
                    raise ValueError("outcome fold county leakage")
            if reasons:
                fold_results.append({"fold":fold,"status":"response_not_evaluable","reasons":reasons,
                                     "n_train_pairs":len(train),"n_test_pairs":len(test)})
                continue
            matrices={m:(design(train,m),design(test,m)) for m in MODELS}
            yhats={}
            try:
                for m in MODELS:
                    beta,_=fit_county_equal_region_equal(matrices[m][0],
                           train.growth.to_numpy(float),train)
                    yhats[m]=matrices[m][1]@beta
            except ValueError as e:
                fold_results.append({"fold":fold,"status":"response_model_nonestimable",
                                     "reason":str(e)})
                continue
            errs=county_mse(test.growth.to_numpy(float),yhats,test)
            county_results.extend(errs)
            fold_results.append({"fold":fold,"status":"country_holdout_fitted",
                                 "n_train_pairs":len(train),"n_test_pairs":len(test),
                                 "n_test_counties_VA":test.loc[test.state=="VA","county"].nunique(),
                                 "n_test_counties_WI":test.loc[test.state=="WI","county"].nunique()})
        result={"species_code":sp,"n_available_folds":sum(x["status"]=="country_holdout_fitted" for x in fold_results),
                "folds":fold_results}
        if result["n_available_folds"]==FOLDS:
            if len({x["county_fips"] for x in county_results})!=len(county_results):
                raise ValueError("one county appeared in more than one heldout fold")
            result.update({"status":"exploratory_five_fold_county_holdout_completed",
                           "n_heldout_counties":len(county_results),
                           **summarize_county_risk(county_results,sp)})
        else:
            result.update({"status":"full_denominator_not_evaluable_no_success_claim",
                           "no_success_claim_from_subset":True})
        out.append(result)
    return {"program":"fia_VA_WI_shared_vs_regional_conditional_growth_v1",
            "fit_states":list(STATES),"external_RI_growth_opened":False,
            "source_spatial_gate":source_gate["program"],
            "n_declared_species":len(cfg["species_codes"]),
            "primary_five_taxa":list(SPECIES),
            "n_primary_complete":sum(x.get("status")=="exploratory_five_fold_county_holdout_completed" for x in out),
            "species":out,
            "folds_and_model_list_frozen":list(MODELS),
            "min_worthwhile_gain_percent":MIN_WORTHWHILE_RELATIVE_RMSE_GAIN_PERCENT,
            "endpoint":"measured_log_diameter_growth_per_year_given_linked_live_live",
            "does_not_test_survival_or_population_mortality":True,
            "not_independent_of_prior_FIA_v4_tree_cohort_if_data_overlap":True,
            "source_version_does_not_establish_independent_individuals":True,
            "biological_promotion_authorized":False,
            "claim_ceiling":CLAIM_CEILING}
