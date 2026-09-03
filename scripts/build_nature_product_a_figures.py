"""Build Nature-track Product-A reporting figures from frozen artifacts only.

This script is a reporting utility, not a Product-A scientific experiment. It
reads already frozen v2.7.2 and v2.8.4 CSV artifacts and produces manuscript
source data plus three draft plots:

- Fig. 3a: stable-process-core precision/recall across six known-truth families;
- Fig. 3b: process-set consensus versus exact-model consensus;
- Fig. 4: ecological-versus-AUC sealed presence-rank identity across 108 fresh
  empirical taxon x M x seed cells.

No thresholds, selectors, candidates, scientific decisions, or endpoints are
recomputed or changed.
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


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--v272-dir",
        type=Path,
        required=True,
        help="Extracted frozen v272-known-truth-a artifact directory.",
    )
    p.add_argument(
        "--v284-part",
        action="append",
        type=Path,
        required=True,
        help=(
            "Extracted v2.8.4 finalized-part artifact directory. Pass exactly "
            "three times, one for each frozen seed."
        ),
    )
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


def build_v284_source(part_dirs: list[Path]) -> pd.DataFrame:
    if len(part_dirs) != 3:
        raise ValueError("pass exactly three --v284-part directories")

    rows: list[dict[str, object]] = []
    observed_seeds: list[int] = []
    for part_dir in part_dirs:
        summary = pd.read_csv(part_dir / "part_summary.csv")
        if len(summary) != 1:
            raise ValueError(f"{part_dir}: expected one part-summary row")
        seed = int(summary.iloc[0]["seed"])
        observed_seeds.append(seed)
        if not bool(summary.iloc[0]["part_available"]):
            raise ValueError(f"{part_dir}: frozen v2.8.4 part is unavailable")

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

    out = pd.DataFrame(rows).sort_values(["seed", "taxon", "M"]).reset_index(drop=True)
    if len(out) != 108:
        raise ValueError(f"expected 108 matched empirical cells, found {len(out)}")
    if not bool(out["candidate_identical"].all()):
        raise ValueError("ecological and AUC candidate IDs are not identical in all 108 cells")
    if not bool(out["selected_predictors_identical"].all()):
        raise ValueError("selected predictor sets are not identical in all 108 cells")
    if set(out["ecological_candidate"]) != {EXPECTED_V284_CANDIDATE}:
        raise ValueError("unexpected ecological candidate identity in v2.8.4")
    if not np.allclose(out["ecological_presence_rank"], out["auc_presence_rank"]):
        raise ValueError("sealed presence-rank values are not identical")
    return out


def render_v272(fig3: pd.DataFrame, output_dir: Path) -> None:
    labels = [
        "Gaussian",
        "Asymmetric",
        "Interaction",
        "Soft threshold",
        "Omitted driver",
        "Observation confounded",
    ]
    x = np.arange(len(fig3))

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(x, fig3["stable_core_precision"], marker="o", label="Stable-core precision")
    ax.plot(x, fig3["stable_core_recall"], marker="s", label="Stable-core recall")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylim(0.84, 1.02)
    ax.set_ylabel("Mean recovery")
    ax.set_xlabel("Known-truth niche family (n = 10 each)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "nature_fig3a_family_recovery.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(x, fig3["process_set_consensus"], marker="o", label="Process-set consensus")
    ax.plot(x, fig3["model_consensus"], marker="s", label="Exact-model consensus")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylim(0.3, 1.05)
    ax.set_ylabel("Consensus fraction")
    ax.set_xlabel("Known-truth niche family (n = 10 each)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "nature_fig3b_consensus.png", dpi=300)
    plt.close(fig)


def render_v284(fig4: pd.DataFrame, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    ax.scatter(fig4["auc_presence_rank"], fig4["ecological_presence_rank"], alpha=0.55)
    lower = float(min(fig4["auc_presence_rank"].min(), fig4["ecological_presence_rank"].min()))
    upper = float(max(fig4["auc_presence_rank"].max(), fig4["ecological_presence_rank"].max()))
    ax.plot([lower, upper], [lower, upper], linewidth=1.2)
    ax.set_xlabel("AUC-selected role: sealed presence rank")
    ax.set_ylabel("Ecological role: sealed presence rank")
    ax.set_title("108/108 matched cells selected the same candidate")
    ax.set_xlim(lower - 0.02, upper + 0.02)
    ax.set_ylim(lower - 0.02, upper + 0.02)
    fig.tight_layout()
    fig.savefig(output_dir / "nature_fig4_empirical_identity.png", dpi=300)
    plt.close(fig)


def main() -> None:
    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fig3 = build_v272_source(args.v272_dir)
    fig4 = build_v284_source(args.v284_part)
    fig3.to_csv(args.output_dir / "nature_source_data_fig3.csv", index=False)
    fig4.to_csv(args.output_dir / "nature_source_data_fig4.csv", index=False)
    render_v272(fig3, args.output_dir)
    render_v284(fig4, args.output_dir)


if __name__ == "__main__":
    main()
