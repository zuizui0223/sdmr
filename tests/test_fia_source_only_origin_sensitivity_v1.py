"""Post-source joint climate-bin origin sensitivity cannot promote biological models."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import fia_joint_support_gate_v1 as gate
import fia_source_only_origin_sensitivity_v1 as sens


def config():
    return json.loads((ROOT / "configs/fia_joint_climate_support_gate_v1.json").read_text())


def source_rows(va_year=2010):
    items = []
    for state, prefix in gate.STATES.items():
        for i in range(6):
            for j in range(5):
                k = i % 2
                items.append({
                    "species_code": "68", "state": state,
                    "county_fips": prefix + f"{i + 1:03d}",
                    "plot_chain_id": f"{state}-{i}-{j}",
                    "interval_id": "window-1",
                    "interval_end_year": va_year if state == "VA" else 2010,
                    "temperature_anomaly_c": 0.2 + 2 * k,
                    "precipitation_anomaly_mm": 10.2 + 200 * k,
                })
    return items


def test_baseline_matches_canonical_and_distinct_site_denominator():
    conf = config()
    conf["species_codes"] = ["68"]
    rows = source_rows()
    canonical = gate.evaluate_source_only(rows, conf)["species"][0]
    shifted = sens.evaluate_offset(rows, conf, 0.0, 0.0, 1990)["per_species"][0]
    assert canonical["n_shared_time_aligned_joint_bins"] == shifted["n_shared_time_aligned_joint_bins"] == 2
    assert shifted["source_eligible"] == (canonical["status"] == "descriptive_source_support_eligible")
    assert shifted["source_eligible"] is True


def test_period_origin_changes_only_time_support_not_climate_source():
    conf = config()
    conf["species_codes"] = ["68"]
    rows = source_rows(va_year=2012)
    first = sens.evaluate_offset(rows, conf, 0.0, 0.0, 1990)
    second = sens.evaluate_offset(rows, conf, 0.0, 0.0, 1992)
    assert first["source_eligible_species_count"] == 1
    assert second["source_eligible_species_count"] == 0
    assert second["per_species"][0]["n_shared_time_aligned_joint_bins"] == 0


def test_marginal_bin_origin_may_change_support_but_not_denominator():
    conf = config()
    conf["species_codes"] = ["68"]
    rows = source_rows()
    aligned = sens.evaluate_offset(rows, conf, 0.0, 0.0, 1990)
    shifted = sens.evaluate_offset(rows, conf, 0.5, 50.0, 1990)
    assert aligned["source_eligible_species_count"] == shifted["source_eligible_species_count"] == 1
    assert len(aligned["per_species"]) == len(shifted["per_species"]) == 1


def test_reconciliation_artifact_mismatch_must_fail_closed(tmp_path):
    conf = config()
    d = tmp_path / "source"
    d.mkdir()
    (d / "fia_new_cohort_joint_source_only_county_stable_v2.csv").write_text("modified")
    (d / "derived_receipt.json").write_text("{}")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(conf))
    with pytest.raises(ValueError, match="source-only identity mismatch"):
        sens.run(d, config_path)


def test_sensitivity_does_not_change_source_only_gate_contract():
    assert sens.SOURCE_RUN == 43696751589
    assert sens.RECONCILIATION_RUN == 43711159676
    assert sens.SOURCE_ARTIFACT == 14160283759
    assert len(sens.DERIVED_CSV_SHA) == len(sens.DERIVED_RECEIPT_SHA) == 64
