# SDMR fresh empirical v3 — final model and promotion freeze

This document closes the remaining design degrees of freedom **before model fitting and before any answer-check environmental value is opened**.

The final50 cohort was selected prospectively by SoilGrids support availability:
- 80 candidate taxa;
- 65 support-eligible;
- first 50 in the frozen candidate order retained;
- final manifest SHA-256 `4b49f457bcf8b74969e39144789c8e20a3b9739558475290f0a7abf77d7f9359`.

The feature-gate execution may read model-pool/background environmental values, but it cannot alter this contract. A feature-gate failure closes the empirical programme before model fitting.

## Primary empirical comparison

Primary taxon-level outcome:

`balanced log score(SDMR process-first) - balanced log score(matched flat predictive selector)`.

The frozen promotion thresholds are inherited unchanged from the 2026-09-26 planning freeze:
- EMP-A mean gain >= 0.01;
- EMP-B paired 95% bootstrap lower bound > 0;
- EMP-C mean answer-check AUC difference >= -0.02;
- EMP-D stable process fraction >= 0.80;
- EMP-E abstention-integrity violations = 0;
- EMP-F all 50 declared taxa retained.

## Process-first route

Process states are determined only from model-pool data using matched full versus process-closure knockouts.

The two frozen learner routes are:
- L2 logistic, C=1;
- shallow3 HistGradientBoosting.

A sharp process state is stable only when both learners agree. Disagreement remains unresolved.

The primary prediction learner is shallow3 HGB. The process-first predictor set is conservative: a predictor is dropped only when every process it represents is stably replaceable. Shared carriers and any predictor associated with supported, unresolved, or unavailable process information are retained.

Stage-R within-process representation refinement is **not** part of the primary empirical test and cannot rescue it.

## Flat comparators

All use the same primary HGB learner and the same model-pool information:
- forward AUC selector;
- VIF<=5 filter;
- forward balanced-log-score selector (primary comparator).

Forward selectors examine prefixes up to eight predictors under the same inner spatial folds. No answer-check information participates.

## Sealed evaluation

The frozen 5000-row 300-km background is split deterministically:
- rank mod 5 != 0: model-pool training/selection background;
- rank mod 5 == 0: sealed evaluation background.

All SDMR states and all comparator predictor sets are frozen before answer-check occurrence coordinates/features are materialized.

No outcome-dependent taxon replacement, predictor deletion, threshold change, or learner change is allowed.
