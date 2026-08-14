"""Reproducible public-data preparation for SDMR."""

from .background import bbox_membership, sample_target_group_background
from .download import GBIFDownloadResult, load_gbif_download
from .gbif import (
    GBIFBulkDownloadRequired,
    GBIF_COL_XR_CHECKLIST_KEY,
    GBIFSearchResult,
    GBIFTaxonMatch,
    fetch_occurrence_search,
    match_taxon,
)
from .quality import (
    OccurrenceAdmissionConfig,
    OccurrenceAdmissionResult,
    admit_occurrences,
    thin_to_grid,
)
from .raster import RasterLayerSpec, extract_raster_values, sha256_file
from .species_gate import species_admission_table

__all__ = [
    "GBIFBulkDownloadRequired",
    "GBIFDownloadResult",
    "GBIF_COL_XR_CHECKLIST_KEY",
    "GBIFSearchResult",
    "GBIFTaxonMatch",
    "OccurrenceAdmissionConfig",
    "OccurrenceAdmissionResult",
    "RasterLayerSpec",
    "admit_occurrences",
    "bbox_membership",
    "extract_raster_values",
    "fetch_occurrence_search",
    "load_gbif_download",
    "match_taxon",
    "sample_target_group_background",
    "sha256_file",
    "species_admission_table",
    "thin_to_grid",
]
