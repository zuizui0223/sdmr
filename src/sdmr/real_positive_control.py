"""Prospective real-data positive controls for counterfactual process membership.

SDM fitting and process scores are created without access to the external
biological process labels. Literature-backed labels are opened only after the
truth-blind temperature/water scores have been completed for all taxa and all
three frozen accessible-area specifications.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from .empirical_product_a_v2 import EmpiricalNichePerturbation
from .model import ModelSpec
from .niche_recovery_cv import RecoveryCandidate, cross_validated_niche_recovery
from .pilot import OUTER_ROLE_COL

PROCESS_NAMES = ("temperature", "water")


def load_contract(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_real_positive_control_process_membership_v1":
        raise ValueError("wrong real positive-control contract")
    if payload.get("frozen_before_sdm_outcome") is not True:
        raise ValueError("positive-control contract was not frozen pre-outcome")
    if payload.get("external_truth_role") != "positive_control_only_no_negative_process_truth":
        raise ValueError("external evidence role changed")
    return payload


def _groups_from_manifest(manifest: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    required = {"predictor", "validation_process"}
    missing = required - set(manifest.columns)
    if missing:
        raise KeyError(f"positive-control manifest missing columns: {sorted(missing)}")
    groups = {
        str(group): tuple(frame["predictor"].astype(str))
        for group, frame in manifest.groupby("validation_process", sort=True)
    }
    for name in (*PROCESS_NAMES, "neutral"):
        if not groups.get(name):
            raise ValueError(f"manifest has no predictors for {name!r}")
    return groups


def build_candidates(
    manifest: pd.DataFrame, contract: Mapping[str, object]
) -> tuple[dict[str, RecoveryCandidate], dict[str, tuple[str, ...]]]:
    groups = _groups_from_manifest(manifest)
    definitions = contract["candidate_library"]["candidates"]
    spec = ModelSpec(C=0.1, degree=1, penalty="l2", random_state=0)
    candidates: dict[str, RecoveryCandidate] = {}
    process_map: dict[str, tuple[str, ...]] = {}
    for name, group_names in definitions.items():
        predictors: list[str] = []
        processes: list[str] = []
        for group in tuple(str(x) for x in group_names):
            if group not in groups:
                raise ValueError(f"candidate {name!r} references unknown group {group!r}")
            predictors.extend(groups[group])
            if group in PROCESS_NAMES:
                processes.append(group)
        candidates[str(name)] = RecoveryCandidate(
            str(name), tuple(dict.fromkeys(predictors)), spec
        )
        process_map[str(name)] = tuple(sorted(set(processes)))
    return candidates, process_map


def summarize_candidates(metrics: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fold metrics without any external biological truth."""
    required = {"candidate", "presence_rank", "niche_overlap_schoener_d_pc12"}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"candidate metrics missing columns: {sorted(missing)}")
    rows = []
    for candidate, frame in metrics.groupby("candidate", sort=True):
        auc = pd.to_numeric(frame["presence_rank"], errors="coerce")
        overlap = pd.to_numeric(frame["niche_overlap_schoener_d_pc12"], errors="coerce")
        keep = np.isfinite(auc) & np.isfinite(overlap)
        auc, overlap = auc[keep], overlap[keep]
        if not len(auc):
            continue
        mean_auc = float(auc.mean())
        sem = float(auc.std(ddof=1) / np.sqrt(len(auc))) if len(auc) >= 2 else 0.0
        rows.append(
            {
                "candidate": str(candidate),
                "n_folds": int(len(auc)),
                "mean_presence_rank": mean_auc,
                "sem_presence_rank": sem,
                "mean_niche_overlap_schoener_d_pc12": float(overlap.mean()),
                "prediction_adequate": bool(
                    mean_auc >= 0.51 - 1e-12 and mean_auc - sem >= 0.50 - 1e-12
                ),
            }
        )
    return pd.DataFrame(rows)


