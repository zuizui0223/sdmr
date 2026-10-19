"""Reproducible controlled worlds for geographic_driver_turnover_v0.

World A: one conserved quadratic environmental response with geographically
opposite environmental availability; a *ranking reversal* can still emerge.
World B: a region-dependent response with overlapping climatic variation.
Both are SIMULATIONS, not observed plant ecology.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from geographic_driver_turnover_v0 import analyze_taxon


def generate_world(kind: str, seed: int = 52) -> pd.DataFrame:
    if kind not in {"constant_surface", "region_shifted_surface"}:
        raise ValueError("kind must be constant_surface or region_shifted_surface")
    rng = np.random.default_rng(seed)
    rows = []
    regions = ("alpine", "arid")
    cells_per_block = 30 if kind == "constant_surface" else 20
    for region in regions:
        for block in range(6):
            for i in range(cells_per_block):
                if kind == "constant_surface":
                    # Availability changes which part of ONE global response is seen.
                    if region == "alpine":
                        t, w = rng.normal(.45, .9), rng.normal(.1, .15)
                    else:
                        t, w = rng.normal(.1, .15), rng.normal(.45, .9)
                    score = -1.0 * (t - .1)**2 - 1.0 * (w - .1)**2
                else:
                    t, w = rng.normal(size=2)
                    if region == "alpine":
                        t -= .8
                        w += .4
                    else:
                        t += .8
                        w -= .4
                    # A true *statistical* environmental-response difference,
                    # not demonstrated physiological evolution.
                    score = 1.6 * t if region == "alpine" else 1.6 * w
                effort = np.exp(rng.normal(scale=.3 if kind == "constant_surface" else .4) + .2*t)
                rows.append(("simulated_taxon", region, f"{region}_{block}_{i}",
                             str(block), t, w, effort, score))
    df = pd.DataFrame(rows, columns=["taxon", "region", "cell_id", "spatial_block",
                                      "temperature", "moisture", "effort", "score"])
    df["n_occ"] = 0
    for _, subset in df.groupby("region", sort=True):
        logits = np.log(subset.effort.to_numpy()) + subset.score.to_numpy()
        prob = np.exp(logits - logits.max()); prob /= prob.sum()
        df.loc[subset.index, "n_occ"] = rng.multinomial(500 if kind == "constant_surface" else 420, prob)
    return df.drop(columns="score")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--replicates", type=int, default=99)
    parser.add_argument("--seed", type=int, default=52)
    args = parser.parse_args()
    results = {}
    for name in ("constant_surface", "region_shifted_surface"):
        df = generate_world(name, seed=args.seed)
        results[name] = analyze_taxon(df, replicates=args.replicates, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"evidence": "synthetic_only", "worlds": results},
                                      indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for kind, v in results.items():
        print(kind, v["observed"], "null_flip_rate=", v["null_direction_reversal_rate"],
              "p=", v["one_sided_bootstrap_p"])


if __name__ == "__main__":
    main()
