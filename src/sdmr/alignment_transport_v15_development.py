"""Consumed-development source->target alignment transport audit (v15)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .alignment_transport import fit_alignment_transport_map, verify_transport_retained_predictors
from .conditional_shared_knockout_v8_development import _load as _load_v8, _specs
from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .interval_evidence_process_challenge import (
    INCOMPLETE_EVIDENCE,
    INDETERMINATE_EVIDENCE,
    INFERIOR_EVIDENCE,
    NONINFERIOR_EVIDENCE,
    _classify_processes as _classify_interval_processes,
    interval_evidence_state,
)
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .model import fit_relative_suitability_model, score_ecological_suitability, score_relative_suitability
from .observation_aware_identification import _prepare_observation_corrections, _weighted_presence_rank
from .process_challenge_learner import CONTRIBUTORY
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .proxy_closed_route_process_challenge import _presence_rank
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "alignment_transport_v15_development.json"
MANIFEST = ROOT / "configs" / "alignment_transport_v15_focus_manifest.csv"


def _config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "alignment_transport_v15_development_only":
        raise ValueError("wrong v15 contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v15 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001, 15011)):
        raise ValueError("v15 must use consumed seeds 15001-15010")
    if cfg.get("new_scientific_thresholds_allowed") is not False or cfg.get("post_outcome_rule_changes_allowed") is not False:
        raise ValueError("v15 threshold/rule changes are forbidden")
    return cfg


def _manifest() -> pd.DataFrame:
    frame = pd.read_csv(MANIFEST)
    expected = {"family", "seed", "target_process", "v14_classification"}
    if set(frame.columns) != expected:
        raise ValueError("unexpected v15 focus manifest schema")
    frame["seed"] = frame["seed"].astype(int)
    if len(frame) != 9 or frame.duplicated(["family", "seed", "target_process"]).any():
        raise ValueError("v15 focus manifest must contain exactly 9 unique cells")
    allowed = {"conditioning_alignment_required", "mixed"}
    if not set(frame["v14_classification"]).issubset(allowed):
        raise ValueError("v15 manifest contains an ineligible v14 class")
    return frame.sort_values(["family", "seed", "target_process"]).reset_index(drop=True)


def _adequate(rank: float, eco_rank: float, learner: dict) -> bool:
    floor = float(learner["chance_score"]) + float(learner["minimum_margin"])
    return bool(np.isfinite(rank) and np.isfinite(eco_rank) and rank >= floor - 1e-12 and eco_rank >= floor - 1e-12)


def _score(model, p_test, b_test, b_reference, model_predictors, observation, correction, eps):
    p_full = score_relative_suitability(model, p_test, model_predictors)
    b_full = score_relative_suitability(model, b_test, model_predictors)
    p_eco = score_ecological_suitability(model, p_test, model_predictors, observation_predictors=observation, observation_reference=b_reference)
    b_eco = score_ecological_suitability(model, b_test, model_predictors, observation_predictors=observation, observation_reference=b_reference)
    return {
        "presence_rank": float(_presence_rank(p_full, b_full)),
        "ecological_presence_rank": float(_weighted_presence_rank(p_eco, b_eco, correction.weights)),
        "balanced_density_log_score": float(balanced_density_ratio_log_score(p_full, b_full, probability_epsilon=float(eps))),
        "ecological_density_log_score": float(balanced_density_ratio_log_score(p_eco, b_eco, presence_weights=correction.weights, probability_epsilon=float(eps))),
    }


def _pair_routes(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    p_groups: np.ndarray,
    b_groups: np.ndarray,
    *,
    process: str,
    source_block: int,
    target_block: int,
    ecological: tuple[str, ...],
    observation: tuple[str, ...],
    registry: pd.DataFrame,
    processes: tuple[str, ...],
    specs,
    learner: dict,
    degree: int,
    ridge_alpha: float,
    minimum_source_rows: int,
):
    p_groups = np.asarray(p_groups)
    b_groups = np.asarray(b_groups)
    p_test_idx = np.flatnonzero(p_groups == int(target_block))
    b_test_idx = np.flatnonzero(b_groups == int(target_block))
    p_train_idx = np.flatnonzero(p_groups != int(target_block))
    b_train_idx = np.flatnonzero(b_groups != int(target_block))
    if min(len(p_train_idx), len(b_train_idx), len(p_test_idx), len(b_test_idx)) < 2:
        return pd.DataFrame(), False, "insufficient_target_rows"

    closure = tuple(process_information_closure(registry, process))
    other = [tuple(process_information_closure(registry, q)) for q in processes if q != process]
    overlap = sorted(set(closure) & set(x for cols in other for x in cols))
    conditioning = tuple(dict.fromkeys(x for cols in other for x in cols if x not in set(closure)))
    if overlap or not conditioning:
        return pd.DataFrame(), False, "structural_overlap_or_empty_conditioning"

    fold = ((p_train_idx, b_train_idx, p_test_idx, b_test_idx),)
    corrections = _prepare_observation_corrections(
        presence, background, p_groups, b_groups, observation, fold,
        observation_signal_chance=float(learner["observation_signal_chance"]),
        observation_signal_margin=float(learner["observation_signal_margin"]),
        observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),
        observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
        observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),
    )
    correction = corrections[0]
    if not correction.complete:
        return pd.DataFrame(), False, "observation_correction_unavailable"

    try:
        amap = fit_alignment_transport_map(
            background, b_groups, source_block=int(source_block), process=process,
            process_predictors=closure, conditioning_predictors=conditioning,
            degree=int(degree), ridge_alpha=float(ridge_alpha), minimum_complete_rows=int(minimum_source_rows),
        )
    except (ValueError, KeyError, np.linalg.LinAlgError):
        return pd.DataFrame(), False, "source_map_unavailable"

    p_train = presence.iloc[p_train_idx].reset_index(drop=True)
    b_train = background.iloc[b_train_idx].reset_index(drop=True)
    p_test = presence.iloc[p_test_idx].reset_index(drop=True)
    b_test = background.iloc[b_test_idx].reset_index(drop=True)
    p_train_k, b_train_k, p_test_k, b_test_k = (amap.transform(x) for x in (p_train, b_train, p_test, b_test))
    if not all(
        verify_transport_retained_predictors(a, b, ecological_predictors=ecological, process_predictors=closure)
        for a, b in ((p_train, p_train_k), (b_train, b_train_k), (p_test, p_test_k), (b_test, b_test_k))
    ):
        return pd.DataFrame(), False, "retained_predictor_violation"

    rows = []
    model_predictors = ecological + observation
    for spec in specs:
        row = {
            "excluded_process": process,
            "model_label": spec.label,
            "source_block": int(source_block),
            "target_block": int(target_block),
            "complete": False,
            "route_adequate": False,
            "baseline_adequate": False,
            "relative_evidence_state": INCOMPLETE_EVIDENCE,
        }
        try:
            base_model = fit_relative_suitability_model(p_train, b_train, model_predictors, model_spec=spec)
            route_model = fit_relative_suitability_model(p_train_k, b_train_k, model_predictors, model_spec=spec)
            base = _score(base_model, p_test, b_test, b_train, model_predictors, observation, correction, learner["density_probability_epsilon"])
            route = _score(route_model, p_test_k, b_test_k, b_train_k, model_predictors, observation, correction, learner["density_probability_epsilon"])
            if not all(np.isfinite(v) for v in (*base.values(), *route.values())):
                raise ValueError("non-finite transport evidence")
            b_ok = _adequate(base["presence_rank"], base["ecological_presence_rank"], learner)
            r_ok = _adequate(route["presence_rank"], route["ecological_presence_rank"], learner)
            deltas = {
                "prediction": route["presence_rank"] - base["presence_rank"],
                "ecological_rank": route["ecological_presence_rank"] - base["ecological_presence_rank"],
                "density": route["balanced_density_log_score"] - base["balanced_density_log_score"],
                "ecological_density": route["ecological_density_log_score"] - base["ecological_density_log_score"],
            }
            states = [
                interval_evidence_state(deltas["prediction"], 0.0, margin=float(learner["relative_noninferiority_margin"]), sem_multiplier=float(learner["relative_sem_multiplier"]), complete=True),
                interval_evidence_state(deltas["ecological_rank"], 0.0, margin=float(learner["relative_noninferiority_margin"]), sem_multiplier=float(learner["relative_sem_multiplier"]), complete=True),
                interval_evidence_state(deltas["density"], 0.0, margin=float(learner["density_noninferiority_margin"]), sem_multiplier=float(learner["density_sem_multiplier"]), complete=True),
                interval_evidence_state(deltas["ecological_density"], 0.0, margin=float(learner["density_noninferiority_margin"]), sem_multiplier=float(learner["density_sem_multiplier"]), complete=True),
            ]
            labels = tuple(str(x["state"]) for x in states)
            if all(x == NONINFERIOR_EVIDENCE for x in labels):
                relative_state = NONINFERIOR_EVIDENCE
            elif any(x == INFERIOR_EVIDENCE for x in labels):
                relative_state = INFERIOR_EVIDENCE
            elif INCOMPLETE_EVIDENCE in labels:
                relative_state = INCOMPLETE_EVIDENCE
            else:
                relative_state = INDETERMINATE_EVIDENCE
            row.update({
                "complete": True,
                "baseline_adequate": bool(b_ok),
                "route_adequate": bool(b_ok and r_ok),
                "relative_evidence_state": relative_state,
                "prediction_delta": float(deltas["prediction"]),
                "ecological_rank_delta": float(deltas["ecological_rank"]),
                "density_delta": float(deltas["density"]),
                "ecological_density_delta": float(deltas["ecological_density"]),
            })
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        rows.append(row)
    routes = pd.DataFrame(rows)
    pair_evaluable = bool(len(routes) == len(specs) and routes["complete"].astype(bool).all() and routes["route_adequate"].astype(bool).any())
    return routes, pair_evaluable, "ok" if pair_evaluable else "no_viable_route"


def _classify_cell(pair_frame: pd.DataFrame, minimum_pairs: int) -> str:
    evaluable = pair_frame.loc[pair_frame["evaluable"].astype(bool)] if len(pair_frame) else pair_frame
    n = int(len(evaluable))
    if n < int(minimum_pairs):
        return "insufficient"
    k = int(evaluable["reproduces_v8_noncontributory"].astype(bool).sum())
    if k == n:
        return "transported"
    if k == 0:
        return "local_alignment_only"
    return "heterogeneous"


def fit_family(family: str, output_dir: str | Path):
    cfg = _config(); dev, v6 = _load_v8(); manifest = _manifest()
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    focus = manifest.loc[manifest["family"].eq(str(family))].copy()
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pair_rows=[]; route_parts=[]; cell_rows=[]
    if focus.empty:
        pd.DataFrame(columns=["family","seed","target_process","source_block","target_block","evaluable","reproduces_v8_noncontributory","pair_status","reason"]).to_csv(out/"pair_summary.csv",index=False)
        pd.DataFrame(columns=["family","seed","target_process","source_block","target_block","model_label","complete","baseline_adequate","route_adequate","relative_evidence_state"]).to_csv(out/"route_summary.csv",index=False)
        pd.DataFrame(columns=["family","seed","target_process","v14_classification","n_evaluable_pairs","n_reproduced_pairs","classification"]).to_csv(out/"cell_summary.csv",index=False)
        return {"family":family,"n_focus_cells":0}

    sim=v6["simulation"]; learner=v6["learner"]
    ecological=tuple(v6["ecological_predictors"]); observation=tuple(v6["observation_predictors"])
    processes=tuple(v6["process_universe"]); registry=pd.DataFrame(v6["process_registry"])[["predictor","process","role"]]
    specs=_specs(v6)
    for item in focus.itertuples(index=False):
        seed=int(item.seed); process=str(item.target_process)
        simulation=simulate_known_truth_plant_niche(family,seed=seed,n_cells=int(sim["n_cells"]),n_occurrences=int(sim["n_occurrences"]),n_target_group=int(sim["n_target_group"]))
        occurrences,background=_selection_frames(simulation,family=family,seed=seed)
        split=freeze_occurrence_answer_check_split(occurrences,id_col="occurrence_id",lon_col="longitude",lat_col="latitude",n_blocks=int(sim["outer_n_blocks"]),holdout_fraction=float(sim["answer_check_fraction"]),random_state=int(sim["outer_random_state_offset"])+seed)
        presence=split.model_pool(occurrences)
        inner=make_spatial_partition(presence["longitude"].to_numpy(float),presence["latitude"].to_numpy(float),background["longitude"].to_numpy(float),background["latitude"].to_numpy(float),n_blocks=int(sim["inner_n_blocks"]),holdout_fraction=0.20,random_state=int(sim["inner_random_state_offset"])+seed)
        p_groups=np.asarray(inner.presence_blocks); b_groups=np.asarray(inner.background_blocks)
        target_blocks=sorted(set(p_groups.tolist()) & set(b_groups.tolist()))
        source_blocks=sorted(set(b_groups.tolist()))
        local_pairs=[]
        for target in target_blocks:
            for source in source_blocks:
                if int(source)==int(target):
                    continue
                routes,evaluable,reason=_pair_routes(
                    presence,background,p_groups,b_groups,process=process,source_block=int(source),target_block=int(target),
                    ecological=ecological,observation=observation,registry=registry,processes=processes,specs=specs,learner=learner,
                    degree=int(dev["knockout_degree"]),ridge_alpha=float(dev["knockout_ridge_alpha"]),minimum_source_rows=int(cfg["minimum_source_complete_rows"]),
                )
                if len(routes):
                    routes.insert(0,"target_process",process); routes.insert(0,"seed",seed); routes.insert(0,"family",family); route_parts.append(routes)
                pair_status="unresolved"
                reproduces=False
                if evaluable:
                    classified=_classify_interval_processes(routes,(process,),expected_model_labels=tuple(s.label for s in specs))
                    pair_status=str(classified.iloc[0]["status"])
                    reproduces=pair_status != CONTRIBUTORY
                rec={"family":family,"seed":seed,"target_process":process,"source_block":int(source),"target_block":int(target),"evaluable":bool(evaluable),"reproduces_v8_noncontributory":bool(reproduces),"pair_status":pair_status,"reason":reason}
                pair_rows.append(rec); local_pairs.append(rec)
        local=pd.DataFrame(local_pairs)
        classification=_classify_cell(local,int(cfg["minimum_distinct_source_target_pairs"]))
        eval_n=int(local["evaluable"].astype(bool).sum()) if len(local) else 0
        rep_n=int(local.loc[local["evaluable"].astype(bool),"reproduces_v8_noncontributory"].astype(bool).sum()) if len(local) else 0
        cell_rows.append({"family":family,"seed":seed,"target_process":process,"v14_classification":str(item.v14_classification),"n_evaluable_pairs":eval_n,"n_reproduced_pairs":rep_n,"classification":classification})

    pairs=pd.DataFrame(pair_rows); cells=pd.DataFrame(cell_rows)
    routes=pd.concat(route_parts,ignore_index=True) if route_parts else pd.DataFrame(columns=["family","seed","target_process","source_block","target_block","model_label","complete","baseline_adequate","route_adequate","relative_evidence_state"])
    pairs.to_csv(out/"pair_summary.csv",index=False); routes.to_csv(out/"route_summary.csv",index=False); cells.to_csv(out/"cell_summary.csv",index=False)
    return {"family":family,"n_focus_cells":int(len(cells)),"n_evaluable_pairs":int(pairs["evaluable"].astype(bool).sum()) if len(pairs) else 0}


def _read(path: Path):
    try:return pd.read_csv(path)
    except pd.errors.EmptyDataError:return pd.DataFrame()


def aggregate(input_dir: str|Path, output_dir: str|Path):
    root=Path(input_dir); expected=len(KNOWN_TRUTH_FAMILIES)
    names=["pair_summary.csv","route_summary.csv","cell_summary.csv"]
    files={n:list(root.rglob(n)) for n in names}
    if any(len(v)!=expected for v in files.values()):
        raise ValueError("v15 aggregate requires one artifact per family")
    merged={n:pd.concat([_read(p) for p in paths],ignore_index=True) for n,paths in files.items()}
    cells=merged["cell_summary.csv"]; manifest=_manifest()
    observed=cells[["family","seed","target_process","v14_classification"]].copy()
    observed["family"]=observed["family"].astype(str)
    observed["seed"]=pd.to_numeric(observed["seed"],errors="raise").astype(int)
    observed["target_process"]=observed["target_process"].astype(str)
    observed["v14_classification"]=observed["v14_classification"].astype(str)
    observed=observed.sort_values(["family","seed","target_process"]).reset_index(drop=True)
    manifest=manifest.copy()
    manifest["family"]=manifest["family"].astype(str)
    manifest["seed"]=pd.to_numeric(manifest["seed"],errors="raise").astype(int)
    manifest["target_process"]=manifest["target_process"].astype(str)
    manifest["v14_classification"]=manifest["v14_classification"].astype(str)
    manifest=manifest.sort_values(["family","seed","target_process"]).reset_index(drop=True)
    if not observed.equals(manifest):
        raise ValueError("v15 aggregate denominator does not equal frozen focus manifest")
    counts=cells["classification"].value_counts()
    result={
        "purpose":"alignment_transport_v15_consumed_development_decision",
        "development_only":True,
        "eligible_for_prospective_performance_claim":False,
        "n_focus_cells":9,
        "n_transported":int(counts.get("transported",0)),
        "n_local_alignment_only":int(counts.get("local_alignment_only",0)),
        "n_heterogeneous":int(counts.get("heterogeneous",0)),
        "n_insufficient":int(counts.get("insufficient",0)),
        "fresh_known_truth_validation_authorized":False,
        "fresh_empirical_validation_authorized":False,
    }
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    for n,f in merged.items(): f.to_csv(out/n,index=False)
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