# Public-data pipeline: GBIF occurrence evidence to environmental features

This layer is intentionally separate from SDMR's statistical benchmark. Its job is to make every admission, exclusion, background choice, and raster value auditable before sealed-test modelling begins.

## 1. GBIF taxon resolution

Resolve each focal scientific name with GBIF's species-match service and retain the complete match response together with the accepted taxon key used for occurrence retrieval. Never silently replace a name without keeping that mapping.

## 2. Search API is for pilots, not the global corpus

`sdmr-gbif-pilot` uses GBIF occurrence search for small development datasets. It requests:

- a resolved `taxonKey`;
- `hasCoordinate=true`;
- `hasGeospatialIssue=false`;
- `occurrenceStatus=PRESENT`.

The pilot client fingerprints the normalized query and records both GBIF's total count and the number actually retrieved. It refuses to treat search pagination as a full corpus when the query exceeds GBIF's 100,000-record search ceiling. Global runs should instead ingest a versioned asynchronous GBIF occurrence download and retain its download key/citation as provenance.

Example:

```bash
sdmr-gbif-pilot \
  --taxon "Arabidopsis thaliana" \
  --max-records 3000 \
  --max-coordinate-uncertainty-m 5000 \
  --output-dir data/pilot/arabidopsis
```

Outputs:

- `occurrences.csv` — admitted occurrence rows;
- `rejected.csv` — rejected rows with explicit reasons;
- `admission_ledger.csv` — counts at every filter;
- `gbif_query.json` — resolved taxon, query, SHA-256 query fingerprint, total/retrieved counts, and filter settings.

The coordinate-uncertainty and year thresholds are **not** hard-coded scientific truths. They are explicit parameters so Product A can test whether method rankings are robust to defensible data-quality choices.

## 3. Duplicate and sampling-density control

Exact same-coordinate duplicates can be removed at admission. `thin_to_grid` provides a generic approximate one-record-per-cell diagnostic, but once environmental rasters are extracted the preferred rule is one occurrence per exact raster cell rather than assuming a grid origin in advance.

## 4. Accessible area (M) remains an experimental factor

SDMR does not hard-code one universal definition of M for every plant. `sample_target_group_background` therefore requires a caller-supplied M-membership mask. This lets Product A compare multiple biologically defensible M constructions without changing the sealed-test engine.

`bbox_membership` exists only as a transparent baseline/sensitivity option. It must not be interpreted as the universal preferred M.

## 5. Target-group background

Within a declared M, background/reference points are drawn from comparable plant occurrence sampling rather than uniformly from the globe. Candidate cells containing a focal presence are excluded, and target-group duplicate cells are collapsed before sampling. The source taxon is retained as `background_source_species` while the model-facing `species` field is set to the focal species.

This design is intended to reduce reward for learning collector effort alone. Background strategy itself remains a Product-A tuning/sensitivity dimension.

## 6. Environmental raster extraction and provenance

`RasterLayerSpec` + `extract_raster_values` support local rasters and rasterio-readable COG URIs. The extractor:

- transforms WGS84 occurrence coordinates to the raster CRS when needed;
- applies raster scale/offset metadata unless explicitly overridden;
- converts nodata to missing values;
- records CRS, dimensions, resolution, nodata, scale, and offset;
- SHA-256 fingerprints local raster files.

Install raster support with:

```bash
pip install -e '.[geo]'
```

CHELSA v2.1/BIOCLIM+ is the initial candidate source. The repository manifest is the variable-selection manifest; actual file/URI provenance belongs in the extraction ledger so a future CHELSA release cannot silently change an existing benchmark.

## 7. Information-barrier rule

Data cleaning, M construction, background generation, and raster extraction must be finalized for a benchmark specification before its sealed occurrence predictions are inspected. If a data-layer rule is materially changed after seeing sealed results, that result belongs to model development and requires a new independent validation set or a fully repeated predeclared benchmark.
