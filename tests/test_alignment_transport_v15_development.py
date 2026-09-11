import pandas as pd

from sdmr.alignment_transport_v15_development import _classify_cell, _config, _manifest


def test_v15_contract_and_manifest_are_frozen():
    cfg = _config()
    manifest = _manifest()
    assert cfg["development_only"] is True
    assert cfg["eligible_for_prospective_performance_claim"] is False
    assert cfg["fresh_known_truth_validation_authorized"] is False
    assert cfg["fresh_empirical_validation_authorized"] is False
    assert len(manifest) == 9
    assert set(manifest["v14_classification"]) == {"conditioning_alignment_required", "mixed"}


def _pairs(values):
    return pd.DataFrame({
        "evaluable": [True] * len(values),
        "reproduces_v8_noncontributory": values,
    })


def test_cell_decision_is_fail_closed_and_frozen():
    assert _classify_cell(_pairs([True, True, True]), 3) == "transported"
    assert _classify_cell(_pairs([False, False, False]), 3) == "local_alignment_only"
    assert _classify_cell(_pairs([True, False, True]), 3) == "heterogeneous"
    assert _classify_cell(_pairs([True, True]), 3) == "insufficient"


def test_unevaluable_pairs_do_not_count_as_transport_success():
    frame = pd.DataFrame({
        "evaluable": [True, True, False, False],
        "reproduces_v8_noncontributory": [True, True, True, True],
    })
    assert _classify_cell(frame, 3) == "insufficient"
