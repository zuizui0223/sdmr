"""Reconstruct concrete v2.7.2 process-identification results from a frozen artifact.

Reporting-only utility. It does not fit models, select candidates, alter truth,
or change any Product-A scientific endpoint.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

import pandas as pd


FAMILIES = (
    "asymmetric",
    "gaussian",
    "interaction",
    "observation_confounded",
    "omitted_driver",
    "soft_threshold",
)

CANONICAL_SELECTOR = "canonical_replicated_observation_niche_recovery"
ROBUST_SELECTOR = "replicated_observation_perturbation_robust_niche_recovery"
AUC_SELECTOR = "canonical_auc"


def parse_set(value: str) -> set[str]:
    return set(ast.literal_eval(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v272-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cert = pd.read_csv(args.v272_dir / "ecological_inference_certificates.csv")
    truth_eval = pd.read_csv(args.v272_dir / "truth_evaluation.csv")
    required = {
        "scenario",
        "seed",
        "canonical_candidate",
        "robust_candidate",
        "model_consensus",
        "canonical_processes",
        "robust_processes",
        "stable_process_core",
        "contested_processes",
        "true_processes",
    }
    missing = required.difference(cert.columns)
    if missing:
        raise ValueError(f"missing v2.7.2 columns: {sorted(missing)}")
    if len(cert) != 60:
        raise ValueError(f"expected 60 certificate cases, found {len(cert)}")
    if len(truth_eval) != 180:
        raise ValueError(f"expected 180 selector truth rows, found {len(truth_eval)}")
    if set(cert["scenario"]) != set(FAMILIES):
        raise ValueError("unexpected frozen niche-family set")

    for col in (
        "canonical_processes",
        "robust_processes",
        "stable_process_core",
        "contested_processes",
        "true_processes",
    ):
        cert[col + "_set"] = cert[col].map(parse_set)

    cert["stable_exact"] = cert.apply(
        lambda r: r["stable_process_core_set"] == r["true_processes_set"], axis=1
    )
    cert["canonical_exact"] = cert.apply(
        lambda r: r["canonical_processes_set"] == r["true_processes_set"], axis=1
    )
    cert["robust_exact"] = cert.apply(
        lambda r: r["robust_processes_set"] == r["true_processes_set"], axis=1
    )
    cert["model_disagreement"] = ~cert["model_consensus"].astype(bool)

    stable_exact = int(cert["stable_exact"].sum())
    canonical_exact = int(cert["canonical_exact"].sum())
    robust_exact = int(cert["robust_exact"].sum())
    model_disagreement = int(cert["model_disagreement"].sum())
    stable_exact_when_model_disagrees = int(
        (cert["stable_exact"] & cert["model_disagreement"]).sum()
    )

    assert stable_exact == 55
    assert canonical_exact == 52
    assert robust_exact == 54
    assert model_disagreement == 22
    assert stable_exact_when_model_disagrees == 19

    family_rows: list[dict[str, object]] = []
    for family in FAMILIES:
        group = cert.loc[cert["scenario"] == family]
        disagreements = group["model_disagreement"]
        n_disagreements = int(disagreements.sum())
        exact_among = int((group["stable_exact"] & disagreements).sum())
        family_rows.append(
            {
                "scenario": family,
                "n": len(group),
                "stable_exact_n": int(group["stable_exact"].sum()),
                "stable_exact_rate": float(group["stable_exact"].mean()),
                "canonical_exact_n": int(group["canonical_exact"].sum()),
                "canonical_exact_rate": float(group["canonical_exact"].mean()),
                "robust_exact_n": int(group["robust_exact"].sum()),
                "robust_exact_rate": float(group["robust_exact"].mean()),
                "model_disagreement_n": n_disagreements,
                "stable_exact_among_model_disagreement_n": exact_among,
                "stable_exact_among_model_disagreement_rate": (
                    exact_among / n_disagreements if n_disagreements else None
                ),
            }
        )
    family_rows.append(
        {
            "scenario": "ALL",
            "n": 60,
            "stable_exact_n": stable_exact,
            "stable_exact_rate": stable_exact / 60,
            "canonical_exact_n": canonical_exact,
            "canonical_exact_rate": canonical_exact / 60,
            "robust_exact_n": robust_exact,
            "robust_exact_rate": robust_exact / 60,
            "model_disagreement_n": model_disagreement,
            "stable_exact_among_model_disagreement_n": stable_exact_when_model_disagrees,
            "stable_exact_among_model_disagreement_rate": (
                stable_exact_when_model_disagrees / model_disagreement
            ),
        }
    )
    exact_df = pd.DataFrame(family_rows)
    exact_df.to_csv(
        args.output_dir / "nature_v272_exact_process_recovery.csv", index=False
    )

    universe = set().union(*cert["true_processes_set"], *cert["stable_process_core_set"])
    if universe != {"soil", "temperature", "water"}:
        raise ValueError(f"unexpected process universe: {sorted(universe)}")

    process_rows: list[dict[str, object]] = []
    for process in ("soil", "temperature", "water"):
        truth = cert["true_processes_set"].map(lambda s: process in s)
        stable = cert["stable_process_core_set"].map(lambda s: process in s)
        contested = cert["contested_processes_set"].map(lambda s: process in s)
        canonical = cert["canonical_processes_set"].map(lambda s: process in s)
        robust = cert["robust_processes_set"].map(lambda s: process in s)
        absent_both = ~(canonical | robust)
        tp = int((truth & stable).sum())
        fp = int((~truth & stable).sum())
        fn = int((truth & ~stable).sum())
        tn = int((~truth & ~stable).sum())
        process_rows.append(
            {
                "process": process,
                "truth_present_n": int(truth.sum()),
                "truth_absent_n": int((~truth).sum()),
                "stable_true_positive_n": tp,
                "stable_false_positive_n": fp,
                "stable_false_negative_n": fn,
                "stable_true_negative_n": tn,
                "stable_precision": tp / (tp + fp) if tp + fp else None,
                "stable_recall": tp / (tp + fn) if tp + fn else None,
                "stable_specificity": tn / (tn + fp) if tn + fp else None,
                "contested_true_n": int((truth & contested).sum()),
                "contested_false_n": int((~truth & contested).sum()),
                "absent_from_both_when_true_n": int((truth & absent_both).sum()),
                "absent_from_both_when_false_n": int((~truth & absent_both).sum()),
            }
        )

    process_df = pd.DataFrame(process_rows)
    process_df.to_csv(
        args.output_dir / "nature_v272_process_identification_summary.csv", index=False
    )

    soil = process_df.loc[process_df["process"] == "soil"].iloc[0]
    assert int(soil["truth_present_n"]) == 10
    assert int(soil["truth_absent_n"]) == 50
    assert int(soil["stable_true_positive_n"]) == 7
    assert int(soil["stable_false_positive_n"]) == 2
    assert int(soil["stable_false_negative_n"]) == 3
    assert int(soil["contested_true_n"]) == 3
    assert int(soil["contested_false_n"]) == 7
    assert int(soil["absent_from_both_when_true_n"]) == 0
    assert int(soil["absent_from_both_when_false_n"]) == 41

    for process in ("temperature", "water"):
        row = process_df.loc[process_df["process"] == process].iloc[0]
        assert int(row["truth_present_n"]) == 60
        assert int(row["stable_true_positive_n"]) == 60
        assert int(row["stable_false_negative_n"]) == 0

    # Controlled-truth comparison with the conventional AUC-selected role.
    for selector in (CANONICAL_SELECTOR, ROBUST_SELECTOR, AUC_SELECTOR):
        if len(truth_eval.loc[truth_eval["selector"] == selector]) != 60:
            raise ValueError(f"unexpected selector count: {selector}")

    selector_exact = (
        truth_eval.assign(process_exact=truth_eval["driver_process_f1"].eq(1.0))
        .groupby(["scenario", "selector"], as_index=False)["process_exact"]
        .sum()
    )

    comparison_rows: list[dict[str, object]] = []
    for family in FAMILIES:
        stable_row = exact_df.loc[exact_df["scenario"] == family].iloc[0]
        family_eval = selector_exact.loc[selector_exact["scenario"] == family]
        values = dict(zip(family_eval["selector"], family_eval["process_exact"]))
        comparison_rows.append(
            {
                "scenario": family,
                "n": 10,
                "stable_core_exact_n": int(stable_row["stable_exact_n"]),
                "auc_process_exact_n": int(values[AUC_SELECTOR]),
                "canonical_ecological_exact_n": int(values[CANONICAL_SELECTOR]),
                "robust_ecological_exact_n": int(values[ROBUST_SELECTOR]),
            }
        )
    comparison_rows.append(
        {
            "scenario": "ALL",
            "n": 60,
            "stable_core_exact_n": stable_exact,
            "auc_process_exact_n": int(
                truth_eval.loc[truth_eval["selector"] == AUC_SELECTOR, "driver_process_f1"].eq(1.0).sum()
            ),
            "canonical_ecological_exact_n": canonical_exact,
            "robust_ecological_exact_n": robust_exact,
        }
    )
    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df.to_csv(
        args.output_dir / "nature_v272_selector_process_comparison.csv", index=False
    )

    overall = comparison_df.loc[comparison_df["scenario"] == "ALL"].iloc[0]
    assert int(overall["auc_process_exact_n"]) == 50
    assert int(overall["stable_core_exact_n"]) == 55

    obs_eval = truth_eval.loc[
        (truth_eval["scenario"] == "observation_confounded")
        & (truth_eval["selector"] == AUC_SELECTOR)
    ].copy()
    assert len(obs_eval) == 10
    assert int(obs_eval["driver_process_f1"].eq(1.0).sum()) == 5
    assert int(obs_eval["candidate"].eq("observer_only").sum()) == 5
    assert bool(
        obs_eval.loc[obs_eval["candidate"] == "observer_only", "driver_process_f1"].eq(0.0).all()
    )
    obs_cert = cert.loc[cert["scenario"] == "observation_confounded"]
    assert int(obs_cert["stable_exact"].sum()) == 10
    assert bool(obs_cert["canonical_candidate"].eq("niche_plus_observer").all())
    assert bool(obs_cert["robust_candidate"].eq("niche_plus_observer").all())

    worked = cert.loc[
        ((cert["scenario"] == "asymmetric") & (cert["seed"] == 3103))
        | ((cert["scenario"] == "omitted_driver") & (cert["seed"] == 3101))
        | ((cert["scenario"] == "soft_threshold") & (cert["seed"] == 3106)),
        [
            "scenario",
            "seed",
            "canonical_candidate",
            "robust_candidate",
            "canonical_processes",
            "robust_processes",
            "stable_process_core",
            "contested_processes",
            "true_processes",
        ],
    ].copy()
    if len(worked) != 3:
        raise ValueError("worked-example rows missing")
    worked.to_csv(args.output_dir / "nature_v272_worked_process_examples.csv", index=False)

    print(f"exact stable process-set recovery: {stable_exact}/60")
    print(
        "exact stable recovery when fitted models disagree: "
        f"{stable_exact_when_model_disagrees}/{model_disagreement}"
    )
    print("AUC-selected exact process-set recovery: 50/60")
    print("observation-confounded: stable core 10/10 exact; AUC role 5/10 exact")
    print(process_df.to_string(index=False))
    print(comparison_df.to_string(index=False))


if __name__ == "__main__":
    main()
