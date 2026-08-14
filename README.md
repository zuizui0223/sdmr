# sdmr

**SDMR (Species Distribution Model Raster benchmark)** is an experimental framework with two linked scientific products:

1. **Product A — niche-tuning methodology:** determine which leakage-free tuning procedure best predicts plant occurrences that were never available during model construction.
2. **Product B — universal-driver synthesis:** freeze the validated Product-A procedure, apply it across many plant taxa, and identify environmental dimensions that repeatedly carry important niche information across taxa, regions, and biomes.

The starting problem is that SDM predictor screening often treats multicollinearity (correlation/VIF) as the main gate. A correlated but ecologically informative raster can therefore disappear before anyone asks the more relevant question: **does it improve prediction of genuinely unused occurrences?** SDMR makes out-of-sample predictive information the primary criterion and keeps VIF as a comparison baseline.

## Core information barrier

For each species, occurrence evidence has two roles:

- **model pool** — available for fitting, predictor selection, regularization/complexity tuning, inner spatial CV, and stopping decisions;
- **sealed answer-check pool** — unavailable to all choices above and opened only after a candidate protocol has been frozen.

There is **no scientifically privileged 50/50 split**. The held-out fraction is configurable and should be chosen with sample size and validation strength in mind. When both pools come from one GBIF-like occurrence dataset, SDMR holds out whole spatial blocks rather than random nearby records. Independent later surveys or external records can be used as an even stronger sealed test.

A GBIF presence is positive occurrence evidence, not calibrated probability = 1. Final evaluation therefore asks whether sealed presences receive high relative-suitability scores compared with defensible background/reference locations. The primary current score is `presence_rank`; a Boyce-style index is secondary.

## Product A — implemented tuning benchmark

The current statistical engine compares, without consulting the sealed occurrence pool:

- **all candidate rasters**;
- **conventional VIF-pruned rasters**;
- **nested predictive raster selection** based on model-pool spatial CV;
- regularization and response-complexity settings (`C`, L1/L2, linear vs degree-2 response surface);
- **same-size random raster sets** as a null benchmark.

Each candidate strategy is tuned inside the model pool, frozen, and then evaluated on the sealed spatial occurrence set. `drop_one_importance` measures how much sealed performance is lost when a predictor is removed. `benchmark_holdout_sensitivity` checks that method rankings are not an artifact of one arbitrary test fraction.

A second information barrier operates across species: `benchmark_method_taxon_split` uses one group of plant taxa to choose the winning **method strategy**, then evaluates that already-chosen strategy on plant taxa that were not used to choose it. This separates "a method happened to win in these species" from "the method transfers to new plants".

## Product B — universal and conditional plant niche drivers

After Product A is frozen, the same protocol can be run across a broad plant corpus. A raster should not be called universally important from selection frequency alone. Evidence should combine:

- **selection stability** across species and resamples;
- **incremental gain** when the variable enters;
- **drop-one loss** when it is removed;
- **within-species transfer** to sealed occurrences;
- **cross-taxon transfer** to taxa excluded from common-set discovery;
- **heterogeneity** by clade/family, growth form, biome, range size, and sampling regime.

The intended synthesis is allowed to be hierarchical: a small **global plant niche core**, **global core + conditional biome/clade/life-form drivers**, or no useful universal core. Highly correlated rasters that carry the same information should ultimately be represented as substitutable/equivalence groups rather than forcing an arbitrary winner.

## Candidate rasters

`configs/chelsa_v2_1_plant_candidates.csv` contains the 19 BIOCLIM variables plus VPD, growing-season, moisture, radiation, wind, and snow candidates. Raster I/O is separated from the statistical core so CHELSA, WorldClim, soils, topography, remote sensing, or future products can be compared under the same sealed-test protocol.

## Data contract

Supply occurrence and background/reference tables containing coordinates plus extracted raster values:

```text
species,longitude,latitude,bio1,bio2,...,vpd,gdd5,...
```

1. `occurrences`: cleaned plant occurrence coordinates with raster values.
2. `background`: species-specific sampling-aware background/reference coordinates within a defensible accessible area (M), with the same raster columns.

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

## Run Product B scaffold

```bash
sdmr \
  --mode drivers \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --spatial-test-fraction 0.20 \
  --taxon-validation-fraction 0.20 \
  --output-dir results/drivers_v1
```

## Current boundary

The Product-A statistical engine is implemented and covered by synthetic/regression tests. The next empirical layer is bulk GBIF ingestion and taxonomic cleaning, accessible-area (M) construction, sampling-aware background generation, CHELSA extraction/provenance, and repeated large-corpus runs. Product B already has the cross-taxon predictor-discovery scaffold, but the final universality synthesis still needs correlated-variable equivalence groups and large-scale heterogeneity analysis.

See [`docs/method.md`](docs/method.md) and [`docs/research_program.md`](docs/research_program.md).
