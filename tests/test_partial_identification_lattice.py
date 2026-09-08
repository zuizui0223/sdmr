from sdmr.partial_identification_lattice import (
    CONTRIBUTORY,
    REPLACEABLE,
    UNRESOLVED,
    REPLACEABLE_STATE,
    SHARED_CANDIDATE,
    UNIQUE_CONTRIBUTORY,
    UNRESOLVED_STATE,
    classify_partial_identification,
)


def test_unique_contribution_is_singleton_attribution():
    out = classify_partial_identification(total_status=CONTRIBUTORY, unique_status=CONTRIBUTORY)
    assert out.state == UNIQUE_CONTRIBUTORY
    assert out.individually_identified is True
    assert out.retained_as_candidate is True


def test_total_only_support_is_not_forced_to_singleton():
    out = classify_partial_identification(total_status=CONTRIBUTORY, unique_status=REPLACEABLE)
    assert out.state == SHARED_CANDIDATE
    assert out.individually_identified is False
    assert out.retained_as_candidate is True


def test_unresolved_unique_evidence_cannot_promote_total_support():
    out = classify_partial_identification(total_status=CONTRIBUTORY, unique_status=UNRESOLVED)
    assert out.state == SHARED_CANDIDATE
    assert out.individually_identified is False


def test_replaceable_in_both_axes_is_replaceable():
    out = classify_partial_identification(total_status=REPLACEABLE, unique_status=REPLACEABLE)
    assert out.state == REPLACEABLE_STATE
    assert out.retained_as_candidate is False


def test_unresolved_inputs_remain_unresolved():
    out = classify_partial_identification(total_status=UNRESOLVED, unique_status=REPLACEABLE)
    assert out.state == UNRESOLVED_STATE
    assert out.individually_identified is False
