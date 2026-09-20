# SDMR v3 Occurrence-Distribution Oracle v2 Correction Plan

**Goal:** Correct the numerical oracle so population identifiability is not confounded with spatial extrapolation.

**Predecessor:** `docs/SDMR_V3_OCCURRENCE_DISTRIBUTION_ORACLE_AUDIT_V1_RESULT.md`

## Frozen development boundary

- Development-only; Product-A remains closed.
- Reuse only already-burned seeds 23001–23008.
- Keep W1–W8, n_cells=1600, n_splits=3, margin=0.01, adequacy floor=-0.75, SEM multiplier=1.0 and Bayes-regret tolerance=0.01 unchanged.
- Keep the exact complete observation distributions and HGB numerical function class unchanged.
- Change exactly one estimand-alignment element: oracle cross-fitting from spatial GroupKFold to deterministic random KFold.
- Existing v1 default behavior remains available as `split_mode="spatial"`; v2 uses `split_mode="random"`.
- No prospective seed, fresh empirical datum, biological threshold, or finite learner is changed.

## Task 1 — split-mode contract

Add `split_mode: Literal["spatial","random"] = "spatial"` to `evaluate_occurrence_oracle_states`.

- `spatial`: existing GroupKFold on `world.spatial_groups`.
- `random`: `KFold(n_splits=n_splits, shuffle=True, random_state=0)` over complete environment cells.
- invalid values fail closed.
- evidence records `split_mode`.

## Task 2 — regression tests

Tests must show:

- spatial default remains deterministic;
- random mode is deterministic;
- W1 seed 23002, which was numerically unavailable under v1 spatial cross-fit, becomes numerically adequate under random cross-fit;
- W7 omitted_driver remains unavailable under random cross-fit at the unchanged 0.01 regret tolerance;
- identical shared-carrier abstention and W6 observation nonseparability remain unchanged.

## Task 3 — v2 burned audit

Create a separate config/workflow using the same v1 profile except:

`occurrence_oracle.split_mode = "random"`.

Outputs and three-level crosswalk remain identical.

## Task 4 — terminal comparison

Record v1 → v2:

- number of numerically inadequate world×seed cases;
- ODO unavailable cells;
- truth-positive → ODO-positive fraction;
- ODO-positive finite recovery by learner;
- ODO state changes by world/process;
- any new false-positive or over-resolution behavior.

Do not freeze prospective thresholds from v2.
