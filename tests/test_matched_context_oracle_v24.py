import pandas as pd
import pytest

from sdmr.matched_context_oracle_v24 import classify_oracle


def frame(a=.2, b=.2, both=.4, full=.95):
    return pd.DataFrame([dict(source_block=s, complete=True, full=full,
                              drop_a=full-a, drop_b=full-b, drop_both=full-both)
                         for s in range(4)])


@pytest.mark.parametrize("a,b,both,state", [
    (.2, 0, .4, "a_specific"), (0, .2, .4, "b_specific"),
    (.2, .2, .4, "joint_required"), (0, 0, .4, "redundant_predictive_support"),
    (0, 0, 0, "joint_contribution_not_established"),
])
def test_oracle_states(a, b, both, state):
    assert classify_oracle(frame(a,b,both))["state"] == state


def test_full_inadequacy_and_missing_evidence_abstain():
    assert classify_oracle(frame(full=.7))["state"] == "oracle_unavailable"
    assert classify_oracle(frame().iloc[:2])["state"] == "oracle_unavailable"


def test_duplicate_source_rejected():
    data = frame()
    with pytest.raises(ValueError, match="duplicate"):
        classify_oracle(pd.concat([data, data.iloc[:1]]))


def test_uncertain_loss_is_not_small_loss():
    data = frame(a=.2,b=0)
    data.loc[0,"drop_b"] -= .2
    data.loc[1,"drop_b"] += .2
    assert classify_oracle(data)["state"] == "joint_supported_attribution_uncertain"
