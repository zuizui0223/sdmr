import numpy as np
import pandas as pd

from sdmr.carrier_coalition_audit import audit_carrier_coalitions


def _joint_only_frame():
    """Balanced interaction world: neither singleton carries P, but q1+q2 does."""
    rows = []
    blocks = []
    levels = (-2.0, -1.0, 1.0, 2.0)
    # Every block contains an exactly balanced Cartesian design. Therefore
    # E[p | q1] = E[p | q2] = 0 for p=q1*q2, while a degree-2 model using
    # q1 and q2 contains the exact interaction term.
    for block in range(4):
        for repeat in range(8):
            for q1 in levels:
                for q2 in levels:
                    p = q1 * q2
                    noise = float(((repeat + block) % 4) - 1.5)
                    rows.append({"p": p, "q1": q1, "q2": q2, "noise": noise})
                    blocks.append(block)
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
