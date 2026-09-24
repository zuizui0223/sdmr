#!/usr/bin/env python3
"""Aggregate SDMR v3 Stage-P 8x safety evidence with full-system gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.safety_audit import summarize_safety


TAIL_COLUMNS = [
    "world","seed","multiplier","replicate","process","odo_state","finite_state",
    "reason","split_mode","hgb_profile","closure_predictors","complete",
    "full_log_score","knockout_log_score","delta_mean","delta_sem",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


SEMANTIC_TAIL_COLUMNS = [
    "world","seed","multiplier","replicate","process","odo_state","finite_state",
    "reason","split_mode","hgb_profile","closure_predictors","complete",
]
NUMERIC_TAIL_COLUMNS = [
    "full_log_score","knockout_log_score","delta_mean","delta_sem",
]


def _canonical_positive_hashes(
    frame: pd.DataFrame,
    *,
    round_decimals: int = 14,
) -> dict[str, str]:
    required = set(TAIL_COLUMNS)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"positive-state table missing columns: {missing}")
    positive = frame.loc[
        frame["odo_state"].isin({"contributory","required"}),
        TAIL_COLUMNS,
    ].copy()
    positive = positive.sort_values(
        ["world","seed","process","replicate","split_mode"],
        kind="mergesort",
    ).reset_index(drop=True)

    semantic_payload = positive.loc[:, SEMANTIC_TAIL_COLUMNS].to_csv(
        index=False
    ).encode("utf-8")
    semantic_hash = hashlib.sha256(semantic_payload).hexdigest()

    rounded = positive.copy()
    for column in NUMERIC_TAIL_COLUMNS:
        rounded[column] = pd.to_numeric(
            rounded[column], errors="raise"
        ).round(int(round_decimals))
    rounded_payload = rounded.to_csv(
        index=False,
        float_format=f"%.{int(round_decimals)}f",
    ).encode("utf-8")
    rounded_hash = hashlib.sha256(rounded_payload).hexdigest()
    return {
        "semantic": semantic_hash,
        "rounded_numeric": rounded_hash,
    }


def _group_metrics(states: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    positive={"contributory","required"}
    sharp={"replaceable","contributory","required"}
    rows=[]
    for keys,group in states.groupby(group_cols,sort=True):
        if not isinstance(keys,tuple):
            keys=(keys,)
        record=dict(zip(group_cols,keys,strict=True))
        odo_positive=group["odo_state"].isin(positive)
        odo_replaceable=group["odo_state"].eq("replaceable")
        odo_unresolved=group["odo_state"].eq("unresolved")
        odo_unavailable=group["odo_state"].eq("unavailable")
        finite_positive=group["finite_state"].isin(positive)
        finite_sharp=group["finite_state"].isin(sharp)
        refusal=group["structural_refusal_expected"].astype(bool)
        record.update({
            "n_rows":int(len(group)),
            "positive_recovery":(
                float((odo_positive&finite_positive).sum()/odo_positive.sum())
                if int(odo_positive.sum()) else float("nan")
            ),
            "false_positive_rate":(
                float((odo_replaceable&finite_positive).sum()/odo_replaceable.sum())
                if int(odo_replaceable.sum()) else float("nan")
            ),
            "overresolution_rate":(
                float((odo_unresolved&finite_sharp).sum()/odo_unresolved.sum())
                if int(odo_unresolved.sum()) else float("nan")
            ),
            "unavailable_favorable_rate":(
                float((odo_unavailable&finite_positive).sum()/odo_unavailable.sum())
                if int(odo_unavailable.sum()) else float("nan")
            ),
            "unavailable_sharp_rate":(
                float((odo_unavailable&finite_sharp).sum()/odo_unavailable.sum())
                if int(odo_unavailable.sum()) else float("nan")
            ),
            "structural_refusal_violation_rate":(
                float((refusal&finite_sharp).sum()/refusal.sum())
                if int(refusal.sum()) else float("nan")
            ),
        })
        rows.append(record)
    return pd.DataFrame(rows)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input-root",required=True)
    parser.add_argument("--outdir",required=True)
    parser.add_argument("--config",required=True)
    parser.add_argument("--expected-shards",type=int,default=8)
    args=parser.parse_args()

    config_path=Path(args.config)
    config=json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("program")!="sdmr-v3-stage-p-safety-audit-v3":
        raise ValueError("wrong Stage-P safety-v3 config")
    if config.get("stage")!="P" or config.get("split_mode")!="random_cell":
        raise ValueError("Stage-P safety-v3 must be random_cell only")
    if config.get("require_full_system_information") is not True:
        raise ValueError("Stage-P safety-v3 requires the full-system information gate")
    if config.get("sampling_seed_world_index_mode")!="frozen_global_world_order":
        raise ValueError("Stage-P safety-v3 requires frozen global world indices")

    input_root=Path(args.input_root)
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    state_files=sorted(input_root.glob("**/states.csv"))
    if len(state_files)!=int(args.expected_shards):
        raise ValueError(f"expected {args.expected_shards} Stage-P shards, found {len(state_files)}")

    frames=[]
    for path in state_files:
        frame=pd.read_csv(path)
        required={
            "world","seed","process","multiplier","replicate","hgb_profile",
            "structural_refusal_expected","odo_state","finite_state","split_mode",
            "full_system_information_adequate","full_system_mean_gain_over_null",
            "full_system_gain_sem","full_system_lower_gain_over_null",
        }
        missing=sorted(required-set(frame.columns))
        if missing:
            raise KeyError(f"{path} missing columns: {missing}")
        frames.append(frame)

    states=pd.concat(frames,ignore_index=True)
    key=["world","seed","process","replicate","split_mode"]
    if states.duplicated(key).any():
        raise ValueError("Stage-P safety evidence contains duplicate cells")
    expected_rows=8*8*6*3
    if len(states)!=expected_rows:
        raise ValueError(f"expected {expected_rows} Stage-P rows, observed {len(states)}")
    if set(states["split_mode"].astype(str))!={"random_cell"}:
        raise ValueError("Stage-P safety contains non-random_cell rows")
    if set(states["multiplier"].astype(int))!={8}:
        raise ValueError("Stage-P safety multiplier drift")
    if set(states["hgb_profile"].astype(str))!={"shallow3"}:
        raise ValueError("Stage-P safety HGB profile drift")

    tail_config=config["power_tail_target"]
    round_decimals=int(tail_config["numeric_hash_round_decimals"])
    observed_positive_hashes=_canonical_positive_hashes(
        states,
        round_decimals=round_decimals,
    )
    expected_semantic_hash=str(
        tail_config["canonical_positive_semantic_sha256"]
    )
    expected_rounded_hash=str(
        tail_config["canonical_positive_rounded14_sha256"]
    )
    if observed_positive_hashes["semantic"]!=expected_semantic_hash:
        raise ValueError(
            "Stage-P positive-tail semantic hash mismatch: "
            f"expected {expected_semantic_hash}, "
            f"observed {observed_positive_hashes['semantic']}"
        )
    if observed_positive_hashes["rounded_numeric"]!=expected_rounded_hash:
        raise ValueError(
            "Stage-P positive-tail rounded numeric hash mismatch: "
            f"expected {expected_rounded_hash}, "
            f"observed {observed_positive_hashes['rounded_numeric']}"
        )

    metrics=summarize_safety(states)
    by_world=_group_metrics(states,["world"])
    by_process=_group_metrics(states,["process"])
    confusion=(
        states.groupby(["odo_state","finite_state"],sort=True)
        .size().rename("count").reset_index()
    )

    # Full-system adequacy is one value per world x seed x replicate, repeated
    # across processes. Deduplicate before reporting gate behavior.
    gate = states.loc[
        :,
        [
            "world","seed","replicate",
            "full_system_information_adequate",
            "full_system_mean_gain_over_null",
            "full_system_gain_sem",
            "full_system_lower_gain_over_null",
        ],
    ].drop_duplicates(["world","seed","replicate"])
    if len(gate)!=8*8*3:
        raise ValueError("unexpected number of full-system gate cells")
    gate_by_world=(
        gate.groupby("world",sort=True)
        .agg(
            n_cases=("seed","size"),
            adequate_rate=("full_system_information_adequate","mean"),
            mean_gain=("full_system_mean_gain_over_null","mean"),
            mean_gain_sem=("full_system_gain_sem","mean"),
            mean_lower_gain=("full_system_lower_gain_over_null","mean"),
        )
        .reset_index()
    )

    refusal=states.loc[states["structural_refusal_expected"].astype(bool)].copy()
    refusal_summary=(
        refusal.groupby(["world","process","finite_state"],sort=True)
        .size().rename("count").reset_index()
    )

    outputs={
        "states.csv":states,
        "metrics.csv":metrics,
        "by_world.csv":by_world,
        "by_process.csv":by_process,
        "confusion.csv":confusion,
        "full_system_gate.csv":gate,
        "full_system_gate_by_world.csv":gate_by_world,
        "structural_refusal.csv":refusal_summary,
    }
    for name,frame in outputs.items():
        frame.to_csv(outdir/name,index=False)

    summary={
        "program":config["program"],
        "status":"development_only",
        "n_state_rows":int(len(states)),
        "n_shards":int(len(state_files)),
        "positive_tail_semantic_hash":observed_positive_hashes["semantic"],
        "positive_tail_rounded_numeric_hash":observed_positive_hashes["rounded_numeric"],
        "metrics":metrics.to_dict(orient="records"),
        "full_system_gate_by_world":gate_by_world.to_dict(orient="records"),
    }
    (outdir/"summary.json").write_text(
        json.dumps(_clean(summary),indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    output_names=list(outputs)+["summary.json"]
    manifest={
        "program":config["program"],
        "status":"development_only",
        "product_a_boundary":"closed_not_reopened",
        "config_path":str(config_path),
        "config_sha256":_sha256(config_path),
        "positive_tail_semantic_hash":observed_positive_hashes["semantic"],
        "positive_tail_rounded_numeric_hash":observed_positive_hashes["rounded_numeric"],
        "outputs":{name:_sha256(outdir/name) for name in output_names},
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
