"""Source-only forest admission receipt over five already published source audits.

Never reads original response rows, biological effects or saved model scores.
The displayed counts are source metadata, not new ecological denominators.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from sdmr.forest_source_gate_v1 import source_catalog_receipt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--catalog", type=Path,
        default=Path("configs/forest_source_gate_archived_sources_v1.json"),
    )
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    source_bytes = args.catalog.read_bytes()
    catalog = json.loads(source_bytes)
    if catalog.get("metadata_only") is not True or (
        catalog.get("no_biological_data_access") is not True
    ):
        raise ValueError("source-only evidence barrier must be declared")
    admission = source_catalog_receipt(
        catalog,
        minimum_independent_blocks=catalog["minimum_independent_blocks"],
        minimum_per_block=catalog["minimum_per_block"],
    )
    admission["source_catalog_sha256"] = sha256(source_bytes).hexdigest()
    admission["evidence_class"] = "archived_source_metadata_reaudit_only"
    admission["no_new_result_promotion"] = True
    serialized = (json.dumps(admission, sort_keys=True, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(serialized)
    print("FOREST_SOURCE_ONLY_AUDIT", admission["n_source_profiles"])
    print("READY_FOR_NEW_PROTOCOL", admission["n_protocol_ready"])
    print("ORIGINAL_BIOLOGICAL_RESPONSES_OPENED", admission["n_biological_outcomes_opened"])
    print("MODELS_FITTED", admission["n_new_models_fit"])
    print("SOURCE_CATALOG_SHA256", admission["source_catalog_sha256"])
    print("DECISION_RECEIPT_SHA256", sha256(serialized).hexdigest())
    for row in admission["decisions"]:
        print("SOURCE", row["source_id"], row["status"],
              "REASONS", ",".join(row["reasons"]))
    if admission["n_protocol_ready"]:
        print("Metadata ready means prefreeze only; NEVER authorizes response opening.")


if __name__ == "__main__":
    main()
