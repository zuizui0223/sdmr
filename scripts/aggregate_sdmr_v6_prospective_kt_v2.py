#!/usr/bin/env python3
"""Aggregate SDMR v6 prospective KT v2 evidence with scoped authorization roles."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.scoped_pipeline_v6 import evaluate_scoped_prospective_kt


KEY=["seed","world","process"]


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_many(root: Path, filename: str, expected: int) -> pd.DataFrame:
    paths=sorted(root.glob(f"**/{filename}"))
    if len(paths)!=int(expected):
        raise ValueError(
            f"expected {expected} copies of {filename}, found {len(paths)}"
        )
    return pd.concat([pd.read_csv(path) for path in paths],ignore_index=True)


def _mapped_gate_vector(config: dict) -> dict:
    source=config["gate_vector"]
    seed_count=len(config["seeds"])
    return {
        "KT-B":{
            "minimum":float(source["KT-B"]["minimum"]),
        },
        "KT-C":{
            "maximum":float(source["KT-C"]["maximum"]),
        },
        "KT-D":{
            "max_overresolution_rate_among_odo_unresolved":float(
                source["KT-D"]["max_overresolution_rate_among_odo_unresolved"]
            ),
            "max_structural_refusal_violation_rate":float(
                source["KT-D"]["max_structural_refusal_violation_rate"]
            ),
        },
        "KT-E":{
            "max_sharp_rate_among_odo_unavailable":float(
                source["KT-E"]["max_sharp_rate_among_odo_unavailable"]
            ),
            "max_favorable_positive_rate_among_odo_unavailable":float(
                source["KT-E"]["max_favorable_positive_rate_among_odo_unavailable"]
            ),
            "minimum_each_informative_control_authorization_rate":float(
                source["KT-E"]["minimum_each_informative_control_authorization_rate"]
            ),
            "maximum_w7_authorized_count":int(
                source["KT-E"]["maximum_w7_authorized_count"]
            ),
        },
        "KT-F":{
            "complete_spatial_transfer_evaluation_required":bool(
                source["KT-F"]["complete_spatial_transfer_evaluation_required"]
            ),
            "max_stage_p_positive_to_spatial_replaceable_contradiction_rate":float(
                source["KT-F"][
                    "max_stage_p_positive_to_spatial_replaceable_contradiction_rate"
                ]
            ),
            "max_spatial_structural_refusal_violation_rate":float(
                source["KT-F"]["max_spatial_structural_refusal_violation_rate"]
            ),
            "spatial_positive_retention_report_only":bool(
                source["KT-F"]["spatial_positive_retention_report_only"]
            ),
        },
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input-root",required=True)
    parser.add_argument("--scientific-contract",required=True)
    parser.add_argument("--execution-profile",required=True)
    parser.add_argument("--activation",required=True)
    parser.add_argument("--outdir",required=True)
    parser.add_argument("--expected-shards",type=int,default=32)
    args=parser.parse_args()

    root=Path(args.input_root)
    scientific_path=Path(args.scientific_contract)
    execution_path=Path(args.execution_profile)
    activation_path=Path(args.activation)
    scientific=_load(scientific_path)
    activation=_load(activation_path)
    outdir=Path(args.outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    if scientific.get("program")!="sdmr-v6-prospective-known-truth-v2":
        raise ValueError("wrong v6 prospective contract")
    if activation.get("purpose")!="execute_sdmr_v6_prospective_known_truth_v2":
        raise ValueError("wrong v6 prospective activation")

    manifests=sorted(root.glob("**/manifest.json"))
    if len(manifests)!=int(args.expected_shards):
        raise ValueError(
            f"expected {args.expected_shards} prospective shard manifests, found {len(manifests)}"
        )
    for path in manifests:
        item=_load(path)
        if item.get("status")!="prospective_evidence":
            raise ValueError("unexpected prospective shard status")
        if item.get("scientific_contract_sha256")!=_sha256(scientific_path):
            raise ValueError("prospective scientific contract hash drift")
        if item.get("execution_profile_sha256")!=_sha256(execution_path):
            raise ValueError("prospective execution profile hash drift")
        if item.get("activation_sha256")!=_sha256(activation_path):
            raise ValueError("prospective activation hash drift")
        for key in ("validation","confirmation","integration"):
            if item.get(f"{key}_artifact_digest")!=activation[f"{key}_prerequisite"]["artifact_digest"]:
                raise ValueError(f"{key} provenance drift")

    stage_p=_read_many(root,"stage_p_states.csv",int(args.expected_shards))
    stage_t=_read_many(root,"stage_t_states.csv",int(args.expected_shards))
    odo=_read_many(root,"odo_states.csv",int(args.expected_shards))
    full_gate=_read_many(root,"full_system_gate.csv",int(args.expected_shards))

    expected_seeds=set(int(x) for x in scientific["seeds"])
    expected_worlds=set(str(x) for x in scientific["worlds"])
    expected_rows=len(expected_seeds)*len(expected_worlds)*6

    for name,frame in (("stage_p",stage_p),("stage_t",stage_t),("odo",odo)):
        if len(frame)!=expected_rows:
            raise ValueError(
                f"expected {expected_rows} {name} rows, observed {len(frame)}"
            )
        if frame.duplicated(KEY).any():
            raise ValueError(f"{name} contains duplicate prospective cells")
        if set(frame["seed"].astype(int))!=expected_seeds:
            raise ValueError(f"{name} seed denominator drift")
        if set(frame["world"].astype(str))!=expected_worlds:
            raise ValueError(f"{name} world denominator drift")

    if len(full_gate)!=len(expected_seeds)*len(expected_worlds):
        raise ValueError("unexpected prospective full-system gate row count")
    if full_gate.duplicated(["seed","world"]).any():
        raise ValueError("duplicate prospective full-system gate rows")

    odo_key=odo.loc[:,KEY+["state"]].rename(
        columns={"state":"odo_state_from_oracle"}
    )
    for name,frame in (("stage_p",stage_p),("stage_t",stage_t)):
        checked=frame.loc[:,KEY+["odo_state"]].merge(
            odo_key,on=KEY,how="left",validate="one_to_one"
        )
        if not checked["odo_state"].astype(str).eq(
            checked["odo_state_from_oracle"].astype(str)
        ).all():
            raise ValueError(f"{name} ODO target drift")

    p_samples=stage_p.loc[:,KEY+["sampling_seed"]]
    t_samples=stage_t.loc[:,KEY+["sampling_seed"]]
    same=p_samples.merge(
        t_samples,on=KEY,how="outer",validate="one_to_one",
        suffixes=("_p","_t"),indicator=True
    )
    if not same["_merge"].eq("both").all():
        raise ValueError("prospective Stage-P/Stage-T cells do not align")
    if not same["sampling_seed_p"].eq(same["sampling_seed_t"]).all():
        raise ValueError("Stage-P and Stage-T used different finite samples")

    decision=evaluate_scoped_prospective_kt(
        stage_p,
        stage_t,
        expected_counts=scientific["expected_odo_counts_total"],
        gate_vector=_mapped_gate_vector(scientific),
        expected_seed_count=len(expected_seeds),
        expected_worlds=tuple(scientific["worlds"]),
        provenance_complete=True,
        informative_control_worlds=tuple(scientific["informative_controls"]),
        report_only_world=str(scientific["report_only_world"]),
        null_world=str(scientific["null_world"]),
    )

    stage_p.to_csv(outdir/"stage_p_states.csv",index=False)
    stage_t.to_csv(outdir/"stage_t_states.csv",index=False)
    odo.to_csv(outdir/"odo_states.csv",index=False)
    full_gate.to_csv(outdir/"full_system_gate.csv",index=False)

    payload={
        "program":scientific["program"],
        "status":"prospective_terminal_result",
        "passed":bool(decision.passed),
        "gates":decision.gates,
        "metrics":decision.metrics,
        "counts":decision.counts,
        "reasons":list(decision.reasons),
        "validation_prerequisite":activation["validation_prerequisite"],
        "confirmation_prerequisite":activation["confirmation_prerequisite"],
        "integration_prerequisite":activation["integration_prerequisite"],
        "prospective_seed_min":min(expected_seeds),
        "prospective_seed_max":max(expected_seeds),
        "fresh_empirical_open":False,
    }
    (outdir/"decision.json").write_text(
        json.dumps(payload,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    outputs=[
        "stage_p_states.csv","stage_t_states.csv","odo_states.csv",
        "full_system_gate.csv","decision.json",
    ]
    manifest={
        "program":scientific["program"],
        "status":"prospective_terminal_result",
        "passed":bool(decision.passed),
        "scientific_contract_sha256":_sha256(scientific_path),
        "execution_profile_sha256":_sha256(execution_path),
        "activation_sha256":_sha256(activation_path),
        "outputs":{name:_sha256(outdir/name) for name in outputs},
    }
    (outdir/"manifest.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
