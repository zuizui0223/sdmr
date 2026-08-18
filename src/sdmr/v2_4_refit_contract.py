"""Immutable stage-2 contract for Product-A v2.4 refits and calibration."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd


PANELS = ("panel_D1", "panel_D2", "panel_D3")
GROUPS = ("base", "noise", "seasonality", "soil", "temperature", "water")
M_SPECS = ("m_core", "m_mid", "m_wide")
ROLE_OFFSETS = {"discovery": 0, "validation": 50000}
GROUP_INDICES = {name: index for index, name in enumerate(GROUPS)}
SPATIAL_REFIT_CODES = (0, 1, 2, 3, 4)
FULL_FIT_CODE = 9
N_BLOCKS = 5
HOLDOUT_FRACTION = 0.20
SEED_BASE = 210000
SOURCE_RUN_ID = "32096477308"
SOURCE_HEAD_SHA = "3c222249109ac2c15f6258ebc79bb1c957dd42a4"

SOURCE_ARTIFACTS = {
    "panel_D1": {
        "artifact_id": "9310256239",
        "artifact_name": "product-a-v2-4-knockout-discovery-panel_D1",
        "artifact_digest": "sha256:aace53635728c8a2edf4a92de8136e127a21d9552679cad0f30048195e25e7db",
        "n_complete_adequate_base_candidates": 4,
        "n_admitted_knockout_candidates": 20,
    },
    "panel_D2": {
        "artifact_id": "9310224903",
        "artifact_name": "product-a-v2-4-knockout-discovery-panel_D2",
        "artifact_digest": "sha256:b47f660cab44e2c8e7a29131c163447a39d7aa6332a4c83a3ea0f7aebdd0936b",
        "n_complete_adequate_base_candidates": 6,
        "n_admitted_knockout_candidates": 30,
    },
    "panel_D3": {
        "artifact_id": "9310181352",
        "artifact_name": "product-a-v2-4-knockout-discovery-panel_D3",
        "artifact_digest": "sha256:5f325c22cffd3048ba99aecf24bf94dc6e95c9264aae6953e7ae0a9b473dc85e",
        "n_complete_adequate_base_candidates": 6,
        "n_admitted_knockout_candidates": 29,
    },
}


@dataclass(frozen=True)
class FrozenGroupCandidates:
    panel: str
    group: str
    candidates: tuple[str, ...]
    base_candidates: tuple[str, ...]
    excluded_processes: tuple[str | None, ...]
    excluded_predictors: tuple[tuple[str, ...], ...]

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "candidate": self.candidates,
                "base_candidate": self.base_candidates,
                "excluded_process": self.excluded_processes,
                "excluded_predictors": [
                    ",".join(values) for values in self.excluded_predictors
                ],
            }
        )


def load_refit_contract(path: str | Path) -> dict[str, Any]:
    """Fail closed if any stage-2 scientific or information contract changed."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    expected_false = (
        "scientific_promotion_run",
        "real_empirical_data_read",
        "old_external_sealed_outcomes_read",
        "discovery_generating_truth_read_before_raw_envelope_freeze",
        "validation_taxa_simulated_or_read",
        "validation_truth_read",
    )
    for key in expected_false:
        if payload.get(key) is not False:
            raise ValueError(f"v2.4 refit contract requires {key}=false")
    if payload.get("opened_discovery_selection_evidence_allowed") is not True:
        raise ValueError("v2.4 stage 2 must explicitly allow frozen discovery evidence")

    source = payload.get("source_discovery", {})
    if str(source.get("run_id")) != SOURCE_RUN_ID:
        raise ValueError("v2.4 discovery source run changed")
    if str(source.get("head_sha")) != SOURCE_HEAD_SHA:
        raise ValueError("v2.4 discovery source head changed")
    if source.get("panels") != SOURCE_ARTIFACTS:
        raise ValueError("v2.4 discovery artifact identities or counts changed")

    if tuple(payload.get("fit_groups", ())) != GROUPS:
        raise ValueError("v2.4 fit group order changed")
    modes = payload.get("fit_modes", {})
    full = modes.get("full_fit", {})
    refit = modes.get("spatial_refit", {})
    if full.get("uses_all_model_pool_rows") is not True:
        raise ValueError("v2.4 full fits must use all model-pool rows")
    if int(full.get("fit_code", -1)) != FULL_FIT_CODE:
        raise ValueError("v2.4 full-fit code changed")
    if int(refit.get("n_refits", -1)) != len(SPATIAL_REFIT_CODES):
        raise ValueError("v2.4 spatial-refit count changed")
    if tuple(refit.get("fit_codes", ())) != SPATIAL_REFIT_CODES:
        raise ValueError("v2.4 spatial-refit codes changed")
    if refit.get("uses_training_blocks_only") is not True:
        raise ValueError("v2.4 spatial refits must use training blocks only")

    partition = payload.get("spatial_partition", {})
    if int(partition.get("n_blocks", -1)) != N_BLOCKS:
        raise ValueError("v2.4 refit block count changed")
    if abs(float(partition.get("holdout_fraction", -1)) - HOLDOUT_FRACTION) > 1e-12:
        raise ValueError("v2.4 refit holdout fraction changed")
    if partition.get("role_offsets") != ROLE_OFFSETS:
        raise ValueError("v2.4 role offsets changed")
    if partition.get("group_indices") != GROUP_INDICES:
        raise ValueError("v2.4 group indices changed")
    expected_formula = (
        "210000 + panel_index*100000 + role_offset + taxon_index*10000 + "
        "group_index*1000 + candidate_index*100 + M_index*10 + fit_code"
    )
    if partition.get("seed_formula") != expected_formula:
        raise ValueError("v2.4 refit seed formula changed")

    projection = payload.get("model_projection", {})
    if projection.get("observation_reference") != "complete_frozen_M_background":
        raise ValueError("v2.4 observation reference changed")
    if float(projection.get("prediction_surface_coverage_floor", -1)) != 0.95:
        raise ValueError("v2.4 prediction-surface coverage floor changed")
    if tuple(projection.get("response_quantities", ())) != (
        "optimum",
        "lower_limit",
        "upper_limit",
    ):
        raise ValueError("v2.4 response quantities changed")

    raw = payload.get("raw_envelope", {})
    if raw.get("requires_every_expected_member") is not True:
        raise ValueError("v2.4 envelope must require every expected member")
    if raw.get("missing_or_nonfinite_member_makes_interval_unavailable") is not True:
        raise ValueError("v2.4 missing refits cannot be silently dropped")

    calibration = payload.get("discovery_calibration", {})
    if calibration.get("truth_opened_only_after_all_raw_discovery_envelopes_frozen") is not True:
        raise ValueError("v2.4 discovery truth barrier changed")
    if calibration.get("validation_truth_used") is not False:
        raise ValueError("v2.4 validation truth cannot calibrate intervals")
    if calibration.get("width_can_override_coverage") is not False:
        raise ValueError("v2.4 interval width cannot override coverage")
    return payload


