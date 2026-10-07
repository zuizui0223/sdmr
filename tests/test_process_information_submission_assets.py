from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
W=ROOT/'.github'/'workflows'/'process-information-mee-submission-assets.yml'

def test_submission_asset_workflow_builds_only_anonymous_review_assets():
    text=W.read_text()
    assert 'build_process_information_figures.py' in text
    assert 'build_process_information_anonymous_review_bundle.py' in text
    assert 'github.com/zuizui0223' in text  # audited as forbidden manuscript content
    assert 'actions/upload-artifact@v4' in text
    assert 'manuscript_under_8000_words' in text
    assert 'abstract_under_350_words' in text
