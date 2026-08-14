# sdmr

**SDMR (Species Distribution Model Raster benchmark)** develops and validates a leakage-free way to estimate plant environmental niches from presence-only occurrence data, then uses that frozen method to ask which environmental dimensions generalize across plants.

The project is deliberately split into two linked scientific products:

1. **Product A — niche-tuning methodology:** determine which SDM tuning procedure best predicts plant occurrences that were never available during model construction.
2. **Product B — universal-driver synthesis:** freeze the validated Product-A procedure, apply it across many plants, and test which rasters, substitutable raster groups, and environmental processes retain predictive information in previously unseen plant taxa.

The starting problem is simple: predictor screening often treats correlation/VIF as the main gate. That can discard an ecologically informative raster before asking the more relevant question: **does it improve prediction of genuinely unused occurrences?** SDMR therefore makes independent predictive transfer the primary criterion and keeps VIF as a comparison baseline rather than a biological admission rule.

## Core information barrier

For every focal species, occurrence evidence has two roles:

- **model pool** — may be used for fitting, predictor selection, regularization/complexity tuning, inner spatial CV, and stopping decisions;
- **sealed answer-check pool** — unavailable to every choice above and opened only after a candidate protocol has been frozen.

There is **no scientifically privileged 50/50 split**. The sealed fraction is configurable and should be tested for sensitivity. When model and answer-check records come from one GBIF-like pool, SDMR withholds whole spatial blocks rather than random nearby points. Truly independent later surveys or external records can provide an even stronger final test.

A GBIF presence is positive occurrence evidence, not calibrated probability = 1, and an unrecorded location is not a verified absence. The current primary metric, `presence_rank`, therefore asks whether sealed presences receive higher relative-suitability scores than defensible background/reference locations. A Boyce-style metric is retained as a secondary check.

## Product A — implemented niche-tuning benchmark

Inside the model pool only, SDMR currently compares:

- **all candidate rasters**;
- **conventional iterative VIF pruning**;
- **nested predictive forward selection** based on spatial CV;
- regularization strength and penalty (`C`, L1/L2);
- linear versus degree-2 environmental response surfaces;
- **same-size random raster subsets** as a null benchmark.

Each strategy is tuned without access to the sealed occurrence pool, frozen, and then evaluated once on the answer-check data. `drop_one_importance` measures sealed predictive loss after removing one selected raster, and `benchmark_holdout_sensitivity` checks whether method rankings depend on an arbitrary holdout fraction.

A second information barrier operates across species. `benchmark_method_taxon_split` uses **discovery taxa** to choose the winning method strategy, then evaluates that already-chosen strategy on separate **validation taxa**. The CLI writes the result to `method_choice.txt` so Product B can inherit it without human reselection.

## Product B — implemented universal-driver validation

Product B is not allowed to choose a new SDM strategy after environmental-driver results are visible. It must receive the frozen Product-A strategy through `--method-choice` or an explicitly predeclared `--strategy`.

Driver evidence is evaluated at three levels:

1. **individual raster** — selection stability, incremental model-pool gain, sealed drop-one loss;
2. **substitutable raster group** — correlated predictors remain available to the model, are grouped only for interpretation, and are removed together in `drop_group_importance` to reveal shared information hidden by substitution;
3. **environmental process** — rasters are mapped to broader processes such as temperature, drought, water balance, thermal energy, phenology, snow, radiation, wind, humidity, and productivity.

`benchmark_driver_corpus_from_strategy` applies one frozen Product-A strategy across a plant corpus and produces raster-, equivalence-group-, and process-level evidence without strategy reselection.

For the strongest universality claim, `benchmark_process_core_taxon_split` discovers candidate **core environmental processes using discovery taxa only**, freezes that process set, and tests whether it retains predictive performance in plant taxa that were never used to define the core. `benchmark_repeated_process_core_splits` repeats this taxon-level discovery/validation barrier and reports process-core stability and transfer.

Thus a process is not called universal merely because it was often selected. The intended evidence combines **stability + independent spatial performance + transfer to unseen plant taxa**. Valid outcomes include:

- a small **global plant niche core**;
- **global core + biome/clade/life-form-specific conditional cores**;
- or **no useful universal core**.

## Candidate environmental universe

`configs/chelsa_v2_1_plant_candidates.csv` is the versioned predictor manifest. It currently spans:

