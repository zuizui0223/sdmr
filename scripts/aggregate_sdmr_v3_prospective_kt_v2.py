#!/usr/bin/env python3
"""Aggregate frozen SDMR v3 prospective KT v2 evidence.

Gate failure is a scientific result and does not raise. Data/provenance
violations fail closed before a decision is emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.process_id.known_truth.prospective_kt import evaluate_prospective_kt


KEY = ["seed", "world", "process"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_many(root: Path, filename: str, expected: int) -> pd.DataFrame:
    paths = sorted(root.glob(f"**/{filename}"))
    if len(paths) != int(expected):
        raise ValueError(
            f"expected {expected} copies of {filename}, found {len(paths)}"
        )
    frames = [pd.read_csv(path) for path in paths]
    return pd.concat(frames, ignore_index=True)


def _validate_manifests(
    root: Path,
    *,
    expected: int,
    contract_sha256: str,
    execution_sha256: str,
    activation_sha256: str,
) -> list[dict]:
    paths = sorted(root.glob("**/manifest.json"))
    if len(paths) != int(expected):
        raise ValueError(
            f"expected {expected} shard manifests, found {len(paths)}"
        )
    manifests = [_load(path) for path in paths]
    for item in manifests:
        if item.get("status") != "prospective_evidence":
            raise ValueError("non-prospective shard in prospective aggregate")
        if item.get("scientific_contract_sha256") != contract_sha256:
            raise ValueError("shard scientific contract hash drift")
        if item.get("execution_profile_sha256") != execution_sha256:
            raise ValueError("shard execution profile hash drift")
        if item.get("activation_sha256") != activation_sha256:
            raise ValueError("shard activation hash drift")
    pairs = {
        (str(item["world"]), tuple(int(x) for x in item["seeds"]))
        for item in manifests
    }
    if len(pairs) != int(expected):
        raise ValueError("prospective shard world/seed-block duplication")
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--execution-profile", required=True)
    parser.add_argument("--activation", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--expected-shards", type=int, default=32)
    args = parser.parse_args()

    root = Path(args.input_root)
    contract_path = Path(args.contract)
    execution_path = Path(args.execution_profile)
    activation_path = Path(args.activation)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    contract = _load(contract_path)
    execution = _load(execution_path)
    activation = _load(activation_path)

    contract_sha = _sha256(contract_path)
    execution_sha = _sha256(execution_path)
    activation_sha = _sha256(activation_path)

    manifests = _validate_manifests(
        root,
        expected=int(args.expected_shards),
        contract_sha256=contract_sha,
        execution_sha256=execution_sha,
        activation_sha256=activation_sha,
    )

    stage_p = _read_many(
        root, "stage_p_states.csv", int(args.expected_shards)
    )
    stage_t = _read_many(
        root, "stage_t_states.csv", int(args.expected_shards)
    )
    odo = _read_many(root, "odo_states.csv", int(args.expected_shards))

    expected_rows = (
        int(contract["seeds"]["count"])
        * len(contract["worlds"])
        * 6
    )
    for name, frame in (("stage_p", stage_p), ("stage_t", stage_t), ("odo", odo)):
        if len(frame) != expected_rows:
            raise ValueError(
                f"expected {expected_rows} {name} rows, observed {len(frame)}"
            )
        if frame.duplicated(KEY).any():
            raise ValueError(f"{name} contains duplicate prospective cells")

    declared_seeds = set(int(x) for x in contract["seeds"]["values"])
    for frame in (stage_p, stage_t, odo):
        if set(frame["seed"].astype(int)) != declared_seeds:
            raise ValueError("prospective seed denominator drift")
        if set(frame["world"].astype(str)) != set(contract["worlds"]):
            raise ValueError("prospective world denominator drift")

    odo_key = odo.loc[:, KEY + ["state"]].rename(
        columns={"state": "odo_state_from_oracle"}
    )
    for name, frame in (("stage_p", stage_p), ("stage_t", stage_t)):
        checked = frame.loc[:, KEY + ["odo_state"]].merge(
            odo_key,
            on=KEY,
            how="left",
            validate="one_to_one",
        )
        if checked["odo_state_from_oracle"].isna().any():
            raise ValueError(f"{name} missing ODO target cells")
        if not checked["odo_state"].astype(str).eq(
            checked["odo_state_from_oracle"].astype(str)
        ).all():
            raise ValueError(f"{name} ODO state drift from oracle output")

    # Same finite sample must feed Stage P and Stage T.
    p_sample = stage_p.loc[:, KEY + ["sampling_seed"]]
    t_sample = stage_t.loc[:, KEY + ["sampling_seed"]]
    sample_check = p_sample.merge(
        t_sample,
        on=KEY,
        how="outer",
        validate="one_to_one",
        suffixes=("_p", "_t"),
        indicator=True,
    )
    if not sample_check["_merge"].eq("both").all():
        raise ValueError("Stage-P/Stage-T cell alignment failure")
    if not sample_check["sampling_seed_p"].eq(
        sample_check["sampling_seed_t"]
    ).all():
        raise ValueError("Stage-P and Stage-T did not use the same sample")

    expected_counts = contract["expected_odo_counts_total"]
    decision = evaluate_prospective_kt(
        stage_p,
        stage_t,
        expected_counts=expected_counts,
        gate_vector=contract["gate_vector"],
        expected_seed_count=int(contract["seeds"]["count"]),
        expected_worlds=tuple(contract["worlds"]),
        provenance_complete=True,
    )

    stage_p.to_csv(outdir / "stage_p_states.csv", index=False)
    stage_t.to_csv(outdir / "stage_t_states.csv", index=False)
    odo.to_csv(outdir / "odo_states.csv", index=False)

    decision_payload = {
        "program": contract["program"],
        "status": "prospective_terminal_result",
        "passed": bool(decision.passed),
        "gates": decision.gates,
        "metrics": decision.metrics,
        "counts": decision.counts,
        "reasons": list(decision.reasons),
        "scientific_contract_sha256": contract_sha,
        "execution_profile_sha256": execution_sha,
        "activation_sha256": activation_sha,
        "development_prerequisite_run": activation[
            "development_prerequisite_run"
        ],
        "development_prerequisite_artifact_digest": activation[
            "development_prerequisite_artifact_digest"
        ],
        "n_shards": int(len(manifests)),
        "n_stage_p_rows": int(len(stage_p)),
        "n_stage_t_rows": int(len(stage_t)),
        "prospective_seed_min": int(min(declared_seeds)),
        "prospective_seed_max": int(max(declared_seeds)),
        "fresh_empirical_open": False,
    }
    (outdir / "decision.json").write_text(
        json.dumps(decision_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    outputs = [
        "stage_p_states.csv",
        "stage_t_states.csv",
        "odo_states.csv",
        "decision.json",
    ]
    manifest = {
        "program": contract["program"],
        "status": "prospective_terminal_result",
        "passed": bool(decision.passed),
        "scientific_contract_sha256": contract_sha,
        "execution_profile_sha256": execution_sha,
        "activation_sha256": activation_sha,
        "outputs": {
            name: _sha256(outdir / name)
            for name in outputs
        },
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
