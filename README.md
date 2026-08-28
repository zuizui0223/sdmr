# sdmr

**SDMR (Species Distribution Model Raster benchmark)** develops a leakage-free way to tune presence-only plant SDMs, then freezes that method before asking which environmental dimensions generalize across plants.

The project has two linked scientific products:

1. **Product A — niche-tuning methodology:** determine which environmental candidate universe, predictor-selection strategy, and model-complexity/regularization setting best predicts plant occurrences that were unavailable during model construction.
2. **Product B — universal-driver synthesis:** inherit the frozen Product-A method **and predictor universe**, then test which rasters, substitutable raster groups, and environmental processes retain predictive information in previously unseen plant taxa.

The starting problem is that correlation/VIF filtering can remove an ecologically informative raster before testing whether it improves genuinely independent prediction. SDMR therefore treats **out-of-sample predictive information** as the main admission criterion and keeps VIF as a comparison baseline.

## Current scientific status — 2026-08-28

SDMR now has two explicitly separate validation lanes. They must not be collapsed into one claim.

### Known-truth lane

The known-truth programme has established that the architecture can recover the frozen ecological target under controlled truth while preserving abstention when the contract cannot be completed.

- **v2.4:** terminal `exclusion_certificate_unavailable`. This is a contract-respecting abstention, not a biological or model-performance failure: discovery-only calibration did not supply every response key required by the frozen validation contract.
- **v2.6:** terminal `v2_6_supported` under the predeclared known-truth coverage/process-safety criteria. Possible-process recall was 1.0 and false-required processes were 0, while possible-process precision remained broad at 0.467; the supported claim therefore does not imply narrow process identification.
- **v2.7.2:** deterministic known-truth successor supported on 60 unused cases. Independent process replicates had maximum floating drift 0.0; robust-selector coverage was 1.0; stable-process-core precision/recall/F1 were 0.9889/0.9833/0.9833.

Known-truth support is necessary implementation/scientific evidence, but it is **not empirical Product-A promotion**.

### Empirical lane

The empirical lane is separately frozen against the 2026-08-01 public-data snapshot and successor source receipts. Earlier fresh empirical attempts correctly returned unavailable/presealed-unavailable states when complete frozen evidence could not be assembled; those states are not reclassified as adverse ecological results.

Product-A v2.8.3 fixed the globally calibrated sealed fraction at `0.25`, used three predeclared seeds, required coordinate-only structural transportability before environmental/model stages, and failed closed if the full denominator could not be audited. Its authoritative run `33036252432` ended `cancelled` during presealed model-pool computation. It never reached aggregate, pretruth/final-model freeze, sealed ecological evidence, or a scientific terminal decision. This is a technical execution terminal, not a favorable, null or adverse ecological result.

The **Product-A v2.8.4** successor is runtime-only. Its truth-blind calibration run `33140419810` completed all 21 frozen runtime cells and proposed a 225-minute group-command timeout. The environment, dependency lock, timeout, source artifacts, checkpoint/retry identity and receipt barrier are now frozen in `configs/product_a_v2_8_4_environment_timeout_freeze.json`; sealed evidence remained unopened and no scientific promotion occurred. Scientific execution is still unauthorized until a separate presealed-workflow and receipt-barrier implementation passes review.

### Product-B block

**Product B remains blocked until Product A obtains a supported fresh empirical confirmation under a prospectively frozen full-denominator design, followed by a separate explicit Product-A promotion / Product-B-unblock decision.**

Known-truth support alone, a partial empirical subset, or a structural-availability success cannot unblock Product B.

See the frozen result records in `docs/` and `evidence/` for exact runs, artifacts, digests, opened-evidence boundaries and terminal decisions.

## Core information barrier

Within each species, occurrence evidence is assigned two roles:

