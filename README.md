# sdmr

**SDMR (Species Distribution Model Raster benchmark)** develops a leakage-free way to tune presence-only plant SDMs, then freezes that method before asking which environmental dimensions generalize across plants.

The project has two linked scientific products:

1. **Product A — niche-tuning methodology:** determine which SDM tuning procedure best predicts plant occurrences that were unavailable during model construction.
2. **Product B — universal-driver synthesis:** inherit the frozen Product-A method, then test which rasters, substitutable raster groups, and environmental processes retain predictive information in previously unseen plant taxa.

The starting problem is that correlation/VIF filtering can remove an ecologically informative raster before testing whether it improves genuinely independent prediction. SDMR therefore treats **out-of-sample predictive information** as the main admission criterion and keeps VIF as a comparison baseline.

## Core information barrier

Within each species, occurrence evidence is assigned two roles:

- **model pool** — available for fitting, predictor selection, regularization/complexity tuning, inner spatial CV, and stopping decisions;
- **sealed answer-check pool** — unavailable to all choices above and opened only after a candidate protocol has been frozen.

There is **no scientifically privileged 50/50 split**. The sealed fraction is configurable and should itself be sensitivity-tested. When both pools come from one GBIF-like dataset, whole spatial blocks are withheld rather than random nearby records. Independent later surveys or external occurrence sources can provide an even stronger final test.

A GBIF presence is positive occurrence evidence, not calibrated probability = 1, and an unrecorded location is not a verified absence. The primary current score, `presence_rank`, asks whether sealed presences receive higher relative-suitability scores than defensible background/reference locations. A Boyce-style metric is secondary.

## Product A — implemented

Inside the model pool only, SDMR compares:

- all candidate rasters;
- conventional iterative VIF pruning;
- nested predictive forward selection;
- regularization strength and penalty (`C`, L1/L2);
- linear versus degree-2 environmental response surfaces;
- same-size random predictor subsets as a null benchmark.

Each strategy is tuned without consulting the sealed occurrences, frozen, then evaluated on the answer-check set. A second information barrier operates across species: `benchmark_method_taxon_split` uses discovery taxa to choose the winning **method strategy**, then evaluates that already-chosen strategy on unseen validation taxa. The CLI writes `method_choice.txt` so Product B can inherit the decision without human reselection.

## Product B — implemented validation scaffold

Product B must receive `method_choice.txt` or another explicitly predeclared frozen strategy. Driver evidence is summarized at three levels:

1. **individual raster** — selection stability, incremental model-pool gain, sealed drop-one loss;
2. **substitutable raster group** — correlated variables remain available during fitting and are grouped only for interpretation; group-drop loss detects information hidden by substitution;
3. **environmental process** — rasters are mapped to broader dimensions such as temperature, drought, water balance, thermal energy, phenology, snow, radiation, wind, humidity, cloud, and productivity.

A candidate process core is discovered using discovery taxa only and then frozen before testing on unseen plant taxa. Repeated taxon splits quantify core stability and transfer. Same-size random process-core nulls are evaluated on the **same sealed spatial blocks** as the discovered core/full comparison. Conditionality can also be summarized by declared strata such as family, growth form, or biome with equal species weighting.

Valid empirical outcomes are a small global core, global + conditional cores, or no useful universal core.

## CHELSA candidate universe and provenance

`configs/chelsa_v2_1_plant_candidates.csv` contains **43 active current COG candidates**: BIO1–BIO19, freeze/growing-season/thermal-energy/snow/productivity variables, plus current VPD, PET, CMI, shortwave radiation, wind, relative humidity, and cloud summaries. Each candidate has process/mechanism metadata and a resolver rule.

`sdmr-chelsa` converts that manifest into explicit CHELSA v2.1 COG URIs and writes a resolution ledger before extraction:

```bash
sdmr-chelsa \
  --manifest configs/chelsa_v2_1_plant_candidates.csv \
  --output-dir data/chelsa_resolution
```

