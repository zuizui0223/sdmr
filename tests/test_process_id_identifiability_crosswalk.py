import pandas as pd
import pytest


def test_truth_positive_distribution_replaceable_is_not_finite_false_negative():
    from sdmr.process_id.known_truth.identifiability_crosswalk import (
        build_identifiability_crosswalk,
    )

    truth = pd.DataFrame([
        {"world": "w", "seed": 1, "process": "thermal", "state": "contributory"},
    ])
    distribution = pd.DataFrame([
        {"world": "w", "seed": 1, "process": "thermal", "state": "replaceable"},
    ])
    finite = pd.DataFrame([
        {"world": "w", "seed": 1, "process": "thermal", "learner": "linear", "state": "replaceable"},
    ])
    out = build_identifiability_crosswalk(truth, distribution, finite)
    row = out.iloc[0]
    assert bool(row["truth_positive_but_distribution_not_positive"])
    assert not bool(row["finite_false_negative_given_distribution_positive"])


def test_distribution_positive_finite_unresolved_is_finite_nonrecovery():
    from sdmr.process_id.known_truth.identifiability_crosswalk import (
        build_identifiability_crosswalk,
    )

    truth = pd.DataFrame([
        {"world": "w", "seed": 2, "process": "water", "state": "contributory"},
    ])
    distribution = pd.DataFrame([
        {"world": "w", "seed": 2, "process": "water", "state": "required"},
    ])
    finite = pd.DataFrame([
        {"world": "w", "seed": 2, "process": "water", "learner": "quadratic", "state": "unresolved"},
    ])
    out = build_identifiability_crosswalk(truth, distribution, finite)
    row = out.iloc[0]
    assert bool(row["distribution_positive"])
    assert not bool(row["finite_positive"])
    assert bool(row["finite_false_negative_given_distribution_positive"])


def test_crosswalk_keeps_multiple_finite_learners():
    from sdmr.process_id.known_truth.identifiability_crosswalk import (
        build_identifiability_crosswalk,
    )

    truth = pd.DataFrame([
        {"world": "w", "seed": 3, "process": "thermal", "state": "contributory"},
    ])
    distribution = pd.DataFrame([
        {"world": "w", "seed": 3, "process": "thermal", "state": "contributory"},
    ])
    finite = pd.DataFrame([
        {"world": "w", "seed": 3, "process": "thermal", "learner": "linear", "state": "unresolved"},
        {"world": "w", "seed": 3, "process": "thermal", "learner": "quadratic", "state": "contributory"},
    ])
    out = build_identifiability_crosswalk(truth, distribution, finite)
    assert set(out["learner"]) == {"linear", "quadratic"}
    assert len(out) == 2


def test_crosswalk_fails_closed_on_duplicate_or_misaligned_keys():
    from sdmr.process_id.known_truth.identifiability_crosswalk import (
        build_identifiability_crosswalk,
    )

    truth = pd.DataFrame([
        {"world": "w", "seed": 1, "process": "thermal", "state": "contributory"},
        {"world": "w", "seed": 1, "process": "thermal", "state": "contributory"},
    ])
    distribution = pd.DataFrame([
        {"world": "w", "seed": 1, "process": "thermal", "state": "contributory"},
    ])
    finite = pd.DataFrame([
        {"world": "w", "seed": 1, "process": "thermal", "learner": "linear", "state": "contributory"},
    ])
    with pytest.raises(ValueError, match="duplicate"):
        build_identifiability_crosswalk(truth, distribution, finite)

    truth = truth.iloc[:1].copy()
    finite = pd.DataFrame([
        {"world": "w", "seed": 9, "process": "thermal", "learner": "linear", "state": "contributory"},
    ])
    with pytest.raises(ValueError, match="align"):
        build_identifiability_crosswalk(truth, distribution, finite)
