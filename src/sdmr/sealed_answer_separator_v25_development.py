"""Consumed-development runner for the sealed answer-check separator v25.

The runner is intentionally split into truth-blind family/refinement stages and a
separate known-truth scoring stage.  Seeds 17001--17010 are already consumed by
v21 and may not support a fresh performance claim here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .attribution_eligibility_v19_prospective import _base_objects
from .known_truth_scenarios import simulate_known_truth_plant_niche
from .model import ModelSpec
from .prospective_identification_validation import _selection_frames
from .sealed_answer_separator_v25 import (
    build_sealed_answer_fold_evidence,
    classify_sealed_answer_separator,
)
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .separating_evidence_refinement_v24 import (
    refine_context_sets,
    score_known_truth_refinement,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "configs" / "sealed_answer_separator_v25_development.json"
HIDDEN_SIMULATION_COLUMNS = (
    "true_suitability",
    "sampling_effort",
    "focal_recording_multiplier",
    "scenario",
)


def load_contract(path: str | Path = CONTRACT_PATH) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if cfg.get("purpose") != "sealed_answer_separator_v25_consumed_development":
        raise ValueError("wrong v25 development contract")
    if cfg.get("development_only") is not True:
        raise ValueError("v25 consumed endpoint must remain development-only")
    seeds = tuple(int(x) for x in cfg.get("consumed_seed_denominator", ()))
    if seeds != tuple(range(17001, 17011)):
        raise ValueError("v25 consumed seed denominator changed")
    families = tuple(str(x) for x in cfg.get("families", ()))
    if len(families) != 6 or len(set(families)) != 6:
        raise ValueError("v25 family denominator changed")
    if tuple(cfg.get("process_universe", ())) != (
        "temperature", "water", "seasonality", "noise"
    ):
        raise ValueError("v25 process universe changed")
    sep = cfg.get("separator", {})
    if float(sep.get("density_noninferiority_margin_nats", -1)) != 0.01:
        raise ValueError("v25 density margin changed")
    if float(sep.get("sem_multiplier", -1)) != 1.0:
        raise ValueError("v25 SEM multiplier changed")
    if int(sep.get("minimum_complete_sealed_occurrences", -1)) != 10:
        raise ValueError("v25 sealed occurrence coverage changed")
    if int(sep.get("minimum_distinct_sealed_spatial_blocks", -1)) != 2:
        raise ValueError("v25 sealed block coverage changed")
    specs = tuple(sep.get("required_model_specs", ()))
    if len(specs) != 6:
        raise ValueError("v25 required model roster changed")
    gov = cfg.get("governance", {})
    if gov.get("truth_may_be_opened_only_after_truth_blind_refinement_is_written") is not True:
        raise ValueError("v25 truth-open ordering guard changed")
    if gov.get("fresh_validation_authorized") is not False:
        raise ValueError("fresh validation must remain unauthorized in v25 development")
    if gov.get("fresh_seed_allocation_authorized") is not False:
        raise ValueError("fresh seed allocation must remain unauthorized in v25 development")
    return cfg


def _coord_keys(frame: pd.DataFrame) -> set[tuple[float, float]]:
    lon = pd.to_numeric(frame["longitude"], errors="raise").to_numpy(float)
    lat = pd.to_numeric(frame["latitude"], errors="raise").to_numpy(float)
    return set(zip(np.round(lon, 12), np.round(lat, 12), strict=True))


def unused_separator_background(
    simulation,
    *,
    n_rows: int,
    random_state: int,
) -> pd.DataFrame:
    """Sample deterministic reference rows never used by v21 inputs."""
    environment = simulation.environment.copy()
    used = _coord_keys(simulation.occurrences) | _coord_keys(simulation.target_group)
    env_keys = list(
        zip(
            np.round(pd.to_numeric(environment["longitude"], errors="raise").to_numpy(float), 12),
            np.round(pd.to_numeric(environment["latitude"], errors="raise").to_numpy(float), 12),
            strict=True,
        )
    )
    keep = np.asarray([key not in used for key in env_keys], dtype=bool)
    available = environment.loc[keep].copy()
    n_rows = int(n_rows)
    if n_rows < 1 or len(available) < n_rows:
        raise ValueError("insufficient unused simulation rows for separator background")
    rng = np.random.default_rng(int(random_state))
    chosen = np.sort(rng.choice(len(available), size=n_rows, replace=False))
    out = available.iloc[chosen].reset_index(drop=True)
    out = out.drop(columns=list(HIDDEN_SIMULATION_COLUMNS), errors="ignore")
    if _coord_keys(out) & used:
        raise RuntimeError("unused separator background is not source-disjoint")
    return out


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
    if len({x.label for x in specs}) != len(specs):
        raise ValueError("v25 model labels must be unique")
    return specs


def _members(value: object) -> tuple[str, ...]:
    if pd.isna(value):
        return ()
    text = str(value).strip()
    return tuple(x for x in text.split("+") if x) if text else ()


def _validate_context_sets(contexts: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    required = {
        "family", "seed", "target_block", "supported_set", "supported_set_size"
    }
    missing = sorted(required - set(contexts.columns))
    if missing:
        raise KeyError("v23 context sets missing columns: " + ", ".join(missing))
    frame = contexts.copy()
    frame["family"] = frame["family"].astype(str)
    frame["seed"] = pd.to_numeric(frame["seed"], errors="raise").astype(int)
    frame["target_block"] = pd.to_numeric(frame["target_block"], errors="raise").astype(int)
    if frame.duplicated(["family", "seed", "target_block"]).any():
        raise ValueError("duplicate v23 context key")
    expected_families = set(str(x) for x in cfg["families"])
    expected_seeds = set(int(x) for x in cfg["consumed_seed_denominator"])
    if set(frame["family"]) != expected_families or set(frame["seed"]) != expected_seeds:
        raise ValueError("v23 context denominator drift")
    if len(frame) != len(expected_families) * len(expected_seeds) * 8:
        raise ValueError("v23 context count drift")
    universe = set(str(x) for x in cfg["process_universe"])
    for row in frame.itertuples(index=False):
        members = _members(row.supported_set)
        if int(row.supported_set_size) != len(members):
            raise ValueError("v23 supported_set_size mismatch")
        if not set(members).issubset(universe):
            raise ValueError("v23 set contains process outside v25 universe")
    return frame


def _upstream_receipt(cfg: dict, family: str, seed: int, process: str, blocks: list[int]) -> str:
    payload = "|".join(
        [
            str(cfg["base_v23"]["v23_artifact_digest"]),
            str(family),
            str(int(seed)),
            str(process),
            ",".join(str(int(x)) for x in sorted(blocks)),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_family(
    family: str,
    context_sets_path: str | Path,
    output_dir: str | Path,
) -> dict:
    cfg = load_contract()
    family = str(family)
    if family not in tuple(cfg["families"]):
        raise ValueError("family outside frozen v25 denominator")
    contexts = _validate_context_sets(pd.read_csv(context_sets_path), cfg)
    contexts = contexts.loc[contexts["family"].eq(family)].copy()

    _, _, upstream_sim_cfg, registry, ecological, observation, _, _ = _base_objects()
    sim_cfg = cfg["simulation"]
    for key in ("n_cells", "n_occurrences", "n_target_group", "outer_n_blocks"):
        if int(upstream_sim_cfg[key]) != int(sim_cfg[key]):
            raise ValueError(f"v25 simulation contract drift: {key}")
    if float(upstream_sim_cfg["answer_check_fraction"]) != float(sim_cfg["answer_check_fraction"]):
        raise ValueError("v25 answer-check fraction drift")
    if int(upstream_sim_cfg["outer_random_state_offset"]) != int(sim_cfg["outer_random_state_offset"]):
        raise ValueError("v25 outer random-state offset drift")

    specs = _model_specs(cfg)
    required_labels = tuple(x.label for x in specs)
    all_fold_rows: list[pd.DataFrame] = []
    separator_rows: list[pd.DataFrame] = []

    for seed in tuple(int(x) for x in cfg["consumed_seed_denominator"]):
        seed_contexts = contexts.loc[contexts["seed"].eq(seed)].copy()
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
        occurrences, support_background = _selection_frames(
            simulation, family=family, seed=seed
        )
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
            receipt = _upstream_receipt(cfg, family, seed, process, blocks)
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
                selection_receipt=receipt,
                outer_n_blocks=int(sim_cfg["outer_n_blocks"]),
                outer_holdout_fraction=float(sim_cfg["answer_check_fraction"]),
                outer_random_state=int(sim_cfg["outer_random_state_offset"]) + seed,
                probability_epsilon=float(cfg["separator"]["probability_epsilon"]),
            )
            all_fold_rows.append(evidence)
            state = classify_sealed_answer_separator(
                evidence,
                required_model_labels=required_labels,
                margin=float(cfg["separator"]["density_noninferiority_margin_nats"]),
                sem_multiplier=float(cfg["separator"]["sem_multiplier"]),
                minimum_complete_occurrences=int(cfg["separator"]["minimum_complete_sealed_occurrences"]),
                minimum_sealed_blocks=int(cfg["separator"]["minimum_distinct_sealed_spatial_blocks"]),
            )
            if len(state) != 1:
                raise RuntimeError("case-level v25 separator did not produce one state")
            for target_block in sorted(blocks):
                clone = state.copy()
                clone["target_block"] = int(target_block)
                separator_rows.append(clone)

    fold_evidence = pd.concat(all_fold_rows, ignore_index=True) if all_fold_rows else pd.DataFrame()
    separator_evidence = pd.concat(separator_rows, ignore_index=True) if separator_rows else pd.DataFrame()
    if not separator_evidence.empty and separator_evidence.duplicated(
        ["family", "seed", "target_block", "target_process"]
    ).any():
        raise ValueError("duplicate v25 context-process separator state")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fold_evidence.to_csv(out / "fold_evidence.csv", index=False)
    separator_evidence.to_csv(out / "separator_evidence.csv", index=False)
    result = {
        "purpose": "sealed_answer_separator_v25_consumed_family_result",
        "family": family,
        "n_fold_rows": int(len(fold_evidence)),
        "n_context_process_states": int(len(separator_evidence)),
        "state_counts": (
            separator_evidence["evidence_state"].value_counts().sort_index().to_dict()
            if len(separator_evidence)
            else {}
        ),
        "truth_opened": False,
        "fresh_validation_authorized": False,
    }
    (out / "family_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def aggregate(
    input_dir: str | Path,
    context_sets_path: str | Path,
    output_dir: str | Path,
) -> dict:
    cfg = load_contract()
    contexts = _validate_context_sets(pd.read_csv(context_sets_path), cfg)
    files = sorted(Path(input_dir).rglob("separator_evidence.csv"))
    if len(files) != len(cfg["families"]):
        raise ValueError("v25 aggregate requires exactly one separator shard per family")
    evidence = pd.concat([pd.read_csv(x) for x in files], ignore_index=True)
    if evidence.duplicated(["family", "seed", "target_block", "target_process"]).any():
        raise ValueError("duplicate v25 context-process evidence across shards")

    expected_members = {
        (str(row.family), int(row.seed), int(row.target_block), process)
        for row in contexts.itertuples(index=False)
        for process in _members(row.supported_set)
    }
    observed_members = set(
        zip(
            evidence["family"].astype(str),
            pd.to_numeric(evidence["seed"], errors="raise").astype(int),
            pd.to_numeric(evidence["target_block"], errors="raise").astype(int),
            evidence["target_process"].astype(str),
            strict=True,
        )
    )
    if observed_members != expected_members:
        raise ValueError("v25 separator evidence denominator does not match v23 supported members")

    refinements, member_audit = refine_context_sets(
        contexts,
        evidence,
        required_separator_ids=(str(cfg["separator"]["separator_id"]),),
    )
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    evidence.to_csv(out / "separator_evidence.csv", index=False)
    refinements.to_csv(out / "context_refinements.csv", index=False)
    member_audit.to_csv(out / "member_audit.csv", index=False)
    receipt = {
        "purpose": "sealed_answer_separator_v25_truth_blind_refinement_receipt",
        "n_contexts": int(len(refinements)),
        "n_supported_members": int(len(expected_members)),
        "n_separator_rows": int(len(evidence)),
        "context_sets_sha256": _sha256_file(context_sets_path),
        "separator_evidence_sha256": _sha256_file(out / "separator_evidence.csv"),
        "context_refinements_sha256": _sha256_file(out / "context_refinements.csv"),
        "truth_opened": False,
        "fresh_validation_authorized": False,
    }
    (out / "truth_blind_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def score(
    refinement_path: str | Path,
    output_dir: str | Path,
) -> dict:
    cfg = load_contract()
    refinements = pd.read_csv(refinement_path, keep_default_na=False)
    required = {"family", "seed", "target_block", "base_supported_set", "refined_supported_set"}
    missing = sorted(required - set(refinements.columns))
    if missing:
        raise KeyError("v25 refinement missing columns: " + ", ".join(missing))

    process_universe = tuple(str(x) for x in cfg["process_universe"])
    true_processes = set(str(x) for x in cfg["true_processes_for_development_scoring"])
    truth_rows: list[dict[str, object]] = []
    for row in refinements.itertuples(index=False):
        for process in process_universe:
            truth_rows.append(
                {
                    "family": str(row.family),
                    "seed": int(row.seed),
                    "target_block": int(row.target_block),
                    "target_process": process,
                    "generating_process_true": process in true_processes,
                }
            )
    truth = pd.DataFrame(truth_rows)
    metrics = score_known_truth_refinement(refinements, truth)
    screen = cfg["development_advancement_screen"]
    advancement = bool(
        int(metrics["n_removed_true_members"]) <= int(screen["n_removed_true_members_max"])
        and int(metrics["n_removed_false_members"]) >= int(screen["n_removed_false_members_min"])
    )
    result = {
        "purpose": "sealed_answer_separator_v25_consumed_development_decision",
        **metrics,
        "development_advancement_screen_passed": advancement,
        "prospective_contract_freeze_authorized": advancement,
        "fresh_seed_allocation_authorized": False,
        "fresh_validation_authorized": False,
        "empirical_validation_authorized": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "known_truth_score.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "development_decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    family_parser = sub.add_parser("run-family")
    family_parser.add_argument("--family", required=True)
    family_parser.add_argument("--context-sets", required=True)
    family_parser.add_argument("--output-dir", required=True)

    aggregate_parser = sub.add_parser("aggregate")
    aggregate_parser.add_argument("--input-dir", required=True)
    aggregate_parser.add_argument("--context-sets", required=True)
    aggregate_parser.add_argument("--output-dir", required=True)

    score_parser = sub.add_parser("score")
    score_parser.add_argument("--refinement", required=True)
    score_parser.add_argument("--output-dir", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "run-family":
        result = run_family(args.family, args.context_sets, args.output_dir)
    elif args.cmd == "aggregate":
        result = aggregate(args.input_dir, args.context_sets, args.output_dir)
    else:
        result = score(args.refinement, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
