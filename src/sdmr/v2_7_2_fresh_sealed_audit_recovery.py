"""Technical recovery wrapper for v2.7.2 sealed-audit abstentions.

This wrapper changes no available/authorized audit computation. It only restores the
predeclared structural-abstention path when a frozen pretruth part is unavailable or
does not authorize sealed audit. In that case no sealed environmental raster is read.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .v2_7_2_fresh_sealed_audit import _unavailable_output, run_fresh_sealed_audit

MATERIALIZATION_PURPOSE = "product_a_v2_7_2_fresh_part_model_pool_materialization"
PRETRUTH_PURPOSE = "product_a_v2_7_2_fresh_part_pretruth_freeze"


def run_recovered_sealed_audit(
    *,
    contract_path: str | Path,
    part_dir: str | Path,
    pretruth_dir: str | Path,
    final_fit_root: str | Path,
    manifest_path: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    part = Path(part_dir)
    pretruth_root = Path(pretruth_dir)
    materialization = json.loads((part / "contract.json").read_text(encoding="utf-8"))
    pretruth = json.loads((pretruth_root / "contract.json").read_text(encoding="utf-8"))

    if materialization.get("purpose") != MATERIALIZATION_PURPOSE:
        raise ValueError("v2.7.2 recovered sealed audit received wrong materialization")
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False:
        raise ValueError("v2.7.2 recovered sealed audit received already-opened materialization")
    if pretruth.get("purpose") != PRETRUTH_PURPOSE:
        raise ValueError("v2.7.2 recovered sealed audit requires frozen pretruth")
    if pretruth.get("deterministic_successor") is not True:
        raise ValueError("v2.7.2 recovered sealed audit received non-deterministic pretruth")

    out = Path(output_dir)
    if pretruth.get("available") is not True:
        return _unavailable_output(
            out=out,
            materialization=materialization,
            pretruth_root=pretruth_root,
            reason=str(pretruth.get("unavailable_reason", "pretruth_unavailable")),
            sealed_environment_read=False,
        )
    if pretruth.get("sealed_audit_authorized") is not True:
        return _unavailable_output(
            out=out,
            materialization=materialization,
            pretruth_root=pretruth_root,
            reason="pretruth_did_not_authorize_sealed_audit",
            sealed_environment_read=False,
        )

    # Available/authorized parts retain the exact frozen scientific audit path,
    # including the original RNG guards and all sealed-evidence calculations.
    return run_fresh_sealed_audit(
        contract_path=contract_path,
        part_dir=part_dir,
        pretruth_dir=pretruth_dir,
        final_fit_root=final_fit_root,
        manifest_path=manifest_path,
        output_dir=output_dir,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--part-dir", required=True)
    p.add_argument("--pretruth-dir", required=True)
    p.add_argument("--final-fit-root", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args(argv)
    run_recovered_sealed_audit(
        contract_path=args.contract,
        part_dir=args.part_dir,
        pretruth_dir=args.pretruth_dir,
        final_fit_root=args.final_fit_root,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
