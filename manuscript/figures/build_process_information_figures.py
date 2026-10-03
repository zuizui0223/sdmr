#!/usr/bin/env python3
"""Build submission-facing quantitative figures from the canonical M5 receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METRICS = ROOT / "results" / "sdmr_v6_prospective_kt_v2_metrics.json"


def load_metrics(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("program") != "sdmr-v6-prospective-known-truth-v2":
        raise ValueError("wrong M5 metrics program")
    if data.get("passed") is not True:
        raise ValueError("canonical M5 endpoint is not PASS")
    if data.get("prospective_seed_min") != 74001 or data.get("prospective_seed_max") != 74020:
        raise ValueError("prospective seed denominator changed")
    return data


def figure_denominator(data: dict, out: Path) -> None:
    counts = data["counts"]
    metrics = data["metrics"]

    labels = [
        "Positive\ntargets",
        "Replaceable\ntargets",
        "Unresolved\ntargets",
        "Unavailable\ntargets",
        "Structural\nrefusal",
    ]
    denominators = [
        int(counts["positive"]),
        int(counts["replaceable"]),
        int(counts["unresolved"]),
        int(counts["unavailable"]),
        int(counts["structural_refusal"]),
    ]
    adverse = [
        int(round(counts["positive"] * (1.0 - float(metrics["positive_recovery"])))),
        int(round(counts["replaceable"] * float(metrics["false_positive_rate"]))),
        int(round(counts["unresolved"] * float(metrics["overresolution_rate"]))),
        int(round(counts["unavailable"] * float(metrics["unavailable_sharp_rate"]))),
        int(round(counts["structural_refusal"] * float(metrics["structural_refusal_violation_rate"]))),
    ]
    supported = [d - a for d, a in zip(denominators, adverse)]

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    x = list(range(len(labels)))
    ax.bar(x, supported, label="Correctly preserved / recovered")
    ax.bar(x, adverse, bottom=supported, label="Missed / violated")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Prospective process-state cells")
    ax.set_title("Prospective known-truth denominator and outcomes")
    for i, (d, a) in enumerate(zip(denominators, adverse)):
        if i == 0:
            ax.text(i, d + max(denominators) * 0.02, f"71/80 recovered", ha="center", va="bottom")
        else:
            ax.text(i, d + max(denominators) * 0.02, f"{a}/{d} violations", ha="center", va="bottom")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out, format="svg")
    plt.close(fig)


def figure_authorization(data: dict, out: Path) -> None:
    rates = data["informative_control_authorization_rates"]
    names = list(rates)
    values = [float(rates[name]) for name in names]
    names.extend(["omitted_driver", "observation_confounded\n(report-only)"])
    values.extend([
        float(data["metrics"]["w7_authorization_rate"]),
        float(data["metrics"]["report_only_world_authorization_rate"]),
    ])

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    x = list(range(len(names)))
    ax.bar(x, values)
    ax.set_ylim(0, 1.05)
    ax.set_xticks(x, [name.replace("_", "\n") for name in names], rotation=0)
    ax.set_ylabel("Full-system authorization rate")
    ax.set_title("Authorization across prospective known-truth worlds")
    for i, value in enumerate(values):
        ax.text(i, min(1.02, value + 0.025), f"{int(round(value * 20))}/20", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(out, format="svg")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    data = load_metrics(args.metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figure_denominator(data, args.output_dir / "figure3_prospective_denominator.svg")
    figure_authorization(data, args.output_dir / "figure4_world_authorization.svg")
    print(args.output_dir)


if __name__ == "__main__":
    main()
