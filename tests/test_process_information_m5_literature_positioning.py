"""Protect an evidence-limited literature comparison for the M5 submission."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PAPER=(ROOT/"manuscript/PROCESS_INFORMATION_MEE_SUBMISSION_V1.md").read_text(encoding="utf-8")
COVER=(ROOT/"manuscript/COVER_LETTER_MEE_V1.md").read_text(encoding="utf-8")

def test_conceptual_predecessors_are_explicitly_recognized():
    for author,source in (
        ("Strobl et al. 2008","https://doi.org/10.1186/1471-2105-9-307"),
        ("Fisher et al. 2019","https://jmlr.org/papers/v20/18-760.html"),
        ("Roberts et al. 2017","https://doi.org/10.1111/ecog.02881"),
        ("Zbinden et al. 2026","https://doi.org/10.1111/2041-210X.70200"),
    ):
        assert author in PAPER
        assert source in PAPER

def test_process_closure_claim_does_not_imply_predictive_superiority():
    assert "researcher-declared modelling assumptions" in PAPER
    assert "No head-to-head benchmark" in PAPER
    assert "not an established predictive advantage" in PAPER
    assert "We do not claim a head-to-head predictive advantage" in COVER
    assert "different inferential outputs" in PAPER

def test_known_truth_and_negative_real_plant_denominators_unchanged():
    for token in ("71 of 80", "0/700", "0/60", "KT-A through KT-F all passed"):
        assert token in PAPER
    for token in ("10/50", "16/300", "−0.00386"):
        assert token in PAPER
    assert "finite-sample outcomes" in PAPER
    assert "not** establish" in PAPER
