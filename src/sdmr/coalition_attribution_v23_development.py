"""Consumed-development runner: fixed v22 pairs, four symmetric model routes."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from importlib.metadata import version

import numpy as np
import pandas as pd

from .attribution_eligibility_v19_prospective import _base_objects, _frames
from .coalition_attribution_v23 import ROUTES, SCORE_COLUMNS, classify_pair
from .model import fit_relative_suitability_model
from .observation_aware_identification import _prepare_observation_corrections
from .process_information_closure import process_information_closure
from .relative_attribution_v22_development import _score

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/coalition_attribution_v23_development.json"
PAIR_KEY = ["family", "seed", "target_block", "process_a", "process_b"]


def load_contract():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg["purpose"] != "coalition_attribution_v23_consumed_development":
        raise ValueError("wrong contract")
    if cfg["seeds"] != list(range(17001, 17011)):
        raise ValueError("consumed seeds changed")
    if any(cfg[k] for k in ("fresh_validation_authorized", "empirical_validation_authorized", "product_b_unblocked")):
        raise ValueError("development contract cannot authorize validation")
    return cfg


def load_manifest(path):
    cfg = load_contract()
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != cfg["pair_manifest_sha256"]:
        raise ValueError("pair manifest hash changed")
    frame = pd.read_csv(path)
    if len(frame) != cfg["expected_pairs"] or frame.duplicated(PAIR_KEY).any():
        raise ValueError("pair denominator changed")
    if len(frame[PAIR_KEY[:3]].drop_duplicates()) != cfg["expected_contexts"]:
        raise ValueError("context denominator changed")
    return frame


def evaluate_pair(item: dict, *, fit_model=None, model_specs=None, score_model=None):
    cfg = load_contract()
    _, v6, sim, registry, eco, obs, _, specs = _base_objects()
    if model_specs is not None:
        specs = tuple(model_specs)
    fitter = fit_relative_suitability_model if fit_model is None else fit_model
    scorer = _score if score_model is None else score_model
    family, seed, target, a, b = (item[k] for k in PAIR_KEY)
    if family not in cfg["families"] or seed not in cfg["seeds"]:
        raise ValueError("pair outside consumed development")
    if a == b or a not in cfg["processes"] or b not in cfg["processes"]:
        raise ValueError("invalid process pair")
    learner = v6["learner"]
    presence, background, pg, bg = _frames(family, int(seed), sim)
    blocks = sorted(set(pg.tolist()) & set(bg.tolist()))
    if target not in blocks:
        raise ValueError("target context missing")
    closure_a = set(process_information_closure(registry, a))
    closure_b = set(process_information_closure(registry, b))
    if not closure_a or not closure_b or closure_a & closure_b:
        raise ValueError("invalid or overlapping closures")
    removed = {"full": set(), "drop_a": closure_a, "drop_b": closure_b,
               "drop_both": closure_a | closure_b}
    predictors = {route: tuple(p for p in eco if p not in remove) + tuple(obs)
                  for route, remove in removed.items()}
    p_test = np.flatnonzero(pg == target)
    b_test = np.flatnonzero(bg == target)
    rows = []
    for source in blocks:
        if source == target:
            continue
        p_train = np.flatnonzero((pg != target) & (pg != source))
        b_train = np.flatnonzero((bg != target) & (bg != source))
        folds = ((p_train, b_train, p_test, b_test),)
        correction = _prepare_observation_corrections(
            presence, background, pg, bg, tuple(obs), folds,
            **{k: learner[k] for k in (
                "observation_signal_chance", "observation_signal_margin", "observation_signal_sem_multiplier",
                "observation_weight_truncation_quantile", "observation_weight_probability_epsilon")},
        )[0]
        ptr, btr = presence.iloc[p_train].reset_index(drop=True), background.iloc[b_train].reset_index(drop=True)
        pte, bte = presence.iloc[p_test].reset_index(drop=True), background.iloc[b_test].reset_index(drop=True)
        for spec in specs:
            row = {**item, "source_block": int(source), "model_label": spec.label,
                   "complete": False, "failure_reason": "", **{c: np.nan for c in SCORE_COLUMNS}}
            try:
                if not correction.complete or min(len(ptr), len(btr), len(pte), len(bte)) < 2:
                    raise ValueError("insufficient observation correction or rows")
                for route in ROUTES:
                    model = fitter(ptr, btr, predictors[route], model_spec=spec)
                    score = scorer(model, pte, bte, btr, predictors[route], tuple(obs), correction,
                                   learner["density_probability_epsilon"])
                    row.update({f"{route}_{k}": v for k, v in score.items()})
                if not all(np.isfinite(row[c]) for c in SCORE_COLUMNS):
                    raise ValueError("nonfinite score")
                row["complete"] = True
            except (ValueError, KeyError, np.linalg.LinAlgError) as error:
                row["failure_reason"] = f"{type(error).__name__}: {error}"
            rows.append(row)
    evidence = pd.DataFrame(rows)
    result = classify_pair(
        evidence, model_labels=[s.label for s in specs], minimum_sources=cfg["minimum_source_perturbations"],
        rank_margin=cfg["rank_margin"], density_margin=cfg["density_margin"],
        chance=cfg["chance_score"], adequacy_margin=cfg["adequacy_margin"],
    )
    return evidence, {**item, **result}


def fit_family(family, manifest_path, output_dir):
    manifest = load_manifest(manifest_path)
    focus = manifest.loc[manifest.family == family, PAIR_KEY]
    if focus.empty:
        raise ValueError("family has no frozen pairs")
    out = Path(output_dir) / family
    out.mkdir(parents=True, exist_ok=True)
    if (out / "pair_results.json").exists():
        raise ValueError("refusing to overwrite completed family")
    results, frames = [], []
    for i, item in enumerate(focus.to_dict("records"), 1):
        evidence, result = evaluate_pair(item)
        frames.append(evidence)
        results.append(result)
        print(f"{family}: {i}/{len(focus)} {result['state']}", flush=True)
    pd.concat(frames, ignore_index=True).to_csv(out / "model_evidence.csv", index=False)
    (out / "pair_results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return family


def aggregate(manifest_path, output_dir, *, purpose="coalition_attribution_v23_consumed_development_result"):
    cfg = load_contract()
    manifest = load_manifest(manifest_path)
    out = Path(output_dir)
    rows = []
    hashes = {}
    for family in cfg["families"]:
        path = out / family / "pair_results.json"
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
        hashes[family] = hashlib.sha256(path.read_bytes()).hexdigest()
    actual = pd.DataFrame(rows)
    if actual.duplicated(PAIR_KEY).any() or set(actual[PAIR_KEY].itertuples(index=False, name=None)) != set(manifest[PAIR_KEY].itertuples(index=False, name=None)):
        raise ValueError("aggregate pair denominator mismatch")
    # Persist truth-blind pair states before the consumed known-truth readout.
    actual.to_json(out / "frozen_pair_states.json", orient="records", indent=2)
    true = {"temperature", "water"}
    mixed = actual.loc[actual.process_a.isin(true) != actual.process_b.isin(true)]
    specific = actual.loc[actual.state.isin(["a_specific", "b_specific"])]
    correct = sum((r.process_a if r.state == "a_specific" else r.process_b) in true
                  for r in specific.itertuples(index=False))
    mixed_correct = sum((r.state == "a_specific" and r.process_a in true) or
                        (r.state == "b_specific" and r.process_b in true)
                        for r in mixed.itertuples(index=False))
    mixed_wrong = sum((r.state == "a_specific" and r.process_a not in true) or
                      (r.state == "b_specific" and r.process_b not in true) or r.state == "joint_required"
                      for r in mixed.itertuples(index=False))
    result = {
        "purpose": purpose,
        "n_pairs": len(actual), "state_counts": actual.state.value_counts().to_dict(),
        "specific_calls": len(specific), "specific_calls_on_generating_true_process": correct,
        "specific_precision": correct / len(specific) if len(specific) else None,
        "mixed_pairs": len(mixed), "mixed_true_specific": mixed_correct,
        "mixed_false_inclusion": mixed_wrong,
        "mixed_true_specific_rate": mixed_correct / len(mixed) if len(mixed) else None,
        "mixed_false_inclusion_rate": mixed_wrong / len(mixed) if len(mixed) else None,
        "input_family_sha256": hashes,
        "fresh_validation_authorized": False, "empirical_validation_authorized": False,
    }
    screen = cfg["development_screen"]
    result["development_screen_passed"] = bool(
        len(specific) and len(mixed)
        and result["specific_precision"] >= screen["specific_precision_min"]
        and result["mixed_true_specific_rate"] >= screen["mixed_true_specific_rate_min"]
        and result["mixed_false_inclusion_rate"] <= screen["mixed_false_inclusion_rate_max"]
    )
    (out / "development_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args()
    cfg = load_contract()
    if not args.aggregate_only:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        receipt_path = out / "execution_receipt.json"
        if receipt_path.exists():
            raise ValueError("refusing to overwrite an existing execution")
        receipt = {
            "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
            "python": platform.python_version(),
            "dependencies": {p: version(p) for p in ("numpy", "pandas", "scikit-learn")},
            "scope": "consumed_development_only",
        }
        load_manifest(args.pair_manifest)
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(fit_family, family, args.pair_manifest, args.output_dir) for family in cfg["families"]]
            for future in futures:
                future.result()
    print(json.dumps(aggregate(args.pair_manifest, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
