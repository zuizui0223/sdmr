# Context geometry v17 development plan

Status: design handoff only. Development-only; consumed seeds 15001–15010 only.

## Motivation

v16 showed 72 frozen target contexts across 9 cells: 39 context-contributory, 14 context-replaceable, 16 context-unresolved, and 3 insufficient. Target-context variation exceeded source-map variation in all 9 cells. The next question is whether context status can be anticipated from background environmental geometry before inspecting occurrence-based process evidence.

## v17 estimand

Predict target-context attribution state from background-only, process-specific geometry. No occurrence labels, suitability scores, v16 pair outcomes, generating-process truth, or source-map reproduction outcomes may enter the feature extractor.

## Predeclared feature families

For target process P and each held-out target background block, using non-target background rows as the reference environment:

1. conditional residual shift: fit P-closure from non-P ecological predictors on non-target background rows, then summarize target-block residual mean magnitude;
2. conditional residual scale: target residual SD relative to non-target residual SD;
3. conditional reconstruction R2 on the held-out target block;
4. P-closure support shift: standardized target-vs-reference mean displacement over P-closure predictors;
5. conditioning support shift: standardized target-vs-reference mean displacement over non-P conditioning predictors.

All features are computed from background rows only. Retained predictor definitions and process closures are inherited unchanged from v16/v8.

## Evaluation contract

The v16 context labels are used only as development outcomes after background-only features are frozen.

Evaluation is cell-disjoint: all target blocks from one `(family, seed, target_process)` cell are held out together. No block from a held-out cell may contribute to fitting or standardizing a classifier.

Primary development readout:
- 3-class macro-F1 over `context_contributory`, `context_replaceable`, `context_unresolved`, excluding the 3 `insufficient` contexts from supervised fitting/scoring;
- majority-class baseline computed within each training fold and applied to the held-out cell;
- confusion matrix and per-class recall;
- a separate clear-state readout on contributory vs replaceable contexts only.

No threshold tuning on the consumed outcome labels is authorized. Use one fixed multinomial logistic regression with L2 penalty and fixed regularization defaults; all numeric preprocessing is fit within the training fold only.

## Decision rule

v17 is not prospective validation. It answers only whether background geometry contains transferable information about context status under cell-disjoint development evaluation. Fresh known-truth and empirical validation remain unauthorized until a fixed v17 representation and classifier are frozen and audited.
