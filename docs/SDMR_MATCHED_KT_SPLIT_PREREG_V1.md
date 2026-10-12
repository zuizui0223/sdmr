# SDMR — matched known-truth split study (pre-outcome development benchmark)

**Status (2026-10-12):** frozen question, seed roster and metrics. Original synthetic M5 and real-plant v5 terminal findings remain unchanged. Do **not** reinterpret v5 using this result.

## One question

When sampled occurrences/background, learner families, predictive adequacy rules and entire-process knockout evidence are held fixed, how much do **random-cell interpolation versus geographically grouped extrapolation** alter (i) joint model authorization, (ii) stable sharp information-state coverage, and (iii) recovery of independently assessed occurrence-distribution process-information states?

## Fixed panel and experiment

- **Never-opened seeds:** 91001, 91002, 91003. No replacements.
- **Eight original worlds:** `unique_process`, `redundant_representation`, `shared_carrier`, `null_correlated`, `interaction`, `observation_confounded`, `omitted_driver`, `geographic_shift`.
- 24 declared world × seed cases, each with 1600 environmental cells, 180 sampled occurrences and 600 sampled background cells from the unchanged known-truth world generator.
- **Exactly the same sampled records within each case** for two separate 3-fold CV regimes: (a) KFold on unique cell IDs, seed 0, and (b) GroupKFold by pre-existing geographic groups. Both prohibit exact-cell leakage; only spatial-fold CV attempts geographic transfer.
- Two **frozen** training learners applied to both folds: `StandardScaler` fitted on training data then balanced C=1 isotropic-L2 logistic (`newton-cholesky`, max100, tol1e-10) and shallow3 HGB (100 rounds, 3 leaves, min leaf40, learning rate 0.05, sample-weight balancing).
- Full-system gate for both learners: mean balanced presence-background log score ≥ −0.75, gain over equal-prior constant ≥ 0.01, and one-sided fixed-prediction label-permutation p ≤ 0.001 under 999 fixed-seed within-fold permutations.
- Each ecological information process is challenged by **removing its complete declared representation closure**. Stable state requires both learners to report the same sharp state. Failed fitting, missing fold evidence, learner mismatch, structural identical carrier, unavailable full system or interval uncertainty remain abstentions. No re-tuning and no selection of favorable learners.

## Explicit truth hierarchy (do not collapse)

1. `generating_processes` is the simulation causal mechanism metadata. A generating process may be observationally replaceable or inseparable from a shared carrier.
2. An **occurrence-distribution oracle (ODO) reference state** uses full-cell suitability × sampling-effort knowledge, modeled under a fixed separately computed random-cell reference. It is an *approximate information-state target*, not literal causal truth.
3. Finite empirical-style learners receive only sampled predictor matrices, labels and declared spatial groups. Their fitted states are **persisted and SHA-256 hashed before ODO labels are computed**. No target can affect fits, variable selection, cutoff selection or world inclusion.

Report *positive-state recovery among ODO contributory/required*, *false positive among ODO replaceable*, *over-resolution among ODO unresolved*, *sharp calls among ODO unavailable*, and exact denominators. An absent target group has **undefined (`null`) rate**, not a zero. All 24×6 cells stay in the denominator of both split arms. World-specific and model-specific eligibility are supplementary. No artificial pass threshold is inferred after viewing results.

## Prospective integrity

Scientific design and all target seeds were committed before execution. Burned-seed implementation smoke is permitted but **cannot inform new prospective parameter changes after new-seed opening**. A one-shot execution receipt pins file hashes and is committed independently of a single activation-lock commit. The workflow checks the pinned state and requires exact case coverage; partial worlds, missing seeds and failed numerical certificates cannot be silently excluded. Implementation errors after truth opening are reported as failures, never rescued by seed replacement.

This is a **development benchmark**, not another M5 prospective pass, a new empirical plant validation, a causal recovery demonstration for real plants, or proof that random CV is preferable. Its role is to distinguish split-driven predictive eligibility from closure-inference reliability under genuinely matched simulation settings. In particular, the real-plant 32/60 agreement result is not a ground-truth accuracy estimate.

## Pre-outcome bookkeeping correction

The initial design commit listed 1008 finite fits; corrected before any target seed opening to **2016 = 24 cases × 2 splits × 2 learners × 7 full-or-knockout subsets × 3 folds**. Oracle regression fits are 504 = 24 × 7 × 3. No sampling or scientific condition changed.
