"""Protect the M5 known-truth claim and transparent empirical applicability boundary."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/"manuscript"/"PROCESS_INFORMATION_MEE_SUBMISSION_V1.md"
COVER=ROOT/"manuscript"/"COVER_LETTER_MEE_V1.md"
LEDGER=ROOT/"manuscript"/"PROCESS_INFORMATION_EMPIRICAL_SCOPE_LEDGER.md"
SI=ROOT/"manuscript"/"PROCESS_INFORMATION_EMPIRICAL_ATTEMPTS_SI_V1.md"

def test_positive_known_truth_evidence_unchanged():
    text=PAPER.read_text(encoding="utf-8")
    assert "71 of 80" in text
    assert "0/700" in text
    assert "KT-A through KT-F all passed" in text

def test_independent_empirical_limit_is_disclosed():
    body=PAPER.read_text(encoding="utf-8")
    cover=COVER.read_text(encoding="utf-8")
    for token in ("10/50", "16/300", "−0.00386"):
        assert token in body
    assert "0.80" in body
    assert "10/50" in cover
    assert "16/300" in cover
    assert "failed" in cover.lower() or "did not pass" in cover.lower()

def test_v5_is_not_promoted_into_positive_evidence():
    text=LEDGER.read_text(encoding="utf-8")
    assert "EMP-A/B/C/D FAIL" in text
    assert "EMP-E/F PASS" in text
    assert "overall FAIL" in text
    assert "not an additional positive promotion result" in text
    assert "40 unavailable taxa" in text

def test_complete_sequential_real_plant_disclosure():
    si=SI.read_text(encoding="utf-8")
    paper=PAPER.read_text(encoding="utf-8")
    for token in ("fresh v2", "fresh v3", "fresh v4", "fresh v5", "37/50", "48/50", "89/90", "16/300", "−0.00385763"):
        assert token in si
    assert "not" in si.lower() and "independent confirmatory replications" in si
    assert "v2 at 37/50" in paper
    assert "v4 at 89/90" in paper
    assert "PROCESS_INFORMATION_EMPIRICAL_ATTEMPTS_SI_V1.md" in paper


def test_scope_ledger_is_anonymous():
    text=(LEDGER.read_text(encoding="utf-8")+"\n"+SI.read_text(encoding="utf-8")).lower()
    assert "zuizui0223" not in text
    assert "github.com/" not in text