def refit_seed(
    *,
    panel: str,
    role: str,
    taxon_index: int,
    group: str,
    candidate_index: int,
    m_index: int,
    fit_code: int,
) -> int:
    """Return the exact deterministic partition seed frozen for stage 2."""

    if panel not in PANELS:
        raise ValueError(f"unknown v2.4 panel: {panel}")
    if role not in ROLE_OFFSETS:
        raise ValueError(f"unknown v2.4 role: {role}")
    if group not in GROUP_INDICES:
        raise ValueError(f"unknown v2.4 group: {group}")
    if not 0 <= int(taxon_index) < 3:
        raise ValueError("taxon_index must be 0, 1 or 2")
    if int(candidate_index) < 0:
        raise ValueError("candidate_index must be >= 0")
    if not 0 <= int(m_index) < len(M_SPECS):
        raise ValueError("m_index is outside the frozen M grid")
    if int(fit_code) not in (*SPATIAL_REFIT_CODES, FULL_FIT_CODE):
        raise ValueError("fit_code is not a frozen full/refit code")
    return int(
        SEED_BASE
        + PANELS.index(panel) * 100000
        + ROLE_OFFSETS[role]
        + int(taxon_index) * 10000
        + GROUP_INDICES[group] * 1000
        + int(candidate_index) * 100
        + int(m_index) * 10
        + int(fit_code)
    )


