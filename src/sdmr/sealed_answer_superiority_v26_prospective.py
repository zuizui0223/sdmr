"""Fresh prospective orchestration helpers for sealed-answer superiority v26.

This module keeps upstream support/set construction truth-blind. Known-truth
labels are reserved for the terminal scoring stage after immutable receipts and
an independent deterministic reproduction gate exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .set_valued_attribution_v23 import build_context_sets


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "sealed_answer_superiority_v26_prospective.json"
KEY = ["family", "seed", "target_process", "target_block"]
CONTEXT_SET_KEY = ["family", "seed", "target_block"]


def load_contract(path: str | Path = CONFIG) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if cfg.get("purpose") != "sealed_answer_superiority_v26_prospective_known_truth_validation":
        raise ValueError("wrong v26 prospective contract")
    if tuple(int(x) for x in cfg.get("fresh_seed_denominator", ())) != tuple(range(20001, 20021)):
        raise ValueError("v26 fresh seed denominator changed")
    families = tuple(str(x) for x in cfg.get("families", ()))
    if families != (
        "gaussian", "asymmetric", "soft_threshold", "interaction",
        "omitted_driver", "observation_confounded",
    ):
        raise ValueError("v26 family denominator changed")
    if tuple(cfg.get("process_universe", ())) != (
        "temperature", "water", "seasonality", "noise"
    ):
        raise ValueError("v26 process universe changed")
    sep = cfg.get("separator", {})
    if float(sep.get("sem_multiplier", -1)) != 1.96:
        raise ValueError("v26 SEM multiplier changed")
    if float(sep.get("superiority_boundary", 1)) != 0.0:
        raise ValueError("v26 superiority boundary changed")
    if int(sep.get("minimum_complete_sealed_occurrences", -1)) != 10:
        raise ValueError("v26 sealed occurrence coverage changed")
    if int(sep.get("minimum_distinct_sealed_spatial_blocks", -1)) != 2:
        raise ValueError("v26 sealed block coverage changed")
    if len(tuple(sep.get("required_model_specs", ()))) != 6:
        raise ValueError("v26 required model roster changed")
    gov = cfg.get("governance", {})
    if gov.get("truth_open_after_refinement_receipt_only") is not True:
        raise ValueError("v26 truth-open ordering guard changed")
    if gov.get("independent_truth_blind_reproduction_required_before_truth_open") is not True:
        raise ValueError("v26 reproduction guard changed")
    if gov.get("post_outcome_rule_changes_allowed") is not False:
        raise ValueError("v26 post-outcome rule changes must remain forbidden")
    return cfg


def assemble_truth_blind_v21_contexts(
    geometry_predictions: pd.DataFrame,
    activity_contexts: pd.DataFrame,
) -> pd.DataFrame:
    """Reproduce the frozen v21 support booleans without opening generating truth."""
    geometry_required = set(KEY) | {"eligibility_prediction"}
    activity_required = set(KEY) | {"context_status"}
    missing_geometry = sorted(geometry_required - set(geometry_predictions.columns))
    missing_activity = sorted(activity_required - set(activity_contexts.columns))
    if missing_geometry:
        raise KeyError("geometry predictions missing columns: " + ", ".join(missing_geometry))
    if missing_activity:
        raise KeyError("activity contexts missing columns: " + ", ".join(missing_activity))

    geometry = geometry_predictions[list(KEY) + ["eligibility_prediction"]].copy()
    activity = activity_contexts[list(KEY) + ["context_status"]].copy()
    if geometry.duplicated(KEY).any() or activity.duplicated(KEY).any():
        raise ValueError("duplicate v21 context key")
    frame = geometry.merge(activity, on=KEY, how="inner", validate="one_to_one")
    if len(frame) != len(geometry) or len(frame) != len(activity):
        raise ValueError("geometry/activity v21 context denominator mismatch")
    frame["supported"] = frame["context_status"].astype(str).eq("context_contributory")
    frame["high_confidence_supported"] = (
        frame["supported"]
        & frame["eligibility_prediction"].astype(str).eq("eligible")
    )
    return frame


def build_truth_blind_v23_sets(context_decisions: pd.DataFrame) -> pd.DataFrame:
    """Build v23 co-supported sets using only the frozen v21 support booleans."""
    sets = build_context_sets(context_decisions)
    forbidden = [col for col in sets.columns if "truth" in str(col).lower()]
    if forbidden:
        raise RuntimeError("truth-like columns leaked into v23 context sets")
    return sets


def _canonical_frame_bytes(frame: pd.DataFrame) -> bytes:
    canonical = frame.copy()
    columns = sorted(str(col) for col in canonical.columns)
    canonical = canonical[columns]
    if columns:
        canonical = canonical.sort_values(columns, kind="mergesort", na_position="last").reset_index(drop=True)
    return canonical.to_csv(index=False, lineterminator="\n", float_format="%.17g").encode("utf-8")


def _sha256_frame(frame: pd.DataFrame) -> str:
    return hashlib.sha256(_canonical_frame_bytes(frame)).hexdigest()


def validate_context_set_provenance(
    context_decisions: pd.DataFrame,
    context_sets: pd.DataFrame,
) -> None:
    """Require exact identity with v23 ``build_context_sets`` output."""
    expected = build_truth_blind_v23_sets(context_decisions)
    expected_bytes = _canonical_frame_bytes(expected)
    observed_bytes = _canonical_frame_bytes(context_sets)
    if expected_bytes != observed_bytes:
        raise ValueError("context sets must be exact output of v23 build_context_sets")


def freeze_truth_blind_context_stage(
    geometry_predictions: pd.DataFrame,
    activity_contexts: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, object]:
    """Write v21 decisions and v23 sets plus a truth-blind immutable receipt."""
    decisions = assemble_truth_blind_v21_contexts(geometry_predictions, activity_contexts)
    sets = build_truth_blind_v23_sets(decisions)
    validate_context_set_provenance(decisions, sets)
    for label, frame in (("context_decisions", decisions), ("context_sets", sets)):
        forbidden = [col for col in frame.columns if "truth" in str(col).lower()]
        if forbidden:
            raise ValueError(f"{label} contains truth-like columns before terminal scoring")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    decisions.to_csv(out / "context_decisions.csv", index=False)
    sets.to_csv(out / "context_sets.csv", index=False)
    receipt: dict[str, object] = {
        "purpose": "sealed_answer_superiority_v26_preterminal_context_receipt",
        "truth_opened": False,
        "context_set_constructor": "set_valued_attribution_v23.build_context_sets",
        "n_context_decision_rows": int(len(decisions)),
        "n_contexts": int(len(sets)),
        "context_decisions_sha256": _sha256_frame(decisions),
        "context_sets_sha256": _sha256_frame(sets),
    }
    (out / "preterminal_context_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
