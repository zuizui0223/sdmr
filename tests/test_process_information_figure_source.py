from pathlib import Path

from manuscript.figures.build_process_information_figures import load_metrics

ROOT=Path(__file__).resolve().parents[1]

def test_m5_figure_source_is_canonical_receipt():
    data=load_metrics(ROOT/"results"/"sdmr_v6_prospective_kt_v2_metrics.json")
    assert data["counts"] == {
        "positive":80,
        "replaceable":700,
        "unresolved":60,
        "unavailable":120,
        "structural_refusal":60,
    }
    assert data["metrics"]["positive_recovery"] == 0.8875
    assert data["metrics"]["false_positive_rate"] == 0
    assert all(data["gates"].values())
