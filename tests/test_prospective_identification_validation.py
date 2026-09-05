import copy

import numpy as np

from sdmr.prospective_identification_validation import (
    fit_case_nontruth,
    load_execution,
)


def _small_execution():
    execution = copy.deepcopy(load_execution())
    execution["simulation"].update(
        {
            "n_cells": 1200,
            "n_occurrences": 120,
            "n_target_group": 400,
            "outer_n_blocks": 4,
            "answer_check_fraction": 0.25,
            "inner_n_blocks": 4,
            "inner_n_splits": 2,
        }
    )
    execution["process_universe"] = ["temperature", "water"]
    execution["process_registry"] = [
        row
        for row in execution["process_registry"]
        if row["process"] in {"temperature", "water"}
    ]
    execution["ecological_predictors"] = ["temperature", "water", "temp_proxy"]
    return execution


def test_noncontract_seed_family_fit_produces_only_pretruth_artifacts() -> None:
    frames = fit_case_nontruth(
        "gaussian",
        9901,
        replicate=1,
        execution=_small_execution(),
    )
    case = frames["case_summary"]
    process = frames["process_status"]

    assert len(case) == 1
    assert bool(case.iloc[0]["case_available"]) is True
    assert str(case.iloc[0]["selection_receipt"])
    assert np.isfinite(float(case.iloc[0]["learner_presence_rank"]))
    assert np.isfinite(float(case.iloc[0]["canonical_presence_rank"]))
    assert set(process["process"]) == {"temperature", "water"}
    assert set(process["status"]).issubset(
        {"required_by_evidence_contract", "refuted_as_necessary", "unresolved"}
    )

    forbidden = {
        "true_suitability",
        "true_processes",
        "expected_required",
        "driver_process_f1",
        "truth_surface_rank",
    }
    for frame in frames.values():
        assert forbidden.isdisjoint(frame.columns)


def test_contract_denominator_stays_frozen() -> None:
    execution = load_execution()
    assert tuple(execution["seeds"]) == tuple(range(4101, 4121))
    assert int(execution["n_cases"]) == 120
    assert len(execution["learner"]["model_specs"]) == 6
    assert execution["post_outcome_changes_allowed"] is False
    assert execution["threshold_relaxation_allowed"] is False
