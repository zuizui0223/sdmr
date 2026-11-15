"""Audit county-stability QC without requerying FIA or opening outcomes."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import fia_joint_source_reconcile_v2 as qc


def config():
    return json.loads((ROOT / "configs/fia_joint_climate_support_gate_v1.json").read_text())


def row(state, county, chain, sp, interval, temp="1.2", precip="55.5", year="2015"):
    return {
        "species_code": sp, "state": state, "county_fips": county,
        "plot_chain_id": chain, "interval_id": interval,
        "interval_end_year": year, "temperature_anomaly_c": temp,
        "precipitation_anomaly_mm": precip,
    }


def test_exclude_whole_unstable_chain_all_species_all_years():
    original = [
        row("VA", "51143", "A", "68", "earlier", year="2002"),
        row("VA", "51083", "A", "68", "later", year="2020"),
        row("VA", "51143", "A", "129", "earlier", year="2002"),
        row("VA", "51083", "A", "129", "later", year="2020"),
        row("VA", "51143", "B", "68", "independent", year="2020"),
        row("RI", "44001", "C", "68", "independent", year="2020"),
    ]
    kept, result = qc.reconcile_rows(original, config())
    assert len(original) == 6
    assert len(kept) == 2
    assert {z["plot_chain_id"] for z in kept} == {"B", "C"}
    assert result["n_original_rows"] == 6
    assert result["n_rejected_rows"] == 4
    assert result["n_county_unstable_plot_chains"] == 1
    assert result["rejected_rows_by_state"] == {"VA": 4}
    assert result["rejected_rows_by_species"] == {"129": 2, "68": 2}
    assert result["exclusion_rule_uses_climate_or_biological_outcomes"] is False
    assert "A" not in "".join(result["county_unstable_chain_hashed_identities"])
    assert result["biological_promotion_authorized"] is False


def test_county_stability_rule_independent_of_temperature_and_year():
    original = [
        row("VA", "51143", "A", "68", "a", temp="-10", precip="-500"),
        row("VA", "51083", "A", "68", "b", temp="50", precip="2000"),
        row("VA", "51143", "B", "68", "c", temp="3", precip="20"),
    ]
    kept, x = qc.reconcile_rows(original, config())
    changed = [{**r, "temperature_anomaly_c": "0", "precipitation_anomaly_mm": "0",
                "interval_end_year": "2015"} for r in original]
    kept2, y = qc.reconcile_rows(changed[::-1], config())
    assert {r["plot_chain_id"] for r in kept} == {"B"}
    assert {r["plot_chain_id"] for r in kept2} == {"B"}
    assert x["county_unstable_chain_hashed_identities"] == y["county_unstable_chain_hashed_identities"]


def test_no_drift_is_noop_preserve_denominator():
    original = [
        row("VA", "51143", "A", "68", "a"),
        row("VA", "51143", "A", "68", "b", year="2020"),
        row("VA", "51083", "B", "129", "c"),
    ]
    kept, report = qc.reconcile_rows(original, config())
    assert kept == original
    assert report["n_rejected_rows"] == 0
    assert report["n_original_rows"] == report["n_kept_rows"] == 3


def test_duplicate_identity_and_outcome_fields_fail_closed():
    first = row("VA", "51143", "A", "68", "a")
    with pytest.raises(ValueError, match="Duplicate"):
        qc.reconcile_rows([first, dict(first)], config())
    with pytest.raises(ValueError, match="unexpected fields"):
        qc.reconcile_rows([{**first, "DIA": "9.3"}], config())
    with pytest.raises(ValueError, match="unexpected fields"):
        qc.reconcile_rows([{**first, "STATUSCD": "1"}], config())


def test_invalid_year_county_or_environment_fail_closed():
    first = row("VA", "51143", "A", "68", "a")
    for changed, reason in [
        ({"county_fips": "44001"}, "Invalid source-only taxon/site"),
        ({"interval_end_year": "2029"}, "Invalid source-only interval year"),
        ({"temperature_anomaly_c": "nan"}, "Nonfinite"),
        ({"precipitation_anomaly_mm": "infinite"}, "Invalid source-only"),
    ]:
        with pytest.raises(ValueError, match=reason):
            qc.reconcile_rows([{**first, **changed}], config())


def test_wrong_original_receipt_cannot_be_reinterpreted(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "fia_new_cohort_joint_source_only.csv").write_text(
        ",".join(sorted(qc.gate.FIELDS)) + "\n", encoding="utf-8")
    (source / "source_receipt.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="first-open source-only file identity mismatch"):
        qc.original_input(source, config())


def test_expected_source_identity_and_provenance_are_fixed():
    assert qc.SOURCE_RUN == 43696751589
    assert qc.SOURCE_ARTIFACT == 14155086669
    assert qc.SOURCE_ROWS == 89630
    assert qc.SOURCE_BY_STATE == {"RI": 1471, "VA": 38142, "WI": 50017}
    assert len(qc.ORIGINAL_CSV_SHA256) == len(qc.ORIGINAL_RECEIPT_SHA256) == 64
