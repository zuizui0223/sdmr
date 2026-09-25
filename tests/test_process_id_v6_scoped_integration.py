import pandas as pd


def _stage_p():
    rows=[]
    # Two seeds, eight worlds, one process per world is enough for scope test.
    for seed in (1,2):
        for world in (
            "unique_process","redundant_representation","shared_carrier",
            "null_correlated","interaction","observation_confounded",
            "omitted_driver","geographic_shift"
        ):
            odo="unavailable" if world=="omitted_driver" else (
                "unresolved" if world=="observation_confounded" else "replaceable"
            )
            finite="unavailable" if world=="omitted_driver" else (
                "unresolved" if world=="observation_confounded" else "replaceable"
            )
            adequate=world not in {"observation_confounded","omitted_driver"}
            rows.append({
                "seed":seed,"world":world,"process":"thermal",
                "odo_state":odo,"finite_state":finite,
                "structural_refusal_expected":world=="observation_confounded",
                "full_system_information_adequate":adequate,
            })
    return pd.DataFrame(rows)


def test_scoped_authorization_ignores_report_only_w6():
    from sdmr.process_id.known_truth.integration_v6 import (
        full_system_authorization_scope,
    )

    rates=full_system_authorization_scope(
        _stage_p(),
        informative_controls=(
            "unique_process","redundant_representation","shared_carrier",
            "null_correlated","interaction","geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
    )
    assert rates["minimum_informative_control_rate"]==1.0
    assert rates["report_only_rate"]==0.0
    assert rates["null_rate"]==0.0


def test_scoped_int_e_passes_when_controls_and_null_are_correct_even_if_w6_blocked():
    from sdmr.process_id.known_truth.integration_v6 import (
        evaluate_scoped_int_e,
    )

    result=evaluate_scoped_int_e(
        _stage_p(),
        informative_controls=(
            "unique_process","redundant_representation","shared_carrier",
            "null_correlated","interaction","geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
        minimum_each_control_rate=0.95,
        maximum_null_authorized_count=0,
        maximum_unavailable_sharp_rate=0.0,
        maximum_unavailable_favorable_rate=0.0,
    )
    assert result["passed"]
    assert result["minimum_informative_control_rate"]==1.0
    assert result["report_only_rate"]==0.0
    assert result["null_authorized_count"]==0


def test_scoped_int_e_fails_if_one_informative_control_drops():
    from sdmr.process_id.known_truth.integration_v6 import evaluate_scoped_int_e

    data=_stage_p()
    mask=(data["world"].eq("geographic_shift") & data["seed"].eq(2))
    data.loc[mask,"full_system_information_adequate"]=False
    result=evaluate_scoped_int_e(
        data,
        informative_controls=(
            "unique_process","redundant_representation","shared_carrier",
            "null_correlated","interaction","geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
        minimum_each_control_rate=0.95,
        maximum_null_authorized_count=0,
        maximum_unavailable_sharp_rate=0.0,
        maximum_unavailable_favorable_rate=0.0,
    )
    assert not result["passed"]
    assert result["minimum_informative_control_rate"]==0.5


def test_scoped_int_e_fails_if_w7_authorizes():
    from sdmr.process_id.known_truth.integration_v6 import evaluate_scoped_int_e

    data=_stage_p()
    mask=(data["world"].eq("omitted_driver") & data["seed"].eq(2))
    data.loc[mask,"full_system_information_adequate"]=True
    data.loc[mask,"finite_state"]="replaceable"
    result=evaluate_scoped_int_e(
        data,
        informative_controls=(
            "unique_process","redundant_representation","shared_carrier",
            "null_correlated","interaction","geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
        minimum_each_control_rate=0.95,
        maximum_null_authorized_count=0,
        maximum_unavailable_sharp_rate=0.0,
        maximum_unavailable_favorable_rate=0.0,
    )
    assert not result["passed"]
    assert result["null_authorized_count"]==1
    assert result["unavailable_sharp_rate"]==0.5
