"""Development-only orchestration for v22 relative attribution.

The denominator is derived mechanically from the authoritative v21 terminal
context table. Directional evidence is then computed symmetrically within each
frozen target context. One non-target spatial block is omitted from training at
a time; frozen ModelSpecs are averaged within that perturbation and source
perturbations are the uncertainty units.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .attribution_eligibility_v19_prospective import _base_objects
from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, simulate_known_truth_plant_niche
from .model import fit_relative_suitability_model, score_ecological_suitability, score_relative_suitability
from .observation_aware_identification import _prepare_observation_corrections, _weighted_presence_rank
from .process_information_closure import process_information_closure
from .prospective_identification_validation import _selection_frames
from .proxy_closed_route_process_challenge import _presence_rank
from .relative_attribution_v22 import (
    DIRECTIONAL_NEGATIVE,
    DIRECTIONAL_POSITIVE,
    DIRECTIONAL_UNRESOLVED,
    build_supported_pair_manifest,
    extract_symmetric_pairwise_evidence,
)
from .sealed_occurrence_contract import freeze_occurrence_answer_check_split
from .validation import make_spatial_partition

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "relative_attribution_v22_development.json"


def load_contract() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("purpose") != "relative_attribution_v22_development":
        raise ValueError("wrong v22 contract")
    if cfg.get("scope") != "development_only_on_consumed_v21_seeds":
        raise ValueError("v22 must remain consumed-development only")
    if tuple(int(x) for x in cfg.get("consumed_seed_denominator", ())) != tuple(range(17001, 17011)):
        raise ValueError("v22 seed denominator changed")
    rule = cfg.get("pairwise_rule", {})
    if rule.get("symmetry_required") is not True:
        raise ValueError("v22 requires mirrored pair evidence")
    if int(rule.get("minimum_source_perturbations", 0)) != 3:
        raise ValueError("v22 source-perturbation floor changed")
    if float(rule.get("rank_margin")) != 0.02 or float(rule.get("density_margin")) != 0.01:
        raise ValueError("v22 inherited scientific margins changed")
    forbidden = set(cfg.get("forbidden", ()))
    required_forbidden = {
        "seasonality_specific_penalty", "process_name_specific_threshold",
        "post_truth_threshold_tuning", "fresh_empirical_claim",
    }
    if not required_forbidden.issubset(forbidden):
        raise ValueError("v22 forbidden-rule set weakened")
    return cfg


def freeze_pair_manifest(context_decisions_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    cfg = load_contract(); source = cfg["authoritative_v21_source"]
    frame = pd.read_csv(context_decisions_csv)
    expected_rows = int(source["expected_context_rows"])
    if len(frame) != expected_rows:
        raise ValueError(f"v21 context row denominator drift: {len(frame)} != {expected_rows}")
    seeds = tuple(sorted(pd.to_numeric(frame["seed"], errors="raise").astype(int).unique().tolist()))
    if seeds != tuple(cfg["consumed_seed_denominator"]):
        raise ValueError("v21 seed denominator drift")
    families = tuple(sorted(frame["family"].astype(str).unique().tolist()))
    if families != tuple(sorted(cfg["families"])):
        raise ValueError("v21 family denominator drift")
    processes = tuple(sorted(frame["target_process"].astype(str).unique().tolist()))
    if processes != tuple(sorted(cfg["processes"])):
        raise ValueError("v21 process denominator drift")
    pairs = build_supported_pair_manifest(frame, process_order=tuple(cfg["processes"]))
    contexts = pairs[["family", "seed", "target_block"]].drop_duplicates()
    expected_contexts = int(source["expected_contexts_with_at_least_two_supported_processes"])
    expected_pairs = int(source["expected_unordered_supported_pairs"])
    if len(contexts) != expected_contexts or len(pairs) != expected_pairs:
        raise ValueError(
            f"v22 denominator drift: contexts={len(contexts)}/{expected_contexts}, pairs={len(pairs)}/{expected_pairs}"
        )
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(out / "pair_manifest.csv", index=False)
    receipt = {
        "purpose": "relative_attribution_v22_frozen_pair_manifest",
        "development_only": True,
        "source_v21_workflow_run": int(source["workflow_run"]),
        "source_v21_terminal_artifact": int(source["terminal_artifact"]),
        "source_v21_artifact_digest": str(source["artifact_digest"]),
        "n_context_rows": int(len(frame)),
        "n_co_supported_contexts": int(len(contexts)),
        "n_unordered_supported_pairs": int(len(pairs)),
        "generating_truth_used_for_pair_selection": False,
        "fresh_validation_authorized": False,
    }
    (out / "pair_manifest_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _score(model, p_test, b_test, b_reference, predictors, observation, correction, eps):
    p_full = score_relative_suitability(model, p_test, predictors)
    b_full = score_relative_suitability(model, b_test, predictors)
    p_eco = score_ecological_suitability(
        model, p_test, predictors, observation_predictors=observation, observation_reference=b_reference
    )
    b_eco = score_ecological_suitability(
        model, b_test, predictors, observation_predictors=observation, observation_reference=b_reference
    )
    return {
        "prediction_rank": float(_presence_rank(p_full, b_full)),
        "ecological_rank": float(_weighted_presence_rank(p_eco, b_eco, correction.weights)),
        "ecological_density": float(
            balanced_density_ratio_log_score(
                p_eco, b_eco, presence_weights=correction.weights, probability_epsilon=float(eps)
            )
        ),
    }


def _direction_state(evidence: pd.DataFrame, prefix: str, *, n_specs: int, learner: dict, cfg: dict) -> dict:
    perturbations = []
    for source, group in evidence.groupby("source_block", sort=True):
        complete = group.loc[group["complete"].astype(bool)]
        if len(complete) != int(n_specs):
            continue
        perturbations.append({
            "source_block": int(source),
            "prediction_rank": float(complete[f"{prefix}_base_prediction_rank"].mean()),
            "ecological_rank": float(complete[f"{prefix}_base_ecological_rank"].mean()),
            "rank_loss": float(complete[f"{prefix}_conditional_rank_loss"].mean()),
            "density_loss": float(complete[f"{prefix}_conditional_density_loss"].mean()),
        })
    minimum = int(cfg["pairwise_rule"]["minimum_source_perturbations"])
    if len(perturbations) < minimum:
        return {"state": DIRECTIONAL_UNRESOLVED, "n_source_perturbations": int(len(perturbations))}
    frame = pd.DataFrame(perturbations)

    def mean_sem(col):
        x = frame[col].to_numpy(float)
        return float(np.mean(x)), float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0

    pmean, psem = mean_sem("prediction_rank"); emean, esem = mean_sem("ecological_rank")
    rmean, rsem = mean_sem("rank_loss"); dmean, dsem = mean_sem("density_loss")
    chance = float(learner["chance_score"]); floor = chance + float(learner["minimum_margin"])
    adequate = bool(
        pmean >= floor - 1e-12 and pmean - psem >= chance - 1e-12
        and emean >= floor - 1e-12 and emean - esem >= chance - 1e-12
    )
    if not adequate:
        state = DIRECTIONAL_UNRESOLVED
    else:
        qualifies = bool(
            rmean - rsem > float(cfg["pairwise_rule"]["rank_margin"])
            and dmean - dsem > float(cfg["pairwise_rule"]["density_margin"])
        )
        state = DIRECTIONAL_POSITIVE if qualifies else DIRECTIONAL_NEGATIVE
    return {
        "state": state,
        "n_source_perturbations": int(len(frame)),
        "base_prediction_rank_mean": pmean,
        "base_prediction_rank_sem": psem,
        "base_ecological_rank_mean": emean,
        "base_ecological_rank_sem": esem,
        "conditional_rank_loss_mean": rmean,
        "conditional_rank_loss_sem": rsem,
        "conditional_density_loss_mean": dmean,
        "conditional_density_loss_sem": dsem,
    }


def evaluate_pair_context(family: str, seed: int, target_block: int, process_a: str, process_b: str):
    cfg = load_contract()
    dev, v6, sim, registry, ecological, observation, _, specs = _base_objects()
    if family not in KNOWN_TRUTH_FAMILIES or int(seed) not in cfg["consumed_seed_denominator"]:
        raise ValueError("pair outside v22 denominator")
    learner = v6["learner"]
    simulation = simulate_known_truth_plant_niche(
        family, seed=int(seed), n_cells=int(sim["n_cells"]),
        n_occurrences=int(sim["n_occurrences"]), n_target_group=int(sim["n_target_group"]),
    )
    occurrences, background = _selection_frames(simulation, family=family, seed=int(seed))
    split = freeze_occurrence_answer_check_split(
        occurrences, id_col="occurrence_id", lon_col="longitude", lat_col="latitude",
        n_blocks=int(sim["outer_n_blocks"]), holdout_fraction=float(sim["answer_check_fraction"]),
        random_state=int(sim["outer_random_state_offset"]) + int(seed),
    )
    presence = split.model_pool(occurrences)
    inner = make_spatial_partition(
        presence["longitude"].to_numpy(float), presence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float), background["latitude"].to_numpy(float),
        n_blocks=int(sim["inner_n_blocks"]), holdout_fraction=0.20,
        random_state=int(sim["inner_random_state_offset"]) + int(seed),
    )
    pg = np.asarray(inner.presence_blocks); bg = np.asarray(inner.background_blocks)
    blocks = sorted(set(pg.tolist()) & set(bg.tolist()))
    if int(target_block) not in blocks:
        raise ValueError("target block unavailable")

    closure_a = set(process_information_closure(registry, process_a))
    closure_b = set(process_information_closure(registry, process_b))
    if closure_a & closure_b:
        return pd.DataFrame(), {
            "a": {"state": DIRECTIONAL_UNRESOLVED}, "b": {"state": DIRECTIONAL_UNRESOLVED},
            "reason": "overlapping_process_closures",
        }
    eco = tuple(ecological); obs = tuple(observation); specs = tuple(specs)
    b_removed = tuple(x for x in eco if x not in closure_b)
    a_removed = tuple(x for x in eco if x not in closure_a)
    ab_removed = tuple(x for x in eco if x not in (closure_a | closure_b))
    if not a_removed or not b_removed or not ab_removed:
        return pd.DataFrame(), {
            "a": {"state": DIRECTIONAL_UNRESOLVED}, "b": {"state": DIRECTIONAL_UNRESOLVED},
            "reason": "empty_predictor_route",
        }

    p_test = np.flatnonzero(pg == int(target_block)); b_test = np.flatnonzero(bg == int(target_block))
    rows = []
    for source in blocks:
        if int(source) == int(target_block):
            continue
        p_train = np.flatnonzero((pg != int(target_block)) & (pg != int(source)))
        b_train = np.flatnonzero((bg != int(target_block)) & (bg != int(source)))
        fold = ((p_train, b_train, p_test, b_test),)
        correction = _prepare_observation_corrections(
            presence, background, pg, bg, obs, fold,
            observation_signal_chance=float(learner["observation_signal_chance"]),
            observation_signal_margin=float(learner["observation_signal_margin"]),
            observation_signal_sem_multiplier=float(learner["observation_signal_sem_multiplier"]),
            observation_weight_truncation_quantile=float(learner["observation_weight_truncation_quantile"]),
            observation_weight_probability_epsilon=float(learner["observation_weight_probability_epsilon"]),
        )[0]
        for spec in specs:
            row = {"source_block": int(source), "model_label": spec.label, "complete": False}
            try:
                if not correction.complete or min(len(p_train), len(b_train), len(p_test), len(b_test)) < 2:
                    raise ValueError("insufficient perturbation")
                ptr = presence.iloc[p_train].reset_index(drop=True); btr = background.iloc[b_train].reset_index(drop=True)
                pte = presence.iloc[p_test].reset_index(drop=True); bte = background.iloc[b_test].reset_index(drop=True)
                mb = fit_relative_suitability_model(ptr, btr, b_removed + obs, model_spec=spec)
                ma = fit_relative_suitability_model(ptr, btr, a_removed + obs, model_spec=spec)
                mab = fit_relative_suitability_model(ptr, btr, ab_removed + obs, model_spec=spec)
                sb = _score(mb, pte, bte, btr, b_removed + obs, obs, correction, learner["density_probability_epsilon"])
                sa = _score(ma, pte, bte, btr, a_removed + obs, obs, correction, learner["density_probability_epsilon"])
                sab = _score(mab, pte, bte, btr, ab_removed + obs, obs, correction, learner["density_probability_epsilon"])
                if not all(np.isfinite(float(x)) for x in tuple(sb.values()) + tuple(sa.values()) + tuple(sab.values())):
                    raise ValueError("non-finite pair evidence")
                row.update({
                    "complete": True,
                    "a_base_prediction_rank": sb["prediction_rank"],
                    "a_base_ecological_rank": sb["ecological_rank"],
                    "a_conditional_rank_loss": sb["ecological_rank"] - sab["ecological_rank"],
                    "a_conditional_density_loss": sb["ecological_density"] - sab["ecological_density"],
                    "b_base_prediction_rank": sa["prediction_rank"],
                    "b_base_ecological_rank": sa["ecological_rank"],
                    "b_conditional_rank_loss": sa["ecological_rank"] - sab["ecological_rank"],
                    "b_conditional_density_loss": sa["ecological_density"] - sab["ecological_density"],
                })
            except (ValueError, KeyError, np.linalg.LinAlgError):
                pass
            rows.append(row)
    evidence = pd.DataFrame(rows)
    return evidence, {
        "a": _direction_state(evidence, "a", n_specs=len(specs), learner=learner, cfg=cfg),
        "b": _direction_state(evidence, "b", n_specs=len(specs), learner=learner, cfg=cfg),
        "reason": "ok",
    }


def fit_family(family: str, pair_manifest_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    cfg = load_contract()
    if family not in cfg["families"]:
        raise ValueError("family outside v22 denominator")
    manifest = pd.read_csv(pair_manifest_csv)
    focus = manifest.loc[manifest["family"].astype(str).eq(str(family))].copy()
    directions = []; evidence_parts = []
    for item in focus.itertuples(index=False):
        evidence, summary = evaluate_pair_context(
            str(family), int(item.seed), int(item.target_block), str(item.process_a), str(item.process_b)
        )
        for target, conditioned, key in (
            (str(item.process_a), str(item.process_b), "a"),
            (str(item.process_b), str(item.process_a), "b"),
        ):
            d = summary[key]
            row = {
                "family": str(family), "seed": int(item.seed), "target_block": int(item.target_block),
                "target_process": target, "conditioned_on_process": conditioned, "state": d["state"],
                "n_source_perturbations": int(d.get("n_source_perturbations", 0)),
            }
            for name, value in d.items():
                if name != "state" and name != "n_source_perturbations": row[name] = value
            directions.append(row)
        if len(evidence):
            e = evidence.copy()
            e.insert(0, "process_b", str(item.process_b)); e.insert(0, "process_a", str(item.process_a))
            e.insert(0, "target_block", int(item.target_block)); e.insert(0, "seed", int(item.seed)); e.insert(0, "family", str(family))
            evidence_parts.append(e)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(directions).to_csv(out / "directional_evidence.csv", index=False)
    if evidence_parts:
        pd.concat(evidence_parts, ignore_index=True).to_csv(out / "model_evidence.csv", index=False)
    else:
        pd.DataFrame().to_csv(out / "model_evidence.csv", index=False)
    return {"family": str(family), "n_pairs": int(len(focus)), "n_directional_rows": int(len(directions))}


def aggregate(input_dir: str | Path, pair_manifest_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(input_dir); manifest = pd.read_csv(pair_manifest_csv)
    files = list(root.rglob("directional_evidence.csv"))
    directional = pd.concat([pd.read_csv(x) for x in files], ignore_index=True) if files else pd.DataFrame()
    pairwise = extract_symmetric_pairwise_evidence(manifest, directional)
    if len(pairwise) != len(manifest):
        raise ValueError("v22 aggregate denominator mismatch")

    true = {"temperature", "water"}; false = {"seasonality", "noise"}
    mixed = []; seasonality_demoted = []; true_true_retained = []
    for r in pairwise.itertuples(index=False):
        a, b, st = str(r.process_a), str(r.process_b), str(r.pair_status)
        at, bt = a in true, b in true
        if at != bt:
            correct = (at and st == "P_favored") or (bt and st == "Q_favored")
            mixed.append(bool(correct))
        if a == "seasonality" and b in true:
            seasonality_demoted.append(st == "Q_favored")
        elif b == "seasonality" and a in true:
            seasonality_demoted.append(st == "P_favored")
        if at and bt:
            true_true_retained.append(st in {"P_favored", "Q_favored", "coessential"})

    status_counts = pairwise["pair_status"].value_counts().to_dict()
    result = {
        "purpose": "relative_attribution_v22_consumed_development_endpoint",
        "n_pairs": int(len(pairwise)),
        "status_counts": {str(k): int(v) for k, v in status_counts.items()},
        "mixed_truth_true_process_favored_rate": float(np.mean(mixed)) if mixed else float("nan"),
        "seasonality_vs_true_demotion_rate": float(np.mean(seasonality_demoted)) if seasonality_demoted else float("nan"),
        "true_true_nonexchangeable_retention_rate": float(np.mean(true_true_retained)) if true_true_retained else float("nan"),
        "unresolved_rate": float(pairwise["pair_status"].eq("unresolved").mean()),
        "development_only": True,
        "fresh_empirical_claim_authorized": False,
    }
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pairwise.to_csv(out / "pair_summary.csv", index=False)
    (out / "development_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="cmd", required=True)
    freeze = sub.add_parser("freeze-pairs"); freeze.add_argument("--context-decisions", required=True); freeze.add_argument("--output-dir", required=True)
    fit = sub.add_parser("fit-family"); fit.add_argument("--family", required=True); fit.add_argument("--pair-manifest", required=True); fit.add_argument("--output-dir", required=True)
    agg = sub.add_parser("aggregate"); agg.add_argument("--input-dir", required=True); agg.add_argument("--pair-manifest", required=True); agg.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "freeze-pairs": result = freeze_pair_manifest(args.context_decisions, args.output_dir)
    elif args.cmd == "fit-family": result = fit_family(args.family, args.pair_manifest, args.output_dir)
    else: result = aggregate(args.input_dir, args.pair_manifest, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
