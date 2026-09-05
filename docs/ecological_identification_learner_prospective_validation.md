# Prospective validation contract for the ecological-identification learner

Status: **design-only / no scientific run authorized by this document**

This contract exists because the learner was designed after Product A closed. It must not be evaluated on Product-A outcomes and then retrofitted into the Product-A paper.

## Scientific question

Does a sealed, set-valued ecological-identification learner recover process status more faithfully than conventional winner selection while preserving prediction adequacy?

## Information barriers

1. Occurrence identities are split into model-pool versus answer-check whole spatial blocks from coordinates only.
2. Answer-check occurrences cannot influence environmental feature decisions, accessible-area construction, background sampling, learner family, hyperparameters, process taxonomy, proxy/composite closure, adequacy thresholds or stopping.
3. All learner selection and process knockout evaluation occur inside the model-pool using grouped inner spatial CV.
4. A deterministic selection receipt is frozen before answer-check occurrence features are opened for scoring.
5. Known-truth generating-process labels are unavailable to fitting/selection code and opened only by the terminal evaluator.

## Known-truth validation

Use six generating families already defined by the repository, but use **new unused seeds 4101-4120** for each family (120 cases total). These seeds were not found in the repository at contract creation time.

Families:

- Gaussian;
- asymmetric;
- interaction;
- soft threshold;
- omitted driver;
- observation confounded.

### Comparators

- canonical prediction winner selected by mean inner presence-rank/AUC-style discrimination;
- conventional single ecological-recovery winner;
- the new set-valued ecological-identification learner.

No comparator may be altered after truth is opened.

### Primary process criteria

The new learner is scientifically supported only if all of the following hold across the full 120-case denominator:

1. **false-required rate <= 0.02**;
2. **true-process recall >= 0.95**;
3. **process-status macro-F1 >= 0.90** across required/refuted-or-possible states after predeclared mapping;
4. no generating family has true-process recall < 0.85;
5. every reported required-process claim has complete knockout evidence under the frozen route contract.

These thresholds are fixed before execution and are not relaxed after inspection.

### Prediction guardrail

Against the canonical prediction winner on the same cases:

- mean sealed presence-rank difference must be >= -0.02;
- no generating family may have mean difference < -0.05.

Prediction superiority is not required; material predictive degradation is disallowed.

### Determinism

Two independent processes must produce identical:

- admitted baseline model labels;
- process states;
- selection receipts;
- discrete selected predictor/process identities.

Floating summaries must agree to the frozen numerical tolerance declared in the execution receipt.

## Fresh empirical validation

A separate fresh occurrence cohort must be frozen before any answer-check environmental value is opened. Product-A taxa/answer-check rows must not be reused as the decisive empirical endpoint.

Minimum design:

- at least 18 plant taxa spanning at least three predeclared life-form/biome strata;
- whole-spatial-block outer answer-check assigned before M/background construction;
- at least three accessible-area assumptions or another predeclared structural sensitivity axis;
- at least three split seeds;
- conventional prediction winner and new identification learner evaluated on the same answer-check denominator.

### Empirical endpoint

The empirical study does **not** claim literal generating-process truth. It asks whether the new learner produces a distinct, reproducible ecological inference while maintaining answer-check prediction adequacy.

Report, without rescue:

- fraction of matched cells where the learner and prediction winner instantiate different fitted-model/process certificates;
- answer-check presence-rank/Boyce/OR10 differences;
- process-status stability across seeds and structural sensitivity conditions;
- full selector-collapse rate;
- all unresolved/unavailable states.

If all methods collapse to the same selected solution again, record observational equivalence rather than changing the cohort or rules.

## Nature-family promotion rule

The learner should only be added to a Nature-family main claim if:

1. the known-truth primary process criteria pass;
2. prediction guardrails pass;
3. the fresh empirical endpoint yields a genuine predeclared inferential contrast (not necessarily prediction superiority) that is independently observable on sealed answer-check data;
4. the ecological interpretation of that contrast is broader than a software benchmark and matters for how observational ecological models are interpreted.

Otherwise keep Product A as the closed methodological study and route the new learner to a separate methods paper or further development.

## Hard boundary

This document does not authorize a scientific run. No threshold, seed, family, taxon, denominator or comparator should be changed after outcome inspection to obtain promotion.
