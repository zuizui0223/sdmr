import hashlib
import json
from pathlib import Path

SELECTED = Path("configs/sdmr_fresh_empirical_selected_taxa_v1.csv")
RESULT = Path("results/sdmr_fresh_empirical_cohort_v1_result.json")
RECEIPT = Path("configs/sdmr_fresh_empirical_cohort_artifact_receipt_v1.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_committed_fresh_cohort_matches_terminal_artifact_receipt():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert _sha256(SELECTED) == receipt["selected_manifest_sha256"]
    assert _sha256(RESULT) == receipt["result_file_sha256"]
    assert result["selected_manifest_sha256"] == receipt["selected_manifest_sha256"]
    assert result["selected_count"] == 50
    assert result["selected_families"] == 42
    assert result["selected_genera"] == 50
    assert result["fresh_outcomes_opened"] is False
    assert result["environmental_values_read"] is False
    assert result["sealed_answer_check_read"] is False


def test_committed_fresh_cohort_keeps_exact_declared_denominator():
    lines = SELECTED.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 51
