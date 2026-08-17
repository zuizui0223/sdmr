import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_2_surface_stability_experiment import (
    DECISION_STATES,
    SELECTORS,
    load_predeclared_panels,
    surface_stability_decision,
)


CONFIG = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "product_a_v2_2_surface_stability_panels.json"
)


def _disagreement(*, differs=True, stable_selected=True):
    return pd.DataFrame(
        [
            {
                "panel": f"panel_S{index}",
                "canonical_auc_selected": True,
                "stable_ecology_selected": stable_selected,
                "stable_differs_from_auc": differs,
            }
            for index in (1, 2, 3)
        ]
    )


def _summary(*, stable_worst=1.0, stable_mean=1.2, auc_worst=2.0, auc_mean=2.2):
    rows = []
    for index in (1, 2, 3):
        panel = f"panel_S{index}"
        rows.extend(
            [
                {
                    "panel": panel,
                    "selector": "canonical_auc",
                    "n_validation_taxa": 3,
                    "n_truth_evaluable": 3,
                    "mean_truth_worst_rank": auc_worst,
                    "mean_truth_mean_rank": auc_mean,
                },
                {
                    "panel": panel,
                    "selector": "stable_ecology",
                    "n_validation_taxa": 3,
                    "n_truth_evaluable": 3,
                    "mean_truth_worst_rank": stable_worst,
                    "mean_truth_mean_rank": stable_mean,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_predeclared_panels_exclude_all_opened_seeds():
    payload, panels = load_predeclared_panels(CONFIG)
    seeds = [
        spec.seed
        for panel in panels
        for spec in (*panel.discovery, *panel.validation)
    ]

    assert tuple(payload["selectors"]) == SELECTORS
    assert len(panels) == 3
    assert len(seeds) == len(set(seeds)) == 18
    assert min(seeds) > 123
    assert set(payload["decision_states"]) == set(DECISION_STATES)


def test_opened_seed_is_rejected(tmp_path):
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    payload["panels"][0]["discovery"][0]["seed"] = 123
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="already opened"):
        load_predeclared_panels(path)


def test_supported_decision_requires_all_evaluable_disagreements_not_worse():
    decision = surface_stability_decision(_disagreement(), _summary())
    row = decision.iloc[0]

    assert row["decision"] == "surface_stability_supported"
    assert not bool(row["scientific_promotion_allowed"])
    assert int(row["n_disagreement_panels_stable_not_worse"]) == 3


def test_indistinguishable_decision_is_negative_evidence():
    decision = surface_stability_decision(
        _disagreement(differs=False),
        _summary(),
    )
    assert decision.iloc[0]["decision"] == "surface_stability_indistinguishable"
    assert bool(decision.iloc[0]["negative_outcome_accepted"])


def test_worse_stable_selector_is_not_supported():
    decision = surface_stability_decision(
        _disagreement(),
        _summary(stable_worst=3.0, stable_mean=3.2),
    )
    assert decision.iloc[0]["decision"] == "surface_stability_not_supported"


def test_selector_abstention_precedes_truth_comparison():
    decision = surface_stability_decision(
        _disagreement(stable_selected=False),
        _summary(),
    )
    assert (
        decision.iloc[0]["decision"]
        == "surface_stability_unstable_or_abstained"
    )
