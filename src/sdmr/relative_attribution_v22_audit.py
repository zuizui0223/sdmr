"""Replay consumed v22 evidence without fitting models or changing decisions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .attribution_eligibility_v19_prospective import _base_objects
from .relative_attribution_v22 import extract_symmetric_pairwise_evidence
from .relative_attribution_v22_development import _direction_state, load_contract

KEY = ["family", "seed", "target_block", "target_process", "conditioned_on_process"]
PAIR_KEY = ["family", "seed", "target_block", "process_a", "process_b"]


def validate_denominator(manifest, directional):
    """Reject extra evidence as well as missing or duplicated mirror rows."""
    if manifest.duplicated(PAIR_KEY).any():
        raise ValueError("duplicate manifest pair")
    expected = set()
    for r in manifest.itertuples(index=False):
        if r.process_a == r.process_b:
            raise ValueError("self pair")
        for a, b in ((r.process_a, r.process_b), (r.process_b, r.process_a)):
            expected.add((r.family, r.seed, r.target_block, a, b))
    actual = list(directional[KEY].itertuples(index=False, name=None))
    if len(expected) != 2 * len(manifest) or len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("directional denominator differs from frozen manifest")


def audit(input_dir: str | Path, output_dir: str | Path):
    root = Path(input_dir)
    manifests = list(root.rglob("pair_manifest.csv"))
    if len(manifests) != 1:
        raise ValueError("require exactly one frozen manifest")
    manifest = pd.read_csv(manifests[0])
    cfg = load_contract()
    if len(manifest) != cfg["authoritative_v21_source"]["expected_unordered_supported_pairs"]:
        raise ValueError("frozen pair count changed")
    files = sorted(root.rglob("directional_evidence.csv"))
    directional = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
    validate_denominator(manifest, directional)
    pairwise = extract_symmetric_pairwise_evidence(manifest, directional)
    _, v6, _, _, _, _, _, specs = _base_objects()
    learner = v6["learner"]
    records = []
    source_files = [manifests[0], *files]
    for path in files:
        model_path = path.with_name("model_evidence.csv")
        source_files.append(model_path)
        models = pd.read_csv(model_path)
        for row in pd.read_csv(path).to_dict("records"):
            focus = models
            for key in KEY[:3]:
                focus = focus.loc[focus[key].eq(row[key])]
            a, b = row["target_process"], row["conditioned_on_process"]
            focus = focus.loc[((focus.process_a == a) & (focus.process_b == b)) |
                              ((focus.process_a == b) & (focus.process_b == a))]
            if focus.empty:
                raise ValueError("missing model evidence; cannot explain directional state")
            for _, group in focus.groupby("source_block"):
                if group.model_label.duplicated().any() or set(group.model_label) != {s.label for s in specs}:
                    raise ValueError("model specification denominator changed")
            prefix = "a" if focus.iloc[0].process_a == a else "b"
            replay = _direction_state(focus, prefix, n_specs=len(specs), learner=learner, cfg=cfg)
            if replay["state"] != row["state"]:
                raise ValueError("replayed directional state differs from frozen result")
            reasons = []
            if replay["n_source_perturbations"] < cfg["pairwise_rule"]["minimum_source_perturbations"]:
                reasons.append("insufficient_complete_perturbations")
            else:
                chance = learner["chance_score"]
                floor = chance + learner["minimum_margin"]
                for score in ("prediction", "ecological"):
                    mean = replay[f"base_{score}_rank_mean"]
                    sem = replay[f"base_{score}_rank_sem"]
                    if mean < floor - 1e-12 or mean - sem < chance - 1e-12:
                        reasons.append(f"{score}_adequacy_failed")
                if not reasons:
                    for score in ("rank", "density"):
                        lower = replay[f"conditional_{score}_loss_mean"] - replay[f"conditional_{score}_loss_sem"]
                        if lower <= cfg["pairwise_rule"][f"{score}_margin"]:
                            reasons.append(f"{score}_contribution_not_revealed")
            records.append({**{k: row[k] for k in KEY}, **replay,
                            "reason": "|".join(reasons) or "conditional_contribution"})
    explained = pd.DataFrame(records)
    result = {
        "purpose": "v22_consumed_evidence_audit",
        "n_pairs": len(pairwise), "n_directions_replayed": len(explained),
        "all_directional_states_reproduced": True,
        "reason_counts": explained.reason.value_counts().to_dict(),
        "pair_status_counts": pairwise.pair_status.value_counts().to_dict(),
        "model_fitting_performed": False, "thresholds_changed": False,
        "fresh_validation_authorized": False,
        "input_sha256": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in source_files},
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    explained.to_csv(out / "directional_audit.csv", index=False)
    (out / "audit_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.input_dir, args.output_dir), indent=2, sort_keys=True))
