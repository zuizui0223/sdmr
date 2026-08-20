"""Thin stage adapters for the Product-B v2.1 fresh known-truth workflow."""
from __future__ import annotations

import argparse

from .product_b_v2_1_known_truth_contract import load_product_b_v2_1_known_truth_contract
from .product_b_v2_known_truth_audit import audit_product_b_v2_known_truth
from .product_b_v2_known_truth_method_freeze import freeze_product_b_v2_method
from .product_b_v2_known_truth_method_worker import run_method_freeze_shard
from .product_b_v2_known_truth_pretruth import freeze_product_b_v2_process_core
from .product_b_v2_known_truth_process_worker import run_product_b_process_shard

PRETRUTH_PURPOSE = "product_b_v2_1_known_truth_process_core_pretruth_freeze"
DECISION_PURPOSE = "product_b_v2_1_fresh_known_truth_decision"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Product-B v2.1 known-truth stage.")
    sub = parser.add_subparsers(dest="stage", required=True)

    method = sub.add_parser("method-shard")
    method.add_argument("--contract", required=True)
    method.add_argument("--taxon-index", type=int, required=True)
    method.add_argument("--m-index", type=int, required=True)
    method.add_argument("--output-dir", required=True)

    freeze = sub.add_parser("method-freeze")
    freeze.add_argument("--contract", required=True)
    freeze.add_argument("--worker-root", required=True)
    freeze.add_argument("--output-dir", required=True)

    process = sub.add_parser("process-shard")
    process.add_argument("--contract", required=True)
    process.add_argument("--method-dir", required=True)
    process.add_argument("--taxon-index", type=int, required=True)
    process.add_argument("--m-index", type=int, required=True)
    process.add_argument("--output-dir", required=True)

    pretruth = sub.add_parser("pretruth-freeze")
    pretruth.add_argument("--contract", required=True)
    pretruth.add_argument("--method-dir", required=True)
    pretruth.add_argument("--worker-root", required=True)
    pretruth.add_argument("--output-dir", required=True)

    audit = sub.add_parser("truth-audit")
    audit.add_argument("--contract", required=True)
    audit.add_argument("--pretruth-dir", required=True)
    audit.add_argument("--output-dir", required=True)

    args = parser.parse_args(argv)
    if args.stage == "method-shard":
        run_method_freeze_shard(
            contract_path=args.contract,
            taxon_index=args.taxon_index,
            m_index=args.m_index,
            output_dir=args.output_dir,
            contract_loader=load_product_b_v2_1_known_truth_contract,
        )
    elif args.stage == "method-freeze":
        freeze_product_b_v2_method(
            contract_path=args.contract,
            worker_root=args.worker_root,
            output_dir=args.output_dir,
            contract_loader=load_product_b_v2_1_known_truth_contract,
        )
    elif args.stage == "process-shard":
        run_product_b_process_shard(
            contract_path=args.contract,
            method_dir=args.method_dir,
            taxon_index=args.taxon_index,
            m_index=args.m_index,
            output_dir=args.output_dir,
            contract_loader=load_product_b_v2_1_known_truth_contract,
        )
    elif args.stage == "pretruth-freeze":
        freeze_product_b_v2_process_core(
            contract_path=args.contract,
            method_dir=args.method_dir,
            worker_root=args.worker_root,
            output_dir=args.output_dir,
            contract_loader=load_product_b_v2_1_known_truth_contract,
            result_purpose=PRETRUTH_PURPOSE,
        )
    else:
        audit_product_b_v2_known_truth(
            contract_path=args.contract,
            pretruth_dir=args.pretruth_dir,
            output_dir=args.output_dir,
            contract_loader=load_product_b_v2_1_known_truth_contract,
            expected_pretruth_purpose=PRETRUTH_PURPOSE,
            result_purpose=DECISION_PURPOSE,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
