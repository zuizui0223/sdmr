"""Read-only GBIF source-volume gate for a NEW geographic-turnover pilot.

Diagnostic country strata only; neither countries nor Search API records define
native ranges, independent ecoregions, background M or a macroecological effect.
Full inference needs a versioned GBIF bulk download, native-range verification,
CHELSA accessible-grid layers, and independent effort weights.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from sdmr.data.gbif import GBIF_COL_XR_CHECKLIST_KEY, fetch_occurrence_search, match_taxon

# Diagnostic support checks only; country boundaries are NOT ecological regions.
PANEL = {
    "Arabidopsis thaliana": ("DE", "ES", "GB", "SE"),
    "Pinus sylvestris": ("ES", "FI", "NO", "SE"),
    "Quercus robur": ("DE", "FR", "GB", "SE"),
}
YEAR_QUERY = "2010,2025"
COUNT_CHECK = 100


def source_gate(*, matcher=match_taxon, fetcher=fetch_occurrence_search) -> dict:
    entries = []
    for taxon, countries in PANEL.items():
        try:
            hit = matcher(taxon, checklist_key=GBIF_COL_XR_CHECKLIST_KEY)
            taxon_key = hit.taxon_key
            accepted_name = hit.canonical_name
            match_status = hit.status
        except Exception as e:
            entries.append({"taxon": taxon, "status": "taxon_match_unavailable", "error": str(e)})
            continue
        for country in countries:
            try:
                out = fetcher(taxon_key, checklist_key=GBIF_COL_XR_CHECKLIST_KEY,
                              max_records=1,
                              extra_params={"country": country, "year": YEAR_QUERY})
                entries.append({
                    "taxon": taxon, "accepted_name": accepted_name,
                    "country_diagnostic_only": country, "taxon_key": taxon_key,
                    "match_status": match_status,
                    "gbif_indexed_count": int(out.total_count),
                    "count_pass_diagnostic": bool(out.total_count >= COUNT_CHECK),
                    "search_query_sha256": out.query_sha256,
                    "status": "count_available",
                })
            except Exception as e:
                entries.append({"taxon": taxon, "country_diagnostic_only": country,
                                "status": "count_unavailable", "error": str(e)})
    return {
        "source": "GBIF public v1 occurrence search count, GBIF v2 taxon match (CoL XR)",
        "read_at_utc": datetime.now(timezone.utc).isoformat(),
        "checklist_key": GBIF_COL_XR_CHECKLIST_KEY,
        "years": YEAR_QUERY,
        "has_coordinate": True,
        "has_geospatial_issue": False,
        "count_threshold_diagnostic_only": COUNT_CHECK,
        "panel_scope": "3 predeclared diagnostic taxa × 4 country checks; NOT final taxon sampling frame",
        "entries": entries,
        "n_count_available": sum(x["status"] == "count_available" for x in entries),
        "n_volume_checks_pass": sum(x.get("count_pass_diagnostic", False) for x in entries),
        "n_unavailable": sum(x["status"] != "count_available" for x in entries),
        "analysis_blocked": True,
        "missing_critical_sources": ["native-range and taxon-status receipts", "GBIF bulk DOI/download",
                                     "complete equal-area accessible M × CHELSA cells", "independent target-group effort"],
        "claim_boundary": "Count-only support gate, not biological native status or any turnover outcome",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = source_gate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"country count checks: {result['n_count_available']}/12 available; "
          f"diagnostic volume: {result['n_volume_checks_pass']}/12; "
          f"macro-analysis-blocked={result['analysis_blocked']}")


if __name__ == "__main__":
    main()
