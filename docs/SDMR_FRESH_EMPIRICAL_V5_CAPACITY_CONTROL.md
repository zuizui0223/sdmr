# SDMR fresh empirical v5 — pre-outcome capacity-control amendment

## Why this amendment exists

The frozen v5 primary comparison was designed as:

`SDMR process-first shallow3 HGB - matched-learner flat predictive selector`.

The flat selector is capped at eight predictors. During code review, before the v5 all-46 preeligibility result completed, before numeric final50 features were opened, before model fitting, and before answer-check access, we noticed that the SDMR route can retain more than eight predictors when multiple processes are not stably replaceable.

A positive sealed gain against the <=8-predictor selector could therefore mix two effects:

1. process-aware filtering;
2. simple model-capacity difference.

This is an interpretation problem, not an error in the already-frozen EMP-A–F endpoint.

## Added control

We add one **report-only** route:

**full_46_flat_hgb**

- same shallow3 HGB learner;
- all 46 frozen predictors;
- no predictor selection;
- same model-pool occurrence rows;
- same training background rows;
- same sealed answer-check occurrence rows;
- same sealed evaluation-background rows;
- no refit or reselection after answer-check opening.

## What does not change

The following remain exactly as frozen:

- primary comparator: matched-learner flat predictive selector;
- EMP-A through EMP-F;
- all numerical promotion thresholds;
- final50 denominator;
- process-state algorithm;
- learner hyperparameters;
- answer-check opening order.

Thus the capacity control cannot rescue or overturn the primary promotion decision.

## Interpretation rule

Let

`Delta_capacity = balanced log score(SDMR) - balanced log score(full46)`.

The same 50-taxon denominator is used. If a capacity comparison is unavailable for a taxon, its capacity gain is recorded as zero rather than deleting that taxon.

We report the 20,000-replicate paired taxon bootstrap interval using seed 20260926.

Only if the 95% lower bound is strictly above zero may the empirical result be described as evidence that **process-aware filtering itself improved predictive reconstruction relative to the unfiltered full predictor system**.

If that bound is not above zero, the original EMP-A/B result can still be reported according to its frozen rule, but its wording is limited to:

> SDMR outperformed the predeclared <=8-predictor flat selector.

It must not be described as proof that process-aware filtering outperformed an equally unrestricted flat model.

## Information boundary

This amendment was frozen before:

- final50 numeric feature outcomes;
- any model-pool fit;
- any process state;
- any comparator score;
- any answer-check coordinate;
- any answer-check environmental value;
- any EMP outcome.

It is therefore a pre-outcome interpretability control, not a response to observed model performance.
