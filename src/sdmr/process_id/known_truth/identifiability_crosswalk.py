"""Crosswalk truth-surface, occurrence-distribution, and finite-learner states."""
from __future__ import annotations

import pandas as pd


_KEYS = ("world", "seed", "process")
_POSITIVE = {"contributory", "required"}


def _validate_oracle(frame: pd.DataFrame, *, name: str) -> pd.DataFrame:
    required = set(_KEYS) | {"state"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"{name} missing columns: {missing}")
    data = frame.copy(deep=True)
    if data.loc[:, list(_KEYS)].isna().any().any():
        raise ValueError(f"{name} keys must not contain missing values")
    if data.duplicated(list(_KEYS)).any():
        raise ValueError(f"{name} contains duplicate world/seed/process cells")
    return data


def build_identifiability_crosswalk(
    truth_states: pd.DataFrame,
    distribution_states: pd.DataFrame,
    finite_states: pd.DataFrame,
) -> pd.DataFrame:
    """Align the three identifiability levels without treating contraction as error."""

    truth = _validate_oracle(truth_states, name="truth_states")
    distribution = _validate_oracle(distribution_states, name="distribution_states")
    finite_required = set(_KEYS) | {"learner", "state"}
    missing = sorted(finite_required - set(finite_states.columns))
    if missing:
        raise KeyError(f"finite_states missing columns: {missing}")
    finite = finite_states.copy(deep=True)
    if finite.loc[:, list(_KEYS) + ["learner"]].isna().any().any():
        raise ValueError("finite_states keys must not contain missing values")
    if finite.duplicated(list(_KEYS) + ["learner"]).any():
        raise ValueError("finite_states contains duplicate world/seed/process/learner cells")

    truth_keys = set(map(tuple, truth.loc[:, list(_KEYS)].itertuples(index=False, name=None)))
    distribution_keys = set(map(tuple, distribution.loc[:, list(_KEYS)].itertuples(index=False, name=None)))
    finite_keys = set(map(tuple, finite.loc[:, list(_KEYS)].itertuples(index=False, name=None)))
    if truth_keys != distribution_keys or truth_keys != finite_keys:
        raise ValueError("truth, distribution, and finite identifiability keys do not align")

    base = truth.loc[:, list(_KEYS) + ["state"]].rename(columns={"state": "truth_state"})
    base = base.merge(
        distribution.loc[:, list(_KEYS) + ["state"]].rename(
            columns={"state": "distribution_state"}
        ),
        on=list(_KEYS),
        how="inner",
        validate="one_to_one",
    )
    out = finite.merge(base, on=list(_KEYS), how="inner", validate="many_to_one")
    out = out.rename(columns={"state": "finite_state"})

    out["truth_positive"] = out["truth_state"].isin(_POSITIVE)
    out["distribution_positive"] = out["distribution_state"].isin(_POSITIVE)
    out["finite_positive"] = out["finite_state"].isin(_POSITIVE)
    out["truth_positive_but_distribution_not_positive"] = (
        out["truth_positive"] & ~out["distribution_positive"]
    )
    out["finite_false_negative_given_distribution_positive"] = (
        out["distribution_positive"] & ~out["finite_positive"]
    )
    out["finite_false_positive_given_distribution_not_positive"] = (
        ~out["distribution_positive"] & out["finite_positive"]
    )
    out["distribution_contracts_truth"] = out["truth_state"].ne(out["distribution_state"])
    return out.sort_values(list(_KEYS) + ["learner"], kind="mergesort").reset_index(drop=True)
