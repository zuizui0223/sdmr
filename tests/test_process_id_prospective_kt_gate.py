import pandas as pd


def _rows():
    stage_p = pd.DataFrame([
        # seed 1
        {"seed":1,"world":"w_pos","process":"thermal","odo_state":"contributory","finite_state":"contributory","structural_refusal_expected":False,"full_system_information_adequate":True},
        {"seed":1,"world":"w_rep","process":"thermal","odo_state":"replaceable","finite_state":"replaceable","structural_refusal_expected":False,"full_system_information_adequate":True},
        {"seed":1,"world":"w_unr","process":"thermal","odo_state":"unresolved","finite_state":"unresolved","structural_refusal_expected":True,"full_system_information_adequate":True},
        {"seed":1,"world":"omitted_driver","process":"thermal","odo_state":"unavailable","finite_state":"unavailable","structural_refusal_expected":False,"full_system_information_adequate":False},
    ])
    stage_t = stage_p.loc[:,["seed","world","process","odo_state","structural_refusal_expected"]].copy()
    stage_t["finite_state"] = ["contributory","replaceable","unresolved","replaceable"]
    return stage_p, stage_t


def _gates():
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
            "min_non_w7_full_system_information_adequacy":0.95,
            "max_w7_full_system_information_adequacy":0.0,
        },
        "KT-F":{
            "complete_spatial_transfer_evaluation_required":True,
            "max_stage_p_positive_to_spatial_replaceable_contradiction_rate":0.05,
            "max_spatial_structural_refusal_violation_rate":0.0,
        },
    }


def test_prospective_gate_all_passes_by_strict_conjunction():
    from sdmr.process_id.known_truth.prospective_kt import evaluate_prospective_kt

    stage_p, stage_t = _rows()
    decision = evaluate_prospective_kt(
        stage_p,
        stage_t,
        expected_counts={"positive":1,"replaceable":1,"unresolved":1,"unavailable":1,"structural_refusal":1},
        gate_vector=_gates(),
        expected_seed_count=1,
        expected_worlds=("w_pos","w_rep","w_unr","omitted_driver"),
        provenance_complete=True,
    )
    assert decision.passed
    assert all(decision.gates.values())
    assert decision.metrics["positive_recovery"] == 1.0
    assert decision.metrics["false_positive_rate"] == 0.0
    assert decision.metrics["unavailable_sharp_rate"] == 0.0


def test_prospective_gate_fails_if_unavailable_is_sharpened():
    from sdmr.process_id.known_truth.prospective_kt import evaluate_prospective_kt

    stage_p, stage_t = _rows()
    stage_p.loc[stage_p["odo_state"].eq("unavailable"),"finite_state"] = "replaceable"
    decision = evaluate_prospective_kt(
        stage_p,
        stage_t,
        expected_counts={"positive":1,"replaceable":1,"unresolved":1,"unavailable":1,"structural_refusal":1},
        gate_vector=_gates(),
        expected_seed_count=1,
        expected_worlds=("w_pos","w_rep","w_unr","omitted_driver"),
        provenance_complete=True,
    )
    assert not decision.passed
    assert decision.gates["KT-E"] is False


def test_prospective_gate_fails_on_spatial_contradiction():
    from sdmr.process_id.known_truth.prospective_kt import evaluate_prospective_kt

    stage_p, stage_t = _rows()
    stage_t.loc[stage_t["world"].eq("w_pos"),"finite_state"] = "replaceable"
    decision = evaluate_prospective_kt(
        stage_p,
        stage_t,
        expected_counts={"positive":1,"replaceable":1,"unresolved":1,"unavailable":1,"structural_refusal":1},
        gate_vector=_gates(),
        expected_seed_count=1,
        expected_worlds=("w_pos","w_rep","w_unr","omitted_driver"),
        provenance_complete=True,
    )
    assert not decision.passed
    assert decision.gates["KT-F"] is False


def test_prospective_gate_fails_closed_on_denominator_mismatch():
    import pytest
    from sdmr.process_id.known_truth.prospective_kt import evaluate_prospective_kt

    stage_p, stage_t = _rows()
    with pytest.raises(ValueError, match="expected ODO denominator"):
        evaluate_prospective_kt(
            stage_p,
            stage_t,
            expected_counts={"positive":2,"replaceable":1,"unresolved":1,"unavailable":0,"structural_refusal":1},
            gate_vector=_gates(),
            expected_seed_count=1,
            expected_worlds=("w_pos","w_rep","w_unr","omitted_driver"),
            provenance_complete=True,
        )
