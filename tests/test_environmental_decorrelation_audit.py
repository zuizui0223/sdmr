import numpy as np
import pandas as pd

from sdmr.environmental_decorrelation_audit import audit_environmental_decorrelation


def _frame(break_block: bool) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(42)
    rows = []
    blocks = []
    for block in range(4):
        q = rng.normal(size=80)
        if break_block and block == 3:
            p = rng.normal(size=80)
        else:
            p = 1.8 * q + rng.normal(scale=0.08, size=80)
        rows.extend({"p": float(a), "q": float(b), "other": float(c)} for a, b, c in zip(p, q, rng.normal(size=80)))
        blocks.extend([block] * 80)
    return pd.DataFrame(rows), np.asarray(blocks)


def test_decorrelation_audit_flags_only_broken_environment():
    frame, blocks = _frame(True)
    result = audit_environmental_decorrelation(
        frame,
        blocks,
        target_process="temperature",
        competitor_process="water",
        target_predictors=("p",),
        competitor_predictors=("q",),
        degree=1,
        material_r2_drop=0.10,
        sem_multiplier=1.0,
        minimum_complete_rows_per_block=20,
    )
    assert result.separating_blocks == (3,)
    row = result.block_table.set_index("block").loc[3]
    assert bool(row["separating_candidate"])
    assert float(row["r2_drop"]) > 0.10


def test_decorrelation_audit_has_no_separator_when_relation_transports():
    frame, blocks = _frame(False)
    result = audit_environmental_decorrelation(
        frame,
        blocks,
        target_process="temperature",
        competitor_process="water",
        target_predictors=("p",),
        competitor_predictors=("q",),
        degree=1,
        material_r2_drop=0.10,
        sem_multiplier=1.0,
        minimum_complete_rows_per_block=20,
    )
    assert result.separating_blocks == ()


def test_decorrelation_audit_rejects_structural_overlap():
    frame, blocks = _frame(True)
    try:
        audit_environmental_decorrelation(
            frame,
            blocks,
            target_process="p",
            competitor_process="q",
            target_predictors=("p",),
            competitor_predictors=("p",),
        )
    except ValueError as exc:
        assert "structurally disjoint" in str(exc)
    else:
        raise AssertionError("expected structural-overlap failure")
