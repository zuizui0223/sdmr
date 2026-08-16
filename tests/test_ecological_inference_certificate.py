from sdmr.ecological_inference_certificate import build_ecological_inference_certificate
from sdmr.known_truth_response import DEFAULT_PROCESS_ALIASES
from sdmr.known_truth_scenarios import standard_known_truth_candidates


def test_same_model_promotes_only_ecological_processes():
    candidates = standard_known_truth_candidates()
    certificate = build_ecological_inference_certificate(
        "niche_plus_observer",
        "niche_plus_observer",
        candidates,
        process_groups=DEFAULT_PROCESS_ALIASES,
    )
    assert certificate.status == "model_consensus"
    assert certificate.model_consensus
    assert certificate.process_set_consensus
    assert certificate.stable_process_core == ("temperature", "water")
    assert "observation_process" not in certificate.stable_process_core
    assert certificate.canonical_observation_predictors == ("recording_bias",)


def test_proxy_and_direct_predictor_can_form_process_consensus():
    candidates = standard_known_truth_candidates()
    certificate = build_ecological_inference_certificate(
        "tw_quadratic",
        "proxy_water_quadratic",
        candidates,
        process_groups=DEFAULT_PROCESS_ALIASES,
    )
    assert certificate.status == "process_consensus_model_uncertainty"
    assert not certificate.model_consensus
    assert certificate.process_set_consensus
    assert certificate.stable_process_core == ("temperature", "water")
    assert certificate.contested_processes == ()


def test_selector_specific_process_is_reported_as_contested_not_averaged():
    candidates = standard_known_truth_candidates()
    certificate = build_ecological_inference_certificate(
        "tw_quadratic",
        "climate_soil_quadratic",
        candidates,
        process_groups=DEFAULT_PROCESS_ALIASES,
    )
    assert certificate.status == "partial_process_consensus"
    assert certificate.stable_process_core == ("temperature", "water")
    assert certificate.canonical_only_processes == ()
    assert certificate.robust_only_processes == ("soil",)
    assert certificate.contested_processes == ("soil",)
    assert certificate.process_union == ("soil", "temperature", "water")


def test_no_shared_ecological_process_is_explicitly_contested():
    candidates = standard_known_truth_candidates()
    certificate = build_ecological_inference_certificate(
        "tw_quadratic",
        "observer_only",
        candidates,
        process_groups=DEFAULT_PROCESS_ALIASES,
    )
    assert certificate.status == "process_contested"
    assert certificate.stable_process_core == ()
    assert certificate.canonical_only_processes == ("temperature", "water")
    assert certificate.robust_only_processes == ()
    assert certificate.contested_processes == ("temperature", "water")


def test_missing_selector_returns_abstention_without_claims():
    certificate = build_ecological_inference_certificate(
        "tw_quadratic",
        None,
        standard_known_truth_candidates(),
        process_groups=DEFAULT_PROCESS_ALIASES,
    )
    assert certificate.status == "abstain_missing_selector"
    assert certificate.stable_process_core == ()
    assert certificate.contested_processes == ()
