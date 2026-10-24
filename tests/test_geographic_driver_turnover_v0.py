"""Standalone geographic-driver-turnover contract tests (outside frozen Product A)."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PATH = Path(__file__).resolve().parents[1] / "experiments" / "geographic_driver_turnover_v0.py"
SPEC = importlib.util.spec_from_file_location("geographic_driver_turnover_v0", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def cells(seed=9, differing=False):
    rng = np.random.default_rng(seed)
    rows = []
    for r in ("alpine", "arid"):
        for b in range(6):
            for c in range(20):
                t, w = rng.normal(size=2)
                # Completely held-out regional environment; same q/C for null.
                if r == "alpine":
                    t -= 0.8
                    w += 0.4
                else:
                    t += 0.8
                    w -= 0.4
                effort = np.exp(rng.normal(scale=0.4) + 0.2 * t)
                if differing:
                    score = (1.6 * t if r == "alpine" else 1.6 * w)
                else:
                    score = 0.65 * t - 0.15 * w - 0.4 * t * t - 0.2 * w * w
                rows.append(("synthetic_species", r, f"{r}_{b}_{c}", str(b), t, w, effort, score))
    df = pd.DataFrame(rows, columns=["taxon", "region", "cell_id", "spatial_block", "temperature", "moisture", "effort", "score"])
    df["n_occ"] = 0
    for r, part in df.groupby("region"):
        logits = np.log(part.effort.to_numpy()) + part.score.to_numpy()
        p = np.exp(logits - np.max(logits)); p /= p.sum()
        df.loc[part.index, "n_occ"] = rng.multinomial(420, p)
    return df.drop(columns="score")


def test_schema_duplicate_effort_and_missing():
    frame = cells()
    with pytest.raises(ValueError, match="duplicate|once"):
        mod._check_frame(pd.concat([frame, frame.iloc[:1]]))
    with pytest.raises(ValueError, match="effort"):
        mod._check_frame(frame.assign(effort=0))
    with pytest.raises(ValueError, match="missing required"):
        mod._check_frame(frame.drop(columns="spatial_block"))


def test_shared_interaction_removed_from_both_knockouts():
    assert 4 in mod.FEATURE_SETS["full"]
    assert 4 not in mod.FEATURE_SETS["without_temperature"]
    assert 4 not in mod.FEATURE_SETS["without_moisture"]


def test_null_result_reproducible_under_reordered_rows():
    frame = cells()
    a = mod.analyze_taxon(frame, replicates=11, seed=51, min_test_records=5)
    b = mod.analyze_taxon(frame.sample(frac=1, random_state=99), replicates=11, seed=51, min_test_records=5)
    assert a == b
    assert 0 < a["one_sided_bootstrap_p"] <= 1
    assert a["mode"].startswith("exploratory")


def test_taxon_denominator_excludes_ineligible_without_claiming_zero_effect():
    ok = cells()
    invalid = ok.copy().assign(taxon="bad_species", spatial_block="one_block")
    out = mod.analyze_table(pd.concat([ok, invalid]), replicates=2, seed=1)
    assert out["n_eligible_taxa"] == 1
    assert out["n_excluded_taxa"] == 1
    assert "spatial blocks" in out["exclusions"][0]["reason"]


def test_region_dependent_generator_is_not_a_false_invariant_claim():
    df = cells(differing=True)
    out = mod.analyze_taxon(df, replicates=11, seed=31, min_test_records=5)
    assert out["n_regions"] == 2
    assert np.isfinite(out["observed"]["spread_nats_per_record"])
    assert out["observed"]["spread_nats_per_record"] >= 0
    # The test is a finite-replicate diagnostic, not a claim of calibrated power.


def test_environment_overlap_ignores_observation_effort_and_counts():
    frame = mod._check_frame(cells())
    a = mod._availability_overlap(frame)
    b = mod._availability_overlap(frame.assign(effort=frame.effort * 200, n_occ=0))
    assert a == b
    assert all(0 <= v <= 1 for v in a.values())
