"""Consumed-development attribution eligibility gate v18."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .context_geometry_v17_development import FEATURES, fit_family as fit_v17_family
from .context_geometry_v17_aggregate import _normalized_keys
from .context_geometry_v17_development import _target_manifest
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "attribution_eligibility_v18_development.json"


def _config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "attribution_eligibility_v18_development_only":
        raise ValueError("wrong v18 contract")
    if cfg.get("development_only") is not True or cfg.get("eligible_for_prospective_performance_claim") is not False:
        raise ValueError("v18 must remain development-only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(15001,15011)):
        raise ValueError("v18 must remain on consumed seeds 15001-15010")
    if cfg.get("cell_disjoint_evaluation") is not True:
        raise ValueError("v18 must remain cell-disjoint")
    if float(cfg.get("decision_threshold")) != 0.5:
        raise ValueError("v18 decision threshold is frozen at 0.5")
    return cfg


def fit_family(family: str, output_dir: str | Path):
    return fit_v17_family(family, output_dir)


def _binary_label(status: str, cfg: dict) -> str | None:
    status = str(status)
    if status == str(cfg["positive_status"]):
        return "eligible"
    if status in {str(x) for x in cfg["negative_statuses"]}:
        return "not_eligible"
    return None


def _evaluate(frame: pd.DataFrame, cfg: dict):
    data = frame.copy()
    data["eligibility"] = [_binary_label(x, cfg) for x in data["context_status"]]
    data = data.loc[data["eligibility"].notna()].copy()
    data = data.loc[np.isfinite(data.loc[:, FEATURES].to_numpy(float)).all(axis=1)].reset_index(drop=True)
    cells = data[["family","seed","target_process"]].astype(str).agg("|".join, axis=1)
    predictions=[]
    for cell in sorted(cells.unique()):
        test = cells.eq(cell).to_numpy(); train = ~test
        y_train = data.loc[train,"eligibility"].astype(str)
        if y_train.nunique() < 2 or not test.any():
            continue
        model = make_pipeline(StandardScaler(), LogisticRegression(C=float(cfg["classifier_C"]), max_iter=int(cfg["max_iter"]), penalty="l2"))
        model.fit(data.loc[train, FEATURES], y_train)
        probs = model.predict_proba(data.loc[test, FEATURES])
        classes = list(model[-1].classes_)
        p_eligible = probs[:, classes.index("eligible")]
        pred = np.where(p_eligible >= float(cfg["decision_threshold"]), "eligible", "not_eligible")
        majority = y_train.value_counts().sort_values(ascending=False).index[0]
        for idx,p,pe in zip(data.index[test], pred, p_eligible, strict=True):
            predictions.append({
                "row_index": int(idx),
                "cell": cell,
                "truth": str(data.loc[idx,"eligibility"]),
                "prediction": str(p),
                "p_eligible": float(pe),
                "majority_prediction": str(majority),
            })
    pred = pd.DataFrame(predictions)
    if pred.empty:
        raise ValueError("no evaluable v18 predictions")
    labels=["eligible","not_eligible"]
    macro=float(f1_score(pred.truth,pred.prediction,labels=labels,average="macro",zero_division=0))
    baseline=float(f1_score(pred.truth,pred.majority_prediction,labels=labels,average="macro",zero_division=0))
    eligible_precision=float(precision_score(pred.truth,pred.prediction,pos_label="eligible",zero_division=0))
    eligible_recall=float(recall_score(pred.truth,pred.prediction,pos_label="eligible",zero_division=0))
    return pred, {
        "n_supervised_contexts": int(len(data)),
        "n_predicted_contexts": int(len(pred)),
        "macro_f1": macro,
        "majority_macro_f1": baseline,
        "macro_f1_gain": float(macro-baseline),
        "eligible_precision": eligible_precision,
        "eligible_recall": eligible_recall,
    }


def aggregate(input_dir: str | Path, output_dir: str | Path):
    cfg=_config(); root=Path(input_dir)
    files=list(root.rglob("context_geometry.csv"))
    if len(files) != len(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v18 aggregate requires one artifact per family")
    parts=[]
    for path in files:
        try: parts.append(pd.read_csv(path))
        except pd.errors.EmptyDataError: pass
    frame=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    if len(frame) != 72:
        raise ValueError(f"v18 must preserve 72 contexts; got {len(frame)}")
    if _normalized_keys(frame) != _normalized_keys(_target_manifest()):
        raise ValueError("v18 denominator differs from frozen v17/v16 manifest")
    pred,metrics=_evaluate(frame,cfg)
    result={
        "purpose":"attribution_eligibility_v18_consumed_development_decision",
        "development_only":True,
        "eligible_for_prospective_performance_claim":False,
        "n_contexts":72,
        **metrics,
        "fresh_known_truth_validation_authorized":False,
        "fresh_empirical_validation_authorized":False,
    }
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    pred.to_csv(out/"cell_disjoint_predictions.csv",index=False)
    (out/"development_decision.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result


def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("fit-family"); f.add_argument("--family",required=True); f.add_argument("--output-dir",required=True)
    a=sub.add_parser("aggregate"); a.add_argument("--input-dir",required=True); a.add_argument("--output-dir",required=True)
    args=p.parse_args(argv)
    result=fit_family(args.family,args.output_dir) if args.cmd=="fit-family" else aggregate(args.input_dir,args.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
