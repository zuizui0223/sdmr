"""Verify all consumed v23 pair states against saved model scores."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .attribution_eligibility_v19_prospective import _base_objects
from .coalition_attribution_v23 import classify_pair
from .coalition_attribution_v23_development import CONFIG, PAIR_KEY, load_contract, load_manifest


def verify(manifest_path, output_dir, *, model_labels=None):
    cfg = load_contract()
    manifest = load_manifest(manifest_path)
    out = Path(output_dir)
    receipt = json.loads((out / "execution_receipt.json").read_text(encoding="utf-8"))
    if receipt["config_sha256"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest():
        raise ValueError("execution config changed")
    _, _, _, _, _, _, _, specs = _base_objects()
    labels = [s.label for s in specs] if model_labels is None else list(model_labels)
    count = 0
    hashes = {}
    for family in cfg["families"]:
        model_path = out / family / "model_evidence.csv"
        result_path = out / family / "pair_results.json"
        frame = pd.read_csv(model_path)
        if frame.source_block.eq(frame.target_block).any():
            raise ValueError("target block reused as source omission")
        saved_rows = json.loads(result_path.read_text(encoding="utf-8"))
        saved = pd.DataFrame(saved_rows)
        expected = set(manifest.loc[manifest.family == family, PAIR_KEY].itertuples(index=False, name=None))
        actual = list(saved[PAIR_KEY].itertuples(index=False, name=None))
        model_keys = set(frame[PAIR_KEY].itertuples(index=False, name=None))
        if len(actual) != len(set(actual)) or set(actual) != expected or model_keys != expected:
            raise ValueError("saved pair denominator mismatch")
        for row in saved_rows:
            group = frame
            for k in PAIR_KEY:
                group = group.loc[group[k] == row[k]]
            replay = classify_pair(
                group, model_labels=labels,
                minimum_sources=cfg["minimum_source_perturbations"], rank_margin=cfg["rank_margin"],
                density_margin=cfg["density_margin"], chance=cfg["chance_score"],
                adequacy_margin=cfg["adequacy_margin"],
            )
            if replay["state"] != row["state"] or replay["n_source_perturbations"] != row["n_source_perturbations"]:
                raise ValueError("saved state differs from replay")
            count += 1
        hashes[model_path.relative_to(out).as_posix()] = hashlib.sha256(model_path.read_bytes()).hexdigest()
        hashes[result_path.relative_to(out).as_posix()] = hashlib.sha256(result_path.read_bytes()).hexdigest()
    frozen_path = out / "frozen_pair_states.json"
    frozen = pd.read_json(frozen_path)
    frozen_states = {tuple(row[k] for k in PAIR_KEY): row["state"] for row in frozen.to_dict("records")}
    if len(frozen) != count or len(frozen_states) != count:
        raise ValueError("frozen aggregate denominator mismatch")
    for family in cfg["families"]:
        rows = json.loads((out / family / "pair_results.json").read_text(encoding="utf-8"))
        for row in rows:
            if frozen_states.get(tuple(row[k] for k in PAIR_KEY)) != row["state"]:
                raise ValueError("frozen aggregate state differs")
    result = {"purpose": "v23_saved_evidence_verification", "n_pair_states_reproduced": count,
              "implementation_commit": receipt["implementation_commit"],
              "config_sha256": receipt["config_sha256"], "input_sha256": hashes,
              "fresh_validation_authorized": False}
    (out / "verification_receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.pair_manifest, args.output_dir), indent=2, sort_keys=True))
