# SDMR v3 Finite-Recovery Capacity and Power Audit Plan

**Goal:** Diagnose whether poor finite-sample recovery of ODO-positive process cells is caused primarily by learner function class or by finite-sample information.

**Authoritative target:** ODO v2 from `docs/SDMR_V3_OCCURRENCE_DISTRIBUTION_ORACLE_AUDIT_V2_RESULT.md`.

## Frozen development boundary

- Development-only; Product-A remains closed.
- Reuse only already-burned ecological seeds 23001–23008.
- ODO v2 states are the occurrence-only population target and are not recomputed to favor any finite learner.
- Biological margin remains 0.01; adequacy floor remains -0.75; SEM multiplier remains 1.0.
- No prospective seeds or fresh empirical data are opened.
- Do not change process closures, W1–W8 definitions, or ODO v2 states.
- The audit may introduce new **sampling replicates**, but these are permanently development-only and cannot become prospective evidence.

## Diagnostic design

### A. Capacity comparison at baseline sample size

Compare:
- linear logistic (existing)
- quadratic logistic (existing)
- finite HGB classifier (new, flexible)

at:
- 180 occurrence records
- 600 background records

Primary denominator:
- ODO-positive process cells only.

Guardrails:
- ODO-replaceable cells for false positives;
- ODO-unresolved cells for over-resolution.

### B. HGB sample-size curve

Hold learner class fixed at HGB and vary only:
- 1× = 180 / 600
- 2× = 360 / 1200
- 4× = 720 / 2400

For each ecological world-seed combination, generate deterministic development-only resamples from the exact complete observation distributions with replacement.

Use 3 fixed resampling replicates per sample-size level.

## Task 1 — finite HGB learner

Extend `evaluate_occurrence_processes` with `learner="hgb"`.

Fit:
- `HistGradientBoostingClassifier(loss="log_loss", learning_rate=0.08, max_iter=200, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=1e-3, early_stopping=False, random_state=0)`.
- Equal-prior training weights: total positive weight = total negative weight = 0.5.
- Full and knockout routes use the same fold and hyperparameters.

Tests:
- invalid learner still fails closed;
- HGB route label is `hgb`;
- imbalanced null sample produces score near `-log(2)`;
- deterministic repeated fit.

## Task 2 — exact-distribution resampler

Add development helper:
`resample_world_observations(world, *, n_occurrences, n_background, sampling_seed) -> KnownTruthWorld`.

Requirements:
- environment, true suitability, process registry, spatial groups and ODO target remain unchanged;
- sample occurrence cells with replacement from exact `q_occurrence`;
- sample background cells with replacement from exact `q_background`;
- repeated cell IDs are allowed but each sampled record receives a unique `sample_id`;
- deterministic under the same sampling seed.

## Task 3 — focused denominator audit

Use all W1–W8 world-seeds but score metrics against ODO v2 states:

- positive recovery among ODO `contributory|required`;
- false positive among ODO `replaceable`;
- over-resolution among ODO `unresolved`;
- unavailable rate among ODO-positive cells.

For 1× baseline, compare all three learners.
For 1×/2×/4× sample curve, use HGB only with 3 sampling replicates.

## Task 4 — decision interpretation

Classify the outcome:

- **capacity-limited**: HGB at 1× materially exceeds linear/quadratic at 1×.
- **power-limited**: HGB recovery rises strongly and monotonically from 1× to 4×.
- **evidence-rule-limited**: HGB deltas are positive but interval rules continue to block sharp positive states even at 4×.
- **population-gap-small**: ODO-positive margins are so close to 0.01 that finite recovery remains intrinsically difficult despite HGB and higher n.

No category authorizes threshold tuning. The audit only selects the next method-design target.
