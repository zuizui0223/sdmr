"""Thin Product-A v2.6 adapter over the frozen v2.5 model-only worker.

v2.6 changes calibration redundancy and partition-seed allocation only. The model
fitting, frozen v2.4 candidate reuse, M grid, spatial refits and response extraction
remain exactly the v2.5 implementation. This adapter swaps only the predeclared
contract loader and deterministic seed function for one process invocation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .v2_1_known_truth_gate_ablation import M_SPECS
from .v2_4_refit_contract import FULL_FIT_CODE, GROUPS, SPATIAL_REFIT_CODES
from . import v2_5_refit_worker as base
from .v2_6_contract import load_v2_6_contract


PANELS = ("panel_D1", "panel_D2", "panel_D3")
ROLE_OFFSETS = {"calibration": 0, "validation": 5000000}
SEED_BASE = 6100000
PANEL_STRIDE = 10000000
TAXON_STRIDE = 500000
GROUP_STRIDE = 50000
CANDIDATE_STRIDE = 100


def v2_6_refit_seed(
    *,
    panel: str,
    role: str,
    taxon_index: int,
    group: str,
    candidate_index: int,
    m_index: int,
    fit_code: int,
) -> int:
    if panel not in PANELS:
        raise ValueError(f"unknown v2.6 panel: {panel}")
    if role not in ROLE_OFFSETS:
        raise ValueError(f"unknown v2.6 role: {role}")
    if group not in GROUPS:
        raise ValueError(f"unknown v2.6 group: {group}")
    maximum_taxon_index = 8 if role == "calibration" else 2
    if not 0 <= int(taxon_index) <= maximum_taxon_index:
        raise ValueError("taxon_index is outside the frozen v2.6 role")
    if not 0 <= int(candidate_index) < 100:
        raise ValueError("candidate_index must be in frozen collision-free range 0..99")
    if not 0 <= int(m_index) < len(M_SPECS):
        raise ValueError("m_index is outside the frozen M grid")
    if int(fit_code) not in (*SPATIAL_REFIT_CODES, FULL_FIT_CODE):
        raise ValueError("fit_code is not a frozen full/refit code")
    return int(
        SEED_BASE
        + PANELS.index(panel) * PANEL_STRIDE
        + ROLE_OFFSETS[role]
        + int(taxon_index) * TAXON_STRIDE
        + GROUPS.index(group) * GROUP_STRIDE
        + int(candidate_index) * CANDIDATE_STRIDE
        + int(m_index) * 10
        + int(fit_code)
    )


def run_v2_6_refit_worker(**kwargs):
    """Execute the unchanged v2.5 fitting core with v2.6 frozen inputs."""

    original_loader = base.load_v2_5_contract
    original_seed = base.v2_5_refit_seed
    try:
        base.load_v2_5_contract = load_v2_6_contract
        base.v2_5_refit_seed = v2_6_refit_seed
        result = base.run_v2_5_refit_worker(**kwargs)
    finally:
        base.load_v2_5_contract = original_loader
        base.v2_5_refit_seed = original_seed
    result["contract"]["purpose"] = "product_a_v2_6_model_only_refit_worker"
    result["contract"]["worker_algorithm_source"] = "v2_5_refit_worker_unchanged_core"
    result["contract"]["calibration_redundancy_version"] = "v2.6"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--discovery-dir", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--role", choices=("calibration", "validation"), required=True)
    parser.add_argument("--taxon-index", type=int, required=True)
    parser.add_argument("--group", choices=GROUPS, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    result = run_v2_6_refit_worker(
        contract_path=args.contract,
        discovery_dir=args.discovery_dir,
        panel=args.panel,
        role=args.role,
        taxon_index=args.taxon_index,
        group=args.group,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "frozen_candidates",
        "expected_members",
        "expected_response_keys",
        "fit_ledger",
        "response_estimates",
        "predictor_coverage",
    ):
        result[name].to_csv(out / f"{name}.csv", index=False)
    (out / "contract.json").write_text(
        json.dumps(result["contract"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
