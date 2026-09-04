"""Build Nature-track Product-A reporting figures from frozen artifacts only.

Reporting utility only: no Product-A scientific experiment, selection, threshold,
or endpoint is recomputed. The script reads already frozen v2.7.2 and v2.8.4
artifacts, asserts the manuscript headline values, writes source data, and renders
publication-oriented combined figures.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EXPECTED_V272_FAMILIES = (
    "gaussian",
    "asymmetric",
    "interaction",
    "soft_threshold",
    "omitted_driver",
    "observation_confounded",
)
EXPECTED_V284_CANDIDATE = "all|logit_l2_C0.1_degree1_rs0"
EXPECTED_V284_SEEDS = (2026082201, 2026082202, 2026082203)
FAMILY_LABELS = {
    "gaussian": "Gaussian",
    "asymmetric": "Asymmetric",
    "interaction": "Interaction",
    "soft_threshold": "Soft threshold",
    "omitted_driver": "Omitted driver",
    "observation_confounded": "Observation confounded",
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--v272-dir", type=Path, required=True)
    p.add_argument("--v284-part", action="append", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def build_v272_source(v272_dir: Path) -> pd.DataFrame:
    cert = pd.read_csv(v272_dir / "ecological_inference_certificates.csv")
    required = {
        "scenario",
        "seed",
        "stable_core_precision",
        "stable_core_recall",
        "stable_core_f1",
        "process_set_consensus",
        "model_consensus",
    }
    missing = required.difference(cert.columns)
    if missing:
        raise ValueError(f"v2.7.2 certificate missing columns: {sorted(missing)}")
    if set(cert["scenario"]) != set(EXPECTED_V272_FAMILIES):
        raise ValueError("v2.7.2 niche-family identity differs from frozen reporting contract")
    if len(cert) != 60:
        raise ValueError(f"expected 60 v2.7.2 cases, found {len(cert)}")

    out = (
        cert.groupby("scenario", as_index=False)
        .agg(
            n=("seed", "size"),
            stable_core_precision=("stable_core_precision", "mean"),
            stable_core_recall=("stable_core_recall", "mean"),
            stable_core_f1=("stable_core_f1", "mean"),
            process_set_consensus=("process_set_consensus", "mean"),
            model_consensus=("model_consensus", "mean"),
        )
    )
    order = {name: i for i, name in enumerate(EXPECTED_V272_FAMILIES)}
    out["_order"] = out["scenario"].map(order)
    out = out.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    pooled = cert[["stable_core_precision", "stable_core_recall", "stable_core_f1"]].mean()
    if not np.isclose(pooled["stable_core_precision"], 0.9888888888888889):
        raise ValueError("v2.7.2 pooled precision differs from frozen result")
    if not np.isclose(pooled["stable_core_recall"], 0.9833333333333333):
        raise ValueError("v2.7.2 pooled recall differs from frozen result")
    if int(cert["model_consensus"].sum()) != 38:
        raise ValueError("expected exact-model consensus 38/60")
    if int(cert["process_set_consensus"].sum()) != 50:
        raise ValueError("expected process-set consensus 50/60")
    return out


def build_v284_source(part_dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(part_dirs) != 3:
        raise ValueError("pass exactly three --v284-part directories")

    rows: list[dict[str, object]] = []
    part_rows: list[dict[str, object]] = []
    observed_seeds: list[int] = []
    for part_dir in part_dirs:
        summary = pd.read_csv(part_dir / "part_summary.csv")
        if len(summary) != 1:
            raise ValueError(f"{part_dir}: expected one part-summary row")
        summary_row = summary.iloc[0]
        seed = int(summary_row["seed"])
        observed_seeds.append(seed)
        if not bool(summary_row["part_available"]):
            raise ValueError(f"{part_dir}: frozen v2.8.4 part is unavailable")
        part_rows.append(
            {
                "seed": seed,
                "nondominated": bool(summary_row["ecologically_nondominated_vs_auc"]),
                "strict_improvement": bool(summary_row["strict_ecological_improvement_vs_auc"]),
                "mean_presence_rank_delta": float(summary_row["mean_presence_rank_delta_vs_auc"]),
            }
        )

        audit = pd.read_csv(part_dir / "sealed_empirical_audit.csv")
        models = pd.read_csv(part_dir / "frozen_models_audited.csv")
        if len(audit) != 72 or len(models) != 72:
            raise ValueError(f"{part_dir}: expected 72 two-role rows")

        for (taxon, m_spec), group in audit.groupby(["taxon", "M"], sort=True):
            if set(group["role"]) != {"ecological", "auc"}:
                raise ValueError(f"{part_dir}: incomplete role pair for {taxon} {m_spec}")
            model_group = models[(models["taxon"] == taxon) & (models["M"] == m_spec)]
            eco_model = model_group.loc[model_group["role"] == "ecological"].iloc[0]
            auc_model = model_group.loc[model_group["role"] == "auc"].iloc[0]
            eco_audit = group.loc[group["role"] == "ecological"].iloc[0]
            auc_audit = group.loc[group["role"] == "auc"].iloc[0]
            rows.append(
                {
                    "seed": seed,
                    "taxon": taxon,
                    "M": m_spec,
                    "ecological_presence_rank": float(eco_audit["presence_rank"]),
                    "auc_presence_rank": float(auc_audit["presence_rank"]),
                    "candidate_identical": eco_model["candidate"] == auc_model["candidate"],
                    "selected_predictors_identical": (
                        eco_model["selected_predictors"] == auc_model["selected_predictors"]
                    ),
                    "ecological_candidate": eco_model["candidate"],
                    "auc_candidate": auc_model["candidate"],
                }
            )

    if tuple(sorted(observed_seeds)) != EXPECTED_V284_SEEDS:
        raise ValueError(f"unexpected v2.8.4 seeds: {sorted(observed_seeds)}")

    cells = pd.DataFrame(rows).sort_values(["seed", "taxon", "M"]).reset_index(drop=True)
    parts = pd.DataFrame(part_rows).sort_values("seed").reset_index(drop=True)
    if len(cells) != 108:
        raise ValueError(f"expected 108 matched empirical cells, found {len(cells)}")
    if not bool(cells["candidate_identical"].all()):
        raise ValueError("ecological and AUC candidate IDs are not identical in all 108 cells")
    if not bool(cells["selected_predictors_identical"].all()):
        raise ValueError("selected predictor sets are not identical in all 108 cells")
    if set(cells["ecological_candidate"]) != {EXPECTED_V284_CANDIDATE}:
        raise ValueError("unexpected ecological candidate identity in v2.8.4")
    if not np.allclose(cells["ecological_presence_rank"], cells["auc_presence_rank"]):
        raise ValueError("sealed presence-rank values are not identical")
    if not bool(parts["nondominated"].all()):
        raise ValueError("expected ecological nondomination in all three parts")
    if bool(parts["strict_improvement"].any()):
        raise ValueError("expected strict ecological improvement in 0/3 parts")
    if not np.allclose(parts["mean_presence_rank_delta"], 0.0):
        raise ValueError("expected mean presence-rank delta 0.0 in every part")
    return cells, parts


def render_v272(fig3: pd.DataFrame, output_dir: Path) -> None:
    labels = [FAMILY_LABELS[s] for s in fig3["scenario"]]
    y = np.arange(len(fig3))[::-1]
    offset = 0.09

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), constrained_layout=True)

    ax = axes[0]
    for yi, p, r in zip(y, fig3["stable_core_precision"], fig3["stable_core_recall"]):
        ax.plot([p, r], [yi, yi], linewidth=1.0, alpha=0.45)
    ax.scatter(fig3["stable_core_precision"], y + offset, marker="o", label="Precision", zorder=3)
    ax.scatter(fig3["stable_core_recall"], y - offset, marker="s", label="Recall", zorder=3)
    ax.set_yticks(y, labels)
    ax.set_ylim(-0.45, len(y) - 0.55)
    ax.set_xlim(0.88, 1.012)
    ax.set_xlabel("Stable-process-core recovery")
    ax.legend(frameon=False, loc="lower left")
    ax.text(-0.13, 1.03, "a", transform=ax.transAxes, fontweight="bold", fontsize=13)

    ax = axes[1]
    for yi, proc, model in zip(y, fig3["process_set_consensus"], fig3["model_consensus"]):
        ax.plot([model, proc], [yi, yi], linewidth=1.0, alpha=0.45)
    ax.scatter(fig3["process_set_consensus"], y + offset, marker="o", label="Process set", zorder=3)
    ax.scatter(fig3["model_consensus"], y - offset, marker="s", label="Exact model", zorder=3)
    ax.set_yticks(y, [""] * len(y))
    ax.set_ylim(-0.45, len(y) - 0.55)
    ax.set_xlim(0.30, 1.04)
    ax.set_xlabel("Consensus fraction")
    ax.legend(frameon=False, loc="upper left", fontsize=8.5)
    ax.text(-0.10, 1.03, "b", transform=ax.transAxes, fontweight="bold", fontsize=13)
    ax.text(
        0.02,
        0.02,
        "All cases: process set 50/60; exact model 38/60\nIndependent-process max difference = 0.0",
        transform=ax.transAxes,
        fontsize=8.3,
        va="bottom",
    )

    fig.savefig(output_dir / "nature_fig3_known_truth.png", dpi=600, bbox_inches="tight")
    fig.savefig(output_dir / "nature_fig3_known_truth.pdf", bbox_inches="tight")
    plt.close(fig)


def render_v284(cells: pd.DataFrame, parts: pd.DataFrame, output_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.6), constrained_layout=True)

    ax = axes[0]
    ax.scatter(cells["auc_presence_rank"], cells["ecological_presence_rank"], alpha=0.42, s=28)
    lower = float(min(cells["auc_presence_rank"].min(), cells["ecological_presence_rank"].min()))
    upper = float(max(cells["auc_presence_rank"].max(), cells["ecological_presence_rank"].max()))
    ax.plot([lower, upper], [lower, upper], linewidth=1.0)
    ax.set_xlabel("AUC role: sealed presence rank")
    ax.set_ylabel("Ecological role: sealed presence rank")
    ax.set_xlim(lower - 0.02, upper + 0.02)
    ax.set_ylim(lower - 0.02, upper + 0.02)
    ax.text(-0.13, 1.03, "a", transform=ax.transAxes, fontweight="bold", fontsize=13)
    ax.text(
        0.04,
        0.94,
        "Same candidate: 108/108\nSame predictors: 108/108",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
    )

    ax = axes[1]
    display = parts.copy()
    display["candidate_identity"] = 1.0
    display["predictor_identity"] = 1.0
    display["strict_improvement_numeric"] = display["strict_improvement"].astype(float)
    x = np.arange(len(display))
    ax.scatter(x - 0.12, display["candidate_identity"], marker="o", label="Same candidate")
    ax.scatter(x, display["predictor_identity"], marker="s", label="Same predictors")
    ax.scatter(x + 0.12, display["strict_improvement_numeric"], marker="^", label="Strict improvement")
    ax.set_xticks(x, [str(s)[-2:] for s in display["seed"]])
    ax.set_xlabel("Frozen split seed (suffix)")
    ax.set_ylabel("Part-level indicator")
    ax.set_ylim(-0.08, 1.12)
    ax.set_yticks([0, 1], ["No", "Yes"])
    ax.legend(frameon=False, loc="center right", fontsize=8.5)
    ax.text(-0.10, 1.03, "b", transform=ax.transAxes, fontweight="bold", fontsize=13)
    ax.text(
        0.02,
        0.14,
        "Nondominated: 3/3\nStrict improvement: 0/3\nFormal endpoint: not supported\nPromotion: not promoted",
        transform=ax.transAxes,
        fontsize=8.5,
        va="bottom",
    )

    fig.savefig(output_dir / "nature_fig4_empirical_identity.png", dpi=600, bbox_inches="tight")
    fig.savefig(output_dir / "nature_fig4_empirical_identity.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fig3 = build_v272_source(args.v272_dir)
    fig4, part_summary = build_v284_source(args.v284_part)
    fig3.to_csv(args.output_dir / "nature_source_data_fig3.csv", index=False)
    fig4.to_csv(args.output_dir / "nature_source_data_fig4.csv", index=False)
    part_summary.to_csv(args.output_dir / "nature_source_data_fig4_parts.csv", index=False)
    render_v272(fig3, args.output_dir)
    render_v284(fig4, part_summary, args.output_dir)


if __name__ == "__main__":
    main()
