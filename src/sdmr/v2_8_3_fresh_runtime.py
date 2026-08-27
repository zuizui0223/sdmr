"""Thin v2.8.3 adapter around the frozen deterministic v2.7.2 scientific core.

No candidate, model, threshold, partition, audit-space, ecological metric, or
process implementation is reimplemented here.  The adapter swaps only the
predeclared v2.8.3 contract/source loaders into the v2.7.2 core entry points and
tags outputs with the v2.8.3 transport identity.  This keeps the scientific
implementation inherited while allowing the frozen fresh panel and 0.25-only
design to be supplied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import v2_7_2_fresh_final_fit as final_core
from . import v2_7_2_fresh_materialize as materialize_core
from . import v2_7_2_fresh_model_pool_shard as shard_core
from . import v2_7_2_fresh_model_pool_shard_aggregate as worker_core
from . import v2_7_2_fresh_pretruth as pretruth_core
from . import v2_7_2_fresh_sealed_audit as sealed_core
from .v2_8_3_fresh_contract import (
    EXPECTED_SOURCE_RECEIPT_BLOB,
    load_v2_8_3_fresh_confirmation_contract,
    load_v2_8_3_source_receipt,
)


def _patch_contract_loader(module) -> None:
    module.load_v2_7_2_fresh_confirmation_contract = (
        load_v2_8_3_fresh_confirmation_contract
    )


def _tag_output(output_dir: str | Path, stage: str) -> dict:
    path = Path(output_dir) / "contract.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["v2_8_3_scientific_transport"] = True
    payload["v2_8_3_stage"] = str(stage)
    payload["source_receipt_blob_sha"] = EXPECTED_SOURCE_RECEIPT_BLOB
    payload["selected_global_sealed_fraction"] = 0.25
    payload["scientific_promotion_allowed"] = False
    payload["product_b_unblocked"] = False
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def materialize(args) -> dict:
    _patch_contract_loader(materialize_core)
    materialize_core.load_v2_7_2_source_receipt = load_v2_8_3_source_receipt
    result = materialize_core.materialize_fresh_part(
        contract_path=args.contract,
        source_gate_path=args.source_receipt,
        source_receipt_path=args.source_receipt,
        focal_path=args.focal,
        target_path=args.target,
        taxa_path=args.taxa,
        grid_path=args.grid,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        seed=args.seed,
        sealed_fraction=0.25,
    )
    del result
    return _tag_output(args.output_dir, "materialize_model_pool_only")


def model_pool_shard(args) -> dict:
    _patch_contract_loader(shard_core)
    result = shard_core.run_fresh_model_pool_M_shard(
        contract_path=args.contract,
        process_registry_path=args.process_registry,
        part_dir=args.part_dir,
        taxon=args.taxon,
        taxon_index=args.taxon_index,
        part_seed=args.part_seed,
        M_name=args.M,
        output_dir=args.output_dir,
    )
    del result
    return _tag_output(args.output_dir, "deterministic_model_pool_M_shard")


def aggregate_worker(args) -> dict:
    result = worker_core.aggregate_fresh_model_pool_shards(
        shard_root=args.shard_root,
        taxon=args.taxon,
        taxon_index=args.taxon_index,
        part_seed=args.part_seed,
        output_dir=args.output_dir,
    )
    del result
    return _tag_output(args.output_dir, "aggregate_three_primary_M_shards")


def pretruth(args) -> dict:
    _patch_contract_loader(pretruth_core)
    result = pretruth_core.run_fresh_pretruth(
        contract_path=args.contract,
        worker_root=args.worker_root,
        output_dir=args.output_dir,
    )
    del result
    return _tag_output(args.output_dir, "pretruth_freeze")


def final_fit(args) -> dict:
    _patch_contract_loader(final_core)
    result = final_core.freeze_fresh_final_models(
        contract_path=args.contract,
        part_dir=args.part_dir,
        worker_dir=args.worker_dir,
        pretruth_dir=args.pretruth_dir,
        taxon=args.taxon,
        taxon_index=args.taxon_index,
        output_dir=args.output_dir,
    )
    del result
    return _tag_output(args.output_dir, "final_models_presealed")


def sealed_audit(args) -> dict:
    _patch_contract_loader(sealed_core)
    result = sealed_core.run_fresh_sealed_audit(
        contract_path=args.contract,
        part_dir=args.part_dir,
        pretruth_dir=args.pretruth_dir,
        final_fit_root=args.final_fit_root,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
    )
    del result
    return _tag_output(args.output_dir, "sealed_ecological_audit")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("materialize")
    q.add_argument("--contract", required=True)
    q.add_argument("--source-receipt", required=True)
    q.add_argument("--focal", required=True)
    q.add_argument("--target", required=True)
    q.add_argument("--taxa", required=True)
    q.add_argument("--grid", required=True)
    q.add_argument("--manifest", required=True)
    q.add_argument("--seed", required=True, type=int)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=materialize)

    q = sub.add_parser("model-pool-shard")
    q.add_argument("--contract", required=True)
    q.add_argument("--process-registry", required=True)
    q.add_argument("--part-dir", required=True)
    q.add_argument("--taxon", required=True)
    q.add_argument("--taxon-index", required=True, type=int)
    q.add_argument("--part-seed", required=True, type=int)
    q.add_argument("--M", required=True)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=model_pool_shard)

    q = sub.add_parser("aggregate-worker")
    q.add_argument("--shard-root", required=True)
    q.add_argument("--taxon", required=True)
    q.add_argument("--taxon-index", required=True, type=int)
    q.add_argument("--part-seed", required=True, type=int)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=aggregate_worker)

    q = sub.add_parser("pretruth")
    q.add_argument("--contract", required=True)
    q.add_argument("--worker-root", required=True)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=pretruth)

    q = sub.add_parser("final-fit")
    q.add_argument("--contract", required=True)
    q.add_argument("--part-dir", required=True)
    q.add_argument("--worker-dir", required=True)
    q.add_argument("--pretruth-dir", required=True)
    q.add_argument("--taxon", required=True)
    q.add_argument("--taxon-index", required=True, type=int)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=final_fit)

    q = sub.add_parser("sealed-audit")
    q.add_argument("--contract", required=True)
    q.add_argument("--part-dir", required=True)
    q.add_argument("--pretruth-dir", required=True)
    q.add_argument("--final-fit-root", required=True)
    q.add_argument("--manifest", required=True)
    q.add_argument("--output-dir", required=True)
    q.set_defaults(func=sealed_audit)
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
