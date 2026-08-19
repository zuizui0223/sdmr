from sdmr.procedure_ecological_certificate import build_procedure_ecological_certificate


def test_dynamic_procedure_predictors_form_process_consensus():
    certificate = build_procedure_ecological_certificate(
        ("bio5", "bio12"),
        ("gdd5", "bio12"),
        process_groups={
            "bio5": "thermal_regime",
            "gdd5": "thermal_regime",
            "bio12": "water_input",
        },
        canonical_label="canonical_ecology",
        robust_label="robust_ecology",
    )
    assert certificate.status == "process_consensus_model_uncertainty"
    assert certificate.stable_process_core == ("thermal_regime", "water_input")
    assert certificate.contested_processes == ()


def test_observation_terms_are_excluded_from_dynamic_process_claims():
    certificate = build_procedure_ecological_certificate(
        ("bio5", "collector_access"),
        ("gdd5", "collector_access"),
        canonical_observation_predictors=("collector_access",),
        robust_observation_predictors=("collector_access",),
        process_groups={
            "bio5": "thermal_regime",
            "gdd5": "thermal_regime",
            "collector_access": "observation_process",
        },
    )
    assert certificate.stable_process_core == ("thermal_regime",)
    assert "observation_process" not in certificate.process_union


def test_dynamic_missing_robust_selection_abstains():
    certificate = build_procedure_ecological_certificate(
        ("bio5", "bio12"),
        None,
        process_groups={"bio5": "thermal", "bio12": "water"},
        canonical_label="canonical_ecology",
    )
    assert certificate.status == "abstain_missing_selector"
    assert certificate.stable_process_core == ()
