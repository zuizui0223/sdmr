# Method: sealed occurrence validation for plant niche tuning

## Scientific questions

SDMR separates two questions that should not be conflated.

### A. Methodological question

> How should predictor choice and model tuning be performed so that a plant SDM
> best predicts occurrences that were completely unavailable during model
> construction?

This is a method-development problem. The target is independent predictive
transfer, not low collinearity by itself.

### B. Empirical synthesis question

> Once that tuning protocol is frozen, which environmental variables repeatedly
> carry important niche information across a broad diversity of plants?

This is a cross-species inference problem. It may reveal a small global core, or
show that universality breaks into clade-, life-form-, or biome-specific drivers.

## Model pool and sealed answer-check pool

Occurrence records are assigned to one of two roles:

1. **model pool** — available for fitting, predictor selection, inner spatial CV,
   regularization/model-complexity tuning, and stopping decisions;
2. **sealed test pool** — unavailable for every choice above and opened only
   after the candidate protocol is frozen.

The split does not need to be 50/50. The fraction is a design choice rather than
a scientific claim. With large occurrence samples a relatively small sealed pool
may give precise validation while preserving most data for fitting; smaller
samples may need a larger fraction or a fixed minimum number of independent test
records. The important invariant is **zero information flow from the sealed pool
into model construction**.

When both pools are generated from one spatial occurrence dataset, hold out whole
spatial blocks rather than random nearby points. When genuinely independent
records exist (for example, later surveys or an external source), those can form
an even stronger sealed test set.

## Why held-out occurrence is not probability = 1

A presence record is strong evidence that a species occurred at that location.
It does not imply that the raster cell has calibrated occurrence probability
1.0, and an unrecorded cell is not a verified absence. SDMR therefore evaluates
whether held-out presences receive high relative-suitability scores compared with
appropriate background/reference locations.

The primary current metric is `presence_rank`; a Boyce-style index is secondary.
The evaluation layer is deliberately separable so additional presence-only
metrics can be added without changing the sealed-test principle.

## Stage A: tune the niche-estimation protocol

For each focal species or methodological benchmark dataset:

1. Reserve the sealed test occurrences before any model choice.
2. Use only the model pool for all tuning.
3. Within the model pool, use spatial folds for predictor selection and model
   complexity/regularization tuning.
4. Allow correlated predictors to compete instead of deleting them solely because
   VIF/correlation is high.
5. Freeze the candidate protocol.
6. Open the sealed occurrences once and quantify final generalization.

At minimum compare:

- all candidate rasters;
- conventional correlation/VIF-pruned subsets;
- nested predictive variable selection;
- alternative complexity/regularization settings;
- same-size random-variable subsets.

The methodological result should report accuracy, calibration/ranking behavior,
predictor count, stability across repeated partitions, and computation cost.

## Stage B: identify broadly important plant niche drivers

Only after Stage A is fixed should the global plant analysis begin. Apply the
same protocol to many taxa without retuning the scientific rules after seeing
which environmental variables win.

For every candidate raster summarize four complementary forms of evidence:

1. **selection stability** — frequency of retention across taxa and resamples;
2. **incremental gain** — improvement when the variable enters a model;
3. **drop-one loss** — degradation when it is removed from a strong reference
   model;
4. **transferability** — persistence of the benefit in independent spatial data
   and, for the strongest universality claim, in taxa not used to define the
   common set.

A variable is stronger evidence for a universal niche driver when all four agree.
Selection frequency alone is insufficient because correlated substitutes can
mask necessity, while a variable can appear often without adding unique
predictive information.

## Cross-taxon validation is separate from occurrence holdout

There are two independent forms of validation:

- **within-species occurrence holdout** tests whether a tuned SDM predicts unseen
  occurrences for the same species;
- **taxon holdout** tests whether an environmental-variable rule learned from one
  set of species transfers to entirely different plant species.

Neither requires a 50/50 division. Their fractions should be declared in advance,
reported, and subjected to sensitivity analysis. Repeated taxon partitions are
preferred to a single lucky split when estimating universality.

## Background recommendation for GBIF

Use target-group background where possible and restrict it to a biologically
defensible accessible area (M) for each focal taxon. This reduces the chance that
the model is rewarded for learning collector effort rather than niche signal.
Sampling-bias controls should be evaluated as part of Stage A because an
apparently superior tuning protocol can otherwise be superior only at reproducing
observation bias.

## Predictor policy

VIF/correlation remain useful diagnostics but are not an admission gate. CHELSA
v2.1 BIOCLIM variables and biologically interpretable extended variables such as
VPD, GDD, growing-season climate, PET/CMI, radiation, wind, and snow can enter the
candidate pool. Predictor importance is earned by independent predictive evidence.

## Interpretation boundary

The methodological output is a validated procedure for estimating *relative
plant niche suitability from occurrence data*. The cross-species output is a set
of *predictively general environmental drivers*. Neither alone proves universal
causal control of fundamental niches.

Universality should therefore be challenged explicitly by clade, growth form,
biome, range size, dispersal context, and sampling density. If a single universal
set fails, the scientifically useful result is a hierarchy such as **global core
+ ecological-stratum-specific drivers**, not a forced global ranking.
