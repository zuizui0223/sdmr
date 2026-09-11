"""Consumed-development evaluator for background-only context geometry v17."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .conditional_shared_knockout_v8_development import _load as _load_v8
from .context_geometry_v17 import context_geometry_features
from .context_indexed_attribution_v16_development import fit_family as fit_v16_family
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "context_geometry_v17_development.json"
FEATURES = (
    "conditional_residual_shift",
    "conditional_residual_scale_ratio",
    "conditional_target_r2",
    "process_support_shift",
    "conditioning_support_shift",
)


def _config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "context_geometry_v17_development_only":
        raise ValueError("wrong v17 contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v17 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001, 15011)):
        raise ValueError("v17 must remain on consumed seeds 15001-15010")
    if cfg.get("background_only_features") is not True or cfg.get("cell_disjoint_evaluation") is not True:
        raise ValueError("v17 background-only/cell-disjoint contract violated")
    return cfg


def fit_family(family: str, output_dir: str | Path):
    cfg = _config(); _, v6 = _load_v8()
    if family not in KNOWN_TRUTH_FAMILIES:
        raise ValueError("unknown family")
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    v16_dir = out / "v16"
    fit_v16_family(family, v16_dir)
    targets = pd.read_csv(v16_dir / "target_context_summary.csv")
    if targets.empty:
        pd.DataFrame(columns=["family","seed","target_process","target_block","context_status",*FEATURES]).to_csv(out/"context_geometry.csv", index=False)
        return {"family": family, "n_contexts": 0}

    simcfg=v6["simulation"]
    ecological=tuple(v6["ecological_predictors"])
    processes=tuple(v6["process_universe"])
    registry=pd.DataFrame(v6["process_registry"])[["predictor","process","role"]]
    rows=[]
    for (seed, process), group in targets.groupby(["seed","target_process"], sort=True):
        seed=int(seed); process=str(process)
        simulation=simulate_known_truth_plant_niche(family, seed=seed, n_cells=int(simcfg["n_cells"]), n_occurrences=int(simcfg["n_occurrences"]), n_target_group=int(simcfg["n_target_group"]))
        occurrences, background=_selection_frames(simulation, family=family, seed=seed)
        split=freeze_occurrence_answer_check_split(occurrences, id_col="occurrence_id", lon_col="longitude", lat_col="latitude", n_blocks=int(simcfg["outer_n_blocks"]), holdout_fraction=float(simcfg["answer_check_fraction"]), random_state=int(simcfg["outer_random_state_offset"])+seed)
        presence=split.model_pool(occurrences)
        inner=make_spatial_partition(presence["longitude"].to_numpy(float), presence["latitude"].to_numpy(float), background["longitude"].to_numpy(float), background["latitude"].to_numpy(float), n_blocks=int(simcfg["inner_n_blocks"]), holdout_fraction=0.20, random_state=int(simcfg["inner_random_state_offset"])+seed)
        b_groups=np.asarray(inner.background_blocks)
        closure=tuple(process_information_closure(registry, process))
        other=[tuple(process_information_closure(registry, q)) for q in processes if q != process]
        overlap=set(closure) & set(x for cols in other for x in cols)
        conditioning=tuple(dict.fromkeys(x for cols in other for x in cols if x not in set(closure)))
        if overlap or not conditioning:
            continue
        for item in group.itertuples(index=False):
            target=int(item.target_block)
            ref=background.loc[b_groups != target].reset_index(drop=True)
            tgt=background.loc[b_groups == target].reset_index(drop=True)
            geom=context_geometry_features(ref, tgt, process_predictors=closure, conditioning_predictors=conditioning)
            rows.append({
                "family":family,"seed":seed,"target_process":process,"target_block":target,"context_status":str(item.context_status),
                **{name:getattr(geom,name) for name in FEATURES},
            })
    frame=pd.DataFrame(rows)
    frame.to_csv(out/"context_geometry.csv", index=False)
    return {"family":family,"n_contexts":int(len(frame))}


def _evaluate(frame: pd.DataFrame, cfg: dict):
    classes=tuple(str(x) for x in cfg["supervised_classes"])
    data=frame.loc[frame["context_status"].astype(str).isin(classes)].copy()
    data=data.loc[np.isfinite(data.loc[:,FEATURES].to_numpy(float)).all(axis=1)].reset_index(drop=True)
    cells=data[["family","seed","target_process"]].astype(str).agg("|".join, axis=1)
    predictions=[]
    for cell in sorted(cells.unique()):
        test=cells.eq(cell).to_numpy(); train=~test
        y_train=data.loc[train,"context_status"].astype(str)
        y_test=data.loc[test,"context_status"].astype(str)
        if y_train.nunique() < 2 or len(y_test)==0:
            continue
        model=make_pipeline(StandardScaler(), LogisticRegression(C=float(cfg["classifier_C"]), max_iter=int(cfg["max_iter"]), penalty="l2"))
        model.fit(data.loc[train,FEATURES], y_train)
        pred=model.predict(data.loc[test,FEATURES])
        majority=y_train.value_counts().sort_values(ascending=False).index[0]
        for idx,p,m in zip(data.index[test], pred, [majority]*int(test.sum()), strict=True):
            predictions.append({"row_index":int(idx),"cell":cell,"truth":str(data.loc[idx,"context_status"]),"prediction":str(p),"majority_prediction":str(m)})
    pred=pd.DataFrame(predictions)
    if pred.empty:
        raise ValueError("no evaluable cell-disjoint predictions")
    labels=list(classes)
    macro=float(f1_score(pred.truth,pred.prediction,labels=labels,average="macro",zero_division=0))
    baseline=float(f1_score(pred.truth,pred.majority_prediction,labels=labels,average="macro",zero_division=0))
    clear=pred.loc[pred.truth.isin(["context_contributory","context_replaceable"])].copy()
    clear_f1=float(f1_score(clear.truth,clear.prediction,labels=["context_contributory","context_replaceable"],average="macro",zero_division=0)) if len(clear) else float("nan")
    clear_base=float(f1_score(clear.truth,clear.majority_prediction,labels=["context_contributory","context_replaceable"],average="macro",zero_division=0)) if len(clear) else float("nan")
    return pred,{"n_supervised_contexts":int(len(data)),"n_predicted_contexts":int(len(pred)),"macro_f1":macro,"majority_macro_f1":baseline,"macro_f1_gain":float(macro-baseline),"clear_state_macro_f1":clear_f1,"clear_state_majority_macro_f1":clear_base}


def aggregate(input_dir: str | Path, output_dir: str | Path):
    cfg=_config(); root=Path(input_dir)
    files=list(root.rglob("context_geometry.csv"))
    if len(files) != len(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v17 aggregate requires one artifact per family")
    parts=[]
    for path in files:
        try: parts.append(pd.read_csv(path))
        except pd.errors.EmptyDataError: pass
    frame=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    if len(frame) != 72:
        raise ValueError(f"v17 must preserve the frozen 72-context denominator; got {len(frame)}")
    pred,metrics=_evaluate(frame,cfg)
    result={"purpose":"context_geometry_v17_consumed_development_decision","development_only":True,"eligible_for_prospective_performance_claim":False,"n_contexts":72,**metrics,"fresh_known_truth_validation_authorized":False,"fresh_empirical_validation_authorized":False}
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/"context_geometry.csv",index=False); pred.to_csv(out/"cell_disjoint_predictions.csv",index=False)
    (out/"development_decision.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result


def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("fit-family"); f.add_argument("--family",required=True); f.add_argument("--output-dir",required=True)
    a=sub.add_parser("aggregate"); a.add_argument("--input-dir",required=True); a.add_argument("--output-dir",required=True)
    args=p.parse_args(argv)
    result=fit_family(args.family,args.output_dir) if args.cmd=="fit-family" else aggregate(args.input_dir,args.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__": main()
