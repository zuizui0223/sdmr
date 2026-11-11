"""Cancel only duplicate PR-192 executions of the four consumed empirical jobs.

Does not delete runs/artifacts, dispatch experiments, or edit scientific files.
Manual reproductions and any other PR, branch, repository or workflow are ignored.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPOSITORY = "zuizui0223/sdmr"
BRANCH = "manuscript/v1-v284-synthesis"
ACCIDENTAL_SHA = "86cd0a94da48c8505886f1e02e9a07816e8aff11"
WORKFLOWS = frozenset({351451195, 351475485, 351498957, 351511089})
ACTIVE = frozenset({"queued", "pending", "in_progress", "waiting", "requested"})


def should_cancel(run: dict[str, Any], current_head_sha: str) -> bool:
    """Exact provenance guard: never infer scope from a display title."""
    prs = {p.get("number") for p in run.get("pull_requests", [])}
    return bool(
        run.get("workflow_id") in WORKFLOWS
        and run.get("head_branch") == BRANCH
        and run.get("head_sha") in {ACCIDENTAL_SHA, current_head_sha}
        and run.get("event") == "pull_request"
        and run.get("status") in ACTIVE
        and prs == {192}
        and run.get("repository", {}).get("full_name") == REPOSITORY
        and run.get("head_repository", {}).get("full_name") == REPOSITORY
    )


def api(path: str, token: str, method: str = "GET") -> Any:
    request = Request(
        "https://api.github.com/repos/" + REPOSITORY + path,
        data=b"" if method == "POST" else None,
        method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def main() -> None:
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise SystemExit("wrong repository")
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as stream:
        event = json.load(stream)
    pr = event.get("pull_request", {})
    if (event.get("number") != 192 or pr.get("head", {}).get("ref") != BRANCH
            or pr.get("head", {}).get("repo", {}).get("full_name") != REPOSITORY):
        raise SystemExit("not the authorized same-repository PR")
    current_sha = pr["head"]["sha"]
    token = os.environ["GH_TOKEN"]
    targets = {}
    for sha in sorted({ACCIDENTAL_SHA, current_sha}):
        payload = api(f"/actions/runs?head_sha={sha}&event=pull_request&per_page=100", token)
        if payload.get("total_count", 0) > 100:
            raise SystemExit("unexpected pagination: refusing an incomplete execution inventory")
        for run in payload.get("workflow_runs", []):
            if should_cancel(run, current_sha):
                targets[run["id"]] = run
    for run_id in sorted(targets):
        # Recheck provenance immediately before the only permitted mutation.
        run = api(f"/actions/runs/{run_id}", token)
        if not should_cancel(run, current_sha):
            print(f"No cancellation needed for {run_id}: {run.get('status')}")
            continue
        try:
            api(f"/actions/runs/{run_id}/cancel", token, method="POST")
        except HTTPError as exc:
            if exc.code == 409 and api(f"/actions/runs/{run_id}", token).get("status") == "completed":
                print(f"Run {run_id} completed before cancellation")
                continue
            raise
        print(f"Cancellation requested: {run_id}, workflow {run['workflow_id']}, head {run['head_sha']}")
    print("Original completed evidence and manual reproductions unchanged.")


if __name__ == "__main__":
    main()
