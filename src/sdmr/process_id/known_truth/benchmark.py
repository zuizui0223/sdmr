"""Known-truth oracle/occurrence comparison for SDMR v3."""
from __future__ import annotations

import pandas as pd


_KEYS = ("world", "seed", "process")
_POSITIVE = {"contributory", "required"}
_SHARP = {"replaceable", "contributory", "required"}
_STATES = _SHARP | {"unresolved", "unavailable"}


def _validate_state_table(frame: pd.DataFrame, *, name: str, state_col: str) -> pd.DataFrame:
    required = set(_KEYS) | {state_col}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"{name} missing columns: {missing}")
    data = frame.copy(deep=True)
    if data.loc[:, list(_KEYS)].isna().any().any():
        raise ValueError(f"{name} keys must not contain missing values")
    if data.duplicated(list(_KEYS)).any():
        raise ValueError(f"{name} contains duplicate world/seed/process cells")
    unknown = sorted(set(data[state_col].astype(str)) - _STATES)
    if unknown:
        raise ValueError(f"{name} contains unknown states: {unknown}")
    return data


def compare_oracle_and_occurrence(
    oracle_states: pd.DataFrame,
    occurrence_states: pd.DataFrame,
) -> pd.DataFrame:
    """Align oracle targets with occurrence-only states without collapsing abstention."""

    oracle = _validate_state_table(oracle_states, name="oracle_states", state_col="state")
    occurrence = _validate_state_table(
        occurrence_states, name="occurrence_states", state_col="state"
    )
    if "expected_state" not in oracle.columns:
        oracle["expected_state"] = oracle["state"].astype(str)
    unknown_expected = sorted(set(oracle["expected_state"].astype(str)) - _STATES)
    if unknown_expected:
        raise ValueError(f"oracle_states contains unknown expected states: {unknown_expected}")
    if "unique_attribution_forbidden" not in oracle.columns:
        oracle["unique_attribution_forbidden"] = False
    if not all(
        isinstance(value, bool)
        for value in oracle["unique_attribution_forbidden"].tolist()
    ):
        raise ValueError("unique_attribution_forbidden must be boolean")

    merged = oracle.loc[:, list(_KEYS) + ["state", "expected_state", "unique_attribution_forbidden"]].merge(
        occurrence.loc[:, list(_KEYS) + ["state"]],
        on=list(_KEYS),
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_oracle", "_occurrence"),
    )
    if not merged["_merge"].eq("both").all():
        missing = merged.loc[~merged["_merge"].eq("both"), list(_KEYS) + ["_merge"]]
        raise ValueError(
            "oracle/occurrence state cells do not align: "
            + missing.to_dict(orient="records").__repr__()
        )
    merged = merged.drop(columns="_merge").rename(
        columns={
            "state_oracle": "oracle_state",
            "expected_state": "target_state",
            "state_occurrence": "occurrence_state",
        }
    )
    merged["target_positive"] = merged["target_state"].isin(_POSITIVE)
    merged["occurrence_positive"] = merged["occurrence_state"].isin(_POSITIVE)
    merged["false_positive"] = merged["target_state"].eq("replaceable") & merged["occurrence_positive"]
    merged["overresolved"] = merged["target_state"].eq("unresolved") & merged["occurrence_state"].isin(_SHARP)
    merged["exact_target_match"] = merged["target_state"].eq(merged["occurrence_state"])
    return merged.reset_index(drop=True)