def _split_csv(value: object) -> tuple[str, ...]:
    if value is None or pd.isna(value) or not str(value):
        return ()
    return tuple(x for x in str(value).split(",") if x)


def load_frozen_group_candidates(
    discovery_dir: str | Path,
    *,
    panel: str,
    group: str,
) -> FrozenGroupCandidates:
    """Load exact base/admitted knockout candidates from one immutable artifact."""

    if panel not in PANELS:
        raise ValueError(f"unknown v2.4 panel: {panel}")
    if group not in GROUPS:
        raise ValueError(f"unknown v2.4 fit group: {group}")
    root = Path(discovery_dir)
    contract = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    if contract.get("panel") != panel:
        raise ValueError("discovery artifact panel does not match requested panel")
    if contract.get("discovery_generating_truth_read") is not False:
        raise ValueError("discovery artifact crossed the generating-truth barrier")
    if contract.get("validation_taxa_simulated_or_read") is not False:
        raise ValueError("discovery artifact accessed validation taxa")
    expected = SOURCE_ARTIFACTS[panel]

    if group == "base":
        products = pd.read_csv(root / "base_products.csv")
        row = products.loc[
            products["product"].astype(str).eq("complete_adequate_certificate")
            & products["status"].astype(str).eq("frozen")
        ]
        if len(row) != 1:
            raise ValueError("frozen complete-adequate base product is unavailable")
        candidates = tuple(sorted(_split_csv(row.iloc[0]["candidates"])))
        if len(candidates) != int(expected["n_complete_adequate_base_candidates"]):
            raise ValueError("base candidate count differs from the frozen stage-2 contract")
        return FrozenGroupCandidates(
            panel=panel,
            group=group,
            candidates=candidates,
            base_candidates=candidates,
            excluded_processes=tuple(None for _ in candidates),
            excluded_predictors=tuple(() for _ in candidates),
        )

    summary = pd.read_csv(root / "knockout_candidate_summary.csv")
    registry = pd.read_csv(root / "knockout_registry.csv")
    subset = summary.loc[
        summary["excluded_process"].astype(str).eq(group)
        & summary["admitted_knockout"].fillna(False).astype(bool)
    ].copy()
    subset = subset.merge(
        registry[
            [
                "candidate",
                "base_candidate",
                "excluded_process",
                "excluded_predictors",
            ]
        ],
        on=["candidate", "base_candidate", "excluded_process", "excluded_predictors"],
        how="inner",
        validate="one_to_one",
    )
    subset = subset.sort_values("candidate", kind="mergesort").reset_index(drop=True)
    total_admitted = int(summary["admitted_knockout"].fillna(False).astype(bool).sum())
    if total_admitted != int(expected["n_admitted_knockout_candidates"]):
        raise ValueError("total admitted knockout count differs from stage-2 contract")
    candidates = tuple(subset["candidate"].astype(str))
    if not candidates:
        raise ValueError(f"frozen process group has no admitted candidates: {group}")
    return FrozenGroupCandidates(
        panel=panel,
        group=group,
        candidates=candidates,
        base_candidates=tuple(subset["base_candidate"].astype(str)),
        excluded_processes=tuple(subset["excluded_process"].astype(str)),
        excluded_predictors=tuple(
            _split_csv(value) for value in subset["excluded_predictors"]
        ),
    )
