# Ecological niche-recovery tuning

## Core distinction

SDMR must not be described as a new model-evaluation metric.

AUC, Boyce/CBI, omission rates such as OR10, and information criteria such as
AICc answer different questions about a fitted model or a set of fitted models.
Product-A v2 instead asks whether a **model-building procedure reconstructs the
environmental niche expressed by genuinely unused occurrences and, in
known-truth experiments, the hidden generating niche itself**.

The distinction is therefore:

- **model evaluation**: how well did this prediction/model score under a chosen
  statistical criterion?
- **niche-recovery tuning**: which predictor universe, variable-selection rule,
  regularization and response complexity recover the location, breadth, shape,
  limits and controlling environmental processes of the niche, and keep doing
  so when space, M, sampling bias, environmental domain and taxon change?

The prediction surface is therefore an intermediate object, not the final
scientific target. The target is an ecologically interpretable niche structure
that remains recoverable under independent information barriers.

## What conventional criteria measure

Conventional model criteria live separately from ecological recovery. In the
current implementation, OR10 and the AICc formula helper are in
`sdmr.model_criteria`; AUC-equivalent presence rank and Boyce/CBI remain
prediction diagnostics. None of them defines Product-A v2's ecological target.

### AUC / presence-rank

Discrimination/ranking: are withheld presences assigned higher values than the
chosen background/reference sample? In presence-background form, SDMR's
`presence_rank` is numerically ROC-AUC with half credit for ties.

### Boyce / continuous Boyce index

Presence-only calibration/consistency: do observed presences become relatively
more frequent as predicted suitability increases? These remain valuable
prediction evaluators, not direct measurements of niche geometry.

### OR10

Threshold-dependent omission: after defining a threshold that excludes the 10%
lowest-scoring training presences, what fraction of independent test occurrences
falls below that threshold? It is useful for diagnosing overfitting/transfer
failure at a declared threshold. SDMR exposes this in the conventional model
criteria layer as
`sdmr.model_criteria.omission_rate_at_training_quantile(...,
training_omission_fraction=0.10)` and the `or10(...)` wrapper. It is not a
niche-recovery objective.

### AICc

Information-criterion model selection: balance likelihood/goodness-of-fit against
parameter complexity, with a small-sample correction. AICc is not the same kind
of quantity as AUC/CBI/OR10, and a favourable AICc still does not directly
establish that the resulting model recovered the species' ecological niche.

`sdmr.model_criteria.corrected_aic` implements the mathematical AICc correction
when the caller supplies a valid log likelihood, defensible parameter/effective-
degrees-of-freedom count, and sample size. SDMR deliberately does **not** infer
those quantities from its class-balanced penalized presence-background logistic
core or manufacture a MaxEnt-style AICc by simply counting coefficients. AICc is
therefore an admissible comparator only for model families/configurations where
those inputs are justified.

## Why prediction quality and niche recovery can diverge

A model can rank observed geographic presences well while representing the wrong
environmental response surface. This is especially relevant when the fitted
model is later interpreted biologically, transferred to another region/time, or
used to identify important environmental drivers.

Accordingly, a high AUC, CBI, low OR10, or favourable AICc is not sufficient for
SDMR's ecological claim. Those metrics remain comparators and diagnostic
outputs. A central Product-A v2 benchmark must explicitly search for cases where
candidate procedures have similar conventional scores but different known-truth
niche recovery, and cases where the highest-scoring predictive model is not the
best ecological reconstruction.

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

## Ecological recovery profile

`sdmr.niche_recovery.empirical_niche_recovery_profile` currently reports a
multi-axis profile rather than a single weighted score.

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

`sdmr.niche_recovery_cv.cross_validated_niche_recovery` deliberately emits the
conventional diagnostics (`presence_rank`, continuous Boyce and OR10) beside the
ecological recovery profile. `benchmark_niche_recovery_candidates` then chooses
the procedure from the ecological recovery dimensions, not from those
conventional scores. This makes the distinction executable rather than merely
terminological.

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

The repository now has a first executable known-truth layer in
`sdmr.known_truth`. `simulate_gaussian_plant_niche` generates an explicit
temperature-water niche with an interaction, a correlated temperature proxy,
an irrelevant variable, and a spatial sampling-effort process. Target-group
records follow sampling effort while focal occurrences follow ecological
suitability × sampling effort. `known_truth_niche_recovery_profile` then compares
a candidate prediction directly with the hidden generating niche in a common
environmental audit space.

`sdmr.known_truth_benchmark.benchmark_selectors_against_known_truth` makes the
critical contrast explicit. Candidate procedures are selected without access to
truth by three routes:

- maximum inner AUC-equivalent presence rank;
- maximum inner continuous Boyce index;
- Pareto + minimax ecological niche-recovery tuning.

OR10 remains in the fold table as an omission/overfitting diagnostic. AICc is
intentionally not manufactured for the current class-balanced penalized logistic
family. After each selector has made its choice, all selected procedures are fit
and evaluated against the same hidden generating niche. The scientific test is
therefore **which selection rule recovers the biological target**, not which rule
wins its own validation statistic.

The existing known-truth profile evaluates environmental overlap, niche-centre
error, breadth error, quantile/tail error, and how much true niche mass falls
inside the predicted envelope. The next benchmark expansion should add
asymmetric/threshold families, omitted-driver cases, stronger domain shifts,
response-shape recovery, and explicit process-group recovery so correlated
raster aliases are not mistaken for different ecological mechanisms.

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

Product A should return an ecological interpretation layer in addition to maps
and conventional scores. For each species or species group, the target output is:

1. **environmental process core** — process/equivalence groups repeatedly needed
   for niche recovery, rather than arbitrary correlated raster winners;
2. **response structure** — direction and support for unimodality, asymmetry,
   thresholds or interactions;
3. **niche centre and breadth** — where the reconstructed niche is centred and
   how specialized/broad it is;
4. **environmental limits/tails** — where occupancy support thins or terminates,
   with stability across splits and M rather than a single fitted boundary;
5. **heterogeneity and transfer** — which constraints are stable across taxa and
   which are clade/biome/growth-form dependent.

This is the bridge from tuning to ecology: SDMR matters when the tuning procedure
changes or stabilizes conclusions about **what constrains the niche**, not merely
when it increases a predictive score.

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
