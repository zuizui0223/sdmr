import numpy as np
import pandas as pd

from sdmr.carrier_coalition_audit import audit_carrier_coalitions


def _joint_only_frame():
    rng = np.random.default_rng(7)
    rows = []
    blocks = []
    for block in range(4):
        q1 = rng.normal(size=120)
        q2 = rng.normal(size=120)
        p = q1 * q2 + rng.normal(scale=0.03, size=120)
        noise = rng.normal(size=120)
        rows.extend(
            {"p": float(a), "q1": float(b), "q2": float(c), "noise": float(d)}
            for a, b, c, d in zip(p, q1, q2, noise)
        )
        blocks.extend([block] * 120)
    return pd.DataFrame(rows), np.asarray(blocks)


def test_joint_coalition_can_qualify_when_singletons_do_not():
    frame, blocks = _joint_only_frame()
    closures = {
        "target": ("p",),
        "q1": ("q1",),
        "q2": ("q2",),
        "noise": ("noise",),
    }
    result = audit_carrier_coalitions(
        frame,
        blocks,
        target_process="target",
        process_universe=("target", "q1", "q2", "noise"),
        closures=closures,
        degree=2,
        minimum_complete_rows_per_block=40,
    )
    keyed = result.set_index("coalition_processes")
    assert not bool(keyed.loc["q1", "eligible_coalition"])
    assert not bool(keyed.loc["q2", "eligible_coalition"])
    assert bool(keyed.loc["q1+q2", "eligible_coalition"])
    assert bool(keyed.loc["q1+q2", "minimal_eligible_coalition"])


def test_superset_is_not_minimal_when_smaller_carrier_exists():
    frame, blocks = _joint_only_frame()
    closures = {
        "target": ("p",),
        "q1": ("q1",),
        "q2": ("q2",),
        "noise": ("noise",),
    }
    result = audit_carrier_coalitions(
        frame,
        blocks,
        target_process="target",
        process_universe=("target", "q1", "q2", "noise"),
        closures=closures,
        degree=2,
        minimum_complete_rows_per_block=40,
    )
    keyed = result.set_index("coalition_processes")
    if bool(keyed.loc["q1+q2+noise", "eligible_coalition"]):
        assert not bool(keyed.loc["q1+q2+noise", "minimal_eligible_coalition"])
