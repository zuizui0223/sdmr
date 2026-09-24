#!/usr/bin/env python3
"""Aggregate SDMR v5 validation shards from multiple execution runs.

Duplicate world/seed evidence is permitted only when every scientific output
column is exactly identical after CSV parsing. Duplicates never increase the
denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


SUMMARY_KEY=["world","seed"]
FOLD_KEY=["world","seed","fold"]


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dedupe_exact(frame: pd.DataFrame, *, key: list[str], name: str) -> pd.DataFrame:
    if frame.empty:
        raise ValueError(f"{name} is empty")
    missing=sorted(set(key)-set(frame.columns))
    if missing:
        raise KeyError(f"{name} missing key columns: {missing}")

    output=[]
    for _,group in frame.groupby(key,sort=False,dropna=False):
        first=group.iloc[0]
        if len(group)>1:
            # Compare all columns after normalizing column order. NaN equals NaN.
            reference=first.to_frame().T.reset_index(drop=True)
            for i in range(1,len(group)):
                candidate=group.iloc[i].to_frame().T.reset_index(drop=True)
                try:
                    pd.testing.assert_frame_equal(
                        reference,
                        candidate,
                        check_dtype=False,
                        check_exact=True,
                    )
                except AssertionError as exc:
                    key_values={column:first[column] for column in key}
                    raise ValueError(
                        f"non-identical duplicate {name} evidence for {key_values}"
                    ) from exc
        output.append(first)
    result=pd.DataFrame(output).reset_index(drop=True)
    if result.duplicated(key).any():
        raise AssertionError(f"{name} deduplication failed")
    return result


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input-root",required=True)
    parser.add_argument("--config",required=True)
    parser.add_argument("--outdir",required=True)
    parser.add_argument("--expected-unique-shards",type=int,default=40)
    parser.add_argument("--source-run",action="append",type=int,required=True)
    args=parser.parse_args()

    root=Path(args.input_root)
    config_path=Path(args.config)
    config=_load(config_path)
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    if config.get("program")!="sdmr-v5-permutation-gate-validation-v1":
        raise ValueError("wrong v5 validation contract")

    summary_files=sorted(root.glob("**/summary.csv"))
    fold_files=sorted(root.glob("**/fold_scores.csv"))
    manifest_files=sorted(root.glob("**/manifest.json"))
    if not summary_files or not fold_files or not manifest_files:
        raise ValueError("validation source evidence is incomplete")

    summaries_raw=pd.concat([pd.read_csv(p) for p in summary_files],ignore_index=True)
    folds_raw=pd.concat([pd.read_csv(p) for p in fold_files],ignore_index=True)

    summaries=_dedupe_exact(
        summaries_raw,
        key=SUMMARY_KEY,
        name="summary",
    )
    folds=_dedupe_exact(
        folds_raw,
        key=FOLD_KEY,
        name="fold",
    )

    expected_worlds=set(config["worlds"])
    expected_seeds=set(int(x) for x in config["seeds"]["validation"])
    if set(summaries["world"].astype(str))!=expected_worlds:
        raise ValueError("validation world denominator drift")
    if set(summaries["seed"].astype(int))!=expected_seeds:
        raise ValueError("validation seed denominator drift")
    expected_rows=len(expected_worlds)*len(expected_seeds)
    if len(summaries)!=expected_rows:
        raise ValueError(
            f"expected {expected_rows} unique validation cells, observed {len(summaries)}"
        )

    expected_fold_rows=expected_rows*int(config["finite_architecture"]["n_splits"])
    if len(folds)!=expected_fold_rows:
        raise ValueError(
            f"expected {expected_fold_rows} unique validation fold rows, observed {len(folds)}"
        )

    # Require exactly 40 distinct world x 20-seed-block evidence groups.
    block_size=20
    summaries=summaries.copy()
    validation_seed_min=min(expected_seeds)
    summaries["seed_block"]=(
        (summaries["seed"].astype(int)-validation_seed_min)//block_size
    ).astype(int)
    unique_shards=summaries[["world","seed_block"]].drop_duplicates()
    if len(unique_shards)!=int(args.expected_unique_shards):
        raise ValueError(
            f"expected {args.expected_unique_shards} unique shards, observed {len(unique_shards)}"
        )

    world_counts=(
        summaries.groupby("world",sort=True)
        .agg(
            authorized_count=("authorized","sum"),
            denominator=("seed","size"),
            minimum_p_value=("p_value","min"),
            median_p_value=("p_value","median"),
            mean_gain=("mean_gain_over_null","mean"),
        )
        .reset_index()
    )

    gate=config["validation_gate"]
    w7=world_counts.loc[world_counts["world"].eq(config["null_world"])].iloc[0]
    informative=world_counts.loc[
        world_counts["world"].isin(config["informative_controls"])
    ].copy()
    failed_controls=informative.loc[
        informative["authorized_count"].astype(int)
        < int(gate["informative_control_min_authorized_count_each"]),
        "world",
    ].astype(str).tolist()
    passed=bool(
        int(w7["authorized_count"])<=int(gate["w7_max_authorized_count"])
        and not failed_controls
    )

    summaries.drop(columns=["seed_block"]).to_csv(outdir/"summary.csv",index=False)
    folds.to_csv(outdir/"fold_scores.csv",index=False)
    world_counts.to_csv(outdir/"world_counts.csv",index=False)

    decision={
        "program":config["program"],
        "status":"development_validation_terminal",
        "passed":passed,
        "w7_authorized_count":int(w7["authorized_count"]),
        "failed_controls":failed_controls,
        "minimum_control_authorized_count":int(informative["authorized_count"].min()),
        "w6_report_only_authorized_count":int(
            world_counts.loc[
                world_counts["world"].eq(config["report_only_world"]),
                "authorized_count",
            ].iloc[0]
        ),
        "source_workflow_runs":sorted(set(int(x) for x in args.source_run)),
        "duplicate_summary_rows_removed":int(len(summaries_raw)-len(summaries)),
        "confirmation_open":False,
        "reserved_future_prospective_open":False,
    }
    (outdir/"decision.json").write_text(
        json.dumps(decision,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    outputs=["summary.csv","fold_scores.csv","world_counts.csv","decision.json"]
    manifest={
        "program":config["program"],
        "status":"development_validation_terminal",
        "passed":passed,
        "source_workflow_runs":decision["source_workflow_runs"],
        "config_sha256":_sha256(config_path),
        "outputs":{name:_sha256(outdir/name) for name in outputs},
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
