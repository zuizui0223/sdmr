import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("guard", Path(__file__).resolve().parents[1] / "scripts/retired_real_control_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def run_record():
    return {"workflow_id": 351511089, "head_branch": guard.BRANCH,
            "head_sha": guard.ACCIDENTAL_SHA, "event": "pull_request",
            "status": "in_progress", "pull_requests": [{"number": 192}],
            "repository": {"full_name": guard.REPOSITORY},
            "head_repository": {"full_name": guard.REPOSITORY}}


def test_only_accidental_or_current_head_is_authorized():
    run = run_record()
    assert guard.should_cancel(run, "newhead")
    run["head_sha"] = "newhead"
    assert guard.should_cancel(run, "newhead")
    run["head_sha"] = "original-evidence-sha"
    assert not guard.should_cancel(run, "newhead")


@pytest.mark.parametrize("key,value", [
    ("event", "workflow_dispatch"), ("workflow_id", 351368052),
    ("status", "completed"), ("head_branch", "main"),
    ("pull_requests", [{"number": 200}]), ("pull_requests", []),
    ("repository", {"full_name": "other/repo"}),
    ("head_repository", {"full_name": "fork/sdmr"}),
])
def test_unrelated_or_completed_runs_are_never_cancelled(key, value):
    run = run_record()
    run[key] = value
    assert not guard.should_cancel(run, "newhead")
