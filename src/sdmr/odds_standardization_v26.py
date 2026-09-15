"""Training-reference odds standardization for consumed v26 development."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd

from .coalition_attribution_v23_development import CONFIG, PAIR_KEY, ROOT, aggregate, evaluate_pair, load_manifest
from .coalition_attribution_v23_verification import verify
from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .model import score_relative_suitability
from .nonlinear_occurrence_v25 import NonlinearSpec, fit_occurrence_model
from .observation_aware_identification import _weighted_presence_rank
from .proxy_closed_route_process_challenge import _presence_rank


def standardized_probabilities(model, evaluation, reference, predictors, observation=(), *, epsilon=1e-6, max_reference_rows=64):
    """Standardize odds over reference observation covariates, then normalize.

    The reference is training background only. All its ecological rows define
    the density-ratio normalizer; up to 64 deterministic observation combinations
    define the marginalization, as in the inherited probability-based method.
    No evaluation rows enter the normalizer.
    """
    columns = list(predictors)
    observation = tuple(observation)
    if not columns or len(set(columns)) != len(columns) or not set(observation).issubset(columns):
        raise ValueError("invalid predictor/observation roles")
    if not 0 < epsilon < .5 or max_reference_rows < 1 or reference.empty:
        raise ValueError("invalid reference or standardization settings")
    ecological = [c for c in columns if c not in observation]
    eval_values = evaluation.reindex(columns=columns).to_numpy(float)
    ref_values = reference.loc[:, columns].to_numpy(float)
    ecological_indices = [columns.index(c) for c in ecological]
    if not np.isfinite(eval_values[:, ecological_indices]).all() or not np.isfinite(ref_values).all():
        raise ValueError("nonfinite standardization input")
    values = np.vstack((eval_values, ref_values))
    if observation:
        indices = np.unique(np.rint(np.linspace(0, len(reference)-1, min(max_reference_rows, len(reference)))).astype(int))
    else:
        indices = [0]
    total = np.zeros(len(values))
    for index in indices:
        for col in observation:
            j = columns.index(col)
            values[:, j] = ref_values[index, j]
        probability = model.predict_proba(values)[:, 1]
        if not np.isfinite(probability).all():
            raise ValueError("nonfinite model prediction")
        probability = np.clip(probability, epsilon, 1-epsilon)
        total += probability / (1-probability)
    odds = total / len(indices)
    normalizer = float(odds[len(evaluation):].mean())
    if not np.isfinite(normalizer) or normalizer <= 0:
        raise ValueError("invalid odds normalizer")
    standardized = odds[:len(evaluation)] / normalizer
    return standardized / (1 + standardized)


def score_routes(model, presence, background, reference, predictors, observation, correction, epsilon):
    p_full = score_relative_suitability(model, presence, predictors)
    b_full = score_relative_suitability(model, background, predictors)
    combined = pd.concat([presence, background], ignore_index=True)
    ecological = standardized_probabilities(model, combined, reference, predictors, observation, epsilon=epsilon)
    p_eco, b_eco = ecological[:len(presence)], ecological[len(presence):]
    return {
        "prediction_rank": float(_presence_rank(p_full, b_full)),
        "ecological_rank": float(_weighted_presence_rank(p_eco, b_eco, correction.weights)),
        "ecological_density": float(balanced_density_ratio_log_score(p_eco, b_eco,
            presence_weights=correction.weights, probability_epsilon=epsilon)),
    }


def fit_pair(item):
    return evaluate_pair(item, fit_model=fit_occurrence_model, model_specs=[NonlinearSpec()], score_model=score_routes)


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
        "purpose": "odds_standardization_v26_consumed_execution",
        "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "learner": NonlinearSpec().label, "python": platform.python_version(),
        "dependencies": {p: version(p) for p in ("numpy", "pandas", "scikit-learn")},
        "normalization_reference": "all_training_background_ecological_rows",
        "observation_reference_max_rows": 64, "fresh_validation_authorized": False,
    }
    (out / "execution_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    results, frames = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fit_pair, item) for item in manifest[PAIR_KEY].to_dict("records")]
        for future in as_completed(futures):
            evidence, result = future.result()
            frames.append(evidence)
            results.append(result)
            print(f"completed {len(results)}/{len(manifest)}", flush=True)
    all_evidence = pd.concat(frames, ignore_index=True)
    for family in sorted(manifest.family.unique()):
        folder = out / family
        folder.mkdir()
        all_evidence.loc[all_evidence.family == family].sort_values(PAIR_KEY+["source_block","model_label"]).to_csv(folder/"model_evidence.csv", index=False)
        rows = sorted([r for r in results if r["family"] == family], key=lambda r: tuple(r[k] for k in PAIR_KEY))
        (folder/"pair_results.json").write_text(json.dumps(rows, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(aggregate(args.pair_manifest, args.output_dir,
        purpose="odds_standardization_v26_consumed_development_result"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
