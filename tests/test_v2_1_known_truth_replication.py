import pandas as pd

from sdmr.v2_1_known_truth_replication import (
    PANELS,
    _replication_decision,
    _selector_disagreement,
)


def test_replication_panels_are_predeclared_unique_and_role_separated():
    discovery = [spec for panel in PANELS for spec in panel.discovery]
    validation = [spec for panel in PANELS for spec in panel.validation]
    assert len(PANELS) == 3
    assert len(discovery) == 9
    assert len(validation) == 9
    assert all(spec.role == "discovery" for spec in discovery)
    assert all(spec.role == "validation" for spec in validation)
    assert len({spec.taxon for spec in (*discovery, *validation)}) == 18
    assert not {spec.seed for spec in discovery}.intersection(
        {spec.seed for spec in validation}
    )


def _selector_rows(auc="a", ecology="a", robust=None):
    rows = []
    for panel in ("panel_1", "panel_2", "panel_3"):
        for selector, candidate in (
            ("canonical_auc", auc),
            ("canonical_ecology", ecology),
            ("robust_ecology", robust),
        ):
            rows.append(
                {
                    "panel": panel,
                    "selector": selector,
                    "candidate": candidate,
                    "status": "selected" if candidate else "abstain",
                    "n_evidence_eligible_candidates": 4,
                    "selection_error": None,
                }
            )
    return pd.DataFrame(rows)


def test_selector_disagreement_identifies_indistinguishable_panels():
    disagreement = _selector_disagreement(_selector_rows())
    assert disagreement["canonical_pair_selected"].all()
    assert not disagreement["canonical_selectors_disagree"].any()
    assert not disagreement["robust_selector_selected"].any()


def test_replication_decision_routes_indistinguishable_selector_to_new_design_line():
    disagreement = _selector_disagreement(_selector_rows())
    summary = pd.DataFrame(
        [
            {
                "panel": panel,
                "selector": selector,
                "n_truth_evaluable": 3,
                "mean_truth_worst_rank": 1.0,
                "mean_truth_mean_rank": 1.0,
            }
            for panel in ("panel_1", "panel_2", "panel_3")
            for selector in ("canonical_auc", "canonical_ecology")
        ]
    )
    decision = _replication_decision(disagreement, summary)
    assert decision.loc[0, "decision"] == "selector_indistinguishable"
    assert not bool(decision.loc[0, "scientific_promotion_allowed"])
    assert "surface-stability" in decision.loc[0, "next_action"]


def test_replication_decision_supports_consistent_ecological_differentiation():
    selectors = _selector_rows(auc="auc", ecology="eco", robust="robust")
    disagreement = _selector_disagreement(selectors)
    rows = []
    for panel in ("panel_1", "panel_2", "panel_3"):
        rows.extend(
            [
                {
                    "panel": panel,
                    "selector": "canonical_auc",
                    "n_truth_evaluable": 3,
                    "mean_truth_worst_rank": 2.0,
                    "mean_truth_mean_rank": 2.0,
                },
                {
                    "panel": panel,
                    "selector": "canonical_ecology",
                    "n_truth_evaluable": 3,
                    "mean_truth_worst_rank": 1.0,
                    "mean_truth_mean_rank": 1.0,
                },
            ]
        )
    decision = _replication_decision(disagreement, pd.DataFrame(rows))
    assert decision.loc[0, "decision"] == "differentiated_supported"
    assert decision.loc[0, "n_panels_with_robust_selector_selected"] == 3
