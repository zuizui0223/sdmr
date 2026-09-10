import numpy as np
import pandas as pd

from sdmr.conditional_shrinkage_null import deterministic_joint_permutation


def test_joint_permutation_preserves_exact_multivariate_rows_and_changes_alignment():
    frame = pd.DataFrame({
        "p1": np.arange(20, dtype=float),
        "p2": np.arange(20, dtype=float) + 100.0,
        "q": np.arange(20, dtype=float),
    })
    out = deterministic_joint_permutation(frame, ("p1", "p2"), salt="fixed")
    before = sorted(map(tuple, frame[["p1", "p2"]].to_numpy()))
    after = sorted(map(tuple, out[["p1", "p2"]].to_numpy()))
    assert before == after
    assert not np.array_equal(frame[["p1", "p2"]].to_numpy(), out[["p1", "p2"]].to_numpy())
    assert np.array_equal(frame["q"].to_numpy(), out["q"].to_numpy())


def test_joint_permutation_is_deterministic_by_salt():
    frame = pd.DataFrame({"p": np.arange(30, dtype=float), "q": np.arange(30, dtype=float)})
    a = deterministic_joint_permutation(frame, ("p",), salt="one")
    b = deterministic_joint_permutation(frame, ("p",), salt="one")
    c = deterministic_joint_permutation(frame, ("p",), salt="two")
    assert np.array_equal(a["p"].to_numpy(), b["p"].to_numpy())
    assert not np.array_equal(a["p"].to_numpy(), c["p"].to_numpy())
