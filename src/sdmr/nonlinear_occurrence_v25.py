"""Consumed v25 candidate: nonlinear occurrence learner, unchanged v23 gates."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from .coalition_attribution_v23_development import CONFIG, PAIR_KEY, ROOT, aggregate, evaluate_pair, load_manifest
from .coalition_attribution_v23_verification import verify


@dataclass(frozen=True)
class NonlinearSpec:
    label: str = "hgb_200_leaf31_min20_lr008_l2001_seed0"


def fit_occurrence_model(presence, background, predictors, *, model_spec):
    if model_spec != NonlinearSpec():
        raise ValueError("unfrozen v25 learner")
    # Explicit predictor selection excludes every hidden simulator target.
    columns = list(predictors)
    forbidden = {"true_suitability", "sampling_effort", "focal_recording_multiplier", "scenario"}
    if forbidden.intersection(columns):
        raise ValueError("hidden truth cannot enter occurrence learner")
    p = presence[columns].dropna().to_numpy(float)
    b = background[columns].dropna().to_numpy(float)
    if min(len(p), len(b)) < 2 or not np.isfinite(p).all() or not np.isfinite(b).all():
        raise ValueError("insufficient finite occurrence/background rows")
    model = HistGradientBoostingClassifier(
        loss="log_loss", learning_rate=.08, max_iter=200, max_leaf_nodes=31,
        min_samples_leaf=20, l2_regularization=.001, class_weight="balanced",
        early_stopping=False, random_state=0,
    )
    model.fit(np.vstack((p,b)), np.r_[np.ones(len(p), dtype=int), np.zeros(len(b), dtype=int)])
    return model


def fit_family(family, manifest_path, output_dir):
    manifest = load_manifest(manifest_path)
    pairs = manifest.loc[manifest.family == family, PAIR_KEY]
    rows, results = [], []
    for index, item in enumerate(pairs.to_dict("records"), 1):
        evidence, result = evaluate_pair(item, fit_model=fit_occurrence_model, model_specs=[NonlinearSpec()])
        rows.append(evidence)
        results.append(result)
        print(f"{family}: {index}/{len(pairs)}", flush=True)
    out = Path(output_dir) / family
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(rows, ignore_index=True).to_csv(out / "model_evidence.csv", index=False)
    (out / "pair_results.json").write_text(json.dumps(results, indent=2, sort_keys=True)+"\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        print(json.dumps(verify(args.pair_manifest, args.output_dir, model_labels=[NonlinearSpec().label]), indent=2))
        return
    manifest = load_manifest(args.pair_manifest)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    receipt = {
        "purpose": "nonlinear_occurrence_v25_consumed_execution",
        "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "learner": NonlinearSpec().label,
        "python": platform.python_version(),
        "dependencies": {p: version(p) for p in ("numpy", "pandas", "scikit-learn")},
        "fresh_validation_authorized": False,
    }
    (out / "execution_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fit_family, family, args.pair_manifest, args.output_dir) for family in sorted(manifest.family.unique())]
        for future in futures:
            future.result()
    print(json.dumps(aggregate(args.pair_manifest, args.output_dir,
        purpose="nonlinear_occurrence_v25_consumed_development_result"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