- **model pool** — available for fitting, predictor selection, candidate-universe comparison, regularization/complexity tuning, inner spatial CV, and stopping decisions;
- **sealed answer-check pool** — unavailable to all choices above and opened only after a candidate protocol has been frozen.

There is **no scientifically privileged 50/50 split**. The sealed fraction is configurable during design/calibration and must be frozen before a confirmation outcome is opened. When both pools come from one GBIF-like dataset, whole spatial blocks are withheld rather than random nearby records. Independent later surveys or external occurrence sources can provide an even stronger final test.

A GBIF presence is positive occurrence evidence, not calibrated probability = 1, and an unrecorded location is not a verified absence. The primary current score, `presence_rank`, asks whether sealed presences receive higher relative-suitability scores than defensible background/reference locations. A Boyce-style metric is secondary.

## Product A — implemented

Product A compares **three nested environmental candidate universes** when the standard CHELSA manifest is used:

1. **BIOCLIM19** — the conventional BIO1–BIO19 climate set;
2. **CHELSA-bioclim** — BIOCLIM19 plus directly distributed freeze/thaw, growing-degree-day, growing-season, snow, and productivity variables;
3. **active-all** — the full currently resolvable active candidate manifest, adding current VPD, PET, CMI, radiation, wind, humidity, and cloud summaries.

Within each candidate universe and using the model pool only, SDMR compares:

- all candidate rasters;
- conventional iterative VIF pruning;
- nested predictive forward selection;
- regularization strength and penalty (`C`, L1/L2);
- linear versus degree-2 environmental response surfaces;
- same-size random predictor subsets as a null benchmark.

All candidate universes see the **same sealed spatial blocks** for a species. Discovery taxa select the winning `candidate universe × strategy`; separate validation taxa then test that already-chosen combination. `method_choice.txt` freezes:

- `winning_strategy`;
- `winning_universe`;
- ordered `winning_predictors`;
- SHA-256 fingerprint of that predictor universe;
- discovery/validation taxa and holdout settings.

Product B verifies that fingerprint and inherits the exact predictor universe rather than silently reopening the variable-search space.

Custom predictor lists remain supported; they are frozen as a `custom` universe with the same SHA-256 contract.

## Product B — implemented validation scaffold

Product B must receive `method_choice.txt` or another explicitly predeclared frozen strategy. If Product A supplied a frozen predictor universe, Product B must use that exact universe as well.

Driver evidence is summarized at three levels:

1. **individual raster** — selection stability, incremental model-pool gain, sealed drop-one loss;
2. **substitutable raster group** — correlated variables remain available during fitting and are grouped only for interpretation; group-drop loss detects information hidden by substitution;
3. **environmental process** — rasters are mapped to broader dimensions such as temperature, drought, water balance, thermal energy, phenology, snow, radiation, wind, humidity, cloud, and productivity.

A candidate process core is discovered using discovery taxa only and then frozen before testing on unseen plant taxa. Repeated taxon splits quantify core stability and transfer. Same-size random process-core nulls are evaluated on the **same sealed spatial blocks** as the discovered core/full comparison. Conditionality can also be summarized by declared strata such as family, growth form, or biome with equal species weighting.

Valid empirical outcomes are a small global core, global + conditional cores, or no useful universal core. Product B does not begin merely because this scaffold exists; its explicit unblock gate above must first be satisfied.

## CHELSA candidate universe and provenance

`configs/chelsa_v2_1_plant_candidates.csv` contains the **active currently resolvable candidates** used by the standard Product-A universe comparison: BIO1–BIO19, freeze/growing-season/thermal-energy/snow/productivity variables, plus current VPD, PET, CMI, shortwave radiation, wind, relative humidity, and cloud summaries. Each candidate has process/mechanism metadata and a resolver rule.

`sdmr-chelsa` converts that manifest into explicit CHELSA v2.1 COG URIs and writes a resolution ledger before extraction:

```bash
sdmr-chelsa \
  --manifest configs/chelsa_v2_1_plant_candidates.csv \
  --output-dir data/chelsa_resolution
```

