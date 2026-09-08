"""Development-only evaluator for v9 conditional residual randomization."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .conditional_residual_randomization_process_challenge import fit_conditional_residual_randomization_process_challenge
from .known_truth_response import infer_true_processes
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .model import ModelSpec
from .process_challenge_learner import CONTRIBUTORY
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
DEV_CONFIG = ROOT / "configs" / "conditional_residual_randomization_v9_development.json"
V6_CONFIG = ROOT / "configs" / "proxy_closed_route_process_challenge_v6_known_truth_validation_successor_v2.json"


def _load():
    dev = json.loads(DEV_CONFIG.read_text(encoding="utf-8"))
    v6 = json.loads(V6_CONFIG.read_text(encoding="utf-8"))
    if dev.get("purpose") != "conditional_residual_randomization_v9_development_only":
        raise ValueError("wrong v9 development contract")
    if dev.get("development_only") is not True or dev.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v9 denominator must remain development-only")
    seeds = tuple(int(x) for x in dev.get("consumed_seed_denominator", ()))
    if seeds != tuple(range(15001, 15011)) or tuple(v6.get("seeds", ())) != seeds:
        raise ValueError("v9 must use exactly consumed 15001-15010")
    if dev.get("post_outcome_threshold_relaxation_allowed") is not False:
        raise ValueError("post-outcome relaxation forbidden")
    if dev.get("fresh_known_truth_validation_authorized") is not False or dev.get("fresh_empirical_validation_authorized") is not False:
        raise ValueError("fresh validation is not authorized in v9 development")
    return dev, v6


def _specs(v6):
    return tuple(ModelSpec(C=float(x["C"]), degree=int(x["degree"]), penalty=str(x["penalty"]), random_state=int(x["random_state"])) for x in v6["model_specs"])


def _truth(family: str) -> set[str]:
    frame = pd.DataFrame({"scenario": [family], "temperature": [0.0], "water": [0.0], "soil": [0.0]})
    return set(infer_true_processes(frame))


def _metrics(frame: pd.DataFrame, col: str):
    truth = frame["expected_true_process"].astype(bool).to_numpy()
    detected = frame[col].astype(bool).to_numpy()
    tp = int(np.sum(truth & detected)); fp = int(np.sum((~truth) & detected))
    fn = int(np.sum(truth & (~detected))); tn = int(np.sum((~truth) & (~detected)))
    pden = 2 * tp + fp + fn; nden = 2 * tn + fn + fp
    pf1 = float(2 * tp / pden) if pden else float("nan")
    nf1 = float(2 * tn / nden) if nden else float("nan")
    return {
        "true_process_recall": float(tp / truth.sum()) if truth.any() else float("nan"),
        "false_process_detection_rate": float(fp / (~truth).sum()) if (~truth).any() else float("nan"),
        "macro_f1": float(np.nanmean([pf1, nf1])),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "n_true_processes": int(truth.sum()), "n_false_processes": int((~truth).sum()),
    }


def fit_family(family: str, output_dir: str | Path):
    dev, v6 = _load()
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    sim = v6["simulation"]; learner = v6["learner"]
    ecological = tuple(v6["ecological_predictors"]); observation = tuple(v6["observation_predictors"])
    processes = tuple(v6["process_universe"]); registry = pd.DataFrame(v6["process_registry"])[["predictor", "process", "role"]]
    truth = _truth(family)
    process_parts=[]; route_parts=[]; audit_parts=[]; case_rows=[]
    for seed in dev["consumed_seed_denominator"]:
        simulation = simulate_known_truth_plant_niche(family, seed=int(seed), n_cells=int(sim["n_cells"]), n_occurrences=int(sim["n_occurrences"]), n_target_group=int(sim["n_target_group"]))
        occurrences, background = _selection_frames(simulation, family=family, seed=int(seed))
        split = freeze_occurrence_answer_check_split(occurrences, id_col="occurrence_id", lon_col="longitude", lat_col="latitude", n_blocks=int(sim["outer_n_blocks"]), holdout_fraction=float(sim["answer_check_fraction"]), random_state=int(sim["outer_random_state_offset"]) + int(seed))
        model_presence = split.model_pool(occurrences)
        inner = make_spatial_partition(model_presence["longitude"].to_numpy(float), model_presence["latitude"].to_numpy(float), background["longitude"].to_numpy(float), background["latitude"].to_numpy(float), n_blocks=int(sim["inner_n_blocks"]), holdout_fraction=0.20, random_state=int(sim["inner_random_state_offset"]) + int(seed))
        fit = fit_conditional_residual_randomization_process_challenge(
            model_presence, background, inner.presence_blocks, inner.background_blocks,
            ecological_predictors=ecological, observation_predictors=observation,
            process_registry=registry, process_universe=processes, model_specs=_specs(v6),
            n_splits=int(sim["inner_n_splits"]), chance_score=float(learner["chance_score"]),
            minimum_margin=float(learner["minimum_margin"]), sem_multiplier=float(learner["sem_multiplier"]),
            relative_noninferiority_margin=float(learner["relative_noninferiority_margin"]), relative_sem_multiplier=float(learner["relative_sem_multiplier"]),
            density_noninferiority_margin=float(learner["density_noninferiority_margin"]), density_sem_multiplier=float(learner["density_sem_multiplier"]),
            density_probability_epsilon=float(learner["density_probability_epsilon"]),
            randomization_degree=int(dev["randomization_degree"]), randomization_ridge_alpha=float(dev["randomization_ridge_alpha"]), randomization_seed=int(dev["randomization_seed"]),
            observation_signal_chance=float(learner["observation_signal_chance"]), observation_signal_margin=float(learner["observation_signal_margin"]),
            observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]), observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
            observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]), occurrence_split=split, occurrence_id_col="occurrence_id",
        )
        p = fit.process_summary.copy(); p.insert(0, "seed", int(seed)); p.insert(0, "family", family)
        p["expected_true_process"] = p["process"].astype(str).isin(truth)
        p["v9_detected"] = p["status"].astype(str).eq(CONTRIBUTORY)
        p["v5_detected"] = p["v5_status"].astype(str).eq(CONTRIBUTORY)
        process_parts.append(p)
        r=fit.randomized_route_summary.copy(); r.insert(0,"seed",int(seed)); r.insert(0,"family",family); route_parts.append(r)
        a=fit.intervention_audit.copy(); a.insert(0,"seed",int(seed)); a.insert(0,"family",family); audit_parts.append(a)
        case_rows.append({"family":family,"seed":int(seed),"selection_receipt":fit.selection_receipt,"generating_truth_used_by_intervention":False,"consumed_truth_opened_only_for_development_scoring":True})
    process=pd.concat(process_parts,ignore_index=True); routes=pd.concat(route_parts,ignore_index=True); audit=pd.concat(audit_parts,ignore_index=True); cases=pd.DataFrame(case_rows)
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    process.to_csv(out/"process_evaluation.csv",index=False); routes.to_csv(out/"route_summary.csv",index=False); audit.to_csv(out/"intervention_audit.csv",index=False); cases.to_csv(out/"case_summary.csv",index=False)
    return {"family":family,"n_cases":len(cases)}


def aggregate(input_dir: str | Path, output_dir: str | Path):
    dev,_=_load(); root=Path(input_dir)
    pfiles=list(root.rglob("process_evaluation.csv")); rfiles=list(root.rglob("route_summary.csv")); afiles=list(root.rglob("intervention_audit.csv")); cfiles=list(root.rglob("case_summary.csv"))
    n=len(KNOWN_TRUTH_FAMILIES)
    if not all(len(x)==n for x in (pfiles,rfiles,afiles,cfiles)):
        raise ValueError("v9 aggregate requires one artifact per family")
    process=pd.concat([pd.read_csv(x) for x in pfiles],ignore_index=True); routes=pd.concat([pd.read_csv(x) for x in rfiles],ignore_index=True); audit=pd.concat([pd.read_csv(x) for x in afiles],ignore_index=True); cases=pd.concat([pd.read_csv(x) for x in cfiles],ignore_index=True)
    expected={(f,s) for f in KNOWN_TRUTH_FAMILIES for s in dev["consumed_seed_denominator"]}
    observed=set(zip(cases["family"].astype(str),cases["seed"].astype(int),strict=True))
    if observed != expected or len(cases) != 60:
        raise ValueError("v9 aggregate denominator mismatch")
    v9=_metrics(process,"v9_detected"); v5=_metrics(process,"v5_detected")
    exact=[]
    for (family,seed),g in process.groupby(["family","seed"],sort=True):
        truth=set(g.loc[g.expected_true_process.astype(bool),"process"].astype(str)); v9set=set(g.loc[g.v9_detected.astype(bool),"process"].astype(str)); v5set=set(g.loc[g.v5_detected.astype(bool),"process"].astype(str))
        exact.append({"family":family,"seed":int(seed),"v9_exact":v9set==truth,"v5_exact":v5set==truth})
    exact=pd.DataFrame(exact)
    season=process[(process.process.astype(str)=="seasonality") & (~process.expected_true_process.astype(bool))]
    decision={
        "purpose":"conditional_residual_randomization_v9_consumed_development_decision",
        "development_only":True,"eligible_for_prospective_performance_claim":False,
        "n_cases":60,"n_process_cells":int(len(process)),
        "v9_metrics":v9,"v5_same_case_metrics":v5,
        "v9_exact_process_sets":int(exact.v9_exact.sum()),"v5_exact_process_sets":int(exact.v5_exact.sum()),
        "v9_false_seasonality_n":int(season.v9_detected.sum()),"v5_false_seasonality_n":int(season.v5_detected.sum()),
        "all_complete_interventions_preserve_non_target_predictors":bool(audit.loc[audit.complete.astype(bool),"non_target_predictors_unchanged"].astype(bool).all()),
        "fresh_known_truth_validation_required_before_promotion":True,"fresh_empirical_validation_authorized":False,"product_a_reopened":False,
    }
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    process.to_csv(out/"process_evaluation.csv",index=False); routes.to_csv(out/"route_summary.csv",index=False); audit.to_csv(out/"intervention_audit.csv",index=False); cases.to_csv(out/"case_summary.csv",index=False); exact.to_csv(out/"exact_process_sets.csv",index=False)
    (out/"development_decision.json").write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return decision


def main(argv=None):
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("fit-family"); f.add_argument("--family",required=True); f.add_argument("--output-dir",required=True)
    a=sub.add_parser("aggregate"); a.add_argument("--input-dir",required=True); a.add_argument("--output-dir",required=True)
    args=parser.parse_args(argv)
    result=fit_family(args.family,args.output_dir) if args.cmd=="fit-family" else aggregate(args.input_dir,args.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__ == "__main__":
    main()