- BIO1–BIO19;
- freeze/thaw and cold-stress variables;
- growing-degree-day and growing-season timing/length variables;
- growing-season precipitation and temperature;
- snow cover / snow-water variables;
- potential climate-related productivity;
- vapor-pressure deficit;
- PET / climate moisture / site-water-balance axes;
- shortwave and longwave radiation;
- near-surface wind;
- relative humidity and cloud fraction;
- available soil-water-capacity context for water-balance variables.

Every candidate has `process` and `mechanism` metadata so Product B can synthesize generality at a biologically interpretable process level instead of reporting only a winner among correlated raster names.

## Public-data and provenance layer

The repository includes an auditable data layer rather than mixing data acquisition into model fitting:

- GBIF v2 taxon matching with an explicitly recorded Catalogue of Life Extended Release checklist key;
- the same checklist key carried into occurrence search;
- a small GBIF search-API pilot client with query SHA-256 and protection against silently treating the search ceiling as a full corpus;
- GBIF bulk-download ZIP/CSV/TSV/Parquet ingestion with download/file provenance;
- row-level occurrence admission/rejection reasons and ledgers;
- explicit species data-sufficiency gates with no hidden minimum-occurrence default;
- caller-declared accessible-area (`M`) membership;
- target-group / sampling-aware background construction inside `M`;
- raster extraction with CRS transformation, nodata and scale/offset handling, and local-file SHA-256 provenance.

See [`docs/data_pipeline.md`](docs/data_pipeline.md) for the data-layer rules. Data-quality thresholds, `M`, and background definitions remain explicit sensitivity dimensions rather than silently fixed assumptions.

## Data contract

The statistical core consumes occurrence and background/reference tables containing coordinates and extracted raster values:

```text
species,longitude,latitude,bio1,bio2,...,vpd,gdd5,...
```

1. `occurrences`: admitted plant occurrence coordinates with environmental values.
2. `background`: species-specific sampling-aware background/reference coordinates within a declared accessible area (`M`) with the same predictor columns.

## Run Product A

```bash
pip install -e .
sdmr \
  --mode method \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --spatial-test-fraction 0.20 \
  --taxon-validation-fraction 0.20 \
  --output-dir results/method_v1
```

The output directory contains `method_choice.txt`, including the winning strategy learned from discovery taxa.

Python:

```python
from sdmr import benchmark_method_taxon_split

result = benchmark_method_taxon_split(
    occurrences,
    background,
    candidate_predictors=["bio1", "bio4", "bio12", "bio15", "vpd", "gdd5", "cmi"],
    sealed_fraction=0.20,
    taxon_validation_fraction=0.20,
)
print(result.winning_strategy)
print(result.validation_summary)
```

## Run Product B with the frozen Product-A choice

```bash
sdmr \
  --mode drivers \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --method-choice results/method_v1/method_choice.txt \
  --spatial-test-fraction 0.20 \
  --output-dir results/drivers_v1
```

The driver run writes per-species sealed metrics, selection traces, drop-one results, equivalence groups, group-drop losses, raster summaries, and environmental-process summaries. The Python API additionally exposes repeated discovery/validation taxon splits for testing the stability and transfer of a reduced process core.

## Validation status

The current synthetic/regression suite covers the sealed information barriers, VIF and predictive baselines, model tuning, holdout sensitivity, GBIF/data provenance utilities, correlated-variable substitution, Product-A-to-Product-B strategy inheritance, process aggregation, and unseen-taxon process-core transfer.

A local reconstructed checkout of the current implementation passes **25 tests**. GitHub Actions now runs the core suite across Python 3.10–3.13 plus a Python 3.12 `rasterio` job.

## Current empirical boundary

The statistical architecture and reproducible data adapters are implemented. The project has **not yet established the biological result** on a real broad plant corpus. The next empirical steps are:

1. obtain and fingerprint a real GBIF plant bulk download;
2. resolve and fingerprint the actual CHELSA v2.1/BIOCLIM+ raster files/COGs used by the expanded manifest;
3. compare multiple defensible occurrence-quality, `M`, and target-group-background specifications;
4. run a moderate multi-species Product-A pilot and determine whether the predictive approach truly outperforms VIF/all-variable baselines;
5. freeze the empirically supported Product-A strategy;
6. run repeated large-corpus Product-B process-core discovery/validation and heterogeneity analyses.

Until those real-data tests are complete, SDMR makes a **methodological implementation claim**, not a claim that a universal plant niche core has already been discovered.

See [`docs/method.md`](docs/method.md), [`docs/research_program.md`](docs/research_program.md), and [`docs/data_pipeline.md`](docs/data_pipeline.md).
