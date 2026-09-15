"""Privileged truth-surface diagnostic on the exact consumed v23 contexts."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from .attribution_eligibility_v19_prospective import _base_objects, _frames
from .coalition_attribution_v23_development import PAIR_KEY, ROOT, load_manifest
from .known_truth_scenarios import simulate_known_truth_plant_niche
from .oracle_process_identifiability import _fit_predict_truth
from .process_information_closure import process_information_closure
from .validation import assign_spatial_blocks, make_spatial_partition

ROUTES = ("full", "drop_a", "drop_b", "drop_both")


def classify_oracle(frame):
    if frame.source_block.duplicated().any():
        raise ValueError("duplicate oracle source")
    complete = frame.loc[frame.complete]
    if not np.isfinite(complete[list(ROUTES)].to_numpy(float)).all():
        raise ValueError("nonfinite complete oracle evidence")
    result = {"n_sources": len(complete)}
    if len(complete) < 3:
        return {**result, "state": "oracle_unavailable"}

    def band(values):
        values = np.asarray(values, dtype=float)
        mean = float(values.mean())
        sem = float(values.std(ddof=1) / np.sqrt(len(values)))
        return {"mean": mean, "sem": sem, "lower": mean-sem, "upper": mean+sem}

    result["full_r2"] = band(complete.full)
    for route in ROUTES[1:]:
        loss = band(complete.full - complete[route])
        result[route] = {**loss, "effect": "supported" if loss["lower"] > .02 else
                         "bounded_small" if loss["upper"] <= .02 else "uncertain"}
    a, b, both = (result[r]["effect"] for r in ROUTES[1:])
    if result["full_r2"]["mean"] < .8:
        state = "oracle_unavailable"
    elif both != "supported":
        state = "joint_contribution_not_established"
    elif a == b == "supported":
        state = "joint_required"
    elif a == "supported" and b == "bounded_small":
        state = "a_specific"
    elif b == "supported" and a == "bounded_small":
        state = "b_specific"
    elif a == b == "bounded_small":
        state = "redundant_predictive_support"
    else:
        state = "joint_supported_attribution_uncertain"
    return {**result, "state": state}


def fit_family(family, manifest_path, output_dir):
    manifest = load_manifest(manifest_path)
    focus = manifest.loc[manifest.family == family, PAIR_KEY]
    _, _, sim, registry, eco, _, _, _ = _base_objects()
    records, evidence_rows = [], []
    for seed, seed_pairs in focus.groupby("seed", sort=True):
        presence, background, pg, bg = _frames(family, int(seed), sim)
        partition = make_spatial_partition(
            presence.longitude.to_numpy(), presence.latitude.to_numpy(),
            background.longitude.to_numpy(), background.latitude.to_numpy(),
            n_blocks=sim["inner_n_blocks"], holdout_fraction=.20,
            random_state=sim["inner_random_state_offset"] + int(seed),
        )
        if not np.array_equal(partition.presence_blocks, pg) or not np.array_equal(partition.background_blocks, bg):
            raise ValueError("v23 spatial partition drift")
        simulation = simulate_known_truth_plant_niche(family, seed=int(seed),
            n_cells=sim["n_cells"], n_occurrences=sim["n_occurrences"], n_target_group=sim["n_target_group"])
        environment = simulation.environment
        groups = assign_spatial_blocks(environment.longitude.to_numpy(), environment.latitude.to_numpy(), partition.centers_xyz)
        blocks = sorted(set(pg.tolist()) & set(bg.tolist()))
        cache = {}
        for item in seed_pairs.to_dict("records"):
            target = item["target_block"]
            a = set(process_information_closure(registry, item["process_a"]))
            b = set(process_information_closure(registry, item["process_b"]))
            if not a or not b or a & b:
                raise ValueError("invalid closures")
            routes = {"full": tuple(eco), "drop_a": tuple(x for x in eco if x not in a),
                      "drop_b": tuple(x for x in eco if x not in b),
                      "drop_both": tuple(x for x in eco if x not in a | b)}
            rows = []
            for source in blocks:
                if source == target:
                    continue
                row = {**item, "source_block": int(source), "complete": True, "reason": ""}
                train = environment.loc[(groups != target) & (groups != source)]
                test = environment.loc[groups == target]
                for route, predictors in routes.items():
                    key = (target, source, predictors)
                    if key not in cache:
                        try:
                            if len(test) < 2 or np.var(test.true_suitability) == 0:
                                raise ValueError("insufficient target truth variance")
                            pred = _fit_predict_truth(train, test, train.true_suitability.to_numpy(), predictors,
                                max_iter=200, max_leaf_nodes=31, min_samples_leaf=20,
                                learning_rate=.08, l2_regularization=.001)
                            value = float(r2_score(test.true_suitability, pred))
                            if not np.isfinite(value):
                                raise ValueError("nonfinite R2")
                            cache[key] = (value, "")
                        except (ValueError, KeyError, np.linalg.LinAlgError) as error:
                            cache[key] = (None, f"{type(error).__name__}: {error}")
                    value, reason = cache[key]
                    row[route] = value
                    if reason:
                        row["complete"] = False
                        row["reason"] += f"{route}:{reason};"
                rows.append(row)
            evidence_rows.extend(rows)
            records.append({**item, **classify_oracle(pd.DataFrame(rows))})
            print(f"{family}: {len(records)}/{len(focus)}", flush=True)
    out = Path(output_dir) / family
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(evidence_rows).to_csv(out / "oracle_evidence.csv", index=False)
    (out / "oracle_pairs.json").write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def aggregate(manifest_path, output_dir):
    manifest = load_manifest(manifest_path)
    out = Path(output_dir)
    records = []
    for family in sorted(manifest.family.unique()):
        records.extend(json.loads((out / family / "oracle_pairs.json").read_text(encoding="utf-8")))
    frame = pd.DataFrame(records)
    if frame.duplicated(PAIR_KEY).any() or set(frame[PAIR_KEY].itertuples(index=False, name=None)) != set(manifest[PAIR_KEY].itertuples(index=False, name=None)):
        raise ValueError("oracle denominator changed")
    frame.to_json(out / "frozen_oracle_states.json", orient="records", indent=2)
    occurrence = pd.read_csv(ROOT / "evidence/coalition_attribution_v23_2026-09-15/pair_states.csv")
    joined = occurrence.merge(frame, on=PAIR_KEY, suffixes=("_occurrence", "_oracle"), validate="one_to_one")
    if len(joined) != len(manifest):
        raise ValueError("crosswalk denominator changed")
    joined.to_json(out / "crosswalk.json", orient="records", indent=2)
    true = {"temperature", "water"}
    mixed = frame.loc[frame.process_a.isin(true) != frame.process_b.isin(true)]
    correct = sum((r.state == "a_specific" and r.process_a in true) or
                  (r.state == "b_specific" and r.process_b in true) for r in mixed.itertuples())
    result = {"purpose": "matched_context_truth_surface_diagnostic_v24", "n_pairs": len(frame),
              "oracle_state_counts": frame.state.value_counts().to_dict(), "mixed_pairs": len(mixed),
              "mixed_true_specific": correct, "fresh_validation_authorized": False,
              "crosswalk": pd.crosstab(joined.state_occurrence, joined.state_oracle).to_dict()}
    (out / "diagnostic_result.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest(args.pair_manifest)
    out = Path(args.output_dir)
    if not args.aggregate_only:
        out.mkdir(parents=True, exist_ok=False)
        receipt = {"implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "pair_manifest_sha256": hashlib.sha256(Path(args.pair_manifest).read_bytes()).hexdigest(),
                   "scope": "consumed_privileged_truth_diagnostic", "fresh_validation_authorized": False}
        (out / "execution_receipt.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(fit_family, family, args.pair_manifest, args.output_dir) for family in sorted(manifest.family.unique())]
            for future in futures:
                future.result()
    print(json.dumps(aggregate(args.pair_manifest, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
