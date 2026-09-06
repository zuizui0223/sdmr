"""Sharded executor for the fixed v4 changed-cell concordance diagnostic."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .density_ratio_concordance_diagnostic import (
    _changed_cells,
    _fit_case,
    _load_diagnostic_config,
)
from .density_ratio_process_challenge_development import _load as _load_v4


def _evaluate_selected(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dev, base = _load_v4()
    route_rows: list[pd.DataFrame] = []
    cell_rows: list[dict[str, object]] = []
    cache: dict[tuple[str, int], tuple[object, object]] = {}

    for item in selected.itertuples(index=False):
        key = (str(item.family), int(item.seed))
        if key not in cache:
            cache[key] = _fit_case(key[0], key[1], dev, base)
        fit, attributed = cache[key]
        process = str(item.process)
        fit_status = str(
            fit.process_summary.loc[fit.process_summary["process"].astype(str).eq(process), "status"].iloc[0]
        )
        v3_status = str(
            fit.v3_fit.process_summary.loc[
                fit.v3_fit.process_summary["process"].astype(str).eq(process), "status"
            ].iloc[0]
        )
        attribution_status = str(
            attributed.process_summary.loc[
                attributed.process_summary["process"].astype(str).eq(process), "attribution_status"
            ].iloc[0]
        )
        if fit_status != str(item.status) or v3_status != str(item.v3_status):
            raise ValueError("sharded rerun status does not reproduce fixed v4 artifact")

        group = fit.route_summary.loc[fit.route_summary["excluded_process"].astype(str).eq(process)].copy()
        if group.empty:
            raise ValueError("changed process has no v4 route evidence")
        group.insert(0, "expected_true_process", bool(item.expected_true_process))
        group.insert(0, "process", process)
        group.insert(0, "seed", int(item.seed))
        group.insert(0, "family", str(item.family))
        group["v3_process_status"] = v3_status
        group["v4_process_status"] = fit_status
        group["v4_attribution_status"] = attribution_status
        group["prediction_delta_negative"] = pd.to_numeric(
            group["mean_prediction_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["ecological_rank_delta_negative"] = pd.to_numeric(
            group["mean_ecological_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["density_delta_negative"] = pd.to_numeric(
            group["mean_density_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["ecological_density_delta_negative"] = pd.to_numeric(
            group["mean_ecological_density_delta_vs_baseline"], errors="coerce"
        ).lt(0.0)
        group["all_four_mean_deltas_negative"] = (
            group["prediction_delta_negative"]
            & group["ecological_rank_delta_negative"]
            & group["density_delta_negative"]
            & group["ecological_density_delta_negative"]
        )
        group["density_rejected_v3_witness"] = (
            group["relative_noninferior"].astype(bool)
            & ~group["multicriterion_noninferior"].astype(bool)
        )
        route_rows.append(group)

        rejected = group.loc[group["density_rejected_v3_witness"].astype(bool)].copy()
        cell_rows.append(
            {
                "family": str(item.family),
                "seed": int(item.seed),
                "process": process,
                "expected_true_process": bool(item.expected_true_process),
                "v3_process_status": v3_status,
                "v4_process_status": fit_status,
                "v4_attribution_status": attribution_status,
                "n_routes": int(len(group)),
                "n_v3_relative_noninferior_routes": int(group["relative_noninferior"].astype(bool).sum()),
                "n_density_rejected_v3_witness_routes": int(len(rejected)),
                "n_rejected_routes_all_four_mean_deltas_negative": int(
                    rejected["all_four_mean_deltas_negative"].astype(bool).sum()
                ),
                "all_rejected_routes_rank_direction_negative": bool(
                    len(rejected)
                    and (
                        rejected["prediction_delta_negative"].astype(bool)
                        & rejected["ecological_rank_delta_negative"].astype(bool)
                    ).all()
                ),
                "any_rejected_route_rank_direction_negative": bool(
                    len(rejected)
                    and (
                        rejected["prediction_delta_negative"].astype(bool)
                        & rejected["ecological_rank_delta_negative"].astype(bool)
                    ).any()
                ),
            }
        )
    return pd.concat(route_rows, ignore_index=True), pd.DataFrame(cell_rows)


def run_family(process_file: str | Path, family: str, output_dir: str | Path) -> dict[str, object]:
    cfg = _load_diagnostic_config()
    changed = _changed_cells(process_file, cfg)
    selected = changed.loc[changed["family"].astype(str).eq(str(family))].copy()
    if selected.empty:
        raise ValueError(f"family has no changed cells in fixed v4 artifact: {family}")
    routes, cells = _evaluate_selected(selected)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    routes.to_csv(out / "changed_cell_route_deltas.csv", index=False)
    cells.to_csv(out / "changed_cell_concordance_summary.csv", index=False)
    decision = {
        "purpose": "density_ratio_v4_changed_cell_concordance_family_shard",
        "family": str(family),
        "n_changed_cells": int(len(cells)),
        "development_only": True,
        "no_margin_retuning": True,
        "no_status_reclassification": True,
        "product_a_reopened": False,
    }
    (out / "concordance_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(decision, indent=2, sort_keys=True))
    return decision


def aggregate(input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    cfg = _load_diagnostic_config()
    root = Path(input_dir)
    cell_files = list(root.rglob("changed_cell_concordance_summary.csv"))
    route_files = list(root.rglob("changed_cell_route_deltas.csv"))
    if len(cell_files) != 5 or len(route_files) != 5:
        raise ValueError("concordance aggregate requires five changed-family shards")
    cells = pd.concat([pd.read_csv(path) for path in cell_files], ignore_index=True)
    routes = pd.concat([pd.read_csv(path) for path in route_files], ignore_index=True)
    expected_n = int(cfg["source"]["expected_changed_cells"])
    if len(cells) != expected_n:
        raise ValueError(f"concordance aggregate expected {expected_n} cells, found {len(cells)}")
    if cells[["family", "seed", "process"]].duplicated().any():
        raise ValueError("concordance aggregate contains duplicate changed cells")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cells = cells.sort_values(["family", "seed", "process"], kind="mergesort")
    routes = routes.sort_values(["family", "seed", "process", "model_label", "route"], kind="mergesort")
    cells.to_csv(out / "changed_cell_concordance_summary.csv", index=False)
    routes.to_csv(out / "changed_cell_route_deltas.csv", index=False)

    true = cells.loc[cells["expected_true_process"].astype(bool)]
    false = cells.loc[~cells["expected_true_process"].astype(bool)]
    decision = {
        "purpose": "density_ratio_v4_changed_cell_concordance_diagnostic",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "n_changed_cells": int(len(cells)),
        "n_true_changed_cells": int(len(true)),
        "n_false_changed_cells": int(len(false)),
        "true_cells_all_rejected_routes_rank_direction_negative": int(
            true["all_rejected_routes_rank_direction_negative"].astype(bool).sum()
        ),
        "false_cells_all_rejected_routes_rank_direction_negative": int(
            false["all_rejected_routes_rank_direction_negative"].astype(bool).sum()
        ),
        "true_cells_any_rejected_route_rank_direction_negative": int(
            true["any_rejected_route_rank_direction_negative"].astype(bool).sum()
        ),
        "false_cells_any_rejected_route_rank_direction_negative": int(
            false["any_rejected_route_rank_direction_negative"].astype(bool).sum()
        ),
        "no_margin_retuning": True,
        "no_status_reclassification": True,
        "product_a_reopened": False,
    }
    (out / "concordance_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(decision, indent=2, sort_keys=True))
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-file")
    parser.add_argument("--family")
    parser.add_argument("--input-dir")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.family:
        if not args.process_file or args.input_dir:
            raise ValueError("family shard requires --process-file and forbids --input-dir")
        run_family(args.process_file, args.family, args.output_dir)
    elif args.input_dir:
        if args.process_file:
            raise ValueError("aggregate mode forbids --process-file")
        aggregate(args.input_dir, args.output_dir)
    else:
        raise ValueError("choose --family or --input-dir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
