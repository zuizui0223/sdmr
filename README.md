# sdmr

**SDMR (Species Distribution Model Raster benchmark)** is an experimental
framework with two linked research goals:

1. **Method development** — develop and validate a tuning strategy that estimates
   plant niches as accurately and transferably as possible from presence-only
   occurrence data.
2. **Universal driver discovery** — apply the frozen best-performing protocol
   across many plant species to identify environmental variables that repeatedly
   carry important niche information across taxa, regions, and biomes.

The starting problem is simple: SDM predictor screening often treats
multicollinearity (correlation/VIF) as the main gate. That can remove an
ecologically important raster just because another raster is correlated with it,
and it does not answer the question we actually care about: **does this variable
improve prediction of occurrences that were never used to build or tune the
model?**

SDMR therefore changes the main admission rule from *low collinearity* to
*out-of-sample predictive information*.

## Core design: model occurrences vs sealed answer-check occurrences

The occurrence data are divided into two roles:

- **model pool**: may be used for fitting, predictor selection, and tuning;
- **sealed test pool**: never used for fitting, predictor selection, stopping,
  hyperparameter choice, or model comparison until the final evaluation.

There is **no scientifically privileged 50/50 split**. The test fraction is a
design parameter and should depend on sample size and the strength of the desired
validation. The current CLI defaults to 20% as a practical starting point, but
10/90, 20/80, 30/70, fixed-count holdouts, or externally collected test records
can all be valid if declared in advance and kept untouched.

Whenever records come from one occurrence pool, SDMR holds out **whole spatial
blocks**, rather than random nearby points, so spatial autocorrelation cannot make
the answer-check artificially easy.

GBIF records are positive occurrence evidence, not calibrated probability = 1.
Final performance therefore asks whether sealed occurrences receive higher
relative-suitability scores than defensible background/reference locations.

## Research output A — plant SDM tuning methodology

Inside the model pool only, SDMR can compare candidate raster sets and tuning
choices with spatial cross-validation. The outer sealed occurrences remain hidden
until a candidate protocol is frozen.

The methodological target is not merely "low VIF" or "few predictors". It is a
protocol that maximizes independent predictive transfer while controlling model
complexity and avoiding leakage.

Benchmarks should compare at least:

- all candidate rasters;
- conventional correlation/VIF-pruned rasters;
- nested predictive raster selection;
- alternative model complexity / regularization settings;
- same-size random raster sets as null controls.

## Research output B — universal environmental drivers of plant niches

After the tuning protocol is frozen, run it across a broad plant corpus. A
candidate variable should be considered broadly important only when evidence is
stable across repeated species samples and independent spatial tests.

For each raster, retain more than raw selection frequency:

- **selection stability** — how often it survives tuning across species/resamples;
- **incremental gain** — how much prediction improves when it is added;
- **drop-one loss** — how much prediction worsens when it is removed from an
  otherwise strong model;
- **cross-taxon transfer** — whether the signal persists in species not used to
  define the common set;
- **heterogeneity** — whether importance changes by clade, growth form, biome,
  range size, or sampling density.

This allows the empirical result to be either a genuinely small **global plant
niche core** or a more realistic hierarchy such as **global core +
clade/biome-specific drivers**.

## Candidate rasters

`configs/chelsa_v2_1_plant_candidates.csv` includes the 19 BIOCLIM variables plus
VPD, growing-season, moisture, radiation, wind, and snow candidates. Raster I/O
is separated from the statistical benchmark so CHELSA, WorldClim, soils,
topography, remote sensing, or future products can be compared under the same
sealed-test logic.

## Data contract

Supply occurrence/background tables containing coordinates and extracted raster
values:

```text
species,longitude,latitude,bio1,bio2,...,vpd,gdd5,...
```

1. `occurrences`: cleaned plant occurrence coordinates with raster values.
2. `background`: species-specific target-group/background coordinates over a
   defensible accessible area (M), with the same raster columns.

## Run

```bash
pip install -e .
sdmr \
  --occurrences data/occurrences.parquet \
  --background data/background.parquet \
  --predictors configs/chelsa_v2_1_plant_candidates.csv \
  --spatial-test-fraction 0.20 \
  --taxon-validation-fraction 0.20 \
  --output-dir results/benchmark_v1
```

Python:

```python
from sdmr import benchmark_taxon_split

result = benchmark_taxon_split(
    occurrences,
    background,
    candidate_predictors=["bio1", "bio4", "bio12", "bio15", "vpd", "gdd5", "cmi"],
    spatial_holdout_fraction=0.20,   # configurable sealed occurrence test
    taxon_holdout_fraction=0.20,    # separate question: cross-species transfer
)
```

The two fractions serve different purposes. `spatial_holdout_fraction` protects
the within-species answer-check occurrences. `taxon_holdout_fraction` is only for
the stronger empirical claim that a common variable set transfers to plant taxa
not used to discover it.

## Current scope

The statistical benchmark is implemented first. Global GBIF ingestion, taxonomic
cleaning, accessible-area construction, target-group background generation, and
CHELSA extraction are the next data layer and must not change the sealed
validation protocol after results are inspected.

See [`docs/method.md`](docs/method.md) and
[`docs/research_program.md`](docs/research_program.md).
