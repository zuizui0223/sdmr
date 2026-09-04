"""Render Nature Product-A Figures 1 and 2 from frozen/reporting inputs.

Figure 1 is a conceptual reporting diagram of the frozen information and
identification logic. Figure 2 reads the frozen v2.3 reporting table derived from
`evidence/product_a_v2_3/decision.md`. This script performs no scientific model
fit, selection, thresholding, or endpoint update.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


EXPECTED_V23 = {
    "C1": (0.2526, 0.0556, 0.3333, 0.3333, 2, 8),
    "C2": (0.2500, 0.0963, 0.2963, 0.2407, 0, 0),
    "C3": (0.1652, 0.1464, 0.2963, 0.2963, 0, 0),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--v23-source",
        type=Path,
        default=Path("source_data/nature_fig2_v23.csv"),
    )
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def box(ax, xy, width, height, text, *, fontsize=9, linewidth=1.0) -> None:
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        fill=False,
        linewidth=linewidth,
    )
    ax.add_patch(patch)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=fontsize)


def arrow(ax, start, end, *, linewidth=1.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=linewidth,
        )
    )


def render_fig1(output_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.0), constrained_layout=True)

    # Panel a: winner-selection logic.
    ax = axes[0]
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(-0.04, 1.00, "a", transform=ax.transAxes, fontweight="bold", fontsize=13, va="top")
    box(ax, (0.05, 0.72), 0.24, 0.13, "Occurrence\nrecords")
    box(ax, (0.38, 0.72), 0.24, 0.13, "Candidate\nmodels")
    box(ax, (0.70, 0.72), 0.24, 0.13, "Winning\nmodel")
    arrow(ax, (0.29, 0.785), (0.38, 0.785))
    arrow(ax, (0.62, 0.785), (0.70, 0.785))
    ax.text(0.50, 0.66, "AUC / Boyce / OR10 / AICc / CV", ha="center", va="center", fontsize=8.5)
    box(ax, (0.38, 0.40), 0.24, 0.13, "Selected\npredictors")
    arrow(ax, (0.82, 0.72), (0.60, 0.53))
    box(ax, (0.38, 0.14), 0.24, 0.13, "Ecological\ninterpretation?")
    arrow(ax, (0.50, 0.40), (0.50, 0.27))
    ax.text(
        0.50,
        0.05,
        "Predictive or functional adequacy does not by itself\nestablish process-information necessity",
        ha="center",
        va="bottom",
        fontsize=9,
    )

    # Panel b: Product-A identification logic.
    ax = axes[1]
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(-0.04, 1.00, "b", transform=ax.transAxes, fontweight="bold", fontsize=13, va="top")
    box(ax, (0.03, 0.78), 0.22, 0.11, "Occurrence\npool")
    box(ax, (0.33, 0.78), 0.22, 0.11, "Model\npool")
    box(ax, (0.67, 0.78), 0.25, 0.11, "Sealed\nanswer-check")
    arrow(ax, (0.25, 0.835), (0.33, 0.835))
    arrow(ax, (0.25, 0.815), (0.67, 0.815))
    ax.text(0.48, 0.73, "split before tuning", ha="center", fontsize=8)

    box(ax, (0.18, 0.54), 0.25, 0.11, "Prediction-adequate\nalternatives")
    arrow(ax, (0.44, 0.78), (0.32, 0.65))
    box(ax, (0.58, 0.54), 0.27, 0.11, "Ecological recovery\n+ sensitivity")
    arrow(ax, (0.79, 0.78), (0.72, 0.65))

    box(ax, (0.32, 0.32), 0.38, 0.12, "Exclude declared process information\nCan an adequate certificate survive?")
    arrow(ax, (0.31, 0.54), (0.43, 0.44))
    arrow(ax, (0.71, 0.54), (0.59, 0.44))

    labels = ["required", "possible / substitutable", "contested", "unresolved"]
    xs = [0.02, 0.27, 0.56, 0.78]
    widths = [0.20, 0.26, 0.20, 0.19]
    for x, w, label in zip(xs, widths, labels):
        box(ax, (x, 0.09), w, 0.10, label, fontsize=8.3)
        arrow(ax, (0.51, 0.32), (x + w / 2, 0.19), linewidth=0.8)
    ax.text(
        0.50,
        0.01,
        "Output is set-valued when the evidence does not identify one ecological explanation",
        ha="center",
        va="bottom",
        fontsize=8.5,
    )

    fig.savefig(output_dir / "nature_fig1_identification_logic.png", dpi=600, bbox_inches="tight")
    fig.savefig(output_dir / "nature_fig1_identification_logic.pdf", bbox_inches="tight")
    plt.close(fig)


def load_v23(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if list(df["panel"]) != ["C1", "C2", "C3"]:
        raise ValueError("unexpected v2.3 panel order/identity")
    for _, row in df.iterrows():
        expected = EXPECTED_V23[row["panel"]]
        observed = (
            float(row["complete_interval_width"]),
            float(row["pareto_interval_width"]),
            float(row["complete_boundary_coverage"]),
            float(row["pareto_boundary_coverage"]),
            int(row["complete_false_necessary"]),
            int(row["pareto_false_necessary"]),
        )
        for a, b in zip(observed[:4], expected[:4]):
            if not np.isclose(a, b):
                raise ValueError(f"v2.3 frozen reporting mismatch for {row['panel']}")
        if observed[4:] != expected[4:]:
            raise ValueError(f"v2.3 frozen false-necessity mismatch for {row['panel']}")
    return df


def render_fig2(df: pd.DataFrame, output_dir: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.4), constrained_layout=True)
    x = np.arange(len(df))

    ax = axes[0]
    for xi, complete, pareto in zip(x, df["complete_interval_width"], df["pareto_interval_width"]):
        ax.plot([xi, xi], [pareto, complete], linewidth=1.0)
    ax.scatter(x - 0.06, df["complete_interval_width"], marker="o", label="Complete adequate")
    ax.scatter(x + 0.06, df["pareto_interval_width"], marker="s", label="Ecological Pareto")
    ax.set_xticks(x, df["panel"])
    ax.set_ylabel("Mean normalized interval width")
    ax.set_xlabel("Known-truth panel")
    ax.legend(frameon=False, fontsize=8)
    ax.text(-0.18, 1.03, "a", transform=ax.transAxes, fontweight="bold", fontsize=13)

    ax = axes[1]
    ax.scatter(x - 0.06, df["complete_boundary_coverage"], marker="o", label="Complete adequate")
    ax.scatter(x + 0.06, df["pareto_boundary_coverage"], marker="s", label="Ecological Pareto")
    for xi, complete, pareto in zip(x, df["complete_boundary_coverage"], df["pareto_boundary_coverage"]):
        ax.plot([xi - 0.06, xi + 0.06], [complete, pareto], linewidth=0.9)
    ax.set_xticks(x, df["panel"])
    ax.set_ylabel("Boundary coverage")
    ax.set_xlabel("Known-truth panel")
    ax.text(-0.18, 1.03, "b", transform=ax.transAxes, fontweight="bold", fontsize=13)
    ax.text(0.38, 0.18, "C2: sharper\nbut lower coverage", transform=ax.transAxes, fontsize=8.5)

    ax = axes[2]
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(-0.10, 1.03, "c", transform=ax.transAxes, fontweight="bold", fontsize=13)
    box(ax, (0.08, 0.73), 0.84, 0.12, "Ecological Pareto set\nlooks sharper")
    box(ax, (0.08, 0.50), 0.84, 0.12, "Panel C1: false-required count\n2 → 8 after pruning")
    arrow(ax, (0.50, 0.73), (0.50, 0.62))
    box(ax, (0.08, 0.27), 0.84, 0.12, "Agreement among retained models\n≠ process necessity")
    arrow(ax, (0.50, 0.50), (0.50, 0.39))
    box(ax, (0.08, 0.04), 0.84, 0.12, "Replacement: falsify necessity\nby process-information exclusion")
    arrow(ax, (0.50, 0.27), (0.50, 0.16))

    fig.savefig(output_dir / "nature_fig2_false_necessity.png", dpi=600, bbox_inches="tight")
    fig.savefig(output_dir / "nature_fig2_false_necessity.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    render_fig1(args.output_dir)
    df = load_v23(args.v23_source)
    df.to_csv(args.output_dir / "nature_source_data_fig2.csv", index=False)
    render_fig2(df, args.output_dir)


if __name__ == "__main__":
    main()
