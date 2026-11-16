"""Archived FIA VA/WI density-versus-climate predictor increment (postoutcome).

Exact frozen first-open source-only and conditional-growth numerical inputs.
Repeat the ORIGINAL five-fold county blocking, environmental eligibility,
county/state fit weights and county/state RMSE score. Additional predictor
knockout (drop basal area) was designed AFTER opening growth: descriptive
predictive audit only, not new confirmatory biological evidence.
No network, no raw FIA ZIP, no re-selection of species, no niche mechanism claim.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

ZIP_SHA256 = "ec8f33c4e179250d6ce4e36d7e4933a48969e0c3e9be6d4b4ae090c0c9c64d24"
INPUT_SHA256 = "ee98608ca4e7582144a886d96c9c908a5a5cd25533e1b74ad2e786b20710db4e"
SOURCE_SHA256 = "cd306e559a663c1ddf65259b2fc5298d426f931c272b4cd1ec15ec17da21e402"
RESULT_SHA256 = "a768b17684ee712e00187fdfd24b3e929139bc1fe4b11e96aed475bb3c03d482"
SOURCE_RUN = 43886130089
SOURCE_ARTIFACT = 14234926861
PRIMARY = ("129", "316", "802", "833", "837")
STATES = ("VA", "WI")
FOLDS = 5
BOOTSTRAP_DRAWS = 1999
MODELS = ("without_density", "baseline", "stationary_climate")
RESPONSE_GRAIN = "linked_live_to_live_log_diameter_change_per_year"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def county_fold(fips: str) -> int:
    if len(fips) != 5 or not fips.isdigit():
        raise ValueError("invalid county FIPS")
    return int.from_bytes(hashlib.sha256(fips.encode()).digest()[:4], "big") % FOLDS


def design(frame: pd.DataFrame, mode: str) -> np.ndarray:
    if mode not in MODELS:
        raise ValueError("unknown fixed predictor family")
    n = len(frame)
    wi = (frame.state == "WI").to_numpy(float)
    x = [np.ones(n), wi] + [frame[k].to_numpy(float)
        for k in ("year_centered", "interval", "ln_dia10", "age60")]
    if mode != "without_density":
        ba = frame.ba100.to_numpy(float)
        x += [ba]
    if mode == "stationary_climate":
        temp = frame.tanom3.to_numpy(float)
        rain = frame.panom200.to_numpy(float)
        x += [temp, rain, ba * temp, ba * rain]
    return np.column_stack(x)


def fit_county_state_balanced(train: pd.DataFrame, mode: str) -> np.ndarray:
    x = design(train, mode)
    counts = train.groupby(["state", "county"])["county"].transform("size").to_numpy(float)
    counties = train.groupby("state")["county"].transform("nunique").to_numpy(float)
    if any(len(train.loc[train.state==st]) == 0 for st in STATES):
        raise ValueError("empty training state")
    w = np.sqrt(1 / (2 * counts * counties))
    coeff, _, rank, _ = np.linalg.lstsq(x * w[:,None],
                                        train.growth.to_numpy(float) * w,
                                        rcond=None)
    if rank != x.shape[1] or not np.all(np.isfinite(coeff)):
        raise ValueError("rank-deficient fitted model")
    return coeff


def training_cells(frame: pd.DataFrame) -> set[tuple[int,int,int]]:
    grid = frame.groupby("cell").agg(
        n_counties=("county_fips", "nunique"),
        n_plots=("plot_chain_id", "nunique"))
    return set(grid.index[(grid.n_counties >= 2) & (grid.n_plots >= 5)])


def prepare_inputs(folder: Path) -> tuple[pd.DataFrame,pd.DataFrame,dict]:
    names={"primary_five_conditional_growth_inputs_v1.csv":INPUT_SHA256,
           "new_source_only_taxon_plot_intervals.csv":SOURCE_SHA256,
           "VA_WI_growth_result_v1.json":RESULT_SHA256}
    for name, digest in names.items():
        if sha(folder/name) != digest:
            raise ValueError("immutable first-open response/source identity mismatch: "+name)
    grow = pd.read_csv(folder/"primary_five_conditional_growth_inputs_v1.csv",
                       dtype={"sp":str,"county":str,"plot":str,"state":str},
                       low_memory=False)
    source = pd.read_csv(folder/"new_source_only_taxon_plot_intervals.csv",
                        dtype={"species_code":str,"state":str,"county_fips":str,
                               "plot_chain_id":str,"interval_id":str},low_memory=False)
    published = json.loads((folder/"VA_WI_growth_result_v1.json").read_text())
    if len(grow) != 170994 or len(source) != 88145 or len(published["species"]) != 13:
        raise ValueError("first-open outcome denominator changed")
    if set(grow.sp) != set(PRIMARY) or set(grow.state) != set(STATES):
        raise ValueError("unexpected fitted taxon or source region")
    if set(source.state) != set(STATES):
        raise ValueError("source-only state panel drift")
    return grow, source, published


def source_and_growth_cells(grow: pd.DataFrame, source: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    src = source.copy()
    src["cell"] = list(zip(np.floor(src.temperature_anomaly_c).astype(int),
                  np.floor(src.precipitation_anomaly_mm / 100).astype(int),
                  np.floor((src.interval_end_year-1990)/5).astype(int)))
    src["fold"] = src.county_fips.map(county_fold)
    y = grow.copy()
    y["fold"] = y.county.map(county_fold)
    src_key = src[["species_code","state","interval_id","cell","county_fips"]].rename(
               columns={"species_code":"sp","interval_id":"plot"})
    y = y.merge(src_key, on=["sp","state","plot"],how="left",validate="many_to_one")
    if y.cell.isna().any() or not (y.county==y.county_fips).all():
        raise ValueError("missing prior-source identity or county mismatch")
    if "growth" not in y or not np.isfinite(y.growth).all():
        raise ValueError("invalid growth response")
    return y, src


def one_county_ledger(grow: pd.DataFrame, src: pd.DataFrame) -> list[dict]:
    rows=[]
    for sp in PRIMARY:
        source_sp = src.loc[src.species_code==sp]
        observed = grow.loc[grow.sp==sp]
        for fold in range(FOLDS):
            allowed=[]
            for st in STATES:
                avail=source_sp[(source_sp.state==st)&(source_sp.fold!=fold)]
                allowed.append(training_cells(avail))
            shared=allowed[0] & allowed[1]
            if len(shared)<2:
                raise ValueError("frozen source eligibility missing common climate cells")
            restricted=observed.loc[observed.cell.isin(shared)]
            train=restricted.loc[restricted.fold!=fold]
            test=restricted.loc[restricted.fold==fold]
            if len(train)==0 or len(test)==0 or set(train.county)&set(test.county):
                raise ValueError("empty fold or county leakage")
            predictions={}
            for mode in MODELS:
                beta=fit_county_state_balanced(train,mode)
                predictions[mode]=design(test,mode)@beta
            for st,county in test[["state","county"]].drop_duplicates().itertuples(index=False,name=None):
                idx=(test.state==st)&(test.county==county)
                target=test.loc[idx,"growth"].to_numpy(float)
                row={"species_code":sp,"state":st,"county_fips":county,
                     "fold":fold,"n_test_growth_rows":len(target)}
                for mode in MODELS:
                    row[mode+"_mse"]=float(np.mean((target-predictions[mode][idx.to_numpy()])**2))
                rows.append(row)
    return rows


def rmse(counties: list[dict], name: str) -> float:
    per=[]
    for region in STATES:
        values=[r[name+"_mse"] for r in counties if r["state"]==region]
        if not values:
            raise ValueError("missing state in county risk")
        per.append(float(np.mean(values)))
    return math.sqrt(float(np.mean(per)))


def gain(before: float, after: float) -> float:
    if before<=0 or not math.isfinite(before+after):
        raise ValueError("invalid RMSE inputs")
    return 100*(before-after)/before


def summarize(species_code: str, counties: list[dict]) -> dict:
    scores={name:rmse(counties,name) for name in MODELS}
    basal_gain=gain(scores["without_density"], scores["baseline"])
    climate_gain=gain(scores["baseline"],scores["stationary_climate"])
    by={st:[r for r in counties if r["state"]==st] for st in STATES}
    rng=np.random.default_rng(20261116+int(species_code))
    sampled=[]
    for _ in range(BOOTSTRAP_DRAWS):
        sample=[]
        for st in STATES:
            rows=by[st]
            ids=rng.integers(0,len(rows),len(rows))
            sample.extend(rows[int(i)] for i in ids)
        sampled.append(gain(rmse(sample,"without_density"),rmse(sample,"baseline")))
    low,high=np.quantile(sampled,[0.025,0.975]).tolist()
    loo=[]
    for st in STATES:
        for i in range(len(by[st])):
            subset=[r for state in STATES for j,r in enumerate(by[state])
                    if not (state==st and i==j)]
            loo.append(gain(rmse(subset,"without_density"),rmse(subset,"baseline")))
    return {
        "species_code":species_code,
        "n_distinct_counties":len(counties),
        "n_by_state":{st:len(by[st]) for st in STATES},
        "rmse":scores,
        "basal_area_incremental_rmse_gain_percent":basal_gain,
        "climate_incremental_rmse_gain_percent":climate_gain,
        "county_bootstrap_postfit_95pct_interval_basal_gain":[float(low),float(high)],
        "leave_one_evaluation_county_out_basal_gain_min_max":[float(min(loo)),float(max(loo))],
        "n_positive_basal_area_counties_by_state":
           {st:sum(row["without_density_mse"]>row["baseline_mse"] for row in by[st])
            for st in STATES},
        "county_bootstrap_uses_no_model_refits":True,
        "posthoc_drop_basal_area_not_preregistered":True,
    }


def run(source_dir: Path) -> tuple[dict,list[dict]]:
    grow,src,original=prepare_inputs(source_dir)
    y,x=source_and_growth_cells(grow,src)
    ledger=one_county_ledger(y,x)
    output=[]
    for sp in PRIMARY:
        group=[z for z in ledger if z["species_code"]==sp]
        result=summarize(sp,group)
        recorded=next(z for z in original["species"] if z["species_code"]==sp)
        if (recorded["status"]!="exploratory_five_fold_county_holdout_completed" or
            recorded["n_heldout_counties"]!=len(group) or
            abs(recorded["shared_climate_vs_baseline_rmse_gain_percent"]-
                result["climate_incremental_rmse_gain_percent"])>1e-8):
            raise ValueError("original climate endpoint does not reproduce exactly")
        output.append(result)
    summary={
        "program":"fia_postoutcome_basal_area_vs_county_climate_predictor_audit_v1",
        "original_first_open_run_id":SOURCE_RUN,
        "original_first_open_artifact_id":SOURCE_ARTIFACT,
        "original_first_open_artifact_zip_sha256":ZIP_SHA256,
        "derived_input_sha256":INPUT_SHA256,
        "source_only_csv_sha256":SOURCE_SHA256,
        "source_rows":len(x),
        "selected_live_live_growth_rows":len(y),
        "five_species_original_climate_endpoints_reproduced_exactly":True,
        "primary_species_fixed_before_this_diagnostic":list(PRIMARY),
        "n_species":len(PRIMARY),
        "bootstrap_county_by_state_postfit_draws":BOOTSTRAP_DRAWS,
        "new_basal_area_knockout_after_response_opening":True,
        "not_independent_biological_replication":True,
        "no_FIA_or_NOAA_network_queries":True,
        "no_survival_or_population_mortality_estimated":True,
        "biological_promotion_authorized":False,
        "no_niche_evolution_or_causal_competition_claim":True,
        "results":output,
    }
    return summary,ledger


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",type=Path,required=True)
    parser.add_argument("--out-dir",type=Path,required=True)
    args=parser.parse_args()
    result,ledger=run(args.source_dir)
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/"density_vs_climate_summary.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    cols=["species_code","state","county_fips","fold","n_test_growth_rows",
          "without_density_mse","baseline_mse","stationary_climate_mse"]
    pd.DataFrame(ledger).loc[:,cols].to_csv(
        args.out_dir/"density_vs_climate_county_ledger.csv",index=False)
    for r in result["results"]:
        print(r["species_code"],"basal gain",round(r["basal_area_incremental_rmse_gain_percent"],4),
              "climate gain",round(r["climate_incremental_rmse_gain_percent"],4),
              "n counties",r["n_distinct_counties"])


if __name__=="__main__":
    main()
