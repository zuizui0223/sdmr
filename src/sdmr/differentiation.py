"""Predeclared empirical differentiation gate versus conventional AUC/Boyce selection.

This gate is intentionally separate from Product-A method promotion. Promotion
asks whether one SDMR method is stable enough to freeze. Differentiation asks
whether that procedure demonstrates a practically non-trivial transfer advantage
against conventional selector baselines on identical outer-sealed cases.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

import pandas as pd


@dataclass(frozen=True)
class DifferentiationCriteria:
    required_comparators: tuple[str, ...]
    min_runs: int
    min_pairs_per_comparator: int
    min_mean_delta_presence_rank: float
    min_positive_pair_fraction: float
    min_positive_run_fraction: float


def read_differentiation_criteria(path: str | Path) -> DifferentiationCriteria:
    values = {row["criterion"]: row["value"] for row in csv.DictReader(Path(path).open(encoding="utf-8"))}
    required = {
        "required_comparators",
        "min_runs",
        "min_pairs_per_comparator",
        "min_mean_delta_presence_rank",
        "min_positive_pair_fraction",
        "min_positive_run_fraction",
    }
    missing = sorted(required - set(values))
    if missing:
        raise ValueError(f"differentiation criteria missing: {missing}")
    comparators = tuple(x.strip() for x in values["required_comparators"].split(";") if x.strip())
    if not comparators:
        raise ValueError("required_comparators must not be empty")
    return DifferentiationCriteria(
        required_comparators=comparators,
        min_runs=int(values["min_runs"]),
        min_pairs_per_comparator=int(values["min_pairs_per_comparator"]),
        min_mean_delta_presence_rank=float(values["min_mean_delta_presence_rank"]),
        min_positive_pair_fraction=float(values["min_positive_pair_fraction"]),
        min_positive_run_fraction=float(values["min_positive_run_fraction"]),
    )


def assess_differentiation(summary: pd.DataFrame, criteria: DifferentiationCriteria) -> tuple[pd.DataFrame, bool]:
    required_cols = {
        "comparator",
        "n_runs",
        "n_pairs",
        "mean_delta_presence_rank",
        "positive_pair_fraction",
        "positive_run_fraction",
    }
    missing = sorted(required_cols - set(summary.columns))
    if missing:
        raise KeyError(f"selector contrast summary missing columns: {missing}")

    indexed = summary.copy()
    indexed["comparator"] = indexed["comparator"].astype(str)
    rows = []
    for comparator in criteria.required_comparators:
        hit = indexed.loc[indexed["comparator"] == comparator]
        if len(hit) != 1:
            rows.append(
                {
                    "comparator": comparator,
                    "present": False,
                    "n_runs": 0,
                    "n_pairs": 0,
                    "mean_delta_presence_rank": float("nan"),
                    "positive_pair_fraction": float("nan"),
                    "positive_run_fraction": float("nan"),
                    "passes": False,
                    "failure_reason": "missing_or_duplicate_comparator",
                }
            )
            continue
        row = hit.iloc[0]
        checks = {
            "runs": int(row["n_runs"]) >= criteria.min_runs,
            "pairs": int(row["n_pairs"]) >= criteria.min_pairs_per_comparator,
            "mean_delta": float(row["mean_delta_presence_rank"]) >= criteria.min_mean_delta_presence_rank,
            "positive_pairs": float(row["positive_pair_fraction"]) >= criteria.min_positive_pair_fraction,
            "positive_runs": float(row["positive_run_fraction"]) >= criteria.min_positive_run_fraction,
        }
        failures = [name for name, passed in checks.items() if not passed]
        rows.append(
            {
                "comparator": comparator,
                "present": True,
                "n_runs": int(row["n_runs"]),
                "n_pairs": int(row["n_pairs"]),
                "mean_delta_presence_rank": float(row["mean_delta_presence_rank"]),
                "positive_pair_fraction": float(row["positive_pair_fraction"]),
                "positive_run_fraction": float(row["positive_run_fraction"]),
                "passes": not failures,
                "failure_reason": ";".join(failures),
            }
        )
    detail = pd.DataFrame(rows)
    overall = bool(len(detail) == len(criteria.required_comparators) and detail["passes"].all())
    return detail, overall
