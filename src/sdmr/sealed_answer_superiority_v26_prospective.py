"""Fresh prospective pipeline for sealed-answer superiority v26.

Upstream v21 support and v23 set construction remain truth-blind. The sealed
answer-check stream is opened only inside the already-audited v25 evidence
builder after model/prediction freezing. Known-truth labels are reserved for a
later terminal scorer after deterministic truth-blind reproduction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .alignment_transport_v15_development import _pair_routes
from .attribution_eligibility_v19 import predict_eligibility
from .attribution_eligibility_v19_prospective import (
    V15_CONFIG,
    V16_CONFIG,
    _base_objects,
    _closure_and_conditioning,
    _frames,
)
from .context_geometry_v17 import context_geometry_features
from .context_indexed_attribution import summarize_context_indexed_attribution
from .interval_evidence_process_challenge import _classify_processes as _classify_interval_processes
from .known_truth_scenarios import simulate_known_truth_plant_niche
from .model import ModelSpec
from .process_challenge_learner import CONTRIBUTORY
from .prospective_identification_validation import _selection_frames
from .sealed_answer_separator_v25 import build_sealed_answer_fold_evidence
from .sealed_answer_separator_v25_development import unused_separator_background
from .sealed_answer_superiority_v26 import classify_sealed_answer_superiority
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .separating_evidence_refinement_v24 import refine_context_sets
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
    if gov.get("seed_replacement_allowed") is not False:
        raise ValueError("v26 seed replacement must remain forbidden")
    if gov.get("family_replacement_allowed") is not False:
        raise ValueError("v26 family replacement must remain forbidden")
    return cfg


def assemble_truth_blind_v21_contexts(
    geometry_predictions: pd.DataFrame,
    activity_contexts: pd.DataFrame,
) -> pd.DataFrame:
    """Reproduce frozen v21 support booleans without generating-truth labels."""
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
    """Build v23 co-supported sets using only frozen v21 support booleans."""
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
    if _canonical_frame_bytes(expected) != _canonical_frame_bytes(context_sets):
        raise ValueError("context sets must be exact output of v23 build_context_sets")


def freeze_truth_blind_context_stage(
    geometry_predictions: pd.DataFrame,
    activity_contexts: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, object]:
    """Write fresh v21 decisions and v23 sets plus a truth-blind receipt."""
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


def support_shard(family: str, process: str, output_dir: str | Path) -> dict[str, object]:
    """Build one fresh v21-compatible family/process shard on v26 seeds."""
    cfg = load_contract()
    family = str(family)
    process = str(process)
    if family not in tuple(str(x) for x in cfg["families"]):
        raise ValueError("family outside frozen v26 denominator")
    if process not in tuple(str(x) for x in cfg["process_universe"]):
        raise ValueError("process outside frozen v26 process universe")

    dev, v6, sim, registry, ecological, observation, processes, specs = _base_objects()
    learner = v6["learner"]
    v15 = json.loads(V15_CONFIG.read_text(encoding="utf-8"))
    v16 = json.loads(V16_CONFIG.read_text(encoding="utf-8"))
    closure, conditioning, closure_ok = _closure_and_conditioning(registry, processes, process)
    if not closure_ok:
        raise ValueError("process closure is not available in frozen v21 machinery")

    geometry_rows: list[dict[str, object]] = []
    pair_rows: list[dict[str, object]] = []
    for seed in tuple(int(x) for x in cfg["fresh_seed_denominator"]):
        presence, background, p_groups, b_groups = _frames(family, seed, sim)
        target_blocks = sorted(set(p_groups.tolist()) & set(b_groups.tolist()))
        source_blocks = sorted(set(b_groups.tolist()))

        for target in target_blocks:
            ref = background.loc[b_groups != int(target)].reset_index(drop=True)
            tgt = background.loc[b_groups == int(target)].reset_index(drop=True)
            geom = context_geometry_features(
                ref,
                tgt,
                process_predictors=closure,
                conditioning_predictors=conditioning,
            )
            geometry_rows.append(
                {
                    "family": family,
                    "seed": seed,
                    "target_process": process,
                    "target_block": int(target),
                    "conditional_residual_shift": geom.conditional_residual_shift,
                    "conditional_residual_scale_ratio": geom.conditional_residual_scale_ratio,
                    "conditional_target_r2": geom.conditional_target_r2,
                    "process_support_shift": geom.process_support_shift,
                    "conditioning_support_shift": geom.conditioning_support_shift,
                    "n_reference": int(geom.n_reference),
                    "n_target": int(geom.n_target),
                }
            )

            for source in source_blocks:
                if int(source) == int(target):
                    continue
                routes, evaluable, reason = _pair_routes(
                    presence,
                    background,
                    p_groups,
                    b_groups,
                    process=process,
                    source_block=int(source),
                    target_block=int(target),
                    ecological=ecological,
                    observation=observation,
                    registry=registry,
                    processes=processes,
                    specs=specs,
                    learner=learner,
                    degree=int(dev["knockout_degree"]),
                    ridge_alpha=float(dev["knockout_ridge_alpha"]),
                    minimum_source_rows=int(v15["minimum_source_complete_rows"]),
                )
                pair_status = "unresolved"
                reproduces = False
                if evaluable:
                    classified = _classify_interval_processes(
                        routes,
                        (process,),
                        expected_model_labels=tuple(s.label for s in specs),
                    )
                    pair_status = str(classified.iloc[0]["status"])
                    reproduces = pair_status != CONTRIBUTORY
                pair_rows.append(
                    {
                        "family": family,
                        "seed": seed,
                        "target_process": process,
                        "source_block": int(source),
                        "target_block": int(target),
                        "evaluable": bool(evaluable),
                        "reproduces_v8_noncontributory": bool(reproduces),
                        "pair_status": pair_status,
                        "reason": str(reason),
                    }
                )

    geometry = predict_eligibility(pd.DataFrame(geometry_rows)) if geometry_rows else pd.DataFrame()
    pairs = pd.DataFrame(pair_rows)
    if pairs.empty:
        activity = pd.DataFrame()
    else:
        activity, _, _ = summarize_context_indexed_attribution(
            pairs,
            minimum_evaluable_sources=int(v16["minimum_evaluable_source_maps"]),
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    geometry.to_csv(out / "geometry_predictions.csv", index=False)
    activity.to_csv(out / "activity_contexts.csv", index=False)
    receipt: dict[str, object] = {
        "purpose": "sealed_answer_superiority_v26_fresh_support_shard",
        "family": family,
        "target_process": process,
        "fresh_seed_start": int(min(cfg["fresh_seed_denominator"])),
        "fresh_seed_end": int(max(cfg["fresh_seed_denominator"])),
        "n_geometry_contexts": int(len(geometry)),
        "n_activity_contexts": int(len(activity)),
        "truth_opened": False,
        "v21_threshold_changed": False,
        "classifier_refit": False,
    }
    (out / "support_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def assemble_context_stage_from_shards(
    input_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """Assemble exactly 24 frozen support shards and freeze fresh v23 sets."""
    cfg = load_contract()
    root = Path(input_dir)
    geometry_files = sorted(root.rglob("geometry_predictions.csv"))
    activity_files = sorted(root.rglob("activity_contexts.csv"))
    expected_shards = len(cfg["families"]) * len(cfg["process_universe"])
    if len(geometry_files) != expected_shards or len(activity_files) != expected_shards:
        raise ValueError(f"v26 context assembly requires exactly {expected_shards} geometry and activity shards")

    geometry = pd.concat([pd.read_csv(path) for path in geometry_files], ignore_index=True)
    activity = pd.concat([pd.read_csv(path) for path in activity_files], ignore_index=True)
    expected_pairs = {
        (str(family), str(process))
        for family in cfg["families"]
        for process in cfg["process_universe"]
    }
    for label, frame in (("geometry", geometry), ("activity", activity)):
        pairs = set(zip(frame["family"].astype(str), frame["target_process"].astype(str), strict=True))
        if pairs != expected_pairs:
            raise ValueError(f"{label} support shard roster drift")
        seeds = set(pd.to_numeric(frame["seed"], errors="raise").astype(int))
        if seeds != set(int(x) for x in cfg["fresh_seed_denominator"]):
            raise ValueError(f"{label} seed denominator drift")

    receipt = freeze_truth_blind_context_stage(geometry, activity, output_dir)
    decisions = pd.read_csv(Path(output_dir) / "context_decisions.csv")
    sets = pd.read_csv(Path(output_dir) / "context_sets.csv")
    expected_decisions = (
        len(cfg["families"])
        * len(cfg["fresh_seed_denominator"])
        * len(cfg["process_universe"])
        * int(cfg["simulation"]["outer_n_blocks"])
    )
    expected_contexts = (
        len(cfg["families"])
        * len(cfg["fresh_seed_denominator"])
        * int(cfg["simulation"]["outer_n_blocks"])
    )
    if len(decisions) != expected_decisions or len(sets) != expected_contexts:
        raise ValueError("fresh v21/v23 context denominator is incomplete; refusing silent case deletion")
    return receipt


def _members(value: object) -> tuple[str, ...]:
    if pd.isna(value):
        return ()
    text = str(value).strip()
    return tuple(part for part in text.split("+") if part) if text else ()


def _model_specs(cfg: dict) -> tuple[ModelSpec, ...]:
    specs = tuple(
        ModelSpec(
            C=float(row["C"]),
            degree=int(row["degree"]),
            penalty=str(row["penalty"]),
            random_state=int(row["random_state"]),
        )
        for row in cfg["separator"]["required_model_specs"]
    )
    if len({spec.label for spec in specs}) != len(specs):
        raise ValueError("v26 model labels must be unique")
    return specs


def _upstream_receipt(
    context_sets_digest: str,
    family: str,
    seed: int,
    process: str,
    blocks: list[int],
) -> str:
    payload = "|".join(
        [
            str(context_sets_digest),
            str(family),
            str(int(seed)),
            str(process),
            ",".join(str(int(block)) for block in sorted(blocks)),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_full_context_sets(contexts: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    required = {"family", "seed", "target_block", "supported_set", "supported_set_size"}
    missing = sorted(required - set(contexts.columns))
    if missing:
        raise KeyError("v23 context sets missing columns: " + ", ".join(missing))
    frame = contexts.copy()
    frame["family"] = frame["family"].astype(str)
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    if frame.duplicated(CONTEXT_SET_KEY).any():
        raise ValueError("duplicate v23 context key")
    if set(frame["family"]) != set(str(x) for x in cfg["families"]):
        raise ValueError("v23 family denominator drift")
    if set(frame["seed"]) != set(int(x) for x in cfg["fresh_seed_denominator"]):
        raise ValueError("v23 seed denominator drift")
    expected_contexts = (
        len(cfg["families"])
        * len(cfg["fresh_seed_denominator"])
        * int(cfg["simulation"]["outer_n_blocks"])
    )
    if len(frame) != expected_contexts:
        raise ValueError("v23 context denominator incomplete")
    universe = set(str(x) for x in cfg["process_universe"])
    for row in frame.itertuples(index=False):
        members = _members(row.supported_set)
        if int(row.supported_set_size) != len(members):
            raise ValueError("v23 supported_set_size mismatch")
        if not set(members).issubset(universe):
            raise ValueError("v23 set contains process outside v26 universe")
    return frame


def run_family_separator(
    family: str,
    context_sets_path: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """Generate and classify source-disjoint sealed superiority evidence."""
    cfg = load_contract()
    family = str(family)
    if family not in tuple(str(x) for x in cfg["families"]):
        raise ValueError("family outside frozen v26 denominator")
    contexts = _validate_full_context_sets(pd.read_csv(context_sets_path), cfg)
    family_contexts = contexts.loc[contexts["family"].eq(family)].copy()

    _, _, upstream_sim_cfg, registry, ecological, observation, _, _ = _base_objects()
    sim_cfg = cfg["simulation"]
    for key in ("n_cells", "n_occurrences", "n_target_group", "outer_n_blocks"):
        if int(upstream_sim_cfg[key]) != int(sim_cfg[key]):
            raise ValueError(f"v26 simulation contract drift: {key}")
    if float(upstream_sim_cfg["answer_check_fraction"]) != float(sim_cfg["answer_check_fraction"]):
        raise ValueError("v26 answer-check fraction drift")
    if int(upstream_sim_cfg["outer_random_state_offset"]) != int(sim_cfg["outer_random_state_offset"]):
        raise ValueError("v26 outer random-state offset drift")

    specs = _model_specs(cfg)
    required_labels = tuple(spec.label for spec in specs)
    context_digest = _sha256_frame(contexts)
    fold_parts: list[pd.DataFrame] = []
    separator_parts: list[pd.DataFrame] = []

    for seed in tuple(int(x) for x in cfg["fresh_seed_denominator"]):
        seed_contexts = family_contexts.loc[family_contexts["seed"].eq(seed)].copy()
        supported_blocks: dict[str, list[int]] = {}
        for row in seed_contexts.itertuples(index=False):
            for process in _members(row.supported_set):
                supported_blocks.setdefault(process, []).append(int(row.target_block))
        if not supported_blocks:
            continue

        simulation = simulate_known_truth_plant_niche(
            family,
            seed=seed,
            n_cells=int(sim_cfg["n_cells"]),
            n_occurrences=int(sim_cfg["n_occurrences"]),
            n_target_group=int(sim_cfg["n_target_group"]),
        )
        occurrences, support_background = _selection_frames(simulation, family=family, seed=seed)
        split = freeze_occurrence_answer_check_split(
            occurrences,
            id_col="occurrence_id",
            lon_col="longitude",
            lat_col="latitude",
            n_blocks=int(sim_cfg["outer_n_blocks"]),
            holdout_fraction=float(sim_cfg["answer_check_fraction"]),
            random_state=int(sim_cfg["outer_random_state_offset"]) + seed,
        )
        separator_background = unused_separator_background(
            simulation,
            n_rows=int(sim_cfg["separator_background_rows"]),
            random_state=int(sim_cfg["separator_background_seed_offset"]) + seed,
        )

        for process, blocks in sorted(supported_blocks.items()):
            evidence = build_sealed_answer_fold_evidence(
                occurrences,
                support_background,
                separator_background,
                occurrence_split=split,
                family=family,
                seed=seed,
                target_block=-1,
                target_process=process,
                process_registry=registry,
                ecological_predictors=ecological,
                observation_predictors=observation,
                model_specs=specs,
                selection_receipt=_upstream_receipt(context_digest, family, seed, process, blocks),
                outer_n_blocks=int(sim_cfg["outer_n_blocks"]),
                outer_holdout_fraction=float(sim_cfg["answer_check_fraction"]),
                outer_random_state=int(sim_cfg["outer_random_state_offset"]) + seed,
                probability_epsilon=float(cfg["separator"]["probability_epsilon"]),
            )
            fold_parts.append(evidence)
            state = classify_sealed_answer_superiority(
                evidence,
                required_model_labels=required_labels,
                sem_multiplier=float(cfg["separator"]["sem_multiplier"]),
                minimum_complete_occurrences=int(cfg["separator"]["minimum_complete_sealed_occurrences"]),
                minimum_sealed_blocks=int(cfg["separator"]["minimum_distinct_sealed_spatial_blocks"]),
            )
            if len(state) != 1:
                raise RuntimeError("case-level v26 separator did not produce one state")
            for target_block in sorted(blocks):
                clone = state.copy()
                clone["target_block"] = int(target_block)
                separator_parts.append(clone)

    fold_evidence = pd.concat(fold_parts, ignore_index=True) if fold_parts else pd.DataFrame()
    separator_evidence = pd.concat(separator_parts, ignore_index=True) if separator_parts else pd.DataFrame()
    if not separator_evidence.empty and separator_evidence.duplicated(
        ["family", "seed", "target_block", "target_process"]
    ).any():
        raise ValueError("duplicate v26 context-process separator state")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fold_evidence.to_csv(out / "fold_evidence.csv", index=False)
    separator_evidence.to_csv(out / "separator_evidence.csv", index=False)
    result: dict[str, object] = {
        "purpose": "sealed_answer_superiority_v26_truth_blind_family_result",
        "family": family,
        "n_fold_rows": int(len(fold_evidence)),
        "n_context_process_states": int(len(separator_evidence)),
        "state_counts": (
            separator_evidence["evidence_state"].value_counts().sort_index().to_dict()
            if len(separator_evidence)
            else {}
        ),
        "truth_opened": False,
    }
    (out / "family_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def aggregate_truth_blind(
    input_dir: str | Path,
    context_sets_path: str | Path,
    output_dir: str | Path,
    *,
    replicate_id: str,
) -> dict[str, object]:
    """Freeze one complete truth-blind refinement replicate."""
    cfg = load_contract()
    files = sorted(Path(input_dir).rglob("separator_evidence.csv"))
    if len(files) != len(cfg["families"]):
        raise ValueError(f"v26 aggregate requires exactly {len(cfg['families'])} separator shards")
    contexts = _validate_full_context_sets(pd.read_csv(context_sets_path), cfg)
    evidence_parts = [pd.read_csv(path) for path in files]
    evidence = pd.concat(evidence_parts, ignore_index=True) if evidence_parts else pd.DataFrame()
    if evidence.duplicated(["family", "seed", "target_block", "target_process"]).any():
        raise ValueError("duplicate v26 context-process evidence across shards")

    expected_members = {
        (str(row.family), int(row.seed), int(row.target_block), process)
        for row in contexts.itertuples(index=False)
        for process in _members(row.supported_set)
    }
    if expected_members:
        observed_members = set(
            zip(
                evidence["family"].astype(str),
                pd.to_numeric(evidence["seed"], errors="raise").astype(int),
                pd.to_numeric(evidence["target_block"], errors="raise").astype(int),
                evidence["target_process"].astype(str),
                strict=True,
            )
        )
    else:
        observed_members = set()
    if observed_members != expected_members:
        raise ValueError("v26 separator evidence denominator does not match v23 supported members")

    refinements, member_audit = refine_context_sets(
        contexts,
        evidence,
        required_separator_ids=(str(cfg["separator"]["separator_id"]),),
    )
    for label, frame in (("separator_evidence", evidence), ("context_refinements", refinements), ("member_audit", member_audit)):
        if any("truth" in str(col).lower() for col in frame.columns):
            raise ValueError(f"{label} contains truth-like columns before terminal scoring")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    evidence.to_csv(out / "separator_evidence.csv", index=False)
    refinements.to_csv(out / "context_refinements.csv", index=False)
    member_audit.to_csv(out / "member_audit.csv", index=False)
    receipt: dict[str, object] = {
        "purpose": "sealed_answer_superiority_v26_truth_blind_refinement_receipt",
        "replicate_id": str(replicate_id),
        "truth_opened": False,
        "n_contexts": int(len(refinements)),
        "n_supported_members": int(len(expected_members)),
        "n_separator_rows": int(len(evidence)),
        "context_sets_sha256": _sha256_frame(contexts),
        "separator_evidence_sha256": _sha256_frame(evidence),
        "context_refinements_sha256": _sha256_frame(refinements),
        "member_audit_sha256": _sha256_frame(member_audit),
    }
    (out / "truth_blind_refinement_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    shard = sub.add_parser("support-shard")
    shard.add_argument("--family", required=True)
    shard.add_argument("--process", required=True)
    shard.add_argument("--output-dir", required=True)

    contexts = sub.add_parser("assemble-contexts")
    contexts.add_argument("--input-dir", required=True)
    contexts.add_argument("--output-dir", required=True)

    family = sub.add_parser("run-family")
    family.add_argument("--family", required=True)
    family.add_argument("--context-sets", required=True)
    family.add_argument("--output-dir", required=True)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--input-dir", required=True)
    aggregate.add_argument("--context-sets", required=True)
    aggregate.add_argument("--output-dir", required=True)
    aggregate.add_argument("--replicate-id", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "support-shard":
        result = support_shard(args.family, args.process, args.output_dir)
    elif args.cmd == "assemble-contexts":
        result = assemble_context_stage_from_shards(args.input_dir, args.output_dir)
    elif args.cmd == "run-family":
        result = run_family_separator(args.family, args.context_sets, args.output_dir)
    else:
        result = aggregate_truth_blind(
            args.input_dir,
            args.context_sets,
            args.output_dir,
            replicate_id=args.replicate_id,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
