import pandas as pd
import pytest

from sdmr.relative_attribution_v22_audit import KEY, validate_denominator


def fixture():
    manifest = pd.DataFrame([dict(family="gaussian", seed=17001, target_block=0,
                                  process_a="temperature", process_b="water")])
    directions = pd.DataFrame([
        ["gaussian", 17001, 0, "temperature", "water"],
        ["gaussian", 17001, 0, "water", "temperature"],
    ], columns=KEY)
    return manifest, directions


def test_exact_mirrors_accept_arbitrary_row_order():
    manifest, directions = fixture()
    validate_denominator(manifest, directions.iloc[::-1])


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra", "wrong_context"])
def test_changed_directional_denominator_fails_closed(mutation):
    manifest, directions = fixture()
    if mutation == "missing":
        directions = directions.iloc[:1]
    elif mutation == "duplicate":
        directions = pd.concat([directions, directions.iloc[:1]])
    elif mutation == "extra":
        extra = directions.iloc[:1].assign(target_process="noise")
        directions = pd.concat([directions, extra])
    else:
        directions.loc[0, "target_block"] = 1
    with pytest.raises(ValueError, match="denominator"):
        validate_denominator(manifest, directions)


def test_duplicate_and_reversed_manifest_pairs_fail_closed():
    manifest, directions = fixture()
    with pytest.raises(ValueError, match="duplicate"):
        validate_denominator(pd.concat([manifest, manifest]), directions)
    reverse = manifest.rename(columns={"process_a": "process_b", "process_b": "process_a"})
    with pytest.raises(ValueError, match="denominator"):
        validate_denominator(pd.concat([manifest, reverse]), directions)
