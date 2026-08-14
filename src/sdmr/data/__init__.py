"""Reproducible public-data preparation for SDMR."""

from .background import bbox_membership, occurrence_buffer_membership, sample_target_group_background
from .chelsa import (
    CHELSA_V21_BASE,
    build_chelsa_cog_uri,
    raster_specs_from_chelsa_manifest,
    resolve_chelsa_manifest,
)
from .download import GBIFDownloadResult, load_gbif_download
from .gbif import (
    GBIFBulkDownloadRequired,
    GBIF_COL_XR_CHECKLIST_KEY,
    GBIFSearchResult,
    GBIFTaxonMatch,
    fetch_occurrence_search,
    match_taxon,
)
from .monthly import (
    aggregate_monthly_climatology_features,
    monthly_column_names,
    validate_monthly_feature_recipes,
)
from .quality import (
    OccurrenceAdmissionConfig,
    OccurrenceAdmissionResult,
    admit_occurrences,
    thin_to_grid,
)
from .raster import RasterLayerSpec, extract_raster_values, probe_raster_layers, sha256_file
from .snapshot import (
    GBIF_AWS_REGIONS,
    GBIFSnapshotSubsetResult,
    SnapshotBounds,
    build_snapshot_filter_sql,
    build_snapshot_select_query,
    gbif_snapshot_s3_uri,
    materialize_gbif_snapshot_subset,
)
from .snapshot_bounds import bounds_from_occurrences, tiled_bounds_from_occurrences
from .species_gate import species_admission_table

__all__ = [
    "CHELSA_V21_BASE",
    "GBIFBulkDownloadRequired",
    "GBIFDownloadResult",
    "GBIFSnapshotSubsetResult",
    "GBIF_AWS_REGIONS",
    "GBIF_COL_XR_CHECKLIST_KEY",
    "GBIFSearchResult",
    "GBIFTaxonMatch",
    "OccurrenceAdmissionConfig",
    "OccurrenceAdmissionResult",
    "RasterLayerSpec",
    "SnapshotBounds",
    "admit_occurrences",
    "aggregate_monthly_climatology_features",
    "bbox_membership",
    "bounds_from_occurrences",
    "build_chelsa_cog_uri",
    "build_snapshot_filter_sql",
    "build_snapshot_select_query",
    "extract_raster_values",
    "fetch_occurrence_search",
    "gbif_snapshot_s3_uri",
    "load_gbif_download",
    "match_taxon",
    "materialize_gbif_snapshot_subset",
    "monthly_column_names",
    "occurrence_buffer_membership",
    "probe_raster_layers",
    "raster_specs_from_chelsa_manifest",
    "resolve_chelsa_manifest",
    "sample_target_group_background",
    "sha256_file",
    "species_admission_table",
    "thin_to_grid",
    "tiled_bounds_from_occurrences",
    "validate_monthly_feature_recipes",
]
