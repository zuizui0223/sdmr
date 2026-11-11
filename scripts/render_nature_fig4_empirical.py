"""Render the empirical Product-A Figure 4 from frozen reporting source data.

Reporting only: this script does not fit SDMs, alter thresholds, reinterpret missing
cells, or change any scientific endpoint. It combines the already frozen v2.8.4
selector-collapse source data with the audited September-7 real positive controls.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EXPECTED_COMMON_CANDIDATE = "all|logit_l2_C0.1_degree1_rs0"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--selector-cells", type=Path, required=True)
    p.add_argument("--positive-control-taxa", type=Path, required=True)
    p.add_argument("--positive-control-cells", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False})


def validate_sources(
    selector: pd.DataFrame,
    taxa: pd.DataFrame,
    cells: pd.DataFrame,
) -> None:
    if len(selector) != 108:
        raise ValueError(f"expected 108 v2.8.4 selector cells, found {len(selector)}")
    if not bool(_as_bool(selector["candidate_identical"]).all()):
        raise ValueError("v2.8.4 candidate identity is not 108/108")
    if not bool(_as_bool(selector["selected_predictors_identical"]).all()):
        raise ValueError("v2.8.4 predictor identity is not 108/108")
    if set(selector["common_candidate"]) != {EXPECTED_COMMON_CANDIDATE}:
        raise ValueError("unexpected frozen v2.8.4 common candidate")

    required_taxa = {
        "lane",
        "species",
        "expected_process",
        "mean_score_all_three_M",
        "missing_M_count",
        "recovered",
    }
    missing = required_taxa.difference(taxa.columns)
    if missing:
        raise ValueError(f"positive-control taxon audit missing columns: {sorted(missing)}")
    if len(taxa) != 8 or set(taxa["lane"]) != {"plant", "nonplant"}:
        raise ValueError("expected exactly eight frozen positive controls in two lanes")

    taxa = taxa.copy()
    taxa["recovered"] = _as_bool(taxa["recovered"])
    plant = taxa.loc[taxa["lane"].eq("plant")]
    nonplant = taxa.loc[taxa["lane"].eq("nonplant")]
    if len(plant) != 4 or int(plant["recovered"].sum()) != 2:
        raise ValueError("plant positive-control outcome differs from frozen 2/4")
    if len(nonplant) != 4 or int(nonplant["recovered"].sum()) != 1:
        raise ValueError("nonplant positive-control outcome differs from frozen 1/4")
    water = taxa.loc[taxa["expected_process"].eq("water")]
    temp = taxa.loc[taxa["expected_process"].eq("temperature")]
    if len(water) != 4 or int(water["recovered"].sum()) != 0:
        raise ValueError("water positive-control outcome differs from frozen 0/4")
    if len(temp) != 4 or int(temp["recovered"].sum()) != 3:
        raise ValueError("temperature positive-control outcome differs from frozen 3/4")

    q = taxa.loc[taxa["species"].eq("Quercus robur")].iloc[0]
    s = taxa.loc[taxa["species"].eq("Silene ciliata")].iloc[0]
    if not np.isclose(float(q["mean_score_all_three_M"]), -0.2766923360923064):
        raise ValueError("Quercus frozen mean score changed")
    if not np.isclose(float(s["mean_score_all_three_M"]), -0.0007037840653768869):
        raise ValueError("Silene ciliata frozen mean score changed")

    required_cells = {
        "pipeline_available",
        "n_adequate",
        "expected_process_comparable",
        "boundary_code_not_measured_loss",
    }
    missing = required_cells.difference(cells.columns)
    if missing:
        raise ValueError(f"positive-control cell audit missing columns: {sorted(missing)}")
    if len(cells) != 24:
        raise ValueError(f"expected 24 taxon x M cells, found {len(cells)}")
    if not bool(_as_bool(cells["pipeline_available"]).all()):
        raise ValueError("all 24 frozen pipelines should be technically available")
    if int((cells["n_adequate"].astype(int) > 0).sum()) != 21:
        raise ValueError("prediction-adequate availability differs from frozen 21/24")
    if int(_as_bool(cells["expected_process_comparable"]).sum()) != 17:
        raise ValueError("two-sided comparable cell count differs from frozen 17/24")


def render(
    selector: pd.DataFrame,
    taxa: pd.DataFrame,
    cells: pd.DataFrame,
    output_dir: Path,
) -> None:
    taxa = taxa.copy()
    taxa["recovered"] = _as_bool(taxa["recovered"])
    taxa["available"] = taxa["missing_M_count"].astype(int).eq(0)

    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.9), constrained_layout=True)

    # a: previous empirical endpoint collapsed ecological and AUC roles.
    ax = axes[0]
    rank = selector["sealed_presence_rank"].astype(float)
    ax.scatter(rank, rank, alpha=0.38, s=24)
    lo = float(rank.min())
    hi = float(rank.max())
    ax.plot([lo, hi], [lo, hi], linewidth=1.0)
    ax.set_xlim(lo - 0.03, hi + 0.03)
    ax.set_ylim(lo - 0.03, hi + 0.03)
    ax.set_xlabel("AUC role: sealed presence rank")
    ax.set_ylabel("Ecological role: sealed presence rank")
    ax.text(-0.16, 1.03, "a", transform=ax.transAxes, fontweight="bold", fontsize=13)
    ax.text(
        0.04,
        0.96,
        "Same candidate: 108/108\nSame predictors: 108/108\nStrict improvement: 0/3",
        transform=ax.transAxes,
        va="top",
        fontsize=8.6,
    )

    # b: actual frozen positive-control process scores.
    ax = axes[1]
    order = [
        "Quercus robur",
        "Silene ciliata",
        "Plantago alpina",
        "Silene acaulis",
        "Bombus terrestris",
        "Ochotona princeps",
        "Plethodon cinereus",
        "Cepaea nemoralis",
    ]
    display = taxa.set_index("species").loc[order].reset_index()
    y = np.arange(len(display))[::-1]
    available = display["available"].to_numpy(bool)
    recovered = display["recovered"].to_numpy(bool)
    score = pd.to_numeric(display["mean_score_all_three_M"], errors="coerce").to_numpy(float)

    ax.axvline(0.0, linewidth=1.0)
    ax.scatter(
        score[available & recovered],
        y[available & recovered],
        marker="o",
        s=48,
        label="Recovered",
    )
    ax.scatter(
        score[available & ~recovered],
        y[available & ~recovered],
        marker="x",
        s=52,
        label="Not recovered",
    )
    # Do not place unavailable all-three-M means at x=0: that would look like a
    # measured zero. Their status is shown explicitly in the right-side labels.
    for yi, row in zip(y, display.itertuples(index=False)):
        proc = "T" if row.expected_process == "temperature" else "W"
        if int(row.missing_M_count) > 0:
            suffix = f"[{proc}] mean NA ({int(row.missing_M_count)} M missing)"
        else:
            suffix = f"[{proc}]"
        ax.text(1.02, yi, suffix, transform=ax.get_yaxis_transform(), va="center", fontsize=7.4)
    ax.set_yticks(y, display["species"])
    ax.set_xlabel("Mean expected-process score across all 3 M")
    ax.set_xlim(-0.62, 0.88)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.text(-0.20, 1.03, "b", transform=ax.transAxes, fontweight="bold", fontsize=13)

    # c: frozen lane decision plus evidence availability.
    ax = axes[2]
    lane_labels = ["Plant", "Nonplant"]
    lane_recovered = [
        int(display.loc[display["lane"].eq("plant"), "recovered"].sum()),
        int(display.loc[display["lane"].eq("nonplant"), "recovered"].sum()),
    ]
    lane_fraction = np.array(lane_recovered, dtype=float) / 4.0
    lane_process = ["T 2/2; W 0/2", "T 1/2; W 0/2"]
    x = np.arange(2)
    ax.bar(x, lane_fraction, width=0.55)
    ax.axhline(0.75, linestyle="--", linewidth=1.0)
    ax.set_xticks(x, lane_labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Positive controls recovered")
    for xi, n, frac, proc_text in zip(x, lane_recovered, lane_fraction, lane_process):
        ax.text(
            xi,
            frac + 0.035,
            f"{n}/4\n{proc_text}",
            ha="center",
            va="bottom",
            fontsize=8.0,
        )
    ax.text(
        0.98,
        0.765,
        "predeclared >=3/4 lane gate",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.5,
    )
    ax.text(
        0.03,
        0.97,
        "Evidence: 24/24 pipelines; 21/24 adequate; 17/24 two-sided\n"
        "Positive-only controls: specificity not estimable\n"
        "Process scores: inner CV; outer transfer not evaluated",
        transform=ax.transAxes,
        fontsize=7.4,
        va="top",
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "white", "alpha": 0.92, "linewidth": 0.6},
    )
    ax.text(-0.15, 1.03, "c", transform=ax.transAxes, fontweight="bold", fontsize=13)

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "nature_fig4_empirical_validation.png", dpi=600, bbox_inches="tight")
    fig.savefig(output_dir / "nature_fig4_empirical_validation.pdf", bbox_inches="tight")
    plt.close(fig)

    taxa.to_csv(output_dir / "nature_source_data_fig4_positive_controls_taxa.csv", index=False)
    cells.to_csv(output_dir / "nature_source_data_fig4_positive_controls_cells.csv", index=False)


def main() -> None:
    args = parse_args()
    selector = pd.read_csv(args.selector_cells)
    taxa = pd.read_csv(args.positive_control_taxa)
    cells = pd.read_csv(args.positive_control_cells)
    validate_sources(selector, taxa, cells)
    render(selector, taxa, cells, args.output_dir)


if __name__ == "__main__":
    main()
