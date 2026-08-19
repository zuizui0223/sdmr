"""Materialize a small real-GBIF diagnostic corpus for CI smoke testing.

This is deliberately NOT a citable Product-A benchmark. It exists only to test
that public GBIF occurrences and real CHELSA rasters can traverse the full SDMR
pipeline. Scientific promotion still requires versioned bulk/snapshot inputs and
an external target-group sampling-effort corpus.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from sdmr.data import fetch_occurrence_search, match_taxon

TAXA = (
    "Arabidopsis thaliana",
    "Plantago major",
    "Trifolium repens",
    "Taraxacum officinale",
    "Poa annua",
    "Phragmites australis",
    "Quercus robur",
    "Pinus sylvestris",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--records-per-taxon", type=int, default=180)
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    frames = []
    taxa_rows = []
    provenance = []
    for name in TAXA:
        match = match_taxon(name)
        result = fetch_occurrence_search(
            match.taxon_key,
            checklist_key=match.checklist_key,
            max_records=args.records_per_taxon,
        )
        frame = result.records.copy()
        frame["species"] = match.canonical_name or name
        frames.append(frame)
        taxa_rows.append({"scientific_name": match.canonical_name or name, "taxon_key": match.taxon_key})
        provenance.append({
            "query_name": name,
            "canonical_name": match.canonical_name,
            "taxon_key": match.taxon_key,
            "checklist_key": match.checklist_key,
            "query_sha256": result.query_sha256,
            "total_count": result.total_count,
            "retrieved_count": result.retrieved_count,
            "truncated": result.truncated,
        })

    pd.concat(frames, ignore_index=True).to_csv(out / "diagnostic_occurrences.csv", index=False)
    pd.DataFrame(taxa_rows).to_csv(out / "diagnostic_taxa.csv", index=False)
    pd.DataFrame(provenance).to_csv(out / "diagnostic_gbif_api_provenance.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
