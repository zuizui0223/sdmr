import numpy as np
import pandas as pd

from sdmr.v2_5_calibration_aggregate import calibrate_complete_calibration_taxa


def _row(species, status, lower, upper, span=10.0):
    return {
        "species": species,
        "predictor": "soil",
        "quantity": "optimum",
        "interval_status": status,
        "lower_bound": lower,
        "upper_bound": upper,
        "environment_span": span,
    }


def test_v25_uses_only_complete_taxa_but_requires_frozen_minimum():
    envelopes = pd.DataFrame(
        [
            _row("taxon_a", "complete", 2.0, 6.0),
            _row("taxon_b", "complete", 3.0, 7.0),
            _row("taxon_c", "unavailable_incomplete_refits", np.nan, np.nan),
        ]
    )
    truth = pd.DataFrame(
        [
            {"species": "taxon_a", "predictor": "soil", "quantity": "optimum", "estimate": 1.0},
            {"species": "taxon_b", "predictor": "soil", "quantity": "optimum", "estimate": 8.0},
            {"species": "taxon_c", "predictor": "soil", "quantity": "optimum", "estimate": 5.0},
        ]
    )

    calibration, audit = calibrate_complete_calibration_taxa(
        envelopes,
        truth,
        minimum_complete_taxa=2,
    )

    row = calibration.iloc[0]
    assert row["calibration_status"] == "complete"
    assert int(row["n_discovery_keys"]) == 3
    assert int(row["n_evaluable_discovery_keys"]) == 2
    assert int(row["minimum_complete_calibration_taxa"]) == 2
    assert np.isclose(float(row["normalized_expansion_radius"]), 0.1)
    assert int(audit["complete_calibration_taxon"].sum()) == 2


def test_v25_fails_closed_below_frozen_minimum_support():
    envelopes = pd.DataFrame(
        [
            _row("taxon_a", "complete", 2.0, 6.0),
            _row("taxon_b", "unavailable_incomplete_refits", np.nan, np.nan),
        ]
    )
    truth = pd.DataFrame(
        [
            {"species": "taxon_a", "predictor": "soil", "quantity": "optimum", "estimate": 1.0},
            {"species": "taxon_b", "predictor": "soil", "quantity": "optimum", "estimate": 5.0},
        ]
    )

    calibration, _ = calibrate_complete_calibration_taxa(
        envelopes,
        truth,
        minimum_complete_taxa=2,
    )

    row = calibration.iloc[0]
    assert row["calibration_status"] == "unavailable_insufficient_complete_calibration_taxa"
    assert int(row["n_evaluable_discovery_keys"]) == 1
    assert np.isnan(float(row["normalized_expansion_radius"]))
