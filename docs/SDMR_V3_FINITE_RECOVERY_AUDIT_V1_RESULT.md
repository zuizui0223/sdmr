# SDMR v3 finite-recovery audit v1 — terminal diagnostic

Status: **development-only terminal result / HGB adequacy failure dominates / capacity-vs-power question not yet identified / no prospective freeze**

## Frozen execution

- workflow run: `35548990766`
- workflow head: `f5b221fc43c25c4bd33bdaf3e4193bbcb1bd6b0b`
- artifact: `sdmr-v3-finite-recovery-audit-v1`
- artifact id: `10618658295`
- artifact digest: `sha256:2b72653122f1759eea1d74a6fd7ae90698cce8661a5ece555d07c991831b8637`
- ODO target: v2, workflow `35495871747`, artifact `10601311224`
- seeds: **23001–23008**, already-burned development evidence
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

The ODO-positive denominator contains **32 process cells**: 8 unique-process thermal, 16 interaction thermal/water, and 8 geographic-shift thermal.

## Baseline learner comparison

| learner | positive recovery | positive unavailable | false positive | over-resolution |
|---|---:|---:|---:|---:|
| linear | **0.0625 (2/32)** | 0.000 | 0.00357 | 0.000 |
| quadratic | **0.0000** | 0.15625 (5/32) | 0.000 | 0.000 |
| HGB | **0.0000** | **1.0000 (32/32)** | 0.000 | 0.000 |

HGB cannot be interpreted as a failed high-capacity recovery method because it never passed the absolute full-model adequacy gate on any ODO-positive cell.

Across all eligible HGB baseline cells, mean full balanced log score was approximately **-1.188**, far below the unchanged adequacy floor **-0.75**.

## HGB sample-size curve

The 1x/2x/4x curve used deterministic development-only resampling and three replicates.

| multiplier | positive recovery | unavailable rate | mean full score | mean delta | mean delta SEM |
|---|---:|---:|---:|---:|---:|
| 1x | 0.000 | **1.000** | -1.163 | 0.0213 | 0.0685 |
| 2x | 0.000 | **1.000** | -1.019 | 0.0321 | 0.0480 |
| 4x | 0.000 | **1.000** | -0.828 | 0.0283 | 0.0323 |

Increasing sample size clearly reduced uncertainty and improved the full score, but even at 4x every ODO-positive cell remained unavailable. Therefore the planned capacity-limited versus power-limited comparison is not identified by v1.

The score trend is informative: the finite HGB estimator is learning with increasing n, but the absolute-score failure dominates state classification.

## Root-cause hypothesis for the next development version

The HGB route balances classes with explicit sample weights

```text
positive weight per row = 0.5 / n_positive
negative weight per row = 0.5 / n_negative
```

so the **total training weight is 1.0**.

By contrast, ordinary scikit-learn fitting and the linear/quadratic `class_weight="balanced"` convention retain a total effective weight on the order of the sample size while balancing the two classes.

Absolute weight scale is not innocuous for HGB because gradient/Hessian mass is compared with fixed regularization such as `l2_regularization=1e-3`. Normalizing the entire empirical loss to total weight 1 can therefore make the same fixed L2 term hundreds or thousands of times stronger relative to the data.

This is a concrete implementation hypothesis for the HGB full-score collapse. It is not yet a proven cause.

## Decision

**Finite-recovery audit v1 does not identify capacity limitation or sample-size limitation.**

Do not change the biological margin 0.01, adequacy floor -0.75, ODO target, process closures, or ecological worlds.

The next admissible development change is narrowly scoped:

1. preserve equal class prior by keeping positive and negative **total weights equal**;
2. rescale total HGB training weight to the number of training records, matching ordinary empirical-risk scale;
3. leave every HGB hyperparameter otherwise unchanged;
4. prove the weight contract with focused tests before rerunning the already-burned finite-recovery audit;
5. record the corrected rerun as a separate development version.

Only after full-model HGB adequacy is restored can the learner-capacity and sample-size questions be interpreted.
