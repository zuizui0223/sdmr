# SDMR v3 Finite Split-Geometry Diagnostic Plan

**Goal:** Determine whether finite HGB failure is caused by learner inadequacy or by requiring spatial extrapolation inside the Stage-P process-identification challenge.

## Frozen boundary

- Development-only; Product-A remains closed.
- ODO v2 remains the population target.
- Reuse only already-burned ecological seeds 23001–23008 and development-only resamples.
- Keep learner hyperparameters, margin=0.01, adequacy floor=-0.75, SEM multiplier=1.0, process closures and sample sizes unchanged.
- Change only inner finite split geometry.
- No prospective seeds or fresh empirical data are opened.

## Split modes

### spatial
Existing behavior:
- GroupKFold on declared spatial groups.
- Remains the default for backward compatibility and v1/v2 reproduction.

### random_cell
New diagnostic:
- take unique sampled `cell_id` values;
- deterministic KFold over unique cell IDs with `shuffle=True, random_state=0`;
- all records sharing a cell ID remain together in one fold;
- duplicate resampled records from the same cell can never occur in both train and test.

This estimates process-information recovery within model-pool covariate support without imposing geographic extrapolation.

## Task 1 — split-mode API

Extend `evaluate_occurrence_processes(..., split_mode="spatial")`.

Evidence records `split_mode`.
Invalid split modes fail closed.

## Task 2 — focused tests

- default `spatial` behavior remains deterministic;
- `random_cell` is deterministic;
- same cell ID never appears in both train and test in random-cell helper;
- W1 seed 23002 HGB full model is adequate under random_cell at unchanged floor -0.75;
- observation-confounded and identical-shared-closure refusal rules remain unchanged.

## Task 3 — burned diagnostic

At baseline sample size 180/600, compare finite states under:
- learner: linear, quadratic, HGB;
- split: spatial, random_cell.

Primary metrics against ODO v2:
- positive recovery;
- ODO-positive unavailable rate;
- false-positive rate among ODO-replaceable cells;
- over-resolution among ODO-unresolved cells;
- mean full score and mean paired delta.

No sample-size curve is rerun until split geometry is diagnosed.

## Interpretation

- If HGB adequacy/recovery improves sharply only under random_cell: Stage-P identification and spatial transfer should be separated.
- If HGB remains inadequate under random_cell: HGB calibration/function class remains the bottleneck.
- If all learners improve under random_cell but positive recovery remains weak: finite information/evidence power is the bottleneck.

No result authorizes threshold tuning.
