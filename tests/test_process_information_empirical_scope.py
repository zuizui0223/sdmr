"""Protect the M5 known-truth claim and transparent empirical applicability boundary."""
import hashlib
import json
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

EVIDENCE=ROOT/"evidence"/"mee_real_v5_receipts"
ORIGINAL_GIT_BLOBS={
    "sdmr_fresh_empirical_v5_model_pool_diagnostic.json": "fb6b140f49bf3bc9f28ac5601d108f95d1952fa7",
    "sdmr_fresh_empirical_v5_model_pool_terminal_decision.json": "d6b7ca10d8238a91a45efe036d26728406c62ccc",
    "sdmr_fresh_empirical_v5_sealed_promotion_result.json": "29c7b777d4f38ef47516cb293821ca98e5e8b643",
    "sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json": "88f52b4df1c205b59fcadb9d6fe8ef0e886c6dfa",
}

def test_frozen_v5_receipts_are_original_byte_copies():
    """The anonymous bundle must not silently rewrite archived negative results."""
    for filename, expected_blob_sha in ORIGINAL_GIT_BLOBS.items():
        data=(EVIDENCE/filename).read_bytes()
        git_blob=b"blob "+str(len(data)).encode("ascii")+b"\\0"+data
        assert hashlib.sha1(git_blob).hexdigest()==expected_blob_sha, filename

def test_frozen_v5_bottleneck_counts_and_decision_sequence():
    diagnostic=json.loads((EVIDENCE/"sdmr_fresh_empirical_v5_model_pool_diagnostic.json").read_text())
    decision=json.loads((EVIDENCE/"sdmr_fresh_empirical_v5_model_pool_terminal_decision.json").read_text())
    sealed=json.loads((EVIDENCE/"sdmr_fresh_empirical_v5_sealed_promotion_result.json").read_text())
    receipt=json.loads((EVIDENCE/"sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json").read_text())
    full=diagnostic["full_system_authorization"]
    assert full["shallow3_hgb"]["authorized_taxa"]==32
    assert full["penalized_logistic"]["authorized_taxa"]==10
    assert full["both_authorized_taxa"]==10
    assert full["hgb_only_authorized_taxa"]==22
    stable=diagnostic["route_sharp_states"]["stable_two_route"]
    assert stable["sharp_cells"]==16
    assert stable["total_cells"]==300
    assert stable["both_authorized_cell_denominator"]==60
    assert diagnostic["route_sharp_states"]["shallow3_hgb"]["sharp_cells"]==125
    assert sum(diagnostic["stable_state_counts"].values())==300
    assert diagnostic["stable_state_counts"]=={
        "unavailable":240,"unresolved":44,"replaceable":15,"contributory":1,"required":0
    }
    assert decision["information_state"]["answer_check_opened"] is False
    assert decision["frozen_emp_d"]["passed"] is False
    assert decision["frozen_emp_d"]["required_minimum"]==0.80
    assert decision["promotion_logic"]["rescue_allowed"] is False
    assert sealed["status"]=="promotion_failed"
    assert sealed["strict_promotion_pass"] is False
    assert sealed["taxon_count"]==50
    assert sealed["primary_unavailable_taxa"]==40
    assert sealed["mean_primary_balanced_log_score_gain"]<0
    assert receipt["terminal_decision_status"]==decision["status"]
    assert receipt["equal_result_bytes"] is True
    assert receipt["model_refit_performed"] is False
    assert receipt["promotion_after_terminal_allowed"] is False

def test_negative_diagnostic_is_reported_without_denominator_shift():
    si=SI.read_text(encoding="utf-8")
    paper=PAPER.read_text(encoding="utf-8")
    for text in (si,paper):
        assert "32/50" in text
        assert "10/50" in text
        assert "16/60" in text
        assert "16/300" in text
        assert "125/300" in text
    for file in EVIDENCE.iterdir():
        if file.suffix in {".json",".md"}:
            content=file.read_text(encoding="utf-8").lower()
            assert "zuizui0223" not in content
            assert "github.com/" not in content
