"""Regression guard for the closed fresh-v5 sealed post-terminal record."""
import hashlib
import json
from pathlib import Path

SCORE = Path("results/sdmr_fresh_empirical_v5_sealed_promotion_result.json")
RECEIPT = Path("configs/sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json")
TERMINAL = Path("results/sdmr_fresh_empirical_v5_model_pool_terminal_decision.json")
EXPECTED_SCORE_SHA256 = "67452d2147c890b3ea47ca33ae15ed39b32d637904ea06a32adaf3ab100219c6"
EXPECTED_TAXON_SCORE_SHA256 = "cce79d443f133bb1d8f9a943be0f8e3573ae93a9b71c55230adecd61283b1ce1"


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_archived_sealed_result_is_byte_exact_and_non_promotable():
    assert hashlib.sha256(SCORE.read_bytes()).hexdigest() == EXPECTED_SCORE_SHA256
    s = _read(SCORE)
    assert s["status"] == "promotion_failed"
    assert s["strict_promotion_pass"] is False
    assert s["taxon_count"] == 50
    assert s["primary_evaluable_taxa"] == 10
    assert s["primary_unavailable_taxa"] == 40
    assert s["mean_primary_balanced_log_score_gain"] < 0
    assert s["bootstrap_95pct_lower"] < 0 < s["bootstrap_95pct_upper"]
    assert s["capacity_control_filtering_advantage_supported"] is False
    assert s["capacity_control_bootstrap_95pct_lower"] < 0 < s["capacity_control_bootstrap_95pct_upper"]
    assert s["mean_primary_auc_difference"] is None
    assert s["abstention_integrity_violations"] == 0
    assert s["model_refit_performed"] is False
    assert s["post_opening_reselection_performed"] is False
    assert s["taxon_scores_sha256"] == EXPECTED_TAXON_SCORE_SHA256
    assert {k: s[k] for k in ("EMP_A_pass", "EMP_B_pass", "EMP_C_pass", "EMP_D_pass", "EMP_E_pass", "EMP_F_pass")} == {
        "EMP_A_pass": False, "EMP_B_pass": False, "EMP_C_pass": False,
        "EMP_D_pass": False, "EMP_E_pass": True, "EMP_F_pass": True,
    }


def test_frozen_preopening_terminal_decision_remains_authoritative():
    terminal = _read(TERMINAL)
    archived = _read(SCORE)
    assert terminal["status"] == "terminal_empirical_promotion_failed_pre_answer_check"
    assert terminal["information_state"]["answer_check_opened"] is False
    assert terminal["frozen_emp_d"]["denominator"] == 300
    assert terminal["frozen_emp_d"]["observed_stable_sharp_process_cells"] == 16
    assert terminal["frozen_emp_d"]["passed"] is False
    assert archived["stable_process_fraction"] == 16 / 300


def test_duplicate_runs_are_recorded_only_as_postterminal_evidence():
    receipt = _read(RECEIPT)
    assert receipt["status"] == "postterminal_characterization_only"
    assert receipt["authoritative_run"] == 37643074571
    assert receipt["superseded_run"] == 37642883197
    assert receipt["authoritative_artifact_id"] != receipt["superseded_artifact_id"]
    assert receipt["equal_result_bytes"] is True
    assert receipt["equal_taxon_score_bytes"] is True
    assert receipt["sealed_result_sha256"] == EXPECTED_SCORE_SHA256
    assert receipt["taxon_scores_sha256"] == EXPECTED_TAXON_SCORE_SHA256
    assert receipt["promotion_after_terminal_allowed"] is False
    assert receipt["reclassification_allowed"] is False
    assert receipt["model_refit_performed"] is False
    assert receipt["post_opening_reselection_performed"] is False
