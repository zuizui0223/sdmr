"""Consumed-development diagnosis of functional compensation (v13)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .conditional_shared_knockout_v8_development import _load as _load_v8, _specs
from .conditional_shared_knockout_process_challenge import fit_conditional_shared_knockout_process_challenge
from .functional_compensation_audit import (
    classify_functional_compensation,
    enumerate_process_coalitions,
    functional_compensation_evidence,
)
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .process_challenge_learner import CONTRIBUTORY
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "functional_compensation_v13_development.json"

AUDIT_COLUMNS = [
    "family", "seed", "target_process", "coalition_processes", "coalition_size",
    "state", "n_folds", "mean_conditional_rank_loss", "sem_conditional_rank_loss",
    "mean_conditional_density_loss", "sem_conditional_density_loss",
    "minimal_functional_compensator",
]
CASE_COLUMNS = [
    "family", "seed", "n_shared_candidates", "n_shared_candidates_with_functional_compensator",
    "n_minimal_functional_compensators",
]


def _config() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "functional_compensation_v13_development_only":
        raise ValueError("wrong v13 development contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v13 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001, 15011)):
        raise ValueError("v13 must use exactly consumed 15001-15010")
    if cfg.get("enumerate_all_nonempty_compensator_coalitions") is not True:
        raise ValueError("v13 requires exhaustive coalition enumeration")
    if cfg.get("post_outcome_threshold_relaxation_allowed") is not False:
        raise ValueError("post-outcome threshold relaxation forbidden")
    return cfg


def _minimalize(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["minimal_functional_compensator"] = False
    qualified = out.loc[out["state"].astype(str).eq("functional_compensator")].copy()
    if qualified.empty:
        return out
    sets = {
        int(idx): frozenset(str(row["coalition_processes"]).split("+"))
        for idx, row in qualified.iterrows()
    }
    for idx, coalition in sets.items():
        if not any(other < coalition for j, other in sets.items() if j != idx):
            out.loc[idx, "minimal_functional_compensator"] = True
    return out


def fit_family(family: str, output_dir: str | Path) -> dict[str, object]:
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    cfg = _config(); dev, v6 = _load_v8()
    sim = v6["simulation"]; learner = v6["learner"]
    ecological = tuple(v6["ecological_predictors"]); observation = tuple(v6["observation_predictors"])
    processes = tuple(v6["process_universe"]); specs = _specs(v6)
    registry = pd.DataFrame(v6["process_registry"])[["predictor", "process", "role"]]
    closures = {p: tuple(process_information_closure(registry, p)) for p in processes}

    audit_parts: list[pd.DataFrame] = []
    evidence_parts: list[pd.DataFrame] = []
    case_rows: list[dict[str, object]] = []

    for seed_value in cfg["consumed_seed_denominator"]:
        seed = int(seed_value)
        simulation = simulate_known_truth_plant_niche(
            family, seed=seed, n_cells=int(sim["n_cells"]),
            n_occurrences=int(sim["n_occurrences"]), n_target_group=int(sim["n_target_group"]),
        )
        occurrences, background = _selection_frames(simulation, family=family, seed=seed)
        split = freeze_occurrence_answer_check_split(
            occurrences, id_col="occurrence_id", lon_col="longitude", lat_col="latitude",
            n_blocks=int(sim["outer_n_blocks"]), holdout_fraction=float(sim["answer_check_fraction"]),
            random_state=int(sim["outer_random_state_offset"]) + seed,
        )
        model_presence = split.model_pool(occurrences)
        inner = make_spatial_partition(
            model_presence["longitude"].to_numpy(float), model_presence["latitude"].to_numpy(float),
            background["longitude"].to_numpy(float), background["latitude"].to_numpy(float),
            n_blocks=int(sim["inner_n_blocks"]), holdout_fraction=0.20,
            random_state=int(sim["inner_random_state_offset"]) + seed,
        )
        fit = fit_conditional_shared_knockout_process_challenge(
            model_presence, background, inner.presence_blocks, inner.background_blocks,
            ecological_predictors=ecological, observation_predictors=observation,
            process_registry=registry, process_universe=processes, model_specs=specs,
            n_splits=int(sim["inner_n_splits"]), chance_score=float(learner["chance_score"]),
            minimum_margin=float(learner["minimum_margin"]), sem_multiplier=float(learner["sem_multiplier"]),
            relative_noninferiority_margin=float(learner["relative_noninferiority_margin"]),
            relative_sem_multiplier=float(learner["relative_sem_multiplier"]),
            density_noninferiority_margin=float(learner["density_noninferiority_margin"]),
            density_sem_multiplier=float(learner["density_sem_multiplier"]),
            density_probability_epsilon=float(learner["density_probability_epsilon"]),
            knockout_degree=int(dev["knockout_degree"]), knockout_ridge_alpha=float(dev["knockout_ridge_alpha"]),
            observation_signal_chance=float(learner["observation_signal_chance"]),
            observation_signal_margin=float(learner["observation_signal_margin"]),
            observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),
            observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
            observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),
            occurrence_split=split, occurrence_id_col="occurrence_id",
        )
        summary = fit.process_summary.copy()
        summary["shared_candidate"] = summary["v5_status"].astype(str).eq(CONTRIBUTORY) & ~summary["status"].astype(str).eq(CONTRIBUTORY)
        shared = summary.loc[summary["shared_candidate"].astype(bool), "process"].astype(str).tolist()
        shared_with = 0; n_minimal = 0
        for p in shared:
            rows = []
            for coalition in enumerate_process_coalitions(processes, p):
                ev = functional_compensation_evidence(
                    model_presence, background, inner.presence_blocks, inner.background_blocks,
                    target_process=p, coalition_processes=coalition, closures=closures,
                    ecological_predictors=ecological, observation_predictors=observation,
                    model_specs=specs, chance_score=float(learner["chance_score"]),
                    minimum_margin=float(learner["minimum_margin"]),
                    density_probability_epsilon=float(learner["density_probability_epsilon"]),
                    observation_signal_chance=float(learner["observation_signal_chance"]),
                    observation_signal_margin=float(learner["observation_signal_margin"]),
                    observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),
                    observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
                    observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),
                )
                if len(ev):
                    ev.insert(0, "family", family); ev.insert(1, "seed", seed)
                    evidence_parts.append(ev)
                decision = classify_functional_compensation(
                    ev, expected_model_specs=len(specs),
                    rank_margin=float(cfg["conditional_rank_margin"]),
                    density_margin=float(cfg["conditional_density_margin"]),
                    sem_multiplier=float(cfg["sem_multiplier"]),
                )
                rows.append({
                    "family": family, "seed": seed, "target_process": p,
                    "coalition_processes": "+".join(coalition), "coalition_size": len(coalition),
                    "state": decision["state"], "n_folds": int(decision.get("n_folds", 0)),
                    "mean_conditional_rank_loss": decision.get("mean_conditional_rank_loss", float("nan")),
                    "sem_conditional_rank_loss": decision.get("sem_conditional_rank_loss", float("nan")),
                    "mean_conditional_density_loss": decision.get("mean_conditional_density_loss", float("nan")),
                    "sem_conditional_density_loss": decision.get("sem_conditional_density_loss", float("nan")),
                })
            local = _minimalize(pd.DataFrame(rows))
            audit_parts.append(local)
            mins = local.loc[local["minimal_functional_compensator"].astype(bool)]
            if len(mins): shared_with += 1
            n_minimal += len(mins)
        case_rows.append({
            "family": family, "seed": seed, "n_shared_candidates": len(shared),
            "n_shared_candidates_with_functional_compensator": shared_with,
            "n_minimal_functional_compensators": n_minimal,
        })

    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    audit = pd.concat(audit_parts, ignore_index=True) if audit_parts else pd.DataFrame(columns=AUDIT_COLUMNS)
    cases = pd.DataFrame(case_rows, columns=CASE_COLUMNS)
    evidence = pd.concat(evidence_parts, ignore_index=True) if evidence_parts else pd.DataFrame()
    audit.to_csv(out/"compensation_audit.csv", index=False)
    cases.to_csv(out/"case_summary.csv", index=False)
    evidence.to_csv(out/"compensation_evidence.csv", index=False)
    return {
        "family": family,
        "n_shared_candidates": int(cases["n_shared_candidates"].sum()),
        "n_shared_candidates_with_functional_compensator": int(cases["n_shared_candidates_with_functional_compensator"].sum()),
        "n_minimal_functional_compensators": int(cases["n_minimal_functional_compensators"].sum()),
    }


def _read(path: Path, columns=None):
    try: return pd.read_csv(path)
    except pd.errors.EmptyDataError: return pd.DataFrame(columns=columns)


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(input_dir); expected = len(KNOWN_TRUTH_FAMILIES)
    afiles=list(root.rglob("compensation_audit.csv")); cfiles=list(root.rglob("case_summary.csv")); efiles=list(root.rglob("compensation_evidence.csv"))
    if not all(len(x)==expected for x in (afiles,cfiles,efiles)):
        raise ValueError("v13 aggregate requires one artifact per family")
    audits=pd.concat([_read(x,AUDIT_COLUMNS) for x in afiles],ignore_index=True)
    cases=pd.concat([_read(x,CASE_COLUMNS) for x in cfiles],ignore_index=True)
    ep=[x for x in (_read(p) for p in efiles) if len(x.columns)]
    evidence=pd.concat(ep,ignore_index=True) if ep else pd.DataFrame()
    shared=int(cases["n_shared_candidates"].sum()); shared_with=int(cases["n_shared_candidates_with_functional_compensator"].sum())
    result={
        "purpose":"functional_compensation_v13_consumed_development_decision",
        "development_only":True,"eligible_for_prospective_performance_claim":False,
        "n_cases":int(len(cases)),"n_shared_candidate_cells":shared,
        "n_shared_candidates_with_functional_compensator":shared_with,
        "shared_candidate_functional_compensation_coverage":float(shared_with/shared) if shared else 1.0,
        "n_minimal_functional_compensators":int(audits["minimal_functional_compensator"].astype(bool).sum()) if len(audits) else 0,
        "functional_compensation_is_predictive_not_representational":True,
        "fresh_known_truth_validation_authorized":False,"fresh_empirical_validation_authorized":False,
    }
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    audits.to_csv(out/"compensation_audit.csv",index=False); cases.to_csv(out/"case_summary.csv",index=False); evidence.to_csv(out/"compensation_evidence.csv",index=False)
    (out/"development_decision.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("fit-family"); f.add_argument("--family",required=True); f.add_argument("--output-dir",required=True)
    a=sub.add_parser("aggregate"); a.add_argument("--input-dir",required=True); a.add_argument("--output-dir",required=True)
    args=parser.parse_args(argv)
    result=fit_family(args.family,args.output_dir) if args.cmd=="fit-family" else aggregate(args.input_dir,args.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__": main()
