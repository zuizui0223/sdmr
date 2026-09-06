"""Render Nature Figure 3 from frozen counterfactual process source data.

Reporting-only. The script reads committed source tables derived from the
prospectively frozen 35-case validation and unchanged 70-case replication. It
performs no model fitting, threshold calibration or scientific selection.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--methods", type=Path, required=True)
    p.add_argument("--process", type=Path, required=True)
    p.add_argument("--sets", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    methods = pd.read_csv(args.methods)
    proc = pd.read_csv(args.process)
    sets = pd.read_csv(args.sets)

    # Fail closed on all headline replication values.
    rep = methods.loc[methods["phase"].eq("independent_replication_4401_4410")]
    val = methods.loc[methods["phase"].eq("fresh_validation_4301_4305")]
    lookup_rep = rep.set_index("method")
    lookup_val = val.set_index("method")
    assert int(lookup_rep.loc["counterfactual", "exact_n"]) == 65
    assert int(lookup_rep.loc["auc_winner", "exact_n"]) == 56
    assert int(lookup_rep.loc["old_stable_core", "exact_n"]) == 49
    assert int(lookup_val.loc["counterfactual", "exact_n"]) == 30
    assert int(lookup_val.loc["auc_winner", "exact_n"]) == 25
    assert int(lookup_val.loc["old_stable_core", "exact_n"]) == 23
    assert int(lookup_rep.loc["counterfactual", "model_disagreement_n"]) == 30
    assert int(lookup_rep.loc["counterfactual", "exact_when_models_disagree_n"]) == 27

    cproc = proc.loc[proc["method"].eq("counterfactual")].set_index("process")
    assert np.isclose(cproc.loc["temperature", "sensitivity"], 1.0)
    assert np.isclose(cproc.loc["temperature", "specificity"], 28 / 30)
    assert np.isclose(cproc.loc["water", "sensitivity"], 1.0)
    assert np.isclose(cproc.loc["water", "specificity"], 28 / 30)
    assert np.isclose(cproc.loc["soil", "sensitivity"], 39 / 40)
    assert np.isclose(cproc.loc["soil", "specificity"], 1.0)
    assert int(sets["counterfactual_exact_n"].sum()) == 65
    assert int(sets["auc_exact_n"].sum()) == 56

    fig = plt.figure(figsize=(12.2, 4.8), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=(1.05, 0.92, 1.25))

    # a: prospective validation and unchanged replication.
    ax = fig.add_subplot(gs[0, 0])
    method_order = ["counterfactual", "auc_winner", "old_stable_core"]
    method_labels = ["Counterfactual", "AUC winner", "Predecessor"]
    x = np.arange(3)
    width = 0.34
    val_rates = [float(lookup_val.loc[m, "exact_rate"]) for m in method_order]
    rep_rates = [float(lookup_rep.loc[m, "exact_rate"]) for m in method_order]
    bars1 = ax.bar(x - width / 2, val_rates, width, label="Fresh validation (n=35)")
    bars2 = ax.bar(x + width / 2, rep_rates, width, label="Independent replication (n=70)")
    ax.set_xticks(x, method_labels, rotation=18, ha="right")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Exact complete process-set recovery")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    for bar, label in zip(bars1, ("30/35", "25/35", "23/35"), strict=True):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.018, label,
                ha="center", va="bottom", fontsize=8)
    for bar, label in zip(bars2, ("65/70", "56/70", "49/70"), strict=True):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.018, label,
                ha="center", va="bottom", fontsize=8)
    ax.text(-0.13, 1.03, "a", transform=ax.transAxes, fontweight="bold", fontsize=13)

    # b: process-specific operating characteristics in independent replication.
    ax = fig.add_subplot(gs[0, 1])
    processes = ["temperature", "water", "soil"]
    labels = ["Temperature", "Water", "Soil"]
    y = np.arange(3)[::-1]
    sensitivity = [float(cproc.loc[p, "sensitivity"]) for p in processes]
    specificity = [float(cproc.loc[p, "specificity"]) for p in processes]
    for yi, sens, spec in zip(y, sensitivity, specificity, strict=True):
        ax.plot([spec, sens], [yi, yi], linewidth=1.0, alpha=0.5)
    ax.scatter(sensitivity, y + 0.07, marker="o", label="Sensitivity", zorder=3)
    ax.scatter(specificity, y - 0.07, marker="s", label="Specificity", zorder=3)
    ax.set_yticks(y, labels)
    ax.set_xlim(0.74, 1.02)
    ax.set_ylim(-0.45, 2.45)
    ax.set_xlabel("Process classification rate")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    for yi, sens, spec in zip(y, sensitivity, specificity, strict=True):
        ax.text(sens, yi + 0.15, f"{sens:.3f}", ha="center", fontsize=8)
        ax.text(spec, yi - 0.22, f"{spec:.3f}", ha="center", fontsize=8)
    ax.text(-0.18, 1.03, "b", transform=ax.transAxes, fontweight="bold", fontsize=13)

    # c: where the replicated complete-set errors occur.
    ax = fig.add_subplot(gs[0, 2])
    set_order = ["T", "W", "S", "T+W", "T+S", "W+S", "T+W+S"]
    frame = sets.set_index("process_set").loc[set_order].reset_index()
    y = np.arange(len(frame))[::-1]
    c_rate = frame["counterfactual_exact_rate"].to_numpy(float)
    a_rate = frame["auc_exact_rate"].to_numpy(float)
    for yi, cr, ar in zip(y, c_rate, a_rate, strict=True):
        ax.plot([ar, cr], [yi, yi], linewidth=1.0, alpha=0.5)
    ax.scatter(c_rate, y + 0.08, marker="o", label="Counterfactual", zorder=3)
    ax.scatter(a_rate, y - 0.08, marker="s", label="AUC winner", zorder=3)
    ax.set_yticks(y, set_order)
    ax.set_xlim(0.5, 1.035)
    ax.set_ylim(-0.5, len(y) - 0.5)
    ax.set_xlabel("Exact recovery within process set")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.text(-0.13, 1.03, "c", transform=ax.transAxes, fontweight="bold", fontsize=13)
    ax.text(
        0.02, 0.98,
        "Ecological models disagreed in 30/70 cases;\nprocess truth exact in 27/30",
        transform=ax.transAxes, va="top", fontsize=8.2,
    )

    out_png = args.output_dir / "nature_fig3_known_truth.png"
    out_pdf = args.output_dir / "nature_fig3_known_truth.pdf"
    fig.savefig(out_png, dpi=600, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