Variables described in the broader BIOCLIM+ literature but without a verified current direct COG are **not silently admitted**. They live in `configs/chelsa_v2_1_excluded_candidates.csv` with explicit exclusion reasons.

Optional monthly-derived alternatives are declared separately in `configs/chelsa_v2_1_monthly_feature_recipes.csv`. These recipes explicitly convert 12 monthly climatologies into annual means, extrema, or sums, avoiding the assumption that a calendar month represents the same season in both hemispheres. They are an optional candidate-expansion layer, not silently mixed into the active standard universe.

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

The search API is deliberately not the route for deciding Product-A method performance. Real method comparison starts from a **versioned GBIF bulk download or another prospectively frozen source receipt**.

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

With the standard manifest, `--run-method` tunes **candidate universe × method strategy** on discovery taxa and freezes both in `method_choice.txt`. A deliberately small `--only` diagnostic subset that cannot define the nested standard universes safely falls back to a frozen custom universe.

The numeric thresholds above are **example run parameters, not universal biological defaults**. Product A successor confirmations use their own versioned contracts; they must not inherit or change these example parameters implicitly.

For method comparison, a broader target-group download is required by default. `--allow-pilot-target-group` exists only for explicitly diagnostic sensitivity runs where the focal pilot taxa themselves are used as the sampling-effort pool.

The pilot writes GBIF provenance, taxon-selection and occurrence-admission ledgers, species gates, background/M ledgers, CHELSA resolution and raster-provenance tables, prepared occurrence/background tables, method summaries, and the frozen `method_choice.txt`.

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

Product B must inherit the frozen method **and predictor universe**:

```bash
sdmr \
  --mode drivers \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --method-choice results/method_v1/method_choice.txt \
  --output-dir results/drivers_v1
```

The `universality` mode repeats discovery/validation taxon splits for process-core stability and unseen-taxon transfer while retaining the same frozen Product-A universe.

## Validation status

GitHub Actions runs the core suite on Python 3.10–3.13 plus a Python 3.12 `rasterio` job. The suite covers sealed information barriers, candidate-universe comparison, method baselines/tuning, GBIF and raster provenance, CHELSA resolution, correlated-variable substitution, Product-A-to-Product-B strategy/universe inheritance, unseen-taxon process-core transfer, heterogeneity summaries, bulk-download preparation, frozen contract identity and one-shot execution gates.

## Current empirical boundary

The repository is **past architecture-only readiness**. Product A has supported known-truth results, but empirical promotion remains unresolved. v2.8.3 ended technically before sealed evidence, and v2.8.4 has completed only its truth-blind calibration and separate environment/timeout freeze.

Therefore the current claim boundary is:

- supported: the deterministic Product-A architecture and its known-truth recovery/safety claims under the frozen v2.6/v2.7.2 contracts;
- not yet supported: general empirical Product-A promotion on fresh plant data;
- blocked: Product B and any universal-driver/process-core biological claim;
- preserved as valid outcomes: `unavailable`, `presealed_unavailable`, structural non-estimability and other fail-closed states when the predeclared evidence denominator cannot be completed.

Historical frozen results remain authoritative under the code/contracts that produced them. Successor execution-discipline refactors must not be used to recompute, revalidate or silently reinterpret those results.

**Development hard stop:** after one valid fresh empirical Product-A terminal decision under the unchanged full-denominator design and a separate explicit promotion/non-promotion decision, stop Product-A development and close its manuscript without waiting for Product B. Do not change taxa, M, seeds, sealed fraction, thresholds, candidate library, predictor universe, denominator or provider to seek a more favorable result.

See [`docs/method.md`](docs/method.md), [`docs/research_program.md`](docs/research_program.md), [`docs/data_pipeline.md`](docs/data_pipeline.md), and the versioned Product-A result documents under [`docs/`](docs/).
