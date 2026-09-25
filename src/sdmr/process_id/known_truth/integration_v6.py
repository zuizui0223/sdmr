"""SDMR v6 scoped full-system authorization helpers.

This module corrects only the integration/prospective authorization scope:
informative controls are evaluated explicitly, W6 remains report-only, and W7
remains the null-control world. Older v5/v6-v1 evaluators remain untouched.
"""
from __future__ import annotations

import pandas as pd


_SHARP={"replaceable","contributory","required"}
_POSITIVE={"contributory","required"}


def _world_authorization_table(stage_p_states: pd.DataFrame) -> pd.DataFrame:
    required={
        "seed","world","process","odo_state","finite_state",
        "full_system_information_adequate",
    }
    missing=sorted(required-set(stage_p_states.columns))
    if missing:
        raise KeyError(f"stage_p_states missing columns: {missing}")
    if stage_p_states.empty:
        raise ValueError("stage_p_states must be non-empty")

    rows=[]
    for (seed,world),group in stage_p_states.groupby(["seed","world"],sort=True):
        values=set(group["full_system_information_adequate"].astype(bool))
        if len(values)!=1:
            raise ValueError(
                "full-system authorization must be constant within seed/world"
            )
        rows.append({
            "seed":int(seed),
            "world":str(world),
            "authorized":bool(next(iter(values))),
        })
    return pd.DataFrame(rows)


def full_system_authorization_scope(
    stage_p_states: pd.DataFrame,
    *,
    informative_controls: tuple[str,...],
    report_only_world: str,
    null_world: str,
) -> dict[str,object]:
    """Summarize full-system authorization using explicit world roles."""

    controls=tuple(str(x) for x in informative_controls)
    if not controls or len(set(controls))!=len(controls):
        raise ValueError("informative_controls must be non-empty and unique")
    report_only_world=str(report_only_world)
    null_world=str(null_world)
    if report_only_world in controls or null_world in controls:
        raise ValueError("report/null worlds cannot also be informative controls")
    if report_only_world==null_world:
        raise ValueError("report_only_world and null_world must differ")

    table=_world_authorization_table(stage_p_states)
    observed=set(table["world"])
    required=set(controls)|{report_only_world,null_world}
    missing=sorted(required-observed)
    if missing:
        raise ValueError(f"required authorization worlds missing: {missing}")

    rates={}
    counts={}
    denominators={}
    for world,group in table.groupby("world",sort=True):
        rate=float(group["authorized"].mean())
        rates[str(world)]=rate
        counts[str(world)]=int(group["authorized"].sum())
        denominators[str(world)]=int(len(group))

    control_rates={world:rates[world] for world in controls}
    return {
        "world_rates":rates,
        "world_authorized_counts":counts,
        "world_denominators":denominators,
        "minimum_informative_control_rate":float(min(control_rates.values())),
        "informative_control_rates":control_rates,
        "report_only_rate":float(rates[report_only_world]),
        "null_rate":float(rates[null_world]),
        "null_authorized_count":int(counts[null_world]),
    }


def _rate(numerator_mask, denominator_mask) -> float:
    denominator=int(denominator_mask.sum())
    if denominator<=0:
        return float("nan")
    return float((numerator_mask & denominator_mask).sum()/denominator)


def evaluate_scoped_int_e(
    stage_p_states: pd.DataFrame,
    *,
    informative_controls: tuple[str,...],
    report_only_world: str,
    null_world: str,
    minimum_each_control_rate: float,
    maximum_null_authorized_count: int,
    maximum_unavailable_sharp_rate: float,
    maximum_unavailable_favorable_rate: float,
) -> dict[str,object]:
    """Evaluate corrected INT-E without pooling the report-only world."""

    minimum_each_control_rate=float(minimum_each_control_rate)
    maximum_unavailable_sharp_rate=float(maximum_unavailable_sharp_rate)
    maximum_unavailable_favorable_rate=float(maximum_unavailable_favorable_rate)
    maximum_null_authorized_count=int(maximum_null_authorized_count)
    for name,value in (
        ("minimum_each_control_rate",minimum_each_control_rate),
        ("maximum_unavailable_sharp_rate",maximum_unavailable_sharp_rate),
        ("maximum_unavailable_favorable_rate",maximum_unavailable_favorable_rate),
    ):
        if not 0.0<=value<=1.0:
            raise ValueError(f"{name} must be in [0,1]")
    if maximum_null_authorized_count<0:
        raise ValueError("maximum_null_authorized_count must be non-negative")

    scope=full_system_authorization_scope(
        stage_p_states,
        informative_controls=informative_controls,
        report_only_world=report_only_world,
        null_world=null_world,
    )

    odo_unavailable=stage_p_states["odo_state"].eq("unavailable")
    finite_sharp=stage_p_states["finite_state"].isin(_SHARP)
    finite_positive=stage_p_states["finite_state"].isin(_POSITIVE)
    unavailable_sharp_rate=_rate(finite_sharp,odo_unavailable)
    unavailable_favorable_rate=_rate(finite_positive,odo_unavailable)

    passed=bool(
        scope["minimum_informative_control_rate"]>=minimum_each_control_rate
        and scope["null_authorized_count"]<=maximum_null_authorized_count
        and unavailable_sharp_rate<=maximum_unavailable_sharp_rate
        and unavailable_favorable_rate<=maximum_unavailable_favorable_rate
    )
    return {
        **scope,
        "unavailable_sharp_rate":unavailable_sharp_rate,
        "unavailable_favorable_rate":unavailable_favorable_rate,
        "passed":passed,
    }
