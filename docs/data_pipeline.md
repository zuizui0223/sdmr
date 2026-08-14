# Public-data pipeline: GBIF occurrence evidence to environmental features

This layer is separate from SDMR's statistical benchmark. Its purpose is to make every taxonomy choice, occurrence admission/exclusion, accessible-area (`M`) rule, background source, environmental layer, and file/query version auditable **before sealed-test modelling begins**.

## 1. Taxonomy is versioned

SDMR records the declared Catalogue of Life Extended Release checklist key alongside GBIF taxon matching and sends the same checklist key when using occurrence search. Taxon keys from one checklist must not be silently reused against another taxonomy.

For bulk-download analyses, retain the GBIF download key/citation, the checklist used for the analysis, and the local file SHA-256. `load_gbif_download` records file size, archive member, row count, download key, checklist key, and SHA-256.

## 2. Search API is wiring/diagnostic only

`sdmr-gbif-pilot` exists to test taxon resolution, search parameters, admission rules, and small code paths. It fingerprints the normalized query and records GBIF's total count versus the number actually retrieved. It refuses to pretend that the occurrence-search ceiling represents a complete large query.

A **Product-A method comparison must not be promoted from the first N search results**. Real Product-A pilots start from a versioned GBIF bulk download so result ordering/pagination cannot masquerade as a biological validation sample.

## 3. Occurrence admission is explicit

`OccurrenceAdmissionConfig` can declare:

- coordinate-uncertainty threshold;
- minimum/maximum year;
- allowed `basisOfRecord` values;
- present-status requirement;
- exact coordinate deduplication.

Every rejection receives an explicit reason and all counts are written to an admission ledger. None of these thresholds is a hidden scientific default. Product A should repeat defensible admission specifications and ask whether the winning method strategy is stable.

`species_admission_table` separately applies explicit minimum occurrence and minimum independent-cell gates. Again, the caller must provide the thresholds.

## 4. Predeclared pilot taxa

`select_configured_taxa` takes a CSV with `scientific_name` and optional `taxon_key`. Taxon-key matching is preferred when available; otherwise exact canonical-name matching is used. The ledger retains configured taxa with zero matches rather than silently deleting them.

`configs/product_a_pilot_taxa.example.csv` is a deliberately heterogeneous **diagnostic list** for method development. It is not the sampling frame for the final universal-driver claim.

## 5. Accessible area (`M`) is an experimental factor

SDMR does not encode one universal `M` for all plants. The current transparent sensitivity baselines are:

- `bbox_membership` — occurrence bounding rectangle with an explicit optional geographic buffer;
- `occurrence_buffer_membership` — all target-group points within a declared great-circle distance of any focal occurrence.

Neither is asserted to be biologically optimal for every taxon. They provide reproducible alternatives that can be compared before more biologically specific dispersal/biogeographic `M` definitions are introduced.

For global or dateline-spanning taxa, a simple minimum/maximum bounding box may be particularly poor; treat it as a diagnostic baseline rather than an ecological conclusion.

## 6. Target-group background

`sample_target_group_background` samples reference cells from comparable plant sampling effort **inside the declared `M`**, excludes cells containing focal presences, and collapses duplicate target-group cells before sampling.

For real Product-A method comparison, `sdmr-pilot` requires a broader target-group GBIF download by default. Using only the focal pilot taxa as the sampling-effort pool requires the explicit `--allow-pilot-target-group` opt-in and should be labeled diagnostic/sensitivity-only.

## 7. CHELSA candidate resolution

The active direct-COG universe lives in `configs/chelsa_v2_1_plant_candidates.csv`. It currently contains 43 candidates with `process`, `mechanism`, `retrieval`, `remote_name`, and availability metadata.

`sdmr-chelsa` resolves these rows to explicit historical CHELSA v2.1 COG URIs before extraction and writes:

- `chelsa_resolution_ledger.csv`;
- `chelsa_layer_catalog.csv`;
- `chelsa_unresolved.csv`.

Example:

```bash
sdmr-chelsa \
  --manifest configs/chelsa_v2_1_plant_candidates.csv \
  --output-dir data/chelsa_resolution
```

Candidates described in broader BIOCLIM+ material but lacking a verified current direct COG are stored separately in `configs/chelsa_v2_1_excluded_candidates.csv` with explicit reasons. They are not silently mixed into the active model universe.

`configs/chelsa_v2_1_monthly_feature_recipes.csv` declares optional monthly-derived alternatives such as VPD maximum, minimum CMI, annual PET, peak shortwave radiation, and minimum humidity. These are a separate feature-construction experiment, not aliases silently substituted for the active annual summaries.

## 8. Raster extraction and provenance

`RasterLayerSpec` + `extract_raster_values` support local rasters and rasterio-readable COG URIs. The extractor:

- transforms WGS84 coordinates to the raster CRS;
- converts nodata to missing values;
- applies scale/offset metadata unless explicitly overridden;
- records URI, CRS, dimensions, resolution, nodata, scale, and offset;
- SHA-256 fingerprints local raster files.

Install raster support with:

```bash
pip install -e '.[geo]'
```

The extraction ledger, not a human memory of a URL, defines the environmental data actually used by a benchmark.

## 9. End-to-end real Product-A pilot

`sdmr-pilot` joins the data layer and the Product-A benchmark. It requires a versioned focal GBIF bulk download and can also take a separate broad plant target-group download:

```bash
sdmr-pilot \
  --gbif-download data/gbif/focal.zip \
  --gbif-download-key <GBIF_DOWNLOAD_KEY> \
  --target-group-download data/gbif/plant_target_group.zip \
  --target-group-download-key <TARGET_GROUP_DOWNLOAD_KEY> \
  --taxa configs/product_a_pilot_taxa.example.csv \
  --min-occurrences 50 \
  --min-unique-cells 30 \
  --m-strategy buffer \
  --occurrence-buffer-km 300 \
  --extract-chelsa \
  --run-method \
  --output-dir results/product_a_pilot
```

The numeric settings above are example run parameters only. The runner records them in `pilot_specification.json` and writes:

- focal and target-group GBIF provenance;
- taxon selection ledger;
- occurrence admission ledger;
- species sufficiency gate;
- per-species `M`/background ledger;
- CHELSA resolution and raster provenance;
- prepared occurrence/background feature tables;
- Product-A discovery/validation method summaries;
- frozen `method_choice.txt`.

## 10. Information-barrier rule

A benchmark specification includes data cleaning, taxon frame, `M`, target-group source, background rule, environmental candidate universe, feature recipe, holdout rule, and random seed policy. These must be finalized before the relevant sealed predictions are inspected.

If any data-layer rule is materially changed after looking at sealed results, that result belongs to method development. It must not be relabeled as independent validation without a new independent validation layer or a fully repeated predeclared benchmark.
