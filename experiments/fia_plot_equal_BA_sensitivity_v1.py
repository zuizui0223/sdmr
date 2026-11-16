"""Plot-chain-equal robustness for postoutcome within-county BALIVE prediction.

Same SHA-pinned VA/WI first-open survivor cohort, same five county-heldout
folds and source-only environmental bins as original. DIFFERENT descriptive
weighting: equal states -> equal counties -> equal distinct plot chains,
then trees within a plot share its weight. Score county MSE by averaging first
over a plot-chain's trees, then over plot chains.
No raw FIA/NOAA fetch, no prospective causal/niche claim.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import fia_density_vs_county_climate_replay_v1 as prior
import fia_county_within_basal_area_audit_v1 as county

PROGRAM = "fia_BA_within_county_equal_plot_sensitivity_v1"
MODES = ("without_density","original_basal_area","county_mean_basal_area","between_and_within")
BOOTSTRAP = 999
SPECIES = prior.PRIMARY
STATES = prior.STATES


def sqrt_plot_weights(train: pd.DataFrame) -> np.ndarray:
    """No observed response VALUE used for weighting; only cohort membership.

    Note cohort membership already conditions on future observed survival.
    """
    keys = ["state","county"]
    n_counties = train.groupby("state")["county"].transform("nunique").to_numpy(float)
    n_plots = train.groupby(keys)["plot_chain_sha256"].transform("nunique").to_numpy(float)
    n_rows = (train.groupby(keys+["plot_chain_sha256"])["plot_chain_sha256"]
              .transform("size").to_numpy(float))
    if not len(train) or np.any(n_counties <= 0) or np.any(n_plots <= 0) or np.any(n_rows <= 0):
        raise ValueError("empty or incomplete plot-chain sampling panel")
    return np.sqrt(1/(len(STATES)*n_counties*n_plots*n_rows))


def fit(train: pd.DataFrame, model: str) -> np.ndarray:
    X = county.design(train,model)
    w = sqrt_plot_weights(train)
    beta,_,rank,_ = np.linalg.lstsq(X*w[:,None],train.growth.to_numpy(float)*w,rcond=None)
    if rank != X.shape[1] or not np.isfinite(beta).all():
        raise ValueError("plot-equal weighted matrix rank deficient")
    return beta


def heldout_plot_equal_county_mse(test: pd.DataFrame, predictions: np.ndarray) -> pd.Series:
    if len(test) != len(predictions):
        raise ValueError("heldout predictions and test grain differ")
    errors = pd.DataFrame({
        "state":test.state.to_numpy(), "county":test.county.to_numpy(),
        "plot":test.plot_chain_sha256.to_numpy(),
        "se":(test.growth.to_numpy(float)-predictions)**2})
    return (errors.groupby(["state","county","plot"],sort=False)["se"].mean()
            .groupby(["state","county"]).mean())


def county_ledger(growth: pd.DataFrame, source: pd.DataFrame) -> list[dict]:
    if set(growth.sp)!=set(SPECIES) or set(growth.state)!=set(STATES):
        raise ValueError("wrong original five-species/two-state response cohort")
    results = []
    for sp in SPECIES:
        y = growth[growth.sp==sp]
        s = source[source.species_code==sp]
        for fold in range(prior.FOLDS):
            eligible = []
            for state in STATES:
                eligible.append(prior.training_cells(s[(s.state==state)&(s.fold!=fold)]))
            common = eligible[0] & eligible[1]
            if len(common)<2:
                raise ValueError("source-only training climate support lost")
            panel = y[y.cell.isin(common)]
            train = panel[panel.fold!=fold]
            test = panel[panel.fold==fold]
            if not len(train) or not len(test) or set(train.county)&set(test.county):
                raise ValueError("empty test/train or heldout county leakage")
            scores = {}
            for model in MODES:
                estimate = county.design(test,model)@fit(train,model)
                scores[model] = heldout_plot_equal_county_mse(test,estimate)
            first = scores[MODES[0]]
            if not all(s.index.equals(first.index) for s in scores.values()):
                raise ValueError("candidate models scored different county set")
            for (state,fips) in first.index:
                row = {"species_code":sp,"state":state,"county_fips":fips,"fold":fold}
                for model in MODES:
                    row[model+"_mse"] = float(scores[model][(state,fips)])
                results.append(row)
    return results


def score(records: list[dict], model: str) -> float:
    state_scores=[]
    for state in STATES:
        values=[x[model+"_mse"] for x in records if x["state"]==state]
        if not values:
            raise ValueError("missing state in plot-equal county score")
        state_scores.append(float(np.mean(values)))
    return math.sqrt(float(np.mean(state_scores)))


def gain(before: float, after: float) -> float:
    if not before > 0 or not math.isfinite(before+after):
        raise ValueError("invalid plot-equal county score")
    return 100*(before-after)/before


def species_summary(records: list[dict], sp: str) -> dict:
    counties=[x for x in records if x["species_code"]==sp]
    if len({x["county_fips"] for x in counties}) != len(counties):
        raise ValueError("county occurs in multiple heldout folds")
    values={m:score(counties,m) for m in MODES}
    effect={
      "single_BA_vs_no_BA":gain(values["without_density"],values["original_basal_area"]),
      "county_mean_only_vs_no_BA":gain(values["without_density"],values["county_mean_basal_area"]),
      "within_increment_conditional_on_county_mean":
          gain(values["county_mean_basal_area"],values["between_and_within"])}
    rng=np.random.default_rng(20261117+int(sp))
    grouped={st:[x for x in counties if x["state"]==st] for st in STATES}
    boot=[]
    for _ in range(BOOTSTRAP):
        chosen=[]
        for st in STATES:
            rows=grouped[st]
            ids=rng.integers(0,len(rows),size=len(rows))
            chosen.extend(rows[int(i)] for i in ids)
        boot.append(gain(score(chosen,"county_mean_basal_area"),score(chosen,"between_and_within")))
    low,hi=np.quantile(boot,[.025,.975]).tolist()
    return {"species_code":sp,"n_heldout_counties":len(counties),
            "plot_equal_county_equal_state_equal_RMSE":values,
            "relative_gain_percent":effect,
            "within_gain_postfit_county_bootstrap95":[float(low),float(hi)],
            "postfit_resampling_retrains_models":False,
            "predictor_county_means_use_ultimately_surviving_cohort":True}


def run(source_dir: Path) -> tuple[dict,list[dict]]:
    growth,source,original=prior.prepare_inputs(source_dir)
    if original.get("n_primary_complete")!=5 or len(growth)!=170994:
        raise ValueError("first-open prior response and denominator changed")
    y,src=prior.source_and_growth_cells(growth,source)
    df=county.add_predictors(y)
    ledger=county_ledger(df,src)
    results=[species_summary(ledger,sp) for sp in SPECIES]
    return {"program":PROGRAM,
            "original_first_open_run":prior.SOURCE_RUN,
            "original_first_open_artifact":prior.SOURCE_ARTIFACT,
            "first_open_ZIP_sha256":prior.ZIP_SHA256,
            "growth_input_SHA256":prior.INPUT_SHA256,
            "source_input_SHA256":prior.SOURCE_SHA256,
            "n_live_to_live_growth_rows":len(df),
            "n_prior_species_source_rows":len(src),
            "n_scored_counties":len(ledger),
            "n_taxa":len(SPECIES),
            "n_positive_within_county_increment":sum(
                r["relative_gain_percent"]["within_increment_conditional_on_county_mean"]>0
                for r in results),
            "n_county_postfit_95pct_intervals_lower_above_zero":sum(
                r["within_gain_postfit_county_bootstrap95"][0]>0 for r in results),
            "original_county_split_and_train_only_source_bins":True,
            "changed_training_weight_and_scoring_to_plot_chain_equal":True,
            "models_fit_after_previous_outcomes_opened":True,
            "county_mean_transductive_conditional_survivor_information":True,
            "no_new_response_or_raw_FIA_source_read":True,
            "not_an_independent_demographic_replication":True,
            "no_competition_causality_or_niche_inference":True,
            "biological_promotion_authorized":False,
            "species":results},ledger


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args()
    result,ledger=run(a.source_dir)
    a.out_dir.mkdir(parents=True,exist_ok=True)
    (a.out_dir/"plot_equal_BA_summary.json").write_text(json.dumps(
        result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    pd.DataFrame(ledger).to_csv(a.out_dir/"plot_equal_BA_county_ledger.csv",index=False)
    print("postoutcome plot-equal sensitivity",
          result["n_positive_within_county_increment"],"/5; positive postfit intervals",
          result["n_county_postfit_95pct_intervals_lower_above_zero"],"/5")


if __name__=="__main__":
    main()
