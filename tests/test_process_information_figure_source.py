from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODULE_PATH=ROOT/"manuscript"/"figures"/"build_process_information_figures.py"

spec=spec_from_file_location("process_information_figures", MODULE_PATH)
module=module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)
load_metrics=module.load_metrics


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
