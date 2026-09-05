import pandas as pd
import pytest

from sdmr.sealed_occurrence_contract import (
    ANSWER_CHECK_ROLE,
    MODEL_POOL_ROLE,
    freeze_occurrence_answer_check_split,
)


def _occurrences() -> pd.DataFrame:
    rows = []
    for i in range(40):
        rows.append(
            {
                "occurrence_id": f"occ-{i:03d}",
                "longitude": 130.0 + (i % 10) * 0.7,
                "latitude": 30.0 + (i // 10) * 1.3,
                "bio1": 10.0 + i,
            }
        )
    return pd.DataFrame(rows)


def test_split_assigns_whole_occurrence_roles_and_is_deterministic() -> None:
    occurrences = _occurrences()
    a = freeze_occurrence_answer_check_split(
        occurrences,
        n_blocks=8,
        holdout_fraction=0.25,
        random_state=17,
    )
    b = freeze_occurrence_answer_check_split(
        occurrences.sample(frac=1.0, random_state=99).reset_index(drop=True),
        n_blocks=8,
        holdout_fraction=0.25,
        random_state=17,
    )

    assert set(a.assignment["outer_role"]) == {MODEL_POOL_ROLE, ANSWER_CHECK_ROLE}
    assert set(a.model_pool_ids).isdisjoint(set(a.answer_check_ids))
    assert set(a.model_pool_ids) | set(a.answer_check_ids) == set(occurrences["occurrence_id"])
    assert a.split_digest == b.split_digest
    pd.testing.assert_frame_equal(a.assignment, b.assignment)


def test_model_pool_filter_prevents_answer_check_leakage() -> None:
    occurrences = _occurrences()
    split = freeze_occurrence_answer_check_split(
        occurrences,
        n_blocks=8,
        holdout_fraction=0.25,
        random_state=11,
    )

    model_pool = split.model_pool(occurrences)
    assert set(model_pool["occurrence_id"]) == set(split.model_pool_ids)
    split.assert_model_pool_only(model_pool)

    leaked = occurrences.loc[
        occurrences["occurrence_id"].isin(split.answer_check_ids[:1])
    ]
    with pytest.raises(RuntimeError, match="leakage"):
        split.assert_model_pool_only(pd.concat([model_pool, leaked], ignore_index=True))


def test_answer_check_requires_frozen_selection_receipt() -> None:
    occurrences = _occurrences()
    split = freeze_occurrence_answer_check_split(occurrences, random_state=3)

    with pytest.raises(ValueError, match="selection_receipt"):
        split.open_answer_check(occurrences, selection_receipt="")

    sealed = split.open_answer_check(
        occurrences,
        selection_receipt="candidate=ecological-v1;sha=abc123",
    )
    assert set(sealed["occurrence_id"]) == set(split.answer_check_ids)


def test_unknown_ids_fail_closed() -> None:
    occurrences = _occurrences()
    split = freeze_occurrence_answer_check_split(occurrences, random_state=5)
    bad = occurrences.iloc[:3].copy()
    bad.loc[bad.index[0], "occurrence_id"] = "not-in-frozen-split"

    with pytest.raises(ValueError, match="outside frozen occurrence split"):
        split.model_pool(bad)
