"""Render the concrete Nature Figure 3 from already reconstructed frozen source data.

Reporting-only. This script performs no model fitting, selection, thresholding,
or scientific endpoint recomputation. It overwrites only the Figure-3 image/PDF
created by the reporting workflow, using source tables that are themselves
hard-asserted against the frozen v2.7.2 artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FAMILY_LABELS = {
    "gaussian": "Gaussian",
    "asymmetric": "Asymmetric",
    "interaction": "Interaction",
    "soft_threshold": "Soft threshold",
    "omitted_driver": "Omitted driver",
    "observation_confounded": "Observation confounded",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    family = pd.read_csv(args.input_dir / "nature_source_data_fig3.csv")
    disagreement = pd.read_csv(
        args.input_dir / "nature_source_data_fig3_model_disagreement.csv"
    )
    soil = pd.read_csv(args.input_dir / "nature_source_data_fig3_soil.csv")

    if int(family["stable_core_exact_n"].sum()) != 55:
        raise ValueError("expected stable exact process recovery 55/60")
    if int(family["auc_process_exact_n"].sum()) != 50:
        raise ValueError("expected AUC exact process recovery 50/60")
    if tuple(disagreement.iloc[0].astype(int)) != (22, 19, 16, 18):
        raise ValueError("unexpected model-disagreement recovery counts")
    if tuple(soil.iloc[0][["n", "stable_n", "contested_n", "absent_from_both_n"]].astype(int)) != (10, 7, 3, 0):
        raise ValueError("unexpected true-soil status counts")
    if tuple(soil.iloc[1][["n", "stable_n", "contested_n", "absent_from_both_n"]].astype(int)) != (50, 2, 7, 41):
        raise ValueError("unexpected false-soil status counts")

    labels = [FAMILY_LABELS[s] for s in family["scenario"]]
    y = np.arange(len(family))[::-1]
    offset = 0.08

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.2), constrained_layout=True)

    ax = axes[0]
    for yi, stable, auc in zip(
        y, family["stable_core_exact_rate"], family["auc_process_exact_rate"]
    ):
        ax.plot([auc, stable], [yi, yi], linewidth=1.0, alpha=0.5)
    ax.scatter(
        family["stable_core_exact_rate"],
        y + offset,
        marker="o",
        label="Stable process core (55/60 overall)",
        zorder=3,
    )
    ax.scatter(
        family["auc_process_exact_rate"],
        y - offset,
        marker="s",
        label="AUC-selected candidate (50/60 overall)",
        zorder=3,
    )
    ax.set_yticks(y, labels)
    ax.set_ylim(-0.45, len(y) - 0.55)
    ax.set_xlim(0.40, 1.035)
    ax.set_xlabel("Exact hidden process-set recovery")
    ax.legend(frameon=False, loc="upper left", fontsize=8.2)
    ax.set_title(
        "Fitted ecological models disagreed in 22/60 cases;\n"
        "stable process truth remained exact in 19/22",
        fontsize=9,
        loc="left",
        pad=8,
    )
    ax.text(-0.14, 1.10, "a", transform=ax.transAxes, fontweight="bold", fontsize=13)

    ax.annotate(
        "AUC selected observation-only models in 5/10",
        xy=(0.50, y[-1] - offset),
        xytext=(0.48, y[-1] + 0.65),
        arrowprops={"arrowstyle": "->", "linewidth": 0.8},
        fontsize=8.0,
    )

    ax = axes[1]
    x = np.arange(2)
    n = soil["n"].to_numpy(float)
    stable = soil["stable_n"].to_numpy(float) / n
    contested = soil["contested_n"].to_numpy(float) / n
    absent = soil["absent_from_both_n"].to_numpy(float) / n
    ax.bar(x, stable, label="Stable")
    ax.bar(x, contested, bottom=stable, label="Contested")
    ax.bar(x, absent, bottom=stable + contested, label="Absent from both")
    ax.set_xticks(x, ["Soil true\n(n=10)", "Soil false\n(n=50)"])
    ax.set_ylim(0, 1.06)
    ax.set_ylabel("Fraction of cases")
    ax.legend(
        frameon=False,
        fontsize=8.2,
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
    )
    ax.set_title(
        "Only soil varied in process truth;\n"
        "temperature and water were true and stable in 60/60",
        fontsize=9,
        loc="left",
        pad=8,
    )
    ax.text(-0.11, 1.10, "b", transform=ax.transAxes, fontweight="bold", fontsize=13)

    ax.text(0, stable[0] / 2, "7", ha="center", va="center", fontsize=9)
    ax.text(0, stable[0] + contested[0] / 2, "3", ha="center", va="center", fontsize=9)
    ax.text(1, max(stable[1] / 2, 0.025), "2", ha="center", va="center", fontsize=9)
    ax.text(1, stable[1] + contested[1] / 2, "7", ha="center", va="center", fontsize=9)
    ax.text(1, stable[1] + contested[1] + absent[1] / 2, "41", ha="center", va="center", fontsize=9)

    fig.savefig(args.output_dir / "nature_fig3_known_truth.png", dpi=600, bbox_inches="tight")
    fig.savefig(args.output_dir / "nature_fig3_known_truth.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
