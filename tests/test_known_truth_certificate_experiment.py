import pandas as pd

from sdmr.known_truth_certificate_experiment import (
    CANONICAL_ECOLOGY_SELECTOR,
    ROBUST_ECOLOGY_SELECTOR,
    audit_ecological_inference_certificates,
)


def test_certificate_audit_opens_truth_only_after_selector_choices_exist():
    choices = pd.DataFrame(
        [
            {
                "scenario": "gaussian",
                "seed": 1,
                "selector": CANONICAL_ECOLOGY_SELECTOR,
                "candidate": "tw_quadratic",
            },
            {
                "scenario": "gaussian",
                "seed": 1,
                "selector": ROBUST_ECOLOGY_SELECTOR,
                "candidate": "proxy_water_quadratic",
            },
            {
                "scenario": "omitted_driver",
                "seed": 2,
                "selector": CANONICAL_ECOLOGY_SELECTOR,
                "candidate": "tw_quadratic",
            },
            {
                "scenario": "omitted_driver",
                "seed": 2,
                "selector": ROBUST_ECOLOGY_SELECTOR,
                "candidate": "climate_soil_quadratic",
            },
        ]
    )
    result = audit_ecological_inference_certificates(choices)
    gaussian = result.loc[result["scenario"].eq("gaussian")].iloc[0]
    assert gaussian["status"] == "process_consensus_model_uncertainty"
    assert gaussian["stable_process_core"] == ("temperature", "water")
    assert gaussian["stable_core_precision"] == 1.0
    assert gaussian["stable_core_recall"] == 1.0

    omitted = result.loc[result["scenario"].eq("omitted_driver")].iloc[0]
    assert omitted["status"] == "partial_process_consensus"
    assert omitted["stable_process_core"] == ("temperature", "water")
    assert omitted["contested_processes"] == ("soil",)
    assert omitted["stable_core_precision"] == 1.0
    assert omitted["stable_core_recall"] == 2 / 3
    assert omitted["process_union_recall"] == 1.0
