import math

import pandas as pd
import pytest


def _rows(*rows):
    return pd.DataFrame(rows)


def test_replaceable_requires_positive_noninferiority_witness():
    from sdmr.process_id.states import classify_process_state

    evidence = _rows(
        dict(
            route="a",
            complete=True,
            full_adequate=True,
            knockout_adequate=True,
            delta_mean=0.005,
            delta_sem=0.002,
        ),
        dict(
            route="b",
            complete=False,
            full_adequate=True,
            knockout_adequate=False,
            delta_mean=math.nan,
            delta_sem=math.nan,
        ),
    )
    assert (
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)
        == "replaceable"
    )


def test_indeterminate_viable_route_forces_unresolved():
    from sdmr.process_id.states import classify_process_state

    evidence = _rows(
        dict(
            route="a",
            complete=True,
            full_adequate=True,
            knockout_adequate=True,
            delta_mean=0.012,
            delta_sem=0.006,
        ),
        dict(
            route="b",
            complete=True,
            full_adequate=True,
            knockout_adequate=True,
            delta_mean=0.030,
            delta_sem=0.003,
        ),
    )
    assert (
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)
        == "unresolved"
    )


def test_all_complete_positive_loss_with_adequate_survivor_is_contributory():
    from sdmr.process_id.states import classify_process_state

    evidence = _rows(
        dict(
            route="a",
            complete=True,
            full_adequate=True,
            knockout_adequate=True,
            delta_mean=0.030,
            delta_sem=0.003,
        ),
        dict(
            route="b",
            complete=True,
            full_adequate=True,
            knockout_adequate=False,
            delta_mean=0.040,
            delta_sem=0.004,
        ),
    )
    assert (
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)
        == "contributory"
    )


def test_all_complete_positive_loss_and_no_adequate_route_is_required():
    from sdmr.process_id.states import classify_process_state

    evidence = _rows(
        dict(
            route="a",
            complete=True,
            full_adequate=True,
            knockout_adequate=False,
            delta_mean=0.030,
            delta_sem=0.003,
        ),
        dict(
            route="b",
            complete=True,
            full_adequate=True,
            knockout_adequate=False,
            delta_mean=0.040,
            delta_sem=0.004,
        ),
    )
    assert (
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)
        == "required"
    )


def test_inadequate_full_reference_is_unavailable():
    from sdmr.process_id.states import classify_process_state

    evidence = _rows(
        dict(
            route="a",
            complete=True,
            full_adequate=False,
            knockout_adequate=False,
            delta_mean=0.05,
            delta_sem=0.001,
        )
    )
    assert (
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)
        == "unavailable"
    )


@pytest.mark.parametrize(
    "evidence, match",
    [
        (pd.DataFrame(), "non-empty"),
        (
            _rows(
                dict(
                    route="a",
                    complete=True,
                    full_adequate=True,
                    knockout_adequate=True,
                    delta_mean=0.0,
                )
            ),
            "missing columns",
        ),
        (
            _rows(
                dict(
                    route="a",
                    complete=True,
                    full_adequate=True,
                    knockout_adequate=True,
                    delta_mean=0.0,
                    delta_sem=-0.1,
                )
            ),
            "delta_sem",
        ),
        (
            _rows(
                dict(
                    route="a",
                    complete=True,
                    full_adequate=True,
                    knockout_adequate=True,
                    delta_mean=math.nan,
                    delta_sem=0.1,
                )
            ),
            "complete rows",
        ),
    ],
)
def test_state_engine_fails_closed_on_malformed_evidence(evidence, match):
    from sdmr.process_id.states import classify_process_state

    with pytest.raises((KeyError, ValueError), match=match):
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)


def test_state_engine_rejects_duplicate_routes():
    from sdmr.process_id.states import classify_process_state

    evidence = _rows(
        dict(
            route="a",
            complete=True,
            full_adequate=True,
            knockout_adequate=True,
            delta_mean=0.0,
            delta_sem=0.0,
        ),
        dict(
            route="a",
            complete=True,
            full_adequate=True,
            knockout_adequate=True,
            delta_mean=0.0,
            delta_sem=0.0,
        ),
    )
    with pytest.raises(ValueError, match="unique"):
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)


def test_state_engine_rejects_non_boolean_flags():
    from sdmr.process_id.states import classify_process_state

    evidence = _rows(
        dict(
            route="a",
            complete="yes",
            full_adequate=True,
            knockout_adequate=True,
            delta_mean=0.0,
            delta_sem=0.0,
        )
    )
    with pytest.raises(ValueError, match="boolean"):
        classify_process_state(evidence, margin=0.01, adequacy_floor=0.0)


def test_identical_closure_abstention_also_rejects_sharp_replaceable_states():
    import pandas as pd
    from sdmr.process_id.states import apply_identical_closure_abstention

    states = pd.DataFrame([
        {"process": "thermal", "state": "replaceable", "closure_predictors": "pet_shared", "reason": "interval_process_challenge"},
        {"process": "water", "state": "replaceable", "closure_predictors": "pet_shared", "reason": "interval_process_challenge"},
    ])
    out = apply_identical_closure_abstention(states)
    assert set(out["state"]) == {"unresolved"}
    assert set(out["reason"]) == {"identical_shared_carrier_closure"}
