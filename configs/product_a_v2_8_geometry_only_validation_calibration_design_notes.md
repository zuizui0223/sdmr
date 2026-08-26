# Product-A v2.8 geometry-only validation calibration

This stage calibrates validation design only. It is not an ecological confirmation and cannot rescue consumed rank-1/rank-2/rank-3 cohorts.

The 36 historical candidates are used only as a geometry corpus. Allowed information is taxon identity, occurrence and target-group coordinates, fixed M membership, row counts, spatial microblocks, and fold feasibility. Environmental raster values, model fitting, predictive metrics, ecological niche-recovery metrics, selected predictors, fitted coefficients, process outcomes, and sealed ecological outcomes are forbidden.

The inherited evidence-balanced partition algorithm, M=150/300/500 km sensitivity grid, four folds, 12 microblocks, 32 assignment attempts, and row-count thresholds are unchanged. The only calibration axis is the outer sealed fraction, treated explicitly as a validation-design parameter rather than a model/niche tuning target.

A future scientific confirmation must use a new cohort outside these 36 taxa. The future global sealed fraction is frozen before that cohort's ecological outcomes are opened. If the geometry-only calibration cannot identify a robust fraction under the predeclared rule, no scientific confirmation run is launched.
