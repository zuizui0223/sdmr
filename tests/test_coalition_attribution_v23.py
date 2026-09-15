import numpy as np
import pandas as pd
import pytest

from sdmr.coalition_attribution_v23 import ROUTES, SCORE_COLUMNS, classify_pair


def scores(a=0.06, b=0.06, both=0.12, full=0.7):
    rows = []
    for source in range(4):
        for label in ("linear", "quadratic"):
            row = dict(source_block=source, model_label=label, complete=True)
            for route, loss in zip(ROUTES, (0, a, b, both)):
                row[f"{route}_prediction_rank"] = full - loss
                row[f"{route}_ecological_rank"] = full - loss
                row[f"{route}_ecological_density"] = -0.3 - loss
            rows.append(row)
    return pd.DataFrame(rows)


def classify(frame):
    return classify_pair(frame, model_labels=("linear", "quadratic"))


@pytest.mark.parametrize("a,b,both,expected", [
    (0.06, 0, 0.12, "a_specific"),
    (0, 0.06, 0.12, "b_specific"),
    (0.06, 0.06, 0.12, "joint_required"),
    (0, 0, 0.12, "redundant_predictive_support"),
    (0, 0, 0, "joint_contribution_not_established"),
    (0.06, 0.015, 0.12, "joint_supported_attribution_uncertain"),
])
def test_states(a, b, both, expected):
    assert classify(scores(a, b, both))["state"] == expected


def test_inadequate_knockouts_can_support_joint_loss_but_inadequate_full_cannot():
    assert classify(scores(a=0.3, b=0.3, both=0.4))["state"] == "joint_required"
    assert classify(scores(full=0.49))["state"] == "full_inadequate"


def test_swap_symmetry():
    evidence = scores(a=0.06, b=0)
    swapped = evidence.rename(columns={
        c: c.replace("drop_a_", "drop_b_") if c.startswith("drop_a_") else c.replace("drop_b_", "drop_a_")
        for c in SCORE_COLUMNS if c.startswith(("drop_a_", "drop_b_"))
    })
    assert classify(evidence)["state"] == "a_specific"
    assert classify(swapped)["state"] == "b_specific"


def test_uncertainty_does_not_become_small_effect():
    evidence = scores(a=0.06, b=0)
    for score in ("ecological_rank", "ecological_density"):
        evidence.loc[evidence.source_block == 0, f"drop_b_{score}"] -= 0.2
        evidence.loc[evidence.source_block == 1, f"drop_b_{score}"] += 0.2
    assert classify(evidence)["state"] == "joint_supported_attribution_uncertain"


def test_source_omissions_are_uncertainty_units_not_model_specs():
    evidence = scores()
    for source in range(4):
        evidence.loc[evidence.source_block == source, "drop_a_ecological_rank"] -= 0.01 * source
    result = classify(evidence)
    assert result["drop_a"]["rank_loss"]["sem"] == pytest.approx(np.std([.06, .07, .08, .09], ddof=1) / 2)


def test_missing_or_incomplete_model_excludes_entire_source():
    evidence = scores()
    evidence.loc[(evidence.source_block < 2) & (evidence.model_label == "linear"), "complete"] = False
    assert classify(evidence)["state"] == "insufficient_evidence"


@pytest.mark.parametrize("mutation", ["duplicate", "unknown", "nonfinite", "string_boolean"])
def test_corrupt_evidence_is_rejected(mutation):
    evidence = scores()
    if mutation == "duplicate":
        evidence = pd.concat([evidence, evidence.iloc[:1]])
    elif mutation == "unknown":
        evidence.loc[0, "model_label"] = "unfrozen"
    elif mutation == "nonfinite":
        evidence.loc[0, "full_ecological_rank"] = np.nan
    else:
        evidence["complete"] = "False"
    with pytest.raises(ValueError):
        classify(evidence)


def test_generating_truth_columns_cannot_change_state():
    frame = scores()
    baseline = classify(frame)
    assert classify(frame.assign(generating_process_true=False, process_name="noise")) == baseline
