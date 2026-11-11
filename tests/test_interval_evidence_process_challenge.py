import pandas as pd

from sdmr.interval_evidence_process_challenge import (
    INDETERMINATE_EVIDENCE,
    INFERIOR_EVIDENCE,
    NONINFERIOR_EVIDENCE,
    _classify_processes,
    interval_evidence_state,
)
from sdmr.process_challenge_learner import CONTRIBUTORY, REPLACEABLE, REQUIRED, UNRESOLVED


def test_interval_state_separates_noninferior_inferior_and_indeterminate() -> None:
    noninferior = interval_evidence_state(-0.005, 0.002, margin=0.01, sem_multiplier=1.0)
    inferior = interval_evidence_state(-0.020, 0.003, margin=0.01, sem_multiplier=1.0)
    indeterminate = interval_evidence_state(-0.010, 0.004, margin=0.01, sem_multiplier=1.0)
    assert noninferior["state"] == NONINFERIOR_EVIDENCE
    assert inferior["state"] == INFERIOR_EVIDENCE
    assert indeterminate["state"] == INDETERMINATE_EVIDENCE


def _route(model, process, *, adequate, state, complete=True):
    return {
        "model_label": model,
        "excluded_process": process,
        "route": f"{model}:{process}",
        "complete": complete,
        "route_adequate": adequate,
        "relative_evidence_state": state,
    }


def test_process_is_replaceable_with_one_established_noninferior_viable_route() -> None:
    frame = pd.DataFrame(
        [
            _route("m1", "p", adequate=True, state=NONINFERIOR_EVIDENCE),
            _route("m2", "p", adequate=True, state=INFERIOR_EVIDENCE),
        ]
    )
    out = _classify_processes(frame, ("p",), expected_model_labels=("m1", "m2"))
    assert out.iloc[0]["status"] == REPLACEABLE


def test_process_is_contributory_only_when_every_viable_route_establishes_inferiority() -> None:
    frame = pd.DataFrame(
        [
            _route("m1", "p", adequate=True, state=INFERIOR_EVIDENCE),
            _route("m2", "p", adequate=False, state=INDETERMINATE_EVIDENCE),
        ]
    )
    out = _classify_processes(frame, ("p",), expected_model_labels=("m1", "m2"))
    assert out.iloc[0]["status"] == CONTRIBUTORY


def test_failure_to_establish_noninferiority_is_unresolved_not_contributory() -> None:
    frame = pd.DataFrame(
        [
            _route("m1", "p", adequate=True, state=INDETERMINATE_EVIDENCE),
            _route("m2", "p", adequate=False, state=INFERIOR_EVIDENCE),
        ]
    )
    out = _classify_processes(frame, ("p",), expected_model_labels=("m1", "m2"))
    assert out.iloc[0]["status"] == UNRESOLVED
    assert out.iloc[0]["n_indeterminate_viable_routes"] == 1


def test_process_is_required_only_when_all_complete_routes_are_absolutely_inadequate() -> None:
    frame = pd.DataFrame(
        [
            _route("m1", "p", adequate=False, state=INDETERMINATE_EVIDENCE),
            _route("m2", "p", adequate=False, state=INFERIOR_EVIDENCE),
        ]
    )
    out = _classify_processes(frame, ("p",), expected_model_labels=("m1", "m2"))
    assert out.iloc[0]["status"] == REQUIRED


def test_missing_expected_route_is_unresolved() -> None:
    frame = pd.DataFrame([_route("m1", "p", adequate=False, state=INFERIOR_EVIDENCE)])
    out = _classify_processes(frame, ("p",), expected_model_labels=("m1", "m2"))
    assert out.iloc[0]["status"] == UNRESOLVED
