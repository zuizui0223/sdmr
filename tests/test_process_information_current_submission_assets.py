"""Production-level invariants for the current M5 submission refresh."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_current_submission_build_is_revision_audited():
    workflow=(ROOT/".github/workflows/process-information-mee-submission-assets.yml").read_text()
    assert "paper/m5-oct28-submission-assets-refresh" in workflow
    assert "audit_process_information_submission_assets.py" in workflow
    assert "--revision \"$GITHUB_SHA\"" in workflow
    assert "build_process_information_anonymous_review_bundle.py" in workflow


def test_all_four_figures_have_visual_png_previews():
    figures=(ROOT/"manuscript/figures/build_process_information_figures.py").read_text()
    conceptual=(ROOT/"manuscript/figures/build_process_information_conceptual_figures.py").read_text()
    assert figures.count('out.with_suffix(".png")') == 2
    assert "figure1_process_information_closure.svg" in conceptual
    assert "figure2_known_truth_worlds.svg" in conceptual
    assert 'output.with_suffix(".png")' in conceptual


def test_anonymized_science_disclosures_are_required_by_build():
    code=(ROOT/"scripts/audit_process_information_submission_assets.py").read_text()
    for anchor in ("71/80", "0/700", "16/300", "10/50", "0/12 to 4/12", "1/3"):
        assert anchor in code
    assert "REVIEW_RECEIPTS" in (ROOT/"scripts/build_process_information_anonymous_review_bundle.py").read_text()
    assert "continuous_line_numbers_present" in code


def test_journal_ai_disclosure_is_not_treated_as_completed_author_review():
    manuscript=(ROOT/"manuscript/PROCESS_INFORMATION_MEE_SUBMISSION_V1.md").read_text()
    readiness=(ROOT/"manuscript/MEE_SUBMISSION_READINESS_V1.md").read_text()
    builder=(ROOT/"scripts/build_process_information_mee_manuscript_docx.py").read_text()
    assert "### 2.8 AI-assisted preparation and verification" in manuscript
    assert "OpenAI ChatGPT" in manuscript
    assert "before submission" in manuscript
    assert "- [ ] Corresponding author verifies all AI-assisted" in readiness
    assert "Internal routing metadata belongs in the submission form" in builder
