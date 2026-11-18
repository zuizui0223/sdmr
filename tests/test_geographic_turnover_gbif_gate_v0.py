"""Offline tests: source gate never treats search counts as ecological evidence."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

PATH = Path(__file__).resolve().parents[1] / "experiments" / "geographic_turnover_gbif_gate_v0.py"
SPEC = importlib.util.spec_from_file_location("geographic_turnover_gbif_gate_v0", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_all_diagnostic_country_cells_and_blocked_state():
    def match(name, **kwargs):
        return SimpleNamespace(taxon_key=name.replace(" ", "_"), canonical_name=name, status="ACCEPTED")

    def fetch(key, **kwargs):
        assert kwargs["max_records"] == 1
        assert kwargs["extra_params"]["year"] == "2010,2025"
        return SimpleNamespace(total_count=101, query_sha256="fake_query_sha")

    r = mod.source_gate(matcher=match, fetcher=fetch)
    assert r["n_count_available"] == 12
    assert r["n_volume_checks_pass"] == 12
    assert r["analysis_blocked"]
    assert "NOT final" in r["panel_scope"]


def test_missing_live_count_is_explicit_failure():
    def match(name, **kwargs):
        return SimpleNamespace(taxon_key="1", canonical_name=name, status="ACCEPTED")

    def fetch(key, **kwargs):
        raise OSError("offline")

    r = mod.source_gate(matcher=match, fetcher=fetch)
    assert r["n_unavailable"] == 12
    assert r["n_count_available"] == 0
    assert all(entry["status"] == "count_unavailable" for entry in r["entries"])