Variables described in the broader BIOCLIM+ literature but without a verified current direct COG are **not silently admitted**. They live in `configs/chelsa_v2_1_excluded_candidates.csv` with explicit exclusion reasons. Optional monthly-derived alternatives are declared separately in `configs/chelsa_v2_1_monthly_feature_recipes.csv`.

Raster extraction records URI, CRS, resolution, nodata, scale/offset, and local SHA-256 when applicable.

## Public-data layer

The repository includes:

- GBIF v2 taxon matching with a recorded Catalogue of Life Extended Release checklist key;
- the same checklist key carried into occurrence search;
- a small search-API client for **wiring/diagnostic pilots only**;
- GBIF bulk ZIP/CSV/TSV/Parquet ingestion with download/file provenance;
- row-level occurrence admission/rejection reasons;
- explicit species data-sufficiency gates with no hidden minimum-occurrence default;
- two transparent accessible-area (`M`) sensitivity baselines: occurrence bounding box and occurrence-distance buffer;
- target-group background construction inside the declared `M`;
- CHELSA COG resolution/extraction and provenance.

The search API is deliberately not the route for deciding Product-A method performance. Real method comparison starts from a **versioned GBIF bulk download**.

## One-command real Product-A pilot

`sdmr-pilot` prepares an auditable pilot and can run Product A end to end:

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

The numeric thresholds above are **example run parameters, not universal biological defaults**. Product A should repeat defensible quality gates, `M` constructions, background settings, holdout fractions, and seeds to test whether the winning strategy is stable.

For method comparison, a broader target-group download is required by default. `--allow-pilot-target-group` exists only for explicitly diagnostic sensitivity runs where the focal pilot taxa themselves are used as the sampling-effort pool.

The pilot writes GBIF provenance, taxon-selection and occurrence-admission ledgers, species gates, background/M ledgers, CHELSA resolution and raster-provenance tables, prepared occurrence/background tables, method summaries, and `method_choice.txt`.

`configs/product_a_pilot_taxa.example.csv` is an intentionally diverse **diagnostic** taxon list. It is not the final sampling frame for the universal-driver claim.

## Run the statistical stages directly

Product A on already prepared tables:

```bash
sdmr \
  --mode method \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --spatial-test-fraction 0.20 \
  --taxon-validation-fraction 0.20 \
  --output-dir results/method_v1
```

Product B must inherit the frozen method:

```bash
sdmr \
  --mode drivers \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --method-choice results/method_v1/method_choice.txt \
  --output-dir results/drivers_v1
```

The `universality` mode repeats discovery/validation taxon splits for process-core stability and unseen-taxon transfer.

## Validation status

GitHub Actions runs the core suite on Python 3.10–3.13 plus a Python 3.12 `rasterio` job. On the current Product-A pilot head:

- core job: **37 passed, 1 raster-only test skipped**;
- geo/rasterio job: **38 passed**;
- workflow run #11: **success across all five jobs**.

The suite covers sealed information barriers, method baselines/tuning, GBIF and raster provenance, CHELSA resolution, correlated-variable substitution, Product-A-to-Product-B strategy inheritance, unseen-taxon process-core transfer, heterogeneity summaries, and the new bulk-download Product-A pilot preparation path.

## Current empirical boundary

The architecture is now **real-data execution ready**, but the biological result has not yet been established. No claim is made yet that predictive selection beats VIF on real plants or that a universal plant niche core exists.

The remaining empirical sequence is:

1. obtain/fingerprint a real focal plant GBIF bulk download and a broad plant target-group download;
2. run the moderate Product-A pilot across multiple predeclared data specifications;
3. establish whether one method strategy wins robustly on unseen taxa and freeze its claim boundary;
4. define a separate, broad Product-B plant sampling frame;
5. run repeated process-core discovery/validation and conditionality analyses;
6. use independent later/external occurrences where available as the strongest final answer check.

See [`docs/method.md`](docs/method.md), [`docs/research_program.md`](docs/research_program.md), and [`docs/data_pipeline.md`](docs/data_pipeline.md).