def process_scores_from_summary(
    summary: pd.DataFrame,
    candidate_processes: Mapping[str, tuple[str, ...]],
) -> pd.DataFrame:
    """Return truth-blind counterfactual T/W scores for one taxon × M case."""
    adequate = summary.loc[summary["prediction_adequate"].astype(bool)].copy()
    rows = []
    overlap_col = "mean_niche_overlap_schoener_d_pc12"
    for process in PROCESS_NAMES:
        if adequate.empty:
            rows.append({"process": process, "score": np.nan, "status": "no_adequate_candidate"})
            continue
        containing = adequate.loc[
            adequate["candidate"].map(lambda x: process in candidate_processes[str(x)])
        ]
        excluded = adequate.loc[
            adequate["candidate"].map(lambda x: process not in candidate_processes[str(x)])
        ]
        if containing.empty:
            score, status = -1.0, "no_adequate_process_candidate"
        elif excluded.empty:
            score, status = 1.0, "no_adequate_excluded_candidate"
        else:
            values = adequate[overlap_col].to_numpy(float)
            span = float(np.max(values) - np.min(values))
            if span <= 1e-12:
                score, status = 0.0, "zero_overlap_range"
            else:
                score = float(
                    (containing[overlap_col].max() - excluded[overlap_col].max()) / span
                )
                status = "compared"
        rows.append(
            {
                "process": process,
                "score": score,
                "status": status,
                "n_adequate": int(len(adequate)),
                "n_containing": int(len(containing)),
                "n_excluded": int(len(excluded)),
                "best_containing_overlap": (
                    float(containing[overlap_col].max()) if len(containing) else np.nan
                ),
                "best_excluded_overlap": (
                    float(excluded[overlap_col].max()) if len(excluded) else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def aggregate_process_scores(
    process_scores: pd.DataFrame, required_specs: tuple[str, ...]
) -> pd.DataFrame:
    """Require all three frozen M specifications for a taxon-level score."""
    rows = []
    for species, species_frame in process_scores.groupby("species", sort=True):
        for process in PROCESS_NAMES:
            frame = species_frame.loc[species_frame["process"].eq(process)].copy()
            finite = pd.to_numeric(frame["score"], errors="coerce")
            complete = bool(
                set(frame["m_spec"].astype(str)) == set(required_specs)
                and len(frame) == len(required_specs)
                and np.isfinite(finite).all()
            )
            rows.append(
                {
                    "species": str(species),
                    "process": process,
                    "case_score": float(finite.mean()) if complete else np.nan,
                    "positive_m_count": int((finite > 0).sum()) if complete else 0,
                    "m_complete": complete,
                    "m_scores": ";".join(
                        f"{r.m_spec}:{float(r.score):.8g}"
                        for r in frame.sort_values("m_spec").itertuples()
                        if np.isfinite(float(r.score))
                    ),
                }
            )
    return pd.DataFrame(rows)


def evaluate_positive_controls(
    aggregated: pd.DataFrame,
    taxa_with_labels: pd.DataFrame,
    contract: Mapping[str, object],
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Open literature-backed positive labels only after SDM scores are frozen."""
    rule = contract["positive_control_recovery_rule"]
    rows = []
    for taxon in taxa_with_labels.itertuples(index=False):
        species = str(taxon.scientific_name)
        expected = str(taxon.expected_process)
        competitor = "water" if expected == "temperature" else "temperature"
        frame = aggregated.loc[aggregated["species"].eq(species)].set_index("process")
        available = expected in frame.index and competitor in frame.index
        if available:
            expected_score = float(frame.loc[expected, "case_score"])
            competing_score = float(frame.loc[competitor, "case_score"])
            positive_m_count = int(frame.loc[expected, "positive_m_count"])
            available = bool(np.isfinite(expected_score) and np.isfinite(competing_score))
        else:
            expected_score = competing_score = np.nan
            positive_m_count = 0
        # Positive controls provide evidence that the expected process matters;
        # they do NOT establish that the other process is absent or weaker.
        recovered = bool(
            available
            and expected_score > 0
            and positive_m_count >= int(rule["expected_process_positive_m_count_min"])
        )
        rows.append(
            {
                "species": species,
                "expected_process": expected,
                "evidence_type": str(taxon.evidence_type),
                "evidence_doi": str(taxon.evidence_doi),
                "expected_process_score": expected_score,
                "competing_process_score_descriptive": competing_score,
                "expected_process_positive_m_count": positive_m_count,
                "available": bool(available),
                "recovered": recovered,
            }
        )
    results = pd.DataFrame(rows)
    denominator = len(taxa_with_labels)
    recovered_n = int(results["recovered"].sum())
    required_n = int(
        math.ceil(float(rule["primary_overall_recovery_min"]) * denominator - 1e-12)
    )
    group_counts = {
        process: int(
            results.loc[results["expected_process"].eq(process), "recovered"].sum()
        )
        for process in PROCESS_NAMES
    }
    supported = bool(
        denominator == 4
        and recovered_n >= required_n
        and all(
            value >= int(rule["minimum_recovered_per_process_group"])
            for value in group_counts.values()
        )
    )
    decision = {
        "purpose": "product_a_real_positive_control_decision_v1",
        "supported": supported,
        "n_taxa": denominator,
        "recovered_n": recovered_n,
        "recovery_fraction": recovered_n / denominator if denominator else np.nan,
        "required_recovered_n": required_n,
        "recovered_by_expected_process": group_counts,
        "unavailable_n": int((~results["available"]).sum()),
        "external_truth_is_positive_control_only": True,
        "competing_process_is_descriptive_only": True,
        "no_negative_process_truth_inferred": True,
        "v2_8_4_empirical_endpoint_unchanged": True,
    }
    return results, decision


def _read_species_rows(path: Path, species: str, columns: list[str]) -> pd.DataFrame:
    allowed = set(columns)
    frame = pd.read_csv(path, usecols=lambda c: c in allowed)
    if "species" not in frame.columns:
        raise KeyError(f"{path} lacks species")
    return frame.loc[frame["species"].astype(str).eq(species)].reset_index(drop=True)


def _candidate_fold_metrics(
    perturbation: EmpiricalNichePerturbation,
    candidates: Mapping[str, RecoveryCandidate],
    audit_predictors: tuple[str, ...],
) -> pd.DataFrame:
    """Evaluate every candidate without selecting a winner."""
    frames = []
    for name in sorted(candidates):
        candidate = candidates[name]
        frame = cross_validated_niche_recovery(
            perturbation.presence,
            perturbation.background,
            perturbation.presence_groups,
            perturbation.background_groups,
            candidate.predictors,
            audit_predictors,
            n_splits=3,
            model_spec=candidate.model_spec,
        )
        if len(frame):
            frame = frame.copy()
            frame["candidate"] = name
            frame["n_predictors"] = len(candidate.predictors)
            frame["model"] = candidate.model_spec.label
            frames.append(frame)
    if not frames:
        raise ValueError("no positive-control candidate could be evaluated")
    return pd.concat(frames, ignore_index=True)


def run_endpoint(
    prepared_dir: str | Path,
    manifest_path: str | Path,
    taxa_path: str | Path,
    contract_path: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_contract(contract_path)
    manifest = pd.read_csv(manifest_path)
    # Keep only species identities in memory until every SDM score is complete.
    taxa_names = pd.read_csv(taxa_path, usecols=["scientific_name"])
    candidates, candidate_processes = build_candidates(manifest, contract)
    audit_predictors = tuple(manifest["predictor"].astype(str))
    required_specs = tuple(str(x) for x in contract["accessible_area"]["required_specs"])
    seed = int(contract["occurrence_gate"]["seed"])
    root = Path(prepared_dir)
    occurrence_path = root / "pilot_occurrences.csv"
    if not occurrence_path.exists():
        raise SystemExit("prepared positive-control evidence lacks pilot_occurrences.csv")
    required_cols = ["species", "longitude", "latitude", OUTER_ROLE_COL, *audit_predictors]

    fold_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []
    process_frames: list[pd.DataFrame] = []
    availability_rows: list[dict[str, object]] = []

    for taxon_i, species in enumerate(taxa_names["scientific_name"].astype(str)):
        occ = _read_species_rows(occurrence_path, species, required_cols)
        for m_i, m_spec in enumerate(required_specs):
            bg_path = root / "specifications" / m_spec / "background.csv"
            try:
                if occ.empty or not bg_path.exists():
                    raise ValueError("missing eligible occurrence/background evidence")
                bg = _read_species_rows(bg_path, species, required_cols)
                if bg.empty:
                    raise ValueError("empty species background")
                perturbation = EmpiricalNichePerturbation.from_preassigned_outer_roles(
                    m_spec,
                    "accessible_area_sensitivity",
                    occ,
                    bg,
                    n_spatial_blocks=5,
                    random_state=seed + taxon_i * 100 + m_i,
                )
                metrics = _candidate_fold_metrics(
                    perturbation, candidates, audit_predictors
                )
                metrics["species"] = species
                metrics["m_spec"] = m_spec
                fold_frames.append(metrics)
                summary = summarize_candidates(metrics)
                summary["species"] = species
                summary["m_spec"] = m_spec
                candidate_frames.append(summary)
                scores = process_scores_from_summary(summary, candidate_processes)
                scores["species"] = species
                scores["m_spec"] = m_spec
                process_frames.append(scores)
                availability_rows.append(
                    {"species": species, "m_spec": m_spec, "available": True, "error": ""}
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                availability_rows.append(
                    {"species": species, "m_spec": m_spec, "available": False, "error": str(exc)}
                )

    folds = pd.concat(fold_frames, ignore_index=True) if fold_frames else pd.DataFrame()
    candidate_out = (
        pd.concat(candidate_frames, ignore_index=True) if candidate_frames else pd.DataFrame()
    )
    process_scores = (
        pd.concat(process_frames, ignore_index=True)
        if process_frames
        else pd.DataFrame(columns=["process", "score", "status", "species", "m_spec"])
    )
    aggregated = aggregate_process_scores(process_scores, required_specs)

    # Only now open the external experimental/transplant positive-control labels.
    taxa_with_labels = pd.read_csv(taxa_path)
    results, decision = evaluate_positive_controls(
        aggregated, taxa_with_labels, contract
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    folds.to_csv(out / "real_positive_control_fold_metrics.csv", index=False)
    candidate_out.to_csv(out / "real_positive_control_candidate_summary.csv", index=False)
    process_scores.to_csv(out / "real_positive_control_process_scores.csv", index=False)
    aggregated.to_csv(out / "real_positive_control_aggregated_scores.csv", index=False)
    pd.DataFrame(availability_rows).to_csv(
        out / "real_positive_control_availability.csv", index=False
    )
    results.to_csv(out / "real_positive_control_taxon_results.csv", index=False)
    (out / "real_positive_control_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return decision


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prepared-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--taxa", required=True)
    p.add_argument("--contract", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args(argv)
    decision = run_endpoint(
        args.prepared_dir, args.manifest, args.taxa, args.contract, args.output_dir
    )
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
