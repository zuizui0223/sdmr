"""Aggregate independently rebuilt leakage-safe Product-A stability parts."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _read_choice(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _component_stability(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(runs)
    for column, label in (
        ("winning_universe", "universe"),
        ("winning_strategy", "strategy"),
    ):
        counts = runs.groupby(column, as_index=False).size().rename(columns={column: "value", "size": "runs_selected"})
        counts["component"] = label
        counts["n_runs"] = total
        counts["selection_fraction"] = counts["runs_selected"] / float(total)
        rows.append(counts[["component", "value", "runs_selected", "n_runs", "selection_fraction"]])
    return pd.concat(rows, ignore_index=True).sort_values(
        ["component", "selection_fraction", "value"],
        ascending=[True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _delta_summary(deltas: pd.DataFrame) -> pd.DataFrame:
    if not len(deltas):
        return pd.DataFrame(
            columns=[
                "comparator",
                "n_pairs",
                "n_runs",
                "mean_delta_presence_rank",
                "median_delta_presence_rank",
                "positive_fraction",
            ]
        )
    return (
        deltas.groupby("comparator", as_index=False)
        .agg(
            n_pairs=("delta_presence_rank", "size"),
            n_runs=("run_id", "nunique"),
            mean_delta_presence_rank=("delta_presence_rank", "mean"),
            median_delta_presence_rank=("delta_presence_rank", "median"),
            positive_fraction=("delta_presence_rank", lambda x: float((x > 0).mean())),
        )
        .sort_values("mean_delta_presence_rank", ascending=False, kind="mergesort")
        .reset_index(drop=True)
    )


def aggregate_leakage_safe_stability(parts_root: Path, output_dir: Path) -> None:
    """Combine 15 frozen full reruns without optimizing M or reselecting models."""
    part_dirs = sorted({p.parent for p in Path(parts_root).rglob("part_metadata.json")})
    if not part_dirs:
        raise ValueError(f"No stability parts found under {parts_root}")

    run_rows: list[dict[str, object]] = []
    selected_frames: list[pd.DataFrame] = []
    delta_frames: list[pd.DataFrame] = []
    expected_occurrence_sha: str | None = None
    expected_feature_sha: str | None = None

    for run_id, part in enumerate(part_dirs):
        metadata = json.loads((part / "part_metadata.json").read_text(encoding="utf-8"))
        choice_path = part / "product_a_protocol_choice.txt"
        spec_path = part / "pilot_grid_specification.json"
        discovery_summary_path = part / "protocol_discovery_summary.csv"
        if not choice_path.exists() or not spec_path.exists() or not discovery_summary_path.exists():
            raise ValueError(f"Incomplete stability part: {part}")
        if metadata.get("M_background_rebuilt_from_model_pool") is not True:
            raise ValueError(f"Part did not rebuild M/background from its model pool: {part}")
        choice = _read_choice(choice_path)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if spec.get("outer_sealed_before_M") is not True:
            raise ValueError(f"Part was not sealed before M/background construction: {part}")
        if spec.get("m_grid_as_sensitivity") is not True:
            raise ValueError(f"Part optimized M instead of treating it as a sensitivity axis: {part}")
        if float(spec.get("focal_thin_cell_size_degrees", 0) or 0) <= 0:
            raise ValueError(f"Part lacks a declared focal thinning grid: {part}")

        occurrence_sha = str(choice.get("occurrence_sha256", ""))
        feature_sha = str(choice.get("occurrence_feature_sha256", ""))
        if not occurrence_sha or not feature_sha:
            raise ValueError(f"Part lacks occurrence/feature fingerprints: {part}")
        if expected_occurrence_sha is None:
            expected_occurrence_sha = occurrence_sha
            expected_feature_sha = feature_sha
        elif occurrence_sha != expected_occurrence_sha or feature_sha != expected_feature_sha:
            raise ValueError(
                "The prediction-target occurrence identities/features changed across stability parts. "
                "Outer roles may change, but thinned occurrence evidence and CHELSA values must not."
            )

        discovery_summary = pd.read_csv(discovery_summary_path)
        if "spec_win_fraction" not in discovery_summary:
            raise ValueError(f"Part lacks M-sensitivity robustness statistics: {part}")
        chosen = discovery_summary.loc[
            (discovery_summary["universe"].astype(str) == str(choice["winning_universe"]))
            & (discovery_summary["strategy"].astype(str) == str(choice["winning_strategy"]))
        ]
        if len(chosen) != 1:
            raise ValueError(f"Could not uniquely recover chosen method robustness for {part}")
        m_spec_win_fraction = float(chosen.iloc[0]["spec_win_fraction"])

        discovery_species = [x for x in choice.get("discovery_species", "").split(",") if x]
        validation_species = [x for x in choice.get("validation_species", "").split(",") if x]
        predictors = [x for x in choice.get("winning_predictors", "").split(",") if x]
        row = {
            "run_id": run_id,
            "seed": int(metadata["seed"]),
            "sealed_fraction": float(metadata["sealed_fraction"]),
            "taxon_validation_fraction": float(metadata["taxon_validation_fraction"]),
            "winning_data_specification": choice["winning_data_specification"],
            "winning_universe": choice["winning_universe"],
            "winning_strategy": choice["winning_strategy"],
            "winning_universe_sha256": choice["winning_universe_sha256"],
            "m_spec_win_fraction": m_spec_win_fraction,
            "n_winning_predictors": len(predictors),
            "winning_predictors": choice.get("winning_predictors", ""),
            "occurrence_sha256": occurrence_sha,
            "occurrence_feature_sha256": feature_sha,
            "n_discovery_species": len(discovery_species),
            "n_validation_species": len(validation_species),
        }
        run_rows.append(row)

        validation_path = part / "protocol_validation_metrics.csv"
        if validation_path.exists():
            validation = pd.read_csv(validation_path)
            if len(validation) and "selected_by_discovery" in validation:
                selected = validation.loc[validation["selected_by_discovery"].astype(bool)].copy()
                if len(selected):
                    selected_frames.append(
                        selected.assign(
                            run_id=run_id,
                            seed=row["seed"],
                            sealed_fraction=row["sealed_fraction"],
                            winning_data_specification=row["winning_data_specification"],
                            winning_universe=row["winning_universe"],
                            winning_strategy=row["winning_strategy"],
                            m_spec_win_fraction=m_spec_win_fraction,
                        )
                    )

        delta_path = part / "protocol_validation_paired_deltas.csv"
        if delta_path.exists():
            deltas = pd.read_csv(delta_path)
            if len(deltas):
                delta_frames.append(
                    deltas.assign(
                        run_id=run_id,
                        seed=row["seed"],
                        sealed_fraction=row["sealed_fraction"],
                        winning_data_specification=row["winning_data_specification"],
                        winning_universe=row["winning_universe"],
                        winning_strategy=row["winning_strategy"],
                        m_spec_win_fraction=m_spec_win_fraction,
                    )
                )

    runs = pd.DataFrame(run_rows).sort_values(["sealed_fraction", "seed"], kind="mergesort").reset_index(drop=True)
    if len(runs) != 15:
        raise ValueError(f"Expected 15 predeclared stability parts, found {len(runs)}")
    if runs[["seed", "sealed_fraction"]].drop_duplicates().shape[0] != 15:
        raise ValueError("Duplicate seed/sealed-fraction stability parts detected")
    if runs["winning_data_specification"].nunique() != 1:
        raise ValueError("M/background must remain a sensitivity set, not a selected data specification")

    total_runs = len(runs)
    choice_stability = (
        runs.groupby(["winning_data_specification", "winning_universe", "winning_strategy"], as_index=False)
        .agg(
            runs_selected=("run_id", "nunique"),
            mean_n_predictors=("n_winning_predictors", "mean"),
            mean_m_spec_win_fraction=("m_spec_win_fraction", "mean"),
            min_m_spec_win_fraction=("m_spec_win_fraction", "min"),
        )
    )
    choice_stability["n_runs"] = total_runs
    choice_stability["selection_fraction"] = choice_stability["runs_selected"] / float(total_runs)
    choice_stability = choice_stability.sort_values(
        ["selection_fraction", "min_m_spec_win_fraction", "mean_n_predictors", "winning_universe", "winning_strategy"],
        ascending=[False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    selected_metrics = pd.concat(selected_frames, ignore_index=True) if selected_frames else pd.DataFrame()
    deltas = pd.concat(delta_frames, ignore_index=True) if delta_frames else pd.DataFrame()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runs.to_csv(output_dir / "protocol_stability_runs.csv", index=False)
    choice_stability.to_csv(output_dir / "protocol_choice_stability.csv", index=False)
    _component_stability(runs).to_csv(output_dir / "protocol_component_stability.csv", index=False)
    selected_metrics.to_csv(output_dir / "protocol_selected_validation_metrics.csv", index=False)
    deltas.to_csv(output_dir / "protocol_validation_paired_deltas.csv", index=False)
    _delta_summary(deltas).to_csv(output_dir / "protocol_validation_delta_summary.csv", index=False)
