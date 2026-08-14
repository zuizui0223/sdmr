# sdmr

**SDMR (Species Distribution Model Raster benchmark)** is an experimental
framework for discovering environmental rasters that carry reproducible plant
niche information across independent space and independent taxa.

The starting problem is simple: SDM predictor screening often treats
multicollinearity (correlation/VIF) as the main gate. That can remove an
ecologically important raster just because another raster is correlated with it,
and it does not answer the question we actually care about: **does this raster
improve prediction where the model has not seen the species?**

SDMR changes the admission rule from *low collinearity* to *out-of-sample
transferability*.

## Core design

- Presence-only friendly: GBIF records are positive evidence, not assumed true
  absences and not treated as calibrated 100% occurrence probability.
- Spatial 50/50 outer holdout: whole occurrence-derived spatial blocks are kept
  untouched for final evaluation.
- Nested selection: raster choice happens only inside the training half using
  spatial GroupKFold CV.
- Correlated rasters compete instead of being deleted by VIF first.
- Cross-taxon 50/50 holdout: a common raster set is discovered in one group of
  species and frozen before testing on unseen species.
- Equal species weighting: widespread, densely sampled taxa do not automatically
  dominate the definition of "common".
- CHELSA v2.1 ready: `configs/chelsa_v2_1_plant_candidates.csv` includes all 19
  BIOCLIM variables plus VPD, growing-season, moisture, radiation, wind, and snow
  candidates.

The primary score is `presence_rank`: the mean percentile rank of held-out
presences against held-out background. `0.5` is random ranking; `1.0` is perfect
separation. A Boyce-style index is reported as a secondary presence-only metric.

## Data contract

Raster extraction is intentionally separated from model benchmarking. Supply two
CSV/Parquet tables with one row per point:

```text
species,longitude,latitude,bio1,bio2,...,vpd,gdd5,...
```

1. `occurrences`: cleaned GBIF plant occurrence coordinates with raster values.
2. `background`: species-specific target-group/background coordinates over the
   accessible area (M), with the same raster columns.

Keeping raster I/O outside the statistical core makes it possible to swap
CHELSA, WorldClim, soil, topography, remote sensing, or future products without
changing the validation logic.

## Run

```bash
pip install -e .
sdmr \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --output-dir results/benchmark_v1
```

Python:

```python
from sdmr import benchmark_taxon_split

result = benchmark_taxon_split(
    occurrences,
    background,
    candidate_predictors=["bio1", "bio4", "bio12", "bio15", "vpd", "gdd5", "cmi"],
    taxon_holdout_fraction=0.5,
    spatial_holdout_fraction=0.5,
)

print(result.common_predictors)
print(result.predictor_aggregate)
print(result.validation_outer)
```

## What this first implementation does *not* claim

It does not yet download the entire GBIF plant corpus or CHELSA rasters. Global
GBIF ingestion, taxonomic cleaning, accessible-area construction, target-group
background generation, and raster extraction are the next data-engineering
layer. The statistical benchmark is implemented first so those later choices
cannot silently contaminate the test protocol.

See [`docs/method.md`](docs/method.md) for the scientific rationale and guardrails.
