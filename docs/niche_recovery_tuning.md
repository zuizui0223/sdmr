# Ecological niche-recovery tuning

## Core distinction

SDMR must not be described as a new model-evaluation metric.

AUC, Boyce/CBI, omission rates such as OR10, and information criteria such as
AICc answer different questions about a fitted model or a set of fitted models.
Product-A v2 instead asks whether a **model-building procedure reconstructs the
environmental niche expressed by genuinely unused occurrences and, under
known-truth simulation, the hidden generating niche itself**.

The distinction is therefore:

- **model evaluation**: how well did this prediction/model score under a chosen
  statistical criterion?
- **niche-recovery tuning**: which predictor universe, variable-selection rule,
  regularization and response complexity recover the location, breadth, shape,
  limits and controlling environmental processes of the niche, and keep doing
  so when space, M, sampling bias, environmental domain and taxon change?

The ecological object is therefore not the scalar prediction value itself. The
prediction surface is evidence used to reconstruct an environmental niche and
test ecological hypotheses about its structure.

## What conventional criteria measure

### AUC / presence-rank

Discrimination/ranking: are withheld presences assigned higher values than the
chosen background/reference sample? In presence-background form, SDMR's
`presence_rank` is numerically ROC-AUC with half credit for ties.

### Boyce / continuous Boyce index

Presence-only calibration/consistency: do observed presences become relatively
more frequent as predicted suitability increases? These remain valuable
prediction evaluators, not direct measurements of niche geometry.

### OR10

Threshold-dependent omission: after allowing the 10% lowest-ranked training
presences to fall below the threshold, what fraction of test occurrences are
omitted? It is useful for diagnosing overfitting/transfer failure at a declared
threshold. SDMR implements this as
`metrics.omission_rate_at_training_quantile(..., quantile=0.10)` and keeps it in
the conventional evaluation layer.

### AICc

Information-criterion model selection: balance likelihood/goodness-of-fit against
parameter complexity, with a small-sample correction. AICc is therefore not the
same kind of quantity as AUC, CBI or OR10, and it still does not directly
establish that a model recovered the species' ecological niche.

SDMR must **not** attach a naive AICc to its penalized presence-background
logistic core merely by counting non-zero coefficients. AICc is an admissible
comparator only where the likelihood, sample-size convention and parameter
count/effective degrees of freedom are mathematically defensible (for example a
canonical implementation with a documented information-criterion definition).
Until then it remains an external comparator, not a package objective.

## Why prediction quality and niche recovery can diverge

A model can rank observed geographic presences well while representing the wrong
environmental response surface. This is especially relevant when the fitted
model is later interpreted biologically, transferred to another region/time, or
used to identify important environmental drivers.

Accordingly, a high AUC, CBI, low OR10, or favourable AICc is not sufficient for
SDMR's ecological claim. Those metrics remain comparators and diagnostic
outputs. The decisive methodological experiment is to construct cases in which
candidate procedures have similar prediction scores but recover known niche
structure differently, or in which the highest-scoring predictive model is not
the best niche reconstruction.

## Common audit environmental space

Candidate models must not be allowed to define the environmental space in which
they are judged. A model that selects only convenient variables could otherwise
appear to recover its own niche by construction.

SDMR therefore uses a **common audit environmental basis**:

1. start from the frozen active environmental candidate manifest;
2. fit standardization and PCA using **model-pool background environments only**;
3. never use sealed occurrences to fit the audit transform;
4. project every candidate model and every sealed occurrence into the same audit
   space;
5. use the candidate model's relative-suitability values as weights over the
   model-pool environmental reference distribution.

The resulting weighted environmental distribution is the model-implied realized
niche estimate for audit purposes.

## Ecological recovery profile on real holdouts

`sdmr.niche_recovery.empirical_niche_recovery_profile` reports a multi-axis
profile rather than a single weighted score.

### 1. Niche centroid

`centroid_distance`

Distance between the suitability-weighted predicted centroid and the sealed
occurrence centroid in the frozen audit PC space. This asks whether the model
places the niche optimum/centre in the right environmental region.

### 2. Niche breadth

`breadth_log_sd_error`

Mismatch in environmental spread along audit axes. This asks whether the model
is too general or too narrow even if its geographic ranking is acceptable.

### 3. Niche distribution shape and tails

`quantile_profile_error`

Mismatch of 5%, 25%, 50%, 75% and 95% environmental quantiles across audit axes.
This captures location, asymmetry and tails without requiring a fitted Gaussian
niche.

### 4. Environmental niche overlap

`niche_overlap_schoener_d_pc12`

Schoener D between the model-weighted reference distribution and sealed
occurrence density in the first two frozen audit axes. This follows the broader
environmental-niche-overlap tradition rather than treating map overlap as the
only ecological object.

