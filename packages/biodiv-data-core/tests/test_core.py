import pytest

from biodiv_data_core import (
    OccurrenceRecord,
    RasterProvenance,
    admission_ledger,
    assign_spatial_blocks,
    deduplicate_occurrences,
    deterministic_block_split,
    occurrence_manifest,
    raster_manifest,
    stable_fingerprint,
)


def test_admission_ledger_records_invalid_coordinate():
    records = [
        OccurrenceRecord("Plant a", 35.0, 139.0, "ok"),
        OccurrenceRecord("Plant b", 95.0, 139.0, "bad"),
    ]
    ledger = admission_ledger(records)
    assert ledger[0].admitted is True
    assert ledger[1].admitted is False
    assert "invalid_latitude" in ledger[1].reasons


def test_dedup_is_deterministic():
    records = [
        OccurrenceRecord("Plant a", 35.0, 139.0, "b"),
        OccurrenceRecord("Plant a", 35.0, 139.0, "a"),
    ]
    kept = deduplicate_occurrences(records)
    assert len(kept) == 1
    assert kept[0].occurrence_id == "a"


def test_block_assignment_and_split_keep_blocks_intact():
    records = [
        OccurrenceRecord("A", 35.0, 139.0, "1"),
        OccurrenceRecord("B", 35.1, 139.1, "2"),
    ]
    assigned = assign_spatial_blocks(records, block_degrees=1.0)
    block_ids = [block for _, block in assigned]
    split = deterministic_block_split(block_ids, holdout_fraction=0.25, salt="test")
    assert all(split[b] in {"model", "holdout"} for b in block_ids)
    if block_ids[0] == block_ids[1]:
        assert split[block_ids[0]] == split[block_ids[1]]


def test_manifests_are_order_stable():
    a = OccurrenceRecord("A", 1.0, 2.0, "1")
    b = OccurrenceRecord("B", 3.0, 4.0, "2")
    assert occurrence_manifest([a, b]) == occurrence_manifest([b, a])

    r1 = RasterProvenance("bio1", "file:///bio1.tif")
    r2 = RasterProvenance("bio12", "file:///bio12.tif")
    assert raster_manifest([r1, r2]) == raster_manifest([r2, r1])


def test_invalid_fraction_rejected():
    with pytest.raises(ValueError):
        deterministic_block_split(["a"], holdout_fraction=1.1)


def test_mapping_fingerprint_is_key_order_stable():
    assert stable_fingerprint({"a": 1, "b": 2}) == stable_fingerprint({"b": 2, "a": 1})
