import pandas as pd


def test_apply_permutation_authorization_overrides_all_states_when_gate_fails():
    from sdmr.process_id.known_truth.integration_v5 import (
        apply_permutation_authorization,
    )

    states = pd.DataFrame([
        {"process":"thermal","state":"contributory","reason":"interval_process_challenge"},
        {"process":"water","state":"replaceable","reason":"interval_process_challenge"},
    ])
    out = apply_permutation_authorization(
        states,
        authorized=False,
        observed_mean_score=-0.69,
        mean_gain_over_null=0.003,
        p_value=0.02,
    )
    assert set(out["state"]) == {"unavailable"}
    assert set(out["reason"]) == {"full_system_not_informative"}
    assert out["full_system_information_adequate"].eq(False).all()
    assert out["full_system_permutation_p"].eq(0.02).all()


def test_apply_permutation_authorization_preserves_states_when_gate_passes():
    from sdmr.process_id.known_truth.integration_v5 import (
        apply_permutation_authorization,
    )

    states = pd.DataFrame([
        {"process":"thermal","state":"contributory","reason":"interval_process_challenge"},
        {"process":"water","state":"replaceable","reason":"interval_process_challenge"},
    ])
    out = apply_permutation_authorization(
        states,
        authorized=True,
        observed_mean_score=-0.66,
        mean_gain_over_null=0.03,
        p_value=0.001,
    )
    assert out["state"].tolist() == ["contributory","replaceable"]
    assert out["full_system_information_adequate"].eq(True).all()


def test_integration_gate_reuses_strict_stage_p_stage_t_semantics():
    from sdmr.process_id.known_truth.integration_v5 import (
        evaluate_integration_gate,
    )

    stage_p = pd.DataFrame([
        {"seed":1,"world":"w_pos","process":"thermal","odo_state":"contributory","finite_state":"contributory","structural_refusal_expected":False,"full_system_information_adequate":True},
        {"seed":1,"world":"w_rep","process":"thermal","odo_state":"replaceable","finite_state":"replaceable","structural_refusal_expected":False,"full_system_information_adequate":True},
        {"seed":1,"world":"w_unr","process":"thermal","odo_state":"unresolved","finite_state":"unresolved","structural_refusal_expected":True,"full_system_information_adequate":True},
        {"seed":1,"world":"omitted_driver","process":"thermal","odo_state":"unavailable","finite_state":"unavailable","structural_refusal_expected":False,"full_system_information_adequate":False},
    ])
    stage_t = stage_p.loc[:,["seed","world","process","odo_state","structural_refusal_expected"]].copy()
    stage_t["finite_state"]=["contributory","replaceable","unresolved","replaceable"]

    gate_vector = {
        "INT-B":{"minimum_positive_recovery":0.80},
        "INT-C":{"maximum_false_positive_rate":0.01},
        "INT-D":{"maximum_overresolution_rate":0.0,"maximum_structural_refusal_violation_rate":0.0},
        "INT-E":{"maximum_unavailable_sharp_rate":0.0,"maximum_unavailable_favorable_rate":0.0,"maximum_w7_authorized_count":0,"minimum_non_w7_authorization_rate":0.95},
        "INT-F":{"maximum_stage_p_positive_to_spatial_replaceable_contradiction_rate":0.05,"maximum_spatial_structural_refusal_violation_rate":0.0},
    }

    decision = evaluate_integration_gate(
        stage_p,
        stage_t,
        expected_counts={"positive":1,"replaceable":1,"unresolved":1,"unavailable":1,"structural_refusal":1},
        gate_vector=gate_vector,
        expected_seed_count=1,
        expected_worlds=("w_pos","w_rep","w_unr","omitted_driver"),
        provenance_complete=True,
    )
    assert decision.passed
    assert all(decision.gates.values())


def test_integration_gate_fails_unavailable_sharp_state():
    from sdmr.process_id.known_truth.integration_v5 import (
        evaluate_integration_gate,
    )

    stage_p = pd.DataFrame([
        {"seed":1,"world":"w_pos","process":"thermal","odo_state":"contributory","finite_state":"contributory","structural_refusal_expected":False,"full_system_information_adequate":True},
        {"seed":1,"world":"w_rep","process":"thermal","odo_state":"replaceable","finite_state":"replaceable","structural_refusal_expected":False,"full_system_information_adequate":True},
        {"seed":1,"world":"w_unr","process":"thermal","odo_state":"unresolved","finite_state":"unresolved","structural_refusal_expected":True,"full_system_information_adequate":True},
        {"seed":1,"world":"omitted_driver","process":"thermal","odo_state":"unavailable","finite_state":"replaceable","structural_refusal_expected":False,"full_system_information_adequate":True},
    ])
    stage_t = stage_p.loc[:,["seed","world","process","odo_state","structural_refusal_expected"]].copy()
    stage_t["finite_state"]=["contributory","replaceable","unresolved","replaceable"]

    gate_vector = {
        "INT-B":{"minimum_positive_recovery":0.80},
        "INT-C":{"maximum_false_positive_rate":0.01},
        "INT-D":{"maximum_overresolution_rate":0.0,"maximum_structural_refusal_violation_rate":0.0},
        "INT-E":{"maximum_unavailable_sharp_rate":0.0,"maximum_unavailable_favorable_rate":0.0,"maximum_w7_authorized_count":0,"minimum_non_w7_authorization_rate":0.95},
        "INT-F":{"maximum_stage_p_positive_to_spatial_replaceable_contradiction_rate":0.05,"maximum_spatial_structural_refusal_violation_rate":0.0},
    }

    decision = evaluate_integration_gate(
        stage_p,
        stage_t,
        expected_counts={"positive":1,"replaceable":1,"unresolved":1,"unavailable":1,"structural_refusal":1},
        gate_vector=gate_vector,
        expected_seed_count=1,
        expected_worlds=("w_pos","w_rep","w_unr","omitted_driver"),
        provenance_complete=True,
    )
    assert not decision.passed
    assert decision.gates["INT-E"] is False
