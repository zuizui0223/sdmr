# SDMR research program

SDMR is deliberately organized as two linked but distinct scientific products.

## Product A: tuning methodology for accurate plant niche estimation

### Claim target

Develop a reproducible tuning protocol that predicts **sealed, unused plant
occurrences** better than conventional predictor-screening workflows.

### Experimental unit

A species with sufficient occurrence records, a defensible accessible area (M),
and matched background/reference data.

### Information barrier

Before any model choice, reserve a subset of occurrences as the **answer-check
set**. These records are never used for raster selection, regularization,
complexity tuning, stopping rules, or choice among candidate methods.

The fraction is not fixed. Report both the fraction and absolute number of
spatially independent test occurrences. Sensitivity analysis should verify that
method rankings are not an artifact of one arbitrary holdout size.

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

### Primary methodological result

A method should be promoted only if its advantage repeats across species,
spatial partitions, holdout sizes, and reasonable background definitions. Final
sealed-test results should be reported once per pre-specified candidate protocol,
not repeatedly inspected during development.

## Product B: universal and conditional drivers of plant niches

### Claim target

Using the frozen Product-A protocol, identify environmental variables that have
reproducible importance across a broad and taxonomically/ecologically diverse
plant sample.

### Evidence recorded for every raster

- selection stability across species and repeated splits;
- incremental predictive gain when added;
- drop-one predictive loss when removed;
- performance on sealed within-species occurrences;
- transfer to plant taxa excluded from common-set discovery;
- heterogeneity among clades, growth forms, biomes, range sizes, and sampling
  regimes.

### Universality rule

Do not define a universal driver from selection frequency alone. A strong
candidate should repeatedly contribute unique predictive information and should
not depend on one dominant taxonomic or geographic stratum.

The preferred end result is hierarchical:

- **global core** — variables with broad cross-plant support;
- **conditional core** — variables consistently important within a biome, clade,
  growth form, or other ecological stratum;
- **substitutable variables** — correlated alternatives that carry overlapping
  information and should be reported as an equivalence group rather than forcing
  one arbitrary winner.

## Separation of the two products

Product B must not be used to redesign Product A after the universal-driver
results are visible. If the tuning method is changed materially, the global
analysis must be rerun under the new frozen protocol.

This separation is what allows SDMR to make two defensible statements:

1. **methodological** — this procedure estimates plant niche suitability more
   accurately on genuinely unused occurrences;
2. **ecological synthesis** — under that validated procedure, these environmental
   dimensions show the strongest generality in structuring realized plant niche
   distributions.
