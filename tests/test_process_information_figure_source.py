import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
METRICS=ROOT/"results"/"sdmr_v6_prospective_kt_v2_metrics.json"


def test_m5_figure_source_is_canonical_receipt():
    data=json.loads(METRICS.read_text(encoding="utf-8"))
    assert data["program"] == "sdmr-v6-prospective-known-truth-v2"
    assert data["workflow_run"] == 36212033498
    assert data["artifact_id"] == 10896590112
    assert data["prospective_seed_min"] == 74001
    assert data["prospective_seed_max"] == 74020
    assert data["counts"] == {
        "positive":80,
        "replaceable":700,
        "unresolved":60,
        "unavailable":120,
        "structural_refusal":60,
    }
    assert data["metrics"]["positive_recovery"] == 0.8875
    assert data["metrics"]["false_positive_rate"] == 0
    assert data["metrics"]["overresolution_rate"] == 0
    assert data["metrics"]["structural_refusal_violation_rate"] == 0
    assert all(data["gates"].values())
