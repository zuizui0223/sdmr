from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/"manuscript/PROCESS_INFORMATION_IDENTIFICATION_V1.md"
LEDGER=ROOT/"manuscript/PROCESS_INFORMATION_CLAIM_LEDGER_V1.md"

def test_canonical_numbers_are_present():
    text=PAPER.read_text(encoding="utf-8")
    for anchor in (
        "71 of 80",
        "0/700",
        "0/60",
        "0/120",
        "74001–74020",
        "KT-A through KT-F all passed",
    ):
        assert anchor in text

def test_paper_keeps_known_truth_boundary():
    text=PAPER.read_text(encoding="utf-8")
    assert "prospective known-truth validation" in text
    assert "not yet an empirical ecological process claim" in text
    assert "universal superiority" in text
    assert "causal physiological mechanisms" in text

def test_failed_proxy_closed_program_is_not_mixed_into_result():
    text=PAPER.read_text(encoding="utf-8")
    assert "proxy-closed-route-evidence-v6" in text
    # It may appear only in the explicit provenance exclusion, never as evidence.
    assert text.count("proxy-closed-route-evidence-v6")==1

def test_ledger_prohibits_overclaim():
    text=LEDGER.read_text(encoding="utf-8")
    for anchor in (
        "causal physiological mechanism recovery",
        "empirical ecological validation",
        "100% sensitivity",
        "Stage-P support guarantees geographic transfer",
    ):
        assert anchor in text
