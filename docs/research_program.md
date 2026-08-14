# SDMR research program

SDMR is deliberately organized as two linked but distinct scientific products.

## Product A: tuning methodology for accurate plant niche estimation

### Claim target

Develop a reproducible tuning protocol that predicts **sealed, unused plant occurrences** better than conventional predictor-screening workflows.

### Experimental unit

A species with sufficient occurrence records, a defensible accessible area (M), and matched background/reference data.

### Information barrier

Before any model choice, reserve a subset of occurrences as the **answer-check set**. These records are never used for raster selection, regularization, complexity tuning, stopping rules, or choice among candidate settings.

The fraction is not fixed. Report both the fraction and absolute number of spatially independent test occurrences. Sensitivity analysis should verify that method rankings are not an artifact of one arbitrary holdout size.

When method families themselves are compared across species, use a second barrier: discovery taxa may determine which strategy is promoted, but separate validation taxa must remain unavailable until that strategy is fixed.

### Candidate tuning dimensions

- environmental raster subset;
- regularization strength;
- response complexity / feature flexibility;
- background strategy and sampling-bias correction;
- number of predictors / stopping threshold;
- optionally model family, provided comparison remains leakage-free.

### Baselines

At minimum compare the proposed protocol with:

1. conventional correlation/VIF filtering;
2. all candidate variables;
3. same-size random variable subsets;
4. simple biologically motivated standard sets.

### Current implementation

The Product-A engine now implements:

- whole-spatial-block sealed occurrence tests with configurable holdout fraction;
- model-pool spatial CV for every tuning decision;
- all-variable, VIF-pruned, and predictive-forward-selection strategies;
- regularized logistic model tuning over `C`, L1/L2 penalty, and linear/degree-2 response surfaces;
- same-size random-variable null benchmarks;
- sealed-test drop-one predictor loss;
- holdout-fraction sensitivity runs;
- discovery-taxon selection of the winning strategy followed by unseen-taxon validation.

Synthetic and regression tests verify the information barriers and signal recovery. The next test is empirical: whether these advantages persist across real plant species, realistic sampling bias, and alternative accessible-area/background definitions.

### Primary methodological result

A method should be promoted only if its advantage repeats across species, spatial partitions, holdout sizes, and reasonable background definitions. The final claim must be based on validation taxa or external occurrence evidence not used to choose the promoted strategy.

## Product B: universal and conditional drivers of plant niches

### Claim target

Using the frozen Product-A protocol, identify environmental variables that have reproducible importance across a broad and taxonomically/ecologically diverse plant sample.

### Evidence recorded for every raster

- selection stability across species and repeated splits;
- incremental predictive gain when added;
- drop-one predictive loss when removed;
- performance on sealed within-species occurrences;
- transfer to plant taxa excluded from common-set discovery;
- heterogeneity among clades, growth forms, biomes, range sizes, and sampling regimes.

### Universality rule

Do not define a universal driver from selection frequency alone. A strong candidate should repeatedly contribute unique predictive information and should not depend on one dominant taxonomic or geographic stratum.

The preferred end result is hierarchical:

- **global core** — variables with broad cross-plant support;
- **conditional core** — variables consistently important within a biome, clade, growth form, or other ecological stratum;
- **substitutable variables** — correlated alternatives that carry overlapping information and should be reported as an equivalence group rather than forcing one arbitrary winner.

### Current implementation boundary

Cross-taxon predictor discovery and unseen-taxon validation are implemented as a scaffold. Drop-one importance is also available. Before a strong universality claim, the project still needs repeated global taxon splits, correlated-variable equivalence groups, ecological-stratum heterogeneity models, and a fully provenance-tracked GBIF/CHELSA data layer.

## Empirical data layer

The next major workstream is deliberately separate from the statistical core:

1. reproducible GBIF plant admission and taxonomic resolution;
2. coordinate, duplicate, occurrence-status, and basis-of-record filters;
3. defensible accessible-area (M) construction with sensitivity analysis;
4. target-group or otherwise sampling-aware background/reference generation;
5. CHELSA/BIOCLIM+ extraction with version and provenance metadata;
6. repeated method and driver benchmarks with cached fingerprints.

## Separation of the two products

Product B must not be used to redesign Product A after universal-driver results are visible. If Product A changes materially, the global analysis must be rerun under the new frozen protocol.

This separation allows SDMR to make two defensible statements:

1. **methodological** — this procedure estimates relative plant niche suitability more accurately on genuinely unused occurrences;
2. **ecological synthesis** — under that independently validated procedure, these environmental dimensions show the strongest generality in structuring realized plant niche distributions.
