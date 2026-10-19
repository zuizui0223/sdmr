"""Keep the supplemental nonlinear/effort experiment separate from M5 promotion."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
MAIN=ROOT/"manuscript/PROCESS_INFORMATION_MEE_SUBMISSION_V1.md"
SI=ROOT/"manuscript/PROCESS_INFORMATION_KNOWN_TRUTH_SENSITIVITY_SI_V1.md"
SCOPE=ROOT/"manuscript/PROCESS_INFORMATION_EMPIRICAL_SCOPE_LEDGER.md"
M5=ROOT/"results/sdmr_v6_prospective_kt_v2_metrics.json"
NEW=ROOT/"results/sdmr_nonlinear_effort_v2_prospective_result.json"
BUNDLE=ROOT/"scripts/build_process_information_anonymous_review_bundle.py"


def test_separate_frozen_denominators_and_unrevised_m5():
    main=json.loads(M5.read_text())
    newer=json.loads(NEW.read_text())
    assert main["counts"]["positive"]==80
    assert main["metrics"]["positive_recovery"]==0.8875
    assert main["metrics"]["false_positive_rate"]==0.0
    assert all(main["gates"].values())
    assert newer["denominator"]["cases"]==18
    assert newer["denominator"]["positive"]==12
    assert newer["denominator"]["replaceable"]==75
    assert newer["denominator"]["unresolved"]==3
    assert newer["primary_effort_unavailable"]["spatial"]["baseline_hgb_l2"]["positive_recovered"]==[0,12]
    assert newer["primary_effort_unavailable"]["spatial"]["nonlinear_hgb_rf"]["positive_recovered"]==[4,12]
    for split in ("random_cell","spatial"):
        for pair in ("baseline_hgb_l2","nonlinear_hgb_rf"):
            item=newer["primary_effort_unavailable"][split][pair]
            assert item["overresolved_unresolved"]==[1,3]
            assert item["false_positive_replaceable"]==[0,75]
    assert newer["boundaries"]["original_M5_evidence_changed"] is False
    assert newer["boundaries"]["method_promotion_authorized"] is False


def test_claim_ceiling_stays_explicit_in_manuscript_and_support():
    paper=MAIN.read_text()
    si=SI.read_text()
    scope=SCOPE.read_text()
    assert "0/12 to 4/12" in paper
    assert "1/3" in paper
    assert "neither field validation nor a new pass of the original M5 gates" in paper
    assert "**not four independent failures**" in si
    assert "**not a new M5 promotion" in scope
    assert "4/12" in si
    assert "0/75" in si


def test_anonymous_bundle_includes_provenance_redacted_new_receipt():
    script=BUNDLE.read_text()
    assert script.count('"results/sdmr_nonlinear_effort_v2_prospective_result.json"')==2
    assert '"manuscript/PROCESS_INFORMATION_KNOWN_TRUTH_SENSITIVITY_SI_V1.md"' in script
    for key in ('"head_sha"','"aggregate_artifact_id"','"aggregate_artifact_digest"'):
        assert key in script
