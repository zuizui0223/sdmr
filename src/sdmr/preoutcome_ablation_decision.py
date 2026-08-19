"""Decision gate for sealed-blind Product-A v2.1 discovery ablations.

This module consumes only discovery/model-pool artifacts. It independently
reconstructs candidate outer-fold completeness across every predeclared taxon ×
perturbation cell and reports either readiness for known-truth development or an
explicit evidence-insufficiency abstention. Sealed validation outcomes are never
used to choose or rescue a candidate.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .niche_recovery_selection import RECOVERY_DIRECTIONS


@dataclass(frozen=True)
class PreoutcomeAblationDecision:
    status: str
    metrics_file: str | None
    benchmark_status_file: str | None
    expected_outer_folds: int
    expected_cells: tuple[str, ...]
    candidates_seen: tuple[str, ...]
    complete_prediction_candidates: tuple[str, ...]
    complete_ecological_candidates: tuple[str, ...]
    sealed_artifacts_detected: tuple[str, ...]
    uses_sealed_outcomes: bool = False
    scientific_promotion_run: bool = False

    @property
    def ready_for_known_truth(self) -> bool:
        return self.status == "ready_for_known_truth"

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ready_for_known_truth"] = self.ready_for_known_truth
        return payload


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _find_csv(
    root: Path,
    *,
    preferred_name: str,
    required_columns: Iterable[str],
) -> tuple[Path | None, pd.DataFrame]:
    required = set(required_columns)
    paths = sorted(root.rglob("*.csv"))
    preferred = [path for path in paths if path.name == preferred_name]
    ordered = [*preferred, *(path for path in paths if path not in preferred)]
    for path in ordered:
        frame = _read_csv(path)
        if required <= set(frame.columns):
            return path, frame
    return None, pd.DataFrame()


def _cell_key(species: object, perturbation: object) -> str:
    return f"{str(species)}::{str(perturbation)}"


def _finite_in_every_expected_fold(
    frame: pd.DataFrame,
    expected_folds: set[int],
    required_columns: tuple[str, ...],
) -> bool:
    fold_values = pd.to_numeric(frame["fold"], errors="coerce")
    if fold_values.isna().any():
        return False
    observed = set(fold_values.astype(int))
    if observed != expected_folds:
        return False
    for fold in sorted(expected_folds):
        rows = frame.loc[fold_values.astype(int).eq(fold)]
        if rows.empty:
            return False
        for column in required_columns:
            values = pd.to_numeric(rows[column], errors="coerce").to_numpy(float)
            if not np.isfinite(values).any():
                return False
    return True


def _complete_candidates(
    metrics: pd.DataFrame,
    expected_cells: tuple[str, ...],
    expected_outer_folds: int,
    required_columns: tuple[str, ...],
) -> tuple[str, ...]:
    required = {"candidate", "species", "perturbation", "fold", *required_columns}
    if metrics.empty or not required <= set(metrics.columns):
        return ()
    data = metrics.copy()
    data["candidate"] = data["candidate"].astype(str)
    data["__cell"] = [
        _cell_key(species, perturbation)
        for species, perturbation in zip(data["species"], data["perturbation"])
    ]
    expected_cell_set = set(expected_cells)
    expected_folds = set(range(int(expected_outer_folds)))
    complete: list[str] = []
    for candidate, candidate_rows in data.groupby("candidate", sort=True):
        observed_cells = set(candidate_rows["__cell"].astype(str))
        if observed_cells != expected_cell_set:
            continue
        candidate_ok = True
        for cell in expected_cells:
            cell_rows = candidate_rows.loc[candidate_rows["__cell"].eq(cell)]
            if not _finite_in_every_expected_fold(
                cell_rows,
                expected_folds,
                required_columns,
            ):
                candidate_ok = False
                break
        if candidate_ok:
            complete.append(str(candidate))
    return tuple(sorted(complete))


def _detect_sealed_artifacts(root: Path) -> tuple[str, ...]:
    detected: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        lower_name = path.name.lower()
        if any(
            marker in lower_name
            for marker in (
                "validation_outer_sealed",
                "sealed_validation",
                "external_validation",
            )
        ):
            detected.add(str(path.relative_to(root)))
            continue
        if path.suffix.lower() != ".csv":
            continue
        frame = _read_csv(path)
        forbidden_columns = {
            column
            for column in frame.columns
            if str(column).lower().startswith("sealed_")
            or str(column).lower().startswith("n_sealed_")
        }
        if forbidden_columns:
            detected.add(
                f"{path.relative_to(root)}::{','.join(sorted(forbidden_columns))}"
            )
    return tuple(sorted(detected))


def summarize_preoutcome_ablation(
    input_dir: str | Path,
    *,
    expected_outer_folds: int = 2,
) -> tuple[PreoutcomeAblationDecision, pd.DataFrame]:
    """Reconstruct complete-fold candidate eligibility without sealed outcomes."""

    if expected_outer_folds < 2:
        raise ValueError("expected_outer_folds must be >= 2")
    root = Path(input_dir)
    if not root.exists():
        raise FileNotFoundError(root)

    sealed = _detect_sealed_artifacts(root)
    metrics_path, metrics = _find_csv(
        root,
        preferred_name="discovery_procedure_fold_metrics.csv",
        required_columns=("candidate", "species", "perturbation", "fold"),
    )
    status_path, benchmark_status = _find_csv(
        root,
        preferred_name="discovery_benchmark_status.csv",
        required_columns=("species", "perturbation"),
    )

    if not benchmark_status.empty:
        expected_cells = tuple(
            sorted(
                {
                    _cell_key(species, perturbation)
                    for species, perturbation in zip(
                        benchmark_status["species"],
                        benchmark_status["perturbation"],
                    )
                }
            )
        )
    elif not metrics.empty:
        expected_cells = tuple(
            sorted(
                {
                    _cell_key(species, perturbation)
                    for species, perturbation in zip(
                        metrics["species"], metrics["perturbation"]
                    )
                }
            )
        )
    else:
        expected_cells = ()

    candidates_seen = (
        tuple(sorted(metrics["candidate"].astype(str).unique()))
        if not metrics.empty and "candidate" in metrics.columns
        else ()
    )
    prediction_complete = _complete_candidates(
        metrics,
        expected_cells,
        expected_outer_folds,
        ("presence_rank",),
    )
    ecological_complete = _complete_candidates(
        metrics,
        expected_cells,
        expected_outer_folds,
        ("presence_rank", *tuple(RECOVERY_DIRECTIONS)),
    )

    if sealed:
        status = "invalid_sealed_artifact_present"
    elif not expected_cells:
        status = "abstain_no_predeclared_discovery_cells"
    elif not candidates_seen:
        status = "abstain_no_candidate_fold_metrics"
    elif not prediction_complete:
        status = "abstain_no_complete_prediction_candidate"
    elif not ecological_complete:
        status = "abstain_no_complete_ecological_candidate"
    else:
        status = "ready_for_known_truth"

    decision = PreoutcomeAblationDecision(
        status=status,
        metrics_file=(
            str(metrics_path.relative_to(root)) if metrics_path is not None else None
        ),
        benchmark_status_file=(
            str(status_path.relative_to(root)) if status_path is not None else None
        ),
        expected_outer_folds=int(expected_outer_folds),
        expected_cells=expected_cells,
        candidates_seen=candidates_seen,
        complete_prediction_candidates=prediction_complete,
        complete_ecological_candidates=ecological_complete,
        sealed_artifacts_detected=sealed,
    )

    candidate_rows = []
    prediction_set = set(prediction_complete)
    ecology_set = set(ecological_complete)
    for candidate in candidates_seen:
        candidate_rows.append(
            {
                "candidate": candidate,
                "complete_prediction_evidence": candidate in prediction_set,
                "complete_ecological_evidence": candidate in ecology_set,
                "expected_discovery_cells": len(expected_cells),
                "expected_outer_folds_per_cell": int(expected_outer_folds),
            }
        )
    return decision, pd.DataFrame(candidate_rows)


def _markdown(decision: PreoutcomeAblationDecision) -> str:
    return "\n".join(
        [
            "# Product-A v2.1 pre-outcome decision",
            "",
            f"- status: `{decision.status}`",
            f"- ready for known-truth development: `{decision.ready_for_known_truth}`",
            f"- expected discovery cells: `{len(decision.expected_cells)}`",
            f"- expected outer folds per cell: `{decision.expected_outer_folds}`",
            f"- candidates seen: `{len(decision.candidates_seen)}`",
            "- complete prediction candidates: "
            + (", ".join(f"`{x}`" for x in decision.complete_prediction_candidates) or "none"),
            "- complete ecological candidates: "
            + (", ".join(f"`{x}`" for x in decision.complete_ecological_candidates) or "none"),
            "- sealed artifacts detected: "
            + (", ".join(f"`{x}`" for x in decision.sealed_artifacts_detected) or "none"),
            "",
            "This is a development-only, sealed-blind decision. It is not a Product-A promotion result.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    parser.add_argument("--output-candidates", required=True)
    parser.add_argument("--expected-outer-folds", type=int, default=2)
    args = parser.parse_args(argv)

    decision, candidates = summarize_preoutcome_ablation(
        args.input_dir,
        expected_outer_folds=args.expected_outer_folds,
    )
    json_path = Path(args.output_json)
    markdown_path = Path(args.output_markdown)
    candidates_path = Path(args.output_candidates)
    for path in (json_path, markdown_path, candidates_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(decision.as_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(decision) + "\n", encoding="utf-8")
    candidates.to_csv(candidates_path, index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
