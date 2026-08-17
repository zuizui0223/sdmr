import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_3_ecological_certificate_experiment import (
    DECISION_STATES,
    PRODUCTS,
    identified_set_decision,
    load_certificate_panels,
)


CONFIG = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "product_a_v2_3_ecological_certificate_panels.json"
)


def _summary(
    *,
    pareto_possible=2.0,
    complete_possible=3.0,
    pareto_width=0.20,
    complete_width=0.35,
    pareto_recall=1.0,
    complete_recall=1.0,
    pareto_boundary=1.0,
    complete_boundary=1.0,
    false_core=0,
    pareto_complete=3,
):
    rows = []
    for index in (1, 2, 3):
        panel = f"panel_C{index}"
        rows.extend(
            [
                {
                    "panel": panel,
                    "product": "canonical_auc_point",
                    "n_validation_taxa": 3,
                    "n_complete_certificates": 3,
                    "total_false_necessary_processes": 0,
                    "mean_possible_process_recall": 1.0,
                    "mean_boundary_coverage": 0.0,
                    "mean_possible_processes": 1.0,
                    "mean_interval_width": 0.0,
                },
                {
                    "panel": panel,
                    "product": "complete_adequate_certificate",
                    "n_validation_taxa": 3,
                    "n_complete_certificates": 3,
                    "total_false_necessary_processes": 0,
                    "mean_possible_process_recall": complete_recall,
                    "mean_boundary_coverage": complete_boundary,
                    "mean_possible_processes": complete_possible,
                    "mean_interval_width": complete_width,
                },
                {
                    "panel": panel,
                    "product": "ecological_pareto_certificate",
                    "n_validation_taxa": 3,
                    "n_complete_certificates": pareto_complete,
                    "total_false_necessary_processes": false_core,
                    "mean_possible_process_recall": pareto_recall,
                    "mean_boundary_coverage": pareto_boundary,
                    "mean_possible_processes": pareto_possible,
                    "mean_interval_width": pareto_width,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_predeclared_certificate_panels_exclude_opened_seeds():
    payload, panels = load_certificate_panels(CONFIG)
    seeds = [
        spec.seed
        for panel in panels
        for spec in (*panel.discovery, *panel.validation)
    ]

    assert tuple(payload["products"]) == PRODUCTS
    assert len(panels) == 3
    assert len(seeds) == len(set(seeds)) == 18
    assert min(seeds) > 223
    assert set(payload["decision_states"]) == set(DECISION_STATES)
    assert payload["process_set_semantics"]["support_frequency_threshold"] is None


def test_opened_seed_is_rejected(tmp_path):
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    payload["panels"][0]["discovery"][0]["seed"] = 223
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="previously opened"):
        load_certificate_panels(path)


def test_identified_set_supported_requires_coverage_and_sharpness():
    decision = identified_set_decision(_summary())
    row = decision.iloc[0]

    assert row["decision"] == "identified_set_supported"
    assert not bool(row["scientific_promotion_allowed"])
    assert bool(row["full_truth_coverage"])
    assert int(row["n_panels_with_strict_sharpness_gain"]) == 3


def test_identified_set_trivial_when_not_sharper():
    decision = identified_set_decision(
        _summary(
            pareto_possible=3.0,
            complete_possible=3.0,
            pareto_width=0.35,
            complete_width=0.35,
        )
    )
    assert decision.iloc[0]["decision"] == "identified_set_trivial"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pareto_recall": 0.8},
        {"pareto_boundary": 0.8},
        {"false_core": 1},
        {"pareto_possible": 4.0, "complete_possible": 3.0},
        {"pareto_width": 0.50, "complete_width": 0.35},
        {"pareto_recall": 0.9, "complete_recall": 1.0},
        {"pareto_boundary": 0.9, "complete_boundary": 1.0},
    ],
)
def test_identified_set_not_supported_when_coverage_or_sharpness_fails(kwargs):
    decision = identified_set_decision(_summary(**kwargs))
    assert decision.iloc[0]["decision"] == "identified_set_not_supported"


def test_identified_set_unavailable_when_any_panel_lacks_complete_certificate():
    decision = identified_set_decision(_summary(pareto_complete=2))
    assert decision.iloc[0]["decision"] == "identified_set_unavailable"
