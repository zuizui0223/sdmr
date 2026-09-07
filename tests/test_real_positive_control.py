import pandas as pd

from sdmr.real_positive_control import (
    aggregate_process_scores,
    evaluate_positive_controls,
    process_scores_from_summary,
)


def _candidate_processes():
    return {
        "temperature_only": ("temperature",),
        "water_only": ("water",),
        "temperature_water": ("temperature", "water"),
        "neutral_only": (),
    }


def test_process_scoring_uses_candidate_evidence_not_external_labels():
    summary = pd.DataFrame(
        [
            {"candidate": "temperature_only", "prediction_adequate": True, "mean_niche_overlap_schoener_d_pc12": 0.80},
            {"candidate": "water_only", "prediction_adequate": True, "mean_niche_overlap_schoener_d_pc12": 0.60},
            {"candidate": "temperature_water", "prediction_adequate": True, "mean_niche_overlap_schoener_d_pc12": 0.75},
            {"candidate": "neutral_only", "prediction_adequate": True, "mean_niche_overlap_schoener_d_pc12": 0.50},
        ]
    )
    scores = process_scores_from_summary(summary, _candidate_processes()).set_index("process")
    # Span=.30. Temperature: .80-.60=.20. Water: .75-.80=-.05.
    assert abs(float(scores.loc["temperature", "score"]) - 2 / 3) < 1e-12
    assert abs(float(scores.loc["water", "score"]) + 1 / 6) < 1e-12


def test_all_three_m_conditions_are_required():
    rows = []
    for m in ("buffer_150km", "buffer_300km"):
        rows.append({"species": "A", "m_spec": m, "process": "temperature", "score": 0.5})
        rows.append({"species": "A", "m_spec": m, "process": "water", "score": -0.2})
    result = aggregate_process_scores(pd.DataFrame(rows), ("buffer_150km", "buffer_300km", "buffer_500km"))
    assert result["m_complete"].eq(False).all()
    assert result["case_score"].isna().all()


def test_positive_control_decision_is_frozen_four_taxa_and_process_balanced():
    taxa = pd.DataFrame(
        [
            {"scientific_name": "W1", "expected_process": "water", "evidence_type": "x", "evidence_doi": "d1"},
            {"scientific_name": "W2", "expected_process": "water", "evidence_type": "x", "evidence_doi": "d2"},
            {"scientific_name": "T1", "expected_process": "temperature", "evidence_type": "x", "evidence_doi": "d3"},
            {"scientific_name": "T2", "expected_process": "temperature", "evidence_type": "x", "evidence_doi": "d4"},
        ]
    )
    rows = []
    values = {
        "W1": {"water": (0.5, 3), "temperature": (-0.1, 0)},
        "W2": {"water": (0.4, 2), "temperature": (0.2, 2)},
        "T1": {"temperature": (0.6, 3), "water": (0.1, 1)},
        "T2": {"temperature": (-0.1, 1), "water": (0.2, 2)},
    }
    for species, per_process in values.items():
        for process, (score, positive_m) in per_process.items():
            rows.append(
                {
                    "species": species,
                    "process": process,
                    "case_score": score,
                    "positive_m_count": positive_m,
                    "m_complete": True,
                    "m_scores": "",
                }
            )
    contract = {
        "positive_control_recovery_rule": {
            "expected_process_positive_m_count_min": 2,
            "primary_overall_recovery_min": 0.75,
            "minimum_recovered_per_process_group": 1,
        }
    }
    results, decision = evaluate_positive_controls(pd.DataFrame(rows), taxa, contract)
    assert int(results["recovered"].sum()) == 3
    assert decision["supported"] is True
    assert decision["recovered_by_expected_process"] == {"temperature": 1, "water": 2}
