"""Consumed-development matched-null diagnosis for v8 conditional replacement (v14)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .conditional_shared_knockout_v8_development import _load as _load_v8, _specs
from .conditional_shared_knockout_process_challenge import fit_conditional_shared_knockout_process_challenge
from .conditional_shrinkage_null import matched_shrinkage_null_route_cv
from .interval_evidence_process_challenge import (
    INCOMPLETE_EVIDENCE, INDETERMINATE_EVIDENCE, INFERIOR_EVIDENCE, NONINFERIOR_EVIDENCE,
    _classify_processes as _classify_interval_processes, interval_evidence_state,
)
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .observation_aware_identification import _fold_indices, _prepare_observation_corrections, _summary
from .process_challenge_learner import CONTRIBUTORY
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .proxy_closed_route_process_challenge import _paired_delta
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "conditional_shrinkage_null_v14_development.json"


def _config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "conditional_shrinkage_null_v14_development_only":
        raise ValueError("wrong v14 contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v14 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001, 15011)):
        raise ValueError("v14 must use consumed seeds 15001-15010")
    salts = tuple(int(x) for x in cfg.get("null_salts", ()))
    if len(salts) != int(cfg.get("null_replicates", -1)) or len(set(salts)) != len(salts):
        raise ValueError("v14 null salts must be unique and frozen")
    if cfg.get("post_outcome_threshold_relaxation_allowed") is not False:
        raise ValueError("post-outcome relaxation forbidden")
    return cfg


def _route_summary(fold_frame, *, process, model_label, rank_baseline, density_baseline, learner):
    prediction = _summary(fold_frame, "presence_rank", chance_score=float(learner["chance_score"]), minimum_margin=float(learner["minimum_margin"]), sem_multiplier=float(learner["sem_multiplier"]))
    ecology = _summary(fold_frame, "ecological_presence_rank", chance_score=float(learner["chance_score"]), minimum_margin=float(learner["minimum_margin"]), sem_multiplier=float(learner["sem_multiplier"]))
    pred_delta = _paired_delta(rank_baseline, fold_frame, model_label=model_label, baseline_metric="presence_rank", route_metric="presence_rank")
    eco_delta = _paired_delta(rank_baseline, fold_frame, model_label=model_label, baseline_metric="ecological_presence_rank", route_metric="ecological_presence_rank")
    den_delta = _paired_delta(density_baseline, fold_frame, model_label=model_label, baseline_metric="balanced_density_log_score", route_metric="balanced_density_log_score")
    eco_den_delta = _paired_delta(density_baseline, fold_frame, model_label=model_label, baseline_metric="ecological_density_log_score", route_metric="ecological_density_log_score")
    states = [
        interval_evidence_state(pred_delta["mean_delta"], pred_delta["sem_delta"], margin=float(learner["relative_noninferiority_margin"]), sem_multiplier=float(learner["relative_sem_multiplier"]), complete=bool(pred_delta["complete"])),
        interval_evidence_state(eco_delta["mean_delta"], eco_delta["sem_delta"], margin=float(learner["relative_noninferiority_margin"]), sem_multiplier=float(learner["relative_sem_multiplier"]), complete=bool(eco_delta["complete"])),
        interval_evidence_state(den_delta["mean_delta"], den_delta["sem_delta"], margin=float(learner["density_noninferiority_margin"]), sem_multiplier=float(learner["density_sem_multiplier"]), complete=bool(den_delta["complete"])),
        interval_evidence_state(eco_den_delta["mean_delta"], eco_den_delta["sem_delta"], margin=float(learner["density_noninferiority_margin"]), sem_multiplier=float(learner["density_sem_multiplier"]), complete=bool(eco_den_delta["complete"])),
    ]
    labels = tuple(str(x["state"]) for x in states)
    complete = bool(fold_frame["complete"].astype(bool).all())
    if not complete or INCOMPLETE_EVIDENCE in labels:
        relative_state = INCOMPLETE_EVIDENCE
    elif all(x == NONINFERIOR_EVIDENCE for x in labels):
        relative_state = NONINFERIOR_EVIDENCE
    elif any(x == INFERIOR_EVIDENCE for x in labels):
        relative_state = INFERIOR_EVIDENCE
    else:
        relative_state = INDETERMINATE_EVIDENCE
    return {
        "process": process, "excluded_process": process, "model_label": model_label,
        "route": str(fold_frame.iloc[0]["route"]), "route_type": "conditional_shrinkage_matched_null",
        "complete": complete, "route_adequate": bool(prediction["adequate"] and ecology["adequate"]),
        "mean_presence_rank": prediction["mean"], "mean_ecological_presence_rank": ecology["mean"],
        "prediction_interval_state": states[0]["state"], "ecological_rank_interval_state": states[1]["state"],
        "density_interval_state": states[2]["state"], "ecological_density_interval_state": states[3]["state"],
        "relative_evidence_state": relative_state, "n_folds": int(len(fold_frame)),
    }


def fit_family(family: str, output_dir: str | Path):
    cfg = _config(); dev, v6 = _load_v8()
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    sim=v6["simulation"]; learner=v6["learner"]
    ecological=tuple(v6["ecological_predictors"]); observation=tuple(v6["observation_predictors"])
    processes=tuple(v6["process_universe"]); specs=_specs(v6)
    registry=pd.DataFrame(v6["process_registry"])[["predictor","process","role"]]
    closures={p: tuple(process_information_closure(registry,p)) for p in processes}
    case_rows=[]; status_rows=[]; fold_parts=[]; route_parts=[]
    for seed_value in cfg["consumed_seed_denominator"]:
        seed=int(seed_value)
        simulation=simulate_known_truth_plant_niche(family,seed=seed,n_cells=int(sim["n_cells"]),n_occurrences=int(sim["n_occurrences"]),n_target_group=int(sim["n_target_group"]))
        occurrences,background=_selection_frames(simulation,family=family,seed=seed)
        split=freeze_occurrence_answer_check_split(occurrences,id_col="occurrence_id",lon_col="longitude",lat_col="latitude",n_blocks=int(sim["outer_n_blocks"]),holdout_fraction=float(sim["answer_check_fraction"]),random_state=int(sim["outer_random_state_offset"])+seed)
        model_presence=split.model_pool(occurrences)
        inner=make_spatial_partition(model_presence["longitude"].to_numpy(float),model_presence["latitude"].to_numpy(float),background["longitude"].to_numpy(float),background["latitude"].to_numpy(float),n_blocks=int(sim["inner_n_blocks"]),holdout_fraction=0.20,random_state=int(sim["inner_random_state_offset"])+seed)
        fit=fit_conditional_shared_knockout_process_challenge(
            model_presence,background,inner.presence_blocks,inner.background_blocks,
            ecological_predictors=ecological,observation_predictors=observation,process_registry=registry,process_universe=processes,model_specs=specs,n_splits=int(sim["inner_n_splits"]),
            chance_score=float(learner["chance_score"]),minimum_margin=float(learner["minimum_margin"]),sem_multiplier=float(learner["sem_multiplier"]),relative_noninferiority_margin=float(learner["relative_noninferiority_margin"]),relative_sem_multiplier=float(learner["relative_sem_multiplier"]),density_noninferiority_margin=float(learner["density_noninferiority_margin"]),density_sem_multiplier=float(learner["density_sem_multiplier"]),density_probability_epsilon=float(learner["density_probability_epsilon"]),knockout_degree=int(dev["knockout_degree"]),knockout_ridge_alpha=float(dev["knockout_ridge_alpha"]),observation_signal_chance=float(learner["observation_signal_chance"]),observation_signal_margin=float(learner["observation_signal_margin"]),observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),occurrence_split=split,occurrence_id_col="occurrence_id")
        summary=fit.process_summary.copy()
        summary["shared_candidate"]=summary["v5_status"].astype(str).eq(CONTRIBUTORY) & ~summary["status"].astype(str).eq(CONTRIBUTORY)
        shared=summary.loc[summary["shared_candidate"].astype(bool),"process"].astype(str).tolist()
        expected_labels=tuple(sorted(set(fit.v5_fit.v4_fit.v3_fit.route_summary["model_label"].astype(str))))
        rank_baseline=fit.v5_fit.v4_fit.v3_fit.base_fit.fold_evidence
        density_baseline=fit.v5_fit.v4_fit.density_fold_evidence
        folds=_fold_indices(len(model_presence),len(background),np.asarray(inner.presence_blocks),np.asarray(inner.background_blocks),n_splits=int(sim["inner_n_splits"]))
        corrections=_prepare_observation_corrections(model_presence,background,np.asarray(inner.presence_blocks),np.asarray(inner.background_blocks),observation,folds,observation_signal_chance=float(learner["observation_signal_chance"]),observation_signal_margin=float(learner["observation_signal_margin"]),observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]))
        spec_by_label={s.label:s for s in specs}
        reproduced_cells=0; alignment_cells=0; mixed_cells=0
        for p in shared:
            closure=closures[p]
            other=[closures[q] for q in processes if q!=p]
            conditioning=tuple(dict.fromkeys(x for cols in other for x in cols if x not in set(closure)))
            replicate_status=[]
            for salt in cfg["null_salts"]:
                route_rows=[]
                for model_label in expected_labels:
                    ev=matched_shrinkage_null_route_cv(model_presence,background,process=p,process_predictors=closure,conditioning_predictors=conditioning,ecological_predictors=ecological,observation_predictors=observation,model_spec=spec_by_label[model_label],folds=folds,corrections=corrections,degree=int(dev["knockout_degree"]),ridge_alpha=float(dev["knockout_ridge_alpha"]),density_probability_epsilon=float(learner["density_probability_epsilon"]),null_salt=int(salt))
                    ev.insert(0,"family",family); ev.insert(1,"seed",seed); ev.insert(2,"null_salt",int(salt)); fold_parts.append(ev)
                    rr=_route_summary(ev,process=p,model_label=model_label,rank_baseline=rank_baseline,density_baseline=density_baseline,learner=learner)
                    rr.update({"family":family,"seed":seed,"null_salt":int(salt)}); route_rows.append(rr)
                routes=pd.DataFrame(route_rows); route_parts.append(routes)
                null_status=str(_classify_interval_processes(routes,(p,),expected_model_labels=expected_labels).iloc[0]["status"])
                replicate_status.append(null_status)
                status_rows.append({"family":family,"seed":seed,"target_process":p,"null_salt":int(salt),"null_status":null_status,"v5_status":CONTRIBUTORY,"v8_status":str(summary.set_index("process").loc[p,"status"]),"reproduces_v8_noncontributory":null_status!=CONTRIBUTORY})
            nrep=sum(x!=CONTRIBUTORY for x in replicate_status)
            if nrep==len(cfg["null_salts"]): cls="shrinkage_reproduced"; reproduced_cells+=1
            elif nrep==0: cls="conditioning_alignment_required"; alignment_cells+=1
            else: cls="mixed"; mixed_cells+=1
            case_rows.append({"family":family,"seed":seed,"target_process":p,"n_null_replicates":len(replicate_status),"n_null_reproducing_v8_noncontributory":nrep,"classification":cls})
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    cases=pd.DataFrame(case_rows); statuses=pd.DataFrame(status_rows); routes=pd.concat(route_parts,ignore_index=True) if route_parts else pd.DataFrame(); folds_out=pd.concat(fold_parts,ignore_index=True) if fold_parts else pd.DataFrame()
    cases.to_csv(out/"case_summary.csv",index=False); statuses.to_csv(out/"null_status.csv",index=False); routes.to_csv(out/"null_route_summary.csv",index=False); folds_out.to_csv(out/"null_fold_evidence.csv",index=False)
    return {"family":family,"n_shared_candidates":int(len(cases)),"n_shrinkage_reproduced":int((cases.get("classification",pd.Series(dtype=str))=="shrinkage_reproduced").sum())}


def _read(path):
    try:return pd.read_csv(path)
    except pd.errors.EmptyDataError:return pd.DataFrame()


def aggregate(input_dir: str|Path, output_dir: str|Path):
    root=Path(input_dir); expected=len(KNOWN_TRUTH_FAMILIES)
    cfiles=list(root.rglob("case_summary.csv")); sfiles=list(root.rglob("null_status.csv")); rfiles=list(root.rglob("null_route_summary.csv")); ffiles=list(root.rglob("null_fold_evidence.csv"))
    if not all(len(x)==expected for x in (cfiles,sfiles,rfiles,ffiles)): raise ValueError("v14 aggregate requires one artifact per family")
    cases=pd.concat([_read(x) for x in cfiles],ignore_index=True); statuses=pd.concat([_read(x) for x in sfiles],ignore_index=True); routes=pd.concat([_read(x) for x in rfiles],ignore_index=True); folds=pd.concat([_read(x) for x in ffiles],ignore_index=True)
    counts=cases["classification"].value_counts() if len(cases) else pd.Series(dtype=int)
    result={"purpose":"conditional_shrinkage_null_v14_consumed_development_decision","development_only":True,"eligible_for_prospective_performance_claim":False,"n_shared_candidate_cells":int(len(cases)),"n_shrinkage_reproduced":int(counts.get("shrinkage_reproduced",0)),"n_conditioning_alignment_required":int(counts.get("conditioning_alignment_required",0)),"n_mixed":int(counts.get("mixed",0)),"fresh_known_truth_validation_authorized":False,"fresh_empirical_validation_authorized":False}
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); cases.to_csv(out/"case_summary.csv",index=False); statuses.to_csv(out/"null_status.csv",index=False); routes.to_csv(out/"null_route_summary.csv",index=False); folds.to_csv(out/"null_fold_evidence.csv",index=False); (out/"development_decision.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("fit-family"); f.add_argument("--family",required=True); f.add_argument("--output-dir",required=True)
    a=sub.add_parser("aggregate"); a.add_argument("--input-dir",required=True); a.add_argument("--output-dir",required=True)
    args=parser.parse_args(argv); result=fit_family(args.family,args.output_dir) if args.cmd=="fit-family" else aggregate(args.input_dir,args.output_dir); print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__": main()
