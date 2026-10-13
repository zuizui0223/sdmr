#!/usr/bin/env python3
"""Development smoke for observation-aware process challenge on consumed known-truth seeds."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.model import ModelSpec
from sdmr.process_challenge_learner import (
    CONTRIBUTORY,
    REPLACEABLE,
    REQUIRED,
    UNRESOLVED,
    fit_process_challenge_learner,
)
from sdmr.process_id.known_truth.occurrence_oracle import evaluate_occurrence_oracle_states
from sdmr.process_id.known_truth.worlds import KnownTruthWorld, simulate_process_world

STATE_MAP={
    REPLACEABLE:"replaceable",
    CONTRIBUTORY:"contributory",
    REQUIRED:"required",
    UNRESOLVED:"unresolved",
}


def _groups(world:KnownTruthWorld, frame:pd.DataFrame)->np.ndarray:
    lookup=dict(zip(world.environment["cell_id"].astype(int),np.asarray(world.spatial_groups),strict=True))
    g=frame["cell_id"].astype(int).map(lookup)
    if g.isna().any():
        raise ValueError("sample cell outside world group lookup")
    return g.to_numpy()


def _specs(cfg):
    return tuple(
        ModelSpec(
            C=float(r["C"]),degree=int(r["degree"]),penalty=str(r["penalty"]),
            random_state=int(r["random_state"])
        )
        for r in cfg["learner"]["model_specs"]
    )


def _reference(world:KnownTruthWorld,cfg,*,effort_conditioned:bool)->pd.DataFrame:
    o=cfg["reference_oracle"]
    target=world
    if effort_conditioned:
        env=world.environment.copy()
        effort=pd.to_numeric(env["sampling_effort"],errors="raise").to_numpy(float)
        if not np.isfinite(effort).all() or (effort<=0).any():
            raise ValueError("sampling effort must be finite positive")
        env["log_sampling_effort"]=np.log(effort)
        target=replace(
            world,
            environment=env,
            occurrences=env.loc[world.occurrences["cell_id"].astype(int).to_numpy()].copy().reset_index(drop=True)
                if False else world.occurrences.copy(),
            background=world.background.copy(),
            predictor_universe=tuple([*world.predictor_universe,"log_sampling_effort"]),
            observation_unresolved_processes=(),
        )
        target.occurrences["log_sampling_effort"]=np.log(pd.to_numeric(target.occurrences["sampling_effort"],errors="raise").to_numpy(float))
        target.background["log_sampling_effort"]=np.log(pd.to_numeric(target.background["sampling_effort"],errors="raise").to_numpy(float))
    ev=evaluate_occurrence_oracle_states(
        target,
        n_splits=int(o["n_splits"]),margin=float(o["margin"]),
        sem_multiplier=float(o["sem_multiplier"]),adequacy_floor=float(o["adequacy_floor"]),
        approximation_tolerance=float(o["approximation_tolerance"]),
        max_iter=int(o["max_iter"]),max_leaf_nodes=int(o["max_leaf_nodes"]),
        min_samples_leaf=int(o["min_samples_leaf"]),learning_rate=float(o["learning_rate"]),
        l2_regularization=float(o["l2_regularization"]),split_mode=str(o["split_mode"])
    )
    return ev.states[["process","state","reason"]].copy()


def _fit(world:KnownTruthWorld,cfg,*,effort_conditioned:bool):
    p=world.occurrences.copy().reset_index(drop=True)
    b=world.background.copy().reset_index(drop=True)
    obs=()
    if effort_conditioned:
        for frame in (p,b):
            effort=pd.to_numeric(frame["sampling_effort"],errors="raise").to_numpy(float)
            if not np.isfinite(effort).all() or (effort<=0).any():
                raise ValueError("sampling effort must be finite positive")
            frame["log_sampling_effort"]=np.log(effort)
        obs=("log_sampling_effort",)
    l=cfg["learner"]
    fit=fit_process_challenge_learner(
        p,b,_groups(world,p),_groups(world,b),
        ecological_predictors=tuple(world.predictor_universe),
        observation_predictors=obs,
        process_registry=world.process_registry,
        process_universe=world.process_universe,
        model_specs=_specs(cfg),
        n_splits=int(l["n_splits"]),chance_score=float(l["chance_score"]),
        minimum_margin=float(l["minimum_margin"]),sem_multiplier=float(l["sem_multiplier"]),
        relative_noninferiority_margin=float(l["relative_noninferiority_margin"]),
        relative_sem_multiplier=float(l["relative_sem_multiplier"]),
        observation_signal_chance=float(l["observation_signal_chance"]),
        observation_signal_margin=float(l["observation_signal_margin"]),
        observation_signal_sem_multiplier=float(l["observation_signal_sem_multiplier"]),
        observation_weight_truncation_quantile=float(l["observation_weight_truncation_quantile"]),
        observation_weight_probability_epsilon=float(l["observation_weight_probability_epsilon"]),
    )
    states=fit.process_summary[["process","status"]].copy()
    states["state"]=states["status"].map(STATE_MAP)
    if states["state"].isna().any():
        raise ValueError("unknown process challenge state")
    fold=fit.base_fit.fold_evidence
    correction={
        "n_fold_rows":int(len(fold)),
        "active_fraction":float(fold["observation_correction_active"].astype(bool).mean()),
        "mean_signal_auc":float(pd.to_numeric(fold["observation_signal_auc"],errors="coerce").mean()),
        "minimum_weight_ess":float(pd.to_numeric(fold["observation_weight_ess"],errors="coerce").min()),
    }
    return states[["process","state"]],correction


def _one(world_name,seed,cfg):
    world=simulate_process_world(
        world_name,seed=int(seed),n_cells=int(cfg["generator"]["cells"]),
        n_occurrences=int(cfg["generator"]["occurrences"]),
        n_background=int(cfg["generator"]["background"])
    )
    rows=[]
    refs={}
    for mode,conditioned in (("effort_unavailable",False),("effort_conditioned_upper_bound",True)):
        ref=_reference(world,cfg,effort_conditioned=conditioned)
        refs[mode]=dict(zip(ref.process.astype(str),ref.state.astype(str)))
        try:
            states,correction=_fit(world,cfg,effort_conditioned=conditioned)
            pred=dict(zip(states.process.astype(str),states.state.astype(str)))
            available=True; error=""
        except Exception as exc:
            pred={p:"unavailable" for p in world.process_universe}
            correction={"n_fold_rows":0,"active_fraction":0.0,"mean_signal_auc":float("nan"),"minimum_weight_ess":float("nan")}
            available=False;error=f"{type(exc).__name__}: {exc}"
        for process in world.process_universe:
            rows.append({
                "world":world_name,"seed":int(seed),"information_system":mode,
                "process":str(process),"reference_state":refs[mode][str(process)],
                "method_state":pred[str(process)],"method_available":available,
                "error":error,**correction
            })
    return rows


def run(contract_path:Path,out:Path):
    cfg=json.loads(contract_path.read_text())
    if cfg["status"]!="development_smoke_only_fresh_seeds_unopened":
        raise ValueError("wrong observation-aware challenge status")
    if cfg["prospective_reservation"]["opened"] is not False:
        raise ValueError("fresh seeds already marked opened")
    rows=[]
    for world in cfg["smoke"]["worlds"]:
        rows.extend(_one(str(world),int(cfg["smoke"]["consumed_seed"]),cfg))
    frame=pd.DataFrame(rows)
    if len(frame)!=len(cfg["smoke"]["worlds"])*2*6:
        raise RuntimeError("smoke denominator changed")
    out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/"smoke_states.csv",index=False)
    summary={
        "program":"sdmr-observation-aware-process-challenge-v1-smoke",
        "status":"development_smoke_complete",
        "seed":int(cfg["smoke"]["consumed_seed"]),
        "worlds":list(cfg["smoke"]["worlds"]),
        "rows":int(len(frame)),
        "prospective_seeds_opened":False,
        "fresh_93001_93003_accessed":False,
        "scientific_promotion":False,
        "state_counts":frame.groupby(["information_system","method_state"]).size().to_dict(),
    }
    # JSON requires string keys.
    summary["state_counts"]={f"{k[0]}::{k[1]}":int(v) for k,v in summary["state_counts"].items()}
    (out/"smoke_result.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,indent=2,sort_keys=True))
    return summary


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--contract",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    a=ap.parse_args()
    run(a.contract,a.output_dir)


if __name__=="__main__":
    main()
