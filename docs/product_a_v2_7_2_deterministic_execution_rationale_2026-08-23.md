# Product-A v2.7.2 deterministic execution repair — 2026-08-23

## Why v2.7.2 exists

The v2.7.1 scientific design is frozen. Its candidate procedures, prediction-adequacy gate, four ecological recovery dimensions, process domains, M grid, evidence-balanced partition, audit-space rule and six-part empirical decision are not being changed.

The fresh execution exposed a narrower implementation problem: the shared fitting helper uses scikit-learn `LogisticRegression(solver="liblinear")` without an explicit `random_state`. The original monolithic worker and a later M-sharded recomputation therefore execute the same statistical specification with different process-local solver randomness.

This matters for reproducibility. The first strict sharded parity run (`32574696718`) already failed before any sealed environment was opened. A full audit of its preserved artifacts showed:

- shared predictor, partition and audit ledgers were byte-identical;
- `presence_rank` differed only slightly in the inspected worker (maximum absolute difference about `2.33e-4` across the base/knockout tables);
- the four ecological recovery metrics also remained close in that worker;
- reporting metrics that are not fresh-pretruth inputs, especially continuous Boyce, could move more substantially;
- a niche-forward knockout route changed the order in which `bio13` and `gsp` entered the forward path, although the final selected set in that inspected row was the same.

The last point means this cannot responsibly be described as only a CSV floating-point serialization issue. Process boundaries can change the stochastic optimization path.

## Repair boundary

v2.7.2 therefore fixes only execution randomness. `fit_relative_suitability_model` may read the optional environment variable `SDMR_LOGISTIC_RANDOM_STATE`. Historical runs leave it unset and retain the old behavior. The deterministic successor sets it to the predeclared integer `271` before every model-pool and later final-model fit.

The value `271` is a version identifier, not a value selected by ecological or predictive performance. It was fixed while all fresh sealed environmental values and the fresh confirmation outcome remained unopened.

No model family, penalty, C, degree, predictor strategy, ecological metric, AUC guardrail, M definition, taxon panel, split seed, sealed fraction, process rule or decision threshold changes.

## What may be reused

The six existing fresh materialization parts may be reused because they were created before candidate fitting, preserve the already-frozen model/sealed roles, and contain no extracted sealed occurrence or sealed-background environmental values.

Old model-pool worker outputs may not be mixed with v2.7.2. All 72 taxon × part workers and all three M specifications must be recomputed uniformly under the fixed execution seed. No selective repair is allowed.

## Gate before sealed evidence

Before any sealed environment is opened under v2.7.2:

1. ordinary CI must remain green;
2. an independent-process model-pool determinism probe must pass exactly under seed 271;
3. the full 216-shard model-pool build must complete;
4. exactly 72 workers must be reconstructed;
5. all six pretruth parts must freeze;
6. all required final models must be serialized;
7. only then may the frozen sealed audit and unchanged six-part decision run.

Failure at any stage remains a technical or empirical result; the seed, thresholds and candidate set must not be tuned to make the lane pass.

Product B remains blocked.