### 5. Boundary coverage

`sealed_pc12_envelope_coverage90`

Fraction of sealed occurrences inside the model-implied central 90% envelope in
the first two audit axes. It is descriptive and must not be maximized alone,
because an unrealistically broad niche can trivially obtain high coverage.

## Selection rule: procedure, not a new super-score

SDMR v2 does not add the recovery statistics together with arbitrary weights.

`select_niche_recovery_protocol` instead:

1. evaluates each candidate procedure in inner held-out folds;
2. averages each recovery dimension across folds;
3. removes candidates that are Pareto-dominated across the ecological recovery
   dimensions;
4. ranks the remaining Pareto-front candidates separately on each dimension;
5. uses a minimax rule to choose the candidate with the best worst-dimension
   rank;
6. breaks ties by mean recovery rank, then lower complexity.

AUC/CBI/OR10/AICc can be applied as external comparators or explicit guardrails,
but they do not define the ecological recovery target.

## Two evidence tiers

### Tier 1 — known-truth simulation

Real GBIF data cannot reveal the fundamental niche exactly. Product A therefore
needs simulations in which the generating niche is known. Simulations should
vary:

- niche centre and breadth;
- linear/threshold, unimodal, asymmetric and interacting responses;
- correlated environmental predictors and substitutable proxies;
- sampling bias;
- accessible-area truncation;
- spatial autocorrelation and environmental domain shift;
- irrelevant/noise and omitted predictors.

`sdmr.known_truth` now provides the first executable benchmark layer. It can
construct Gaussian, asymmetric, soft-threshold and two-process interaction
niches directly on an empirical environmental reference table (for example
CHELSA-derived environments), sample pseudo-occurrences with an independent
sampling-bias surface, and score a fitted suitability surface against the hidden
truth.

The known-truth recovery profile currently separates:

- `truth_surface_rank`: rank recovery of the complete generating surface;
- `truth_surface_error`: normalized surface-shape error;
- `centroid_error`: error in the environmental niche centre along true process
  axes;
- `breadth_log_sd_error`: error in niche breadth;
- `limit_quantile_error`: error in lower/upper environmental limits;
- process-level precision, recall and F1 for the true generating drivers.

For each simulated species, compare which selector — AUC, CBI, OR10, a
defensible AICc implementation, local nested CV, or niche-recovery tuning —
chooses the model closest to the known generating response/niche distribution.
This is the tier where SDMR can literally evaluate recovery of a known true
niche.

### Tier 2 — real sealed-occurrence transfer

With real plants, make the narrower claim that the procedure recovers a
**realized/accessible environmental niche signal supported by unused occurrence
evidence**.

Require transfer across:

- sealed spatial blocks;
- plausible M/background definitions;
- repeated holdout seeds/fractions;
- sampling-bias alternatives;
- unseen plant taxa and, where possible, shifted environmental domains.

The ecological output is then not just a suitability map but a stable estimate
of where the realized niche lies in environmental space, how broad it is, where
its limits occur, and which environmental dimensions repeatedly control those
features.

## Ecological interpretation product

The final Product-A output should support biological reasoning directly. For
one species or species group, report at least:

1. **environmental process core** — process/equivalence groups repeatedly needed
   for niche recovery, not arbitrary correlated raster winners;
2. **response structure** — direction, unimodality/asymmetry, threshold or
   interaction where supported;
3. **niche centre and breadth** — the environmental optimum/centroid and how
   specialized or broad the reconstructed niche is;
4. **environmental limits/tails** — where the occupied niche thins or terminates,
   with explicit uncertainty/stability across splits and M;
5. **heterogeneity and transfer** — which parts remain universal across taxa and
   which are clade/biome/growth-form dependent.

That is the bridge from tuning to ecology: the method is useful when it changes
or stabilizes conclusions about **what constrains the niche**, not merely when it
adds a few points of predictive score.

## Link to Product B

Product B should inherit only a Product-A procedure that is defensible under
both predictive transfer tests and ecological niche-recovery tests.

Universal-driver analysis should then ask not merely whether removing a raster
reduces AUC, but whether removing an environmental process shifts or degrades:

- niche centroid recovery;
- niche breadth recovery;
- environmental overlap;
- boundary/tail recovery;
- response-shape recovery;
- unseen-taxon/environmental-domain transfer.

This converts variable importance from a map-prediction question into an
ecological question about which environmental processes are necessary for
reconstructing plant realized niches.

## Claim boundary

Presence-only GBIF data do not directly identify the fundamental niche, causal
physiological limits, demographic fitness, dispersal constraints, or biotic
interactions. The empirical claim must therefore remain **realized/accessible
environmental niche recovery** unless independent demographic/physiological
evidence supports a stronger interpretation.
