"""Frozen attribution-eligibility predictor for prospective v19 validation."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLASSIFIER = ROOT / "configs" / "attribution_eligibility_v19_classifier.json"
CONTRACT = ROOT / "configs" / "attribution_eligibility_v19_prospective.json"


def load_classifier() -> dict:
    cfg = json.loads(CLASSIFIER.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "attribution_eligibility_v19_frozen_classifier":
        raise ValueError("wrong v19 classifier")
    if float(cfg.get("decision_threshold")) != 0.5:
        raise ValueError("v19 threshold must remain 0.5")
    return cfg


def load_contract() -> dict:
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "attribution_eligibility_v19_prospective_known_truth_validation":
        raise ValueError("wrong v19 prospective contract")
    if tuple(int(x) for x in cfg.get("fresh_seed_denominator", ())) != tuple(range(16001, 16011)):
        raise ValueError("v19 fresh denominator changed")
    if tuple(cfg.get("target_processes", ())) != ("temperature", "water"):
        raise ValueError("v19 positive-process denominator changed")
    if tuple(cfg.get("negative_control_processes", ())) != ("seasonality", "noise"):
        raise ValueError("v19 negative controls changed")
    if cfg.get("target_selection_uses_outcomes") is not False:
        raise ValueError("v19 target selection must be outcome-blind")
    return cfg


def predict_eligibility(frame: pd.DataFrame) -> pd.DataFrame:
    cfg = load_classifier()
    features = tuple(str(x) for x in cfg["feature_order"])
    missing = [x for x in features if x not in frame.columns]
    if missing:
        raise KeyError(f"missing v19 features: {missing}")
    x = frame.loc[:, list(features)].to_numpy(float)
    mean = np.asarray(cfg["scaler_mean"], float)
    scale = np.asarray(cfg["scaler_scale"], float)
    coef = np.asarray(cfg["logistic_coef"], float)
    intercept = float(cfg["logistic_intercept"])
    if x.shape[1] != len(mean) or len(mean) != len(scale) or len(coef) != len(mean):
        raise ValueError("v19 frozen classifier dimensions do not match")
    finite = np.isfinite(x).all(axis=1)
    z = np.full(len(frame), np.nan, float)
    p = np.full(len(frame), np.nan, float)
    if finite.any():
        xs = (x[finite] - mean) / scale
        logits = intercept + xs @ coef
        z[finite] = logits
        p[finite] = 1.0 / (1.0 + np.exp(-np.clip(logits, -40.0, 40.0)))
    pred = np.where(np.isfinite(p) & (p >= float(cfg["decision_threshold"])), "eligible", "not_eligible")
    pred = np.where(np.isfinite(p), pred, "insufficient_geometry")
    out = frame.copy()
    out["eligibility_logit"] = z
    out["p_eligible"] = p
    out["eligibility_prediction"] = pred
    return out
