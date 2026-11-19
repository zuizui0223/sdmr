"""Audit source-defined forest sampling opportunities WITHOUT organism responses.

A successful opportunity audit proves only that field survey events can be
enumerated without duplicating sites or confusing unvisited with sampled.
It never proves complete capture/detection, independent zero catch, individual
survival, valid process carriers or a causal/empirical model result.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
from math import isfinite
from typing import Mapping

SURVEY_STATUS = frozenset({"surveyed", "not_surveyed", "unknown"})
UNIT_TYPES = frozenset({"trap", "tree", "plot", "sub_plot"})


@dataclass(frozen=True)
class SurveyOpportunity:
    record_id: str
    physical_site_id: str
    source_unit_id: str
    block_id: str
    occasion_id: str
    survey_date: str
    method_id: str
    survey_status: str
    effort: float | None

    def __post_init__(self) -> None:
        for label in (
            "record_id", "physical_site_id", "source_unit_id", "block_id",
            "occasion_id", "method_id", "survey_date",
        ):
            if not str(getattr(self, label)).strip():
                raise ValueError(f"{label} must be nonempty")
        try:
            date.fromisoformat(self.survey_date)
        except (ValueError, TypeError) as exc:
            raise ValueError("survey_date must be ISO-8601 calendar date") from exc
        if self.survey_status not in SURVEY_STATUS:
            raise ValueError("survey status not declared")
        if self.survey_status == "surveyed":
            if self.effort is None or not isfinite(self.effort) or self.effort <= 0:
                raise ValueError("surveyed event requires independently recorded positive effort")
        elif self.survey_status == "not_surveyed":
            if self.effort not in (None, 0):
                raise ValueError("not_surveyed event cannot carry positive effort")
        elif self.effort is not None:
            raise ValueError("unknown status must have unknown effort, not a fabricated zero")


@dataclass(frozen=True)
class SurveyFrameReceipt:
    status: str
    source_file_sha256: str
    unit_kind: str
    n_event_records: int
    n_physical_sites: int
    n_surveyed_physical_sites: int
    n_surveyed_events: int
    n_not_surveyed: int
    n_unknown: int
    n_holdout_blocks: int
    min_eligible_sites_per_block: int
    identity_sha256: str
    sampling_event_sha256: str
    opportunity_data_only: bool
    biological_response_values_opened: bool
    true_zero_catch_inferred: bool
    observation_selection_resolved: bool
    response_opening_authorized: bool


def evaluate_survey_frame(
    source: Mapping[str, object],
    *,
    minimum_blocks: int = 6,
    minimum_sites_per_block: int = 2,
) -> SurveyFrameReceipt:
    if source.get("schema") != "sdmr.forest_sampling_opportunity.v1":
        raise ValueError("invalid sampling opportunity schema")
    if source.get("metadata_only") is not True:
        raise ValueError("opportunity frame must be metadata-only")
    if set(source) != {"schema", "metadata_only", "source_file_sha256", "unit_kind", "rows"}:
        raise ValueError("unexpected top-level source fields; response values forbidden")
    source_digest = source["source_file_sha256"]
    if not isinstance(source_digest, str) or len(source_digest) != 64 or any(
        c not in "0123456789abcdef" for c in source_digest
    ):
        raise ValueError("source digest must be lowercase sha256")
    unit_kind = source["unit_kind"]
    if unit_kind not in UNIT_TYPES:
        raise ValueError("unknown source unit kind")
    if minimum_blocks < 2 or minimum_sites_per_block < 2:
        raise ValueError("holdout minimum must be at least two")
    raw = source["rows"]
    if not isinstance(raw, list) or not raw:
        raise ValueError("sampling rows must be a nonempty list")
    allowed = set(SurveyOpportunity.__dataclass_fields__)
    records: list[SurveyOpportunity] = []
    for row in raw:
        if not isinstance(row, dict) or set(row) != allowed:
            raise ValueError("sampling row schema mismatch; no biological response columns")
        records.append(SurveyOpportunity(**row))

    ids = [r.record_id for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate original survey record IDs")
    site_blocks: dict[str, str] = {}
    for row in records:
        old = site_blocks.setdefault(row.physical_site_id, row.block_id)
        if old != row.block_id:
            raise ValueError("same physical site assigned to multiple holdout blocks")

    all_sites = set(site_blocks)
    eligible = [r for r in records if r.survey_status == "surveyed"]
    eligible_site_ids = {r.physical_site_id for r in eligible}
    by_block: dict[str, set[str]] = {}
    for row in eligible:
        by_block.setdefault(row.block_id, set()).add(row.physical_site_id)
    block_counts = {block: len(sites) for block, sites in by_block.items()}
    n_blocks = len(block_counts)
    smallest = min(block_counts.values()) if block_counts else 0
    if n_blocks < minimum_blocks:
        status = "not_estimable_insufficient_surveyed_blocks"
    elif smallest < minimum_sites_per_block:
        status = "not_estimable_insufficient_independent_sites"
    else:
        status = "survey_opportunity_ready_for_separate_observation_audit"

    site_keys = sorted(site_blocks.items())
    obs_keys = sorted(
        (r.record_id, r.physical_site_id, r.source_unit_id, r.block_id,
         r.occasion_id, r.survey_date, r.method_id, r.survey_status,
         r.effort)
        for r in records
    )
    encode = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return SurveyFrameReceipt(
        status=status,
        source_file_sha256=source_digest,
        unit_kind=unit_kind,
        n_event_records=len(records),
        n_physical_sites=len(all_sites),
        n_surveyed_physical_sites=len(eligible_site_ids),
        n_surveyed_events=len(eligible),
        n_not_surveyed=sum(r.survey_status == "not_surveyed" for r in records),
        n_unknown=sum(r.survey_status == "unknown" for r in records),
        n_holdout_blocks=n_blocks,
        min_eligible_sites_per_block=smallest,
        identity_sha256=sha256(encode(site_keys).encode()).hexdigest(),
        sampling_event_sha256=sha256(encode(obs_keys).encode()).hexdigest(),
        opportunity_data_only=True,
        biological_response_values_opened=False,
        true_zero_catch_inferred=False,
        observation_selection_resolved=False,
        response_opening_authorized=False,
    )
