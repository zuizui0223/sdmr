"""Command-line pilot ingestion from GBIF into SDMR's occurrence schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .data import (
    OccurrenceAdmissionConfig,
    admit_occurrences,
    fetch_occurrence_search,
    match_taxon,
    thin_to_grid,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a small GBIF occurrence-search pilot, resolve the taxon, and "
            "write an auditable SDMR admission ledger. Full/corpus-scale runs must use a GBIF download."
        )
    )
    parser.add_argument("--taxon", required=True, help="Scientific name to resolve with GBIF species match")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-records", type=int, default=3000, help="Pilot cap; GBIF search cannot exceed 100000")
    parser.add_argument("--max-coordinate-uncertainty-m", type=float)
    parser.add_argument("--min-year", type=int)
    parser.add_argument("--max-year", type=int)
    parser.add_argument(
        "--thin-grid-degrees",
        type=float,
        default=None,
        help="Optional approximate one-record-per-cell thinning. Prefer exact raster cell IDs once extracted.",
    )
    args = parser.parse_args(argv)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    match = match_taxon(args.taxon)
    search = fetch_occurrence_search(
        match.taxon_key,
        checklist_key=match.checklist_key,
        max_records=args.max_records,
    )
    admission = admit_occurrences(
        search.records,
        config=OccurrenceAdmissionConfig(
            max_coordinate_uncertainty_m=args.max_coordinate_uncertainty_m,
            min_year=args.min_year,
            max_year=args.max_year,
        ),
    )
    accepted = admission.accepted
    if args.thin_grid_degrees is not None:
        accepted = thin_to_grid(accepted, cell_size_degrees=args.thin_grid_degrees)

    accepted.to_csv(out / "occurrences.csv", index=False)
    admission.rejected.to_csv(out / "rejected.csv", index=False)
    admission.ledger.to_csv(out / "admission_ledger.csv", index=False)
    metadata = {
        "taxon_query": match.query_name,
        "resolved_taxon_key": match.taxon_key,
        "resolved_canonical_name": match.canonical_name,
        "resolved_rank": match.rank,
        "resolved_status": match.status,
        "checklist_key": match.checklist_key,
        "gbif_query": search.query,
        "query_sha256": search.query_sha256,
        "gbif_total_count": search.total_count,
        "retrieved_count": search.retrieved_count,
        "truncated_pilot": search.truncated,
        "accepted_before_optional_grid_thinning": len(admission.accepted),
        "accepted_after_optional_grid_thinning": len(accepted),
        "max_coordinate_uncertainty_m": args.max_coordinate_uncertainty_m,
        "min_year": args.min_year,
        "max_year": args.max_year,
        "thin_grid_degrees": args.thin_grid_degrees,
        "taxon_match_raw": match.raw,
    }
    (out / "gbif_query.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
