from sdmr.cross_taxon_process_evidence import aggregate_cross_taxon_process_evidence
from sdmr.ecological_inference_certificate import build_ecological_inference_certificate
from sdmr.known_truth_response import DEFAULT_PROCESS_ALIASES
from sdmr.known_truth_scenarios import standard_known_truth_candidates


def _certificate(canonical, robust):
    return build_ecological_inference_certificate(
        canonical,
        robust,
        standard_known_truth_candidates(),
        process_groups=DEFAULT_PROCESS_ALIASES,
    )


def test_cross_taxon_evidence_separates_strong_contested_and_absent_support():
    evidence = aggregate_cross_taxon_process_evidence(
        {
            "taxon_a": _certificate("tw_quadratic", "proxy_water_quadratic"),
            "taxon_b": _certificate("tw_quadratic", "climate_soil_quadratic"),
            "taxon_c": _certificate("climate_soil_quadratic", "climate_soil_quadratic"),
        },
        process_universe=("temperature", "water", "soil"),
    )
    long = evidence.taxon_process_evidence
    assert long.loc[
        long["taxon"].eq("taxon_a") & long["process"].eq("temperature"),
        "support_state",
    ].iloc[0] == "stable_core"
    assert long.loc[
        long["taxon"].eq("taxon_b") & long["process"].eq("soil"),
        "support_state",
    ].iloc[0] == "contested"
    assert long.loc[
        long["taxon"].eq("taxon_a") & long["process"].eq("soil"),
        "support_state",
    ].iloc[0] == "not_supported"

    soil = evidence.process_summary.loc[
        evidence.process_summary["process"].eq("soil")
    ].iloc[0]
    assert soil["n_stable_core"] == 1
    assert soil["n_contested"] == 1
    assert soil["n_not_supported"] == 1
    assert soil["strong_support_fraction"] == 1 / 3
    assert soil["any_support_fraction"] == 2 / 3


def test_abstention_is_not_silently_counted_as_negative_evidence():
    evidence = aggregate_cross_taxon_process_evidence(
        {
            "resolved": _certificate("tw_quadratic", "tw_quadratic"),
            "abstained": _certificate("tw_quadratic", None),
        },
        process_universe=("temperature", "water"),
    )
    long = evidence.taxon_process_evidence
    abstained = long.loc[long["taxon"].eq("abstained")]
    assert set(abstained["support_state"]) == {"unresolved_abstention"}

    temperature = evidence.process_summary.loc[
        evidence.process_summary["process"].eq("temperature")
    ].iloc[0]
    assert temperature["n_taxa_total"] == 2
    assert temperature["n_informative_taxa"] == 1
    assert temperature["n_abstained_taxa"] == 1
    assert temperature["strong_support_fraction"] == 1.0


def test_summary_does_not_manufacture_universal_driver_threshold():
    result = aggregate_cross_taxon_process_evidence(
        {"taxon": _certificate("tw_quadratic", "tw_quadratic")},
        process_universe=("temperature", "water", "soil"),
    )
    forbidden = {
        "universal_driver",
        "universal",
        "important",
        "promotion_pass",
        "support_class",
    }
    assert not forbidden.intersection(result.process_summary.columns)
