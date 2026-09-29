import pandas as pd


def _stage_rows():
    rows=[]
    controls=[
        "unique_process",
        "redundant_representation",
        "shared_carrier",
        "null_correlated",
        "interaction",
        "geographic_shift",
    ]
    for seed in (1,2):
        for world in controls:
            rows.append({
                "seed":seed,"world":world,"process":"thermal",
                "odo_state":"contributory","finite_state":"contributory",
                "structural_refusal_expected":False,
                "full_system_information_adequate":True,
            })
        rows.append({
            "seed":seed,"world":"unique_process","process":"productivity",
            "odo_state":"replaceable","finite_state":"replaceable",
            "structural_refusal_expected":False,
            "full_system_information_adequate":True,
        })
        rows.append({
            "seed":seed,"world":"observation_confounded","process":"thermal",
            "odo_state":"unresolved","finite_state":"unresolved",
            "structural_refusal_expected":True,
            "full_system_information_adequate":False,
        })
        rows.append({
            "seed":seed,"world":"omitted_driver","process":"thermal",
            "odo_state":"unavailable","finite_state":"unavailable",
            "structural_refusal_expected":False,
            "full_system_information_adequate":False,
        })
    return pd.DataFrame(rows)


def _stage_t_from_p(stage_p):
    out=stage_p.drop(columns=["full_system_information_adequate"]).copy()
    return out


def _gate_vector():
    return {
        "KT-B":{"minimum":0.80},
        "KT-C":{"maximum":0.01},
        "KT-D":{
            "max_overresolution_rate_among_odo_unresolved":0.0,
            "max_structural_refusal_violation_rate":0.0,
        },
        "KT-E":{
            "max_sharp_rate_among_odo_unavailable":0.0,
            "max_favorable_positive_rate_among_odo_unavailable":0.0,
            "minimum_each_informative_control_authorization_rate":0.95,
            "maximum_w7_authorized_count":0,
        },
        "KT-F":{
            "complete_spatial_transfer_evaluation_required":True,
            "max_stage_p_positive_to_spatial_replaceable_contradiction_rate":0.05,
            "max_spatial_structural_refusal_violation_rate":0.0,
            "spatial_positive_retention_report_only":True,
        },
    }


def test_scoped_pipeline_gate_excludes_report_only_w6_from_authorization_minimum():
    from sdmr.process_id.known_truth.scoped_pipeline_v6 import (
        evaluate_scoped_prospective_kt,
    )

    stage_p=_stage_rows()
    stage_t=_stage_t_from_p(stage_p)
    decision=evaluate_scoped_prospective_kt(
        stage_p,
        stage_t,
        expected_counts={
            "positive":12,
            "replaceable":2,
            "unresolved":2,
            "unavailable":2,
            "structural_refusal":2,
        },
        gate_vector=_gate_vector(),
        expected_seed_count=2,
        expected_worlds=tuple(stage_p["world"].drop_duplicates()),
        provenance_complete=True,
        informative_control_worlds=(
            "unique_process",
            "redundant_representation",
            "shared_carrier",
            "null_correlated",
            "interaction",
            "geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
    )

    assert decision.passed
    assert decision.gates["KT-E"] is True
    assert decision.metrics["minimum_informative_control_authorization_rate"]==1.0
    assert decision.metrics["report_only_world_authorization_rate"]==0.0
    assert decision.metrics["w7_authorized_count"]==0.0


def test_scoped_pipeline_gate_fails_if_one_informative_control_is_below_threshold():
    from sdmr.process_id.known_truth.scoped_pipeline_v6 import (
        evaluate_scoped_prospective_kt,
    )

    stage_p=_stage_rows()
    stage_p.loc[
        stage_p["world"].eq("geographic_shift")
        & stage_p["seed"].eq(2),
        "full_system_information_adequate",
    ]=False
    stage_t=_stage_t_from_p(stage_p)

    decision=evaluate_scoped_prospective_kt(
        stage_p,
        stage_t,
        expected_counts={
            "positive":12,
            "replaceable":2,
            "unresolved":2,
            "unavailable":2,
            "structural_refusal":2,
        },
        gate_vector=_gate_vector(),
        expected_seed_count=2,
        expected_worlds=tuple(stage_p["world"].drop_duplicates()),
        provenance_complete=True,
        informative_control_worlds=(
            "unique_process",
            "redundant_representation",
            "shared_carrier",
            "null_correlated",
            "interaction",
            "geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
    )

    assert not decision.passed
    assert decision.gates["KT-E"] is False
    assert decision.metrics["minimum_informative_control_authorization_rate"]==0.5


def test_scoped_pipeline_gate_fails_if_w7_authorizes():
    from sdmr.process_id.known_truth.scoped_pipeline_v6 import (
        evaluate_scoped_prospective_kt,
    )

    stage_p=_stage_rows()
    stage_p.loc[
        stage_p["world"].eq("omitted_driver")
        & stage_p["seed"].eq(1),
        "full_system_information_adequate",
    ]=True
    stage_t=_stage_t_from_p(stage_p)

    decision=evaluate_scoped_prospective_kt(
        stage_p,
        stage_t,
        expected_counts={
            "positive":12,
            "replaceable":2,
            "unresolved":2,
            "unavailable":2,
            "structural_refusal":2,
        },
        gate_vector=_gate_vector(),
        expected_seed_count=2,
        expected_worlds=tuple(stage_p["world"].drop_duplicates()),
        provenance_complete=True,
        informative_control_worlds=(
            "unique_process",
            "redundant_representation",
            "shared_carrier",
            "null_correlated",
            "interaction",
            "geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
    )

    assert not decision.passed
    assert decision.gates["KT-E"] is False
    assert decision.metrics["w7_authorized_count"]==1.0


def test_scoped_integration_gate_maps_int_names_without_changing_other_gates():
    from sdmr.process_id.known_truth.scoped_pipeline_v6 import (
        evaluate_scoped_integration_gate,
    )

    stage_p=_stage_rows()
    stage_t=_stage_t_from_p(stage_p)
    int_vector={
        "INT-B":{"minimum_positive_recovery":0.80},
        "INT-C":{"maximum_false_positive_rate":0.01},
        "INT-D":{
            "maximum_overresolution_rate":0.0,
            "maximum_structural_refusal_violation_rate":0.0,
        },
        "INT-E":{
            "maximum_unavailable_sharp_rate":0.0,
            "maximum_unavailable_favorable_rate":0.0,
            "minimum_each_informative_control_authorization_rate":0.95,
            "maximum_w7_authorized_count":0,
        },
        "INT-F":{
            "maximum_stage_p_positive_to_spatial_replaceable_contradiction_rate":0.05,
            "maximum_spatial_structural_refusal_violation_rate":0.0,
        },
    }
    decision=evaluate_scoped_integration_gate(
        stage_p,
        stage_t,
        expected_counts={
            "positive":12,
            "replaceable":2,
            "unresolved":2,
            "unavailable":2,
            "structural_refusal":2,
        },
        gate_vector=int_vector,
        expected_seed_count=2,
        expected_worlds=tuple(stage_p["world"].drop_duplicates()),
        provenance_complete=True,
        informative_control_worlds=(
            "unique_process",
            "redundant_representation",
            "shared_carrier",
            "null_correlated",
            "interaction",
            "geographic_shift",
        ),
        report_only_world="observation_confounded",
        null_world="omitted_driver",
    )
    assert decision.passed
    assert all(decision.gates[f"INT-{x}"] for x in "ABCDEF")
