# Frozen-v5 cause probe: training-only predictor standardization

**Status:** new, exploratory post-terminal method-development programme. This is **not** fresh-v5 empirical promotion and cannot alter its pre-answer-check failure.

## Exact question

The frozen v5 logistic route used 46 raw CHELSA/SoilGrids predictors with L2 penalization (C=1), while HGB used the same 46 environmental representations and spatial validation. Does applying `StandardScaler` fitted **inside each training fold** improve full-system balanced-log-score and authorization for the same logistic model?

## First fixed subset and source barrier

- Rank selection: the first **10** taxa in the independently frozen v5 final50 `selection_rank` ordering. No selection on post-terminal learner outcomes.
- Frozen feature workflow: 37545674411, feature artifact 11453480812; read only three model-pool feature files.
- Frozen occurrence workflow: 37305740628, artifact 11347628679; read only `model_pool_occurrences_v5.csv` to preserve exact spatial blocks. Do not read `outer_split_v5.csv`, answer-check occurrence coordinates, answer-check features or answers.
- Frozen model-pool workflow: 37613738626, artifact 11487215382; use only authorization reference and pre-established taxon ranking.
- Original 46-predictor registry is copied verbatim from `archive/sdmr-fresh-v5-sealed-postterminal`; compare source blob hash 6e3e7fc8d3d46cbd4bb983914beadf315635d45b.

## Three-stage interpretive gate

1. **Baseline replay**: refit the original unstandardized L2 logistic on the same grouped folds and verify the observed mean balanced log score against each archived original. If per-species replay differences exceed 0.001, mark the experiment non-comparable; do **not** interpret standardized gains. Unlike v5, the replay is executed on a new software runtime, so differences are possible.
2. **Controlled intervention**: within each training fold only, fit `StandardScaler` on 46 training predictors, then the otherwise identical balanced C=1 L2 logistic; score the original unchanged validation fold. Compare mean balanced log scores and reproduce the full authorization rule (absolute score >= -0.75, improvement over -log(2) >= 0.01, p <= 0.001 with 999 frozen seed-0 within-fold label permutations).
3. **Scientific boundary**: improvement in full-system authorization does **not** imply recovered true processes, stable closure knockouts, identified causal drivers, or superior sealed prediction. Those are separate questions. In particular, later process-state recomputation would require a *new* prospectively designed development stage, never retroactive v5 recalibration.

## Predeclared report

Report every first10 taxon, both scores, paired differences, full conjunction components, model-pool sample sizes, raw replay match, and cohort counts. Both positive and negative effects are retained. If pilot works, a future independent all50 exploratory analysis may be specified without reclassifying v5 or opening its sealed answer-check.

**Data access requirement:** uses preserved Action artifacts, not externally recollected GBIF records. No labels or outcomes from the frozen answer-check enter model fitting, selection or this output. The global file manifest and frozen SHA-256 inputs are validated at read time.
