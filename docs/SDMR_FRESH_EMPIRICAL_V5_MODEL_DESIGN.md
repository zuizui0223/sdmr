# SDMR fresh empirical v5 — model design freeze

This contract freezes the primary empirical model comparison **before v5 final50 numeric feature results and before model fitting**.

The only deliberately unresolved field is the identity/hash of the final50 cohort. That value may be bound later only if the frozen v5 preeligibility route terminally selects exactly the first 50 jointly eligible taxa. The binding step may not alter model settings, process rules, comparators, promotion thresholds, or denominator rules.

## Frozen primary test

The primary taxon-level outcome remains:

`balanced log score(SDMR process-first) - balanced log score(matched-learner flat predictive selector)`.

EMP-A through EMP-F remain unchanged from the planning freeze:
- EMP-A mean gain >= 0.01;
- EMP-B paired 95% bootstrap lower bound > 0;
- EMP-C mean answer-check AUC difference >= -0.02;
- EMP-D stable process fraction >= 0.80;
- EMP-E abstention-integrity violations = 0;
- EMP-F all 50 taxa retained.

## Process-first route

Process states use only model-pool data. Stage-P uses spatially grouped inner validation, full-vs-process closure knockouts, margin 0.01, adequacy floor -0.75, and the frozen full-system permutation authorization.

Two learner routes remain frozen:
- L2 logistic, C=1;
- shallow3 HistGradientBoosting.

A sharp state counts as stable only when both routes agree. Disagreement remains unresolved.

## Flat comparison

All primary prediction comparisons use the same shallow3 HGB learner and the same model-pool/background information. The primary flat comparator remains forward selection by inner-spatial-CV balanced log score, with at most eight predictors.

## Sealed answer-check order

No answer-check occurrence feature may be materialized until:
1. v5 final50 is bound;
2. the v5 feature gate passes;
3. all model-pool process states and flat predictor selections are complete;
4. those states, predictor sets, and fitted specifications are frozen.

Only then is answer-check materialized once for EMP-A through EMP-F.
