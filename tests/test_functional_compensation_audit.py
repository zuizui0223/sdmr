import pandas as pd

from sdmr.functional_compensation_audit import (
    classify_functional_compensation,
    enumerate_process_coalitions,
)


def test_enumerates_all_nonempty_other_process_coalitions():
    got = enumerate_process_coalitions(("p", "q1", "q2", "q3"), "p")
    assert got == (
        ("q1",), ("q2",), ("q3",),
        ("q1", "q2"), ("q1", "q3"), ("q2", "q3"),
        ("q1", "q2", "q3"),
    )


def _evidence(rank_losses, density_losses, coalition_ranks=None):
    coalition_ranks = coalition_ranks or [0.70] * len(rank_losses)
    rows = []
    for fold, (rank, density, coalition_rank) in enumerate(zip(rank_losses, density_losses, coalition_ranks)):
        for model in ("m1", "m2"):
            rows.append({
                "fold": fold,
                "complete": True,
                "coalition_presence_rank": coalition_rank,
                "conditional_rank_loss": rank,
                "conditional_density_loss": density,
            })
    return pd.DataFrame(rows)


def test_classifies_revealed_functional_compensation():
    result = classify_functional_compensation(
        _evidence([0.08, 0.07, 0.09, 0.08], [0.05, 0.04, 0.06, 0.05]),
        expected_model_specs=2,
        chance_score=0.50,
        minimum_margin=0.05,
        rank_margin=0.02,
        density_margin=0.01,
        sem_multiplier=1.0,
    )
    assert result["state"] == "functional_compensator"
    assert result["coalition_route_adequate"] is True


def test_does_not_promote_small_conditional_loss():
    result = classify_functional_compensation(
        _evidence([0.01, 0.015, 0.012, 0.014], [0.003, 0.004, 0.002, 0.004]),
        expected_model_specs=2,
    )
    assert result["state"] == "no_revealed_compensation"


def test_fails_closed_when_conditioning_route_inadequate():
    result = classify_functional_compensation(
        _evidence([0.20, 0.20], [0.20, 0.20], coalition_ranks=[0.51, 0.52]),
        expected_model_specs=2,
        chance_score=0.50,
        minimum_margin=0.05,
    )
    assert result["state"] == "incomplete"
    assert result["coalition_route_adequate"] is False
