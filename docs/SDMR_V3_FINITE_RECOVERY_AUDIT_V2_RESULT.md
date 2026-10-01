# SDMR v3 finite-recovery audit v2 — terminal diagnostic

Status: **development-only terminal result / HGB weight-scale hypothesis rejected / finite split-design diagnostic required / no prospective freeze**

## Frozen execution

- workflow run: `35559380113`
- workflow head: `1b46770fac68978946f0bacccd820c498bb4a592`
- artifact: `sdmr-v3-finite-recovery-audit-v2`
- artifact id: `10622895455`
- artifact digest: `sha256:66ed301693a2aa2e0347e3312c770fc0c581e0551c28b4c2c320f0c67d83cf97`
- ODO target: occurrence-distribution oracle v2
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

Development v2 changed only the absolute scale of HGB class-balancing weights. Class totals remained equal, but total sample weight was restored from 1.0 to the number of training records. All HGB hyperparameters, ecological worlds, ODO targets, margins, adequacy floor and spatial GroupKFold design remained unchanged.

## Result

The weight-scale hypothesis was **rejected**.

At the baseline 180 occurrence / 600 background design:

| learner | positive recovery | ODO-positive unavailable |
|---|---:|---:|
| linear | 0.0625 | 0.0000 |
| quadratic | 0.0000 | 0.15625 |
| HGB | 0.0000 | **1.0000** |

For the 32 ODO-positive cells, HGB mean full balanced log score was approximately **-1.458**, compared with approximately **-0.689** for linear and **-0.720** for quadratic. The unchanged adequacy floor is -0.75.

Thus restoring empirical loss scale did not repair HGB adequacy.

## HGB sample-size curve after weight-scale correction

| multiplier | positive recovery | unavailable | mean full score | mean delta | mean delta SEM |
|---|---:|---:|---:|---:|---:|
| 1x | 0.000 | 1.000 | -1.336 | -0.00187 | 0.0953 |
| 2x | 0.000 | 1.000 | -1.210 | 0.00450 | 0.0718 |
| 4x | 0.000 | 1.000 | -0.956 | 0.01602 | 0.0571 |

More data improves HGB full score and reduces uncertainty, but even 4x remains below the absolute adequacy floor on every ODO-positive audit row.

## Interpretation

The HGB route uses spatial GroupKFold, while tree boosting is an interpolation-oriented learner. The full ODO v2 population oracle already showed that spatial block cross-fitting can confound numerical representation adequacy with spatial extrapolation.

The same confounding remains in the finite learner layer:

```text
process-information recovery
        +
spatial transferability
        are being required simultaneously
```

Linear logistic can extrapolate along covariate gradients and therefore survives this design much more readily than tree boosting. That makes the current learner-capacity comparison structurally asymmetric.

This does not prove that spatial GroupKFold is wrong for final validation. Spatial transfer remains a required downstream property. The issue is whether it should define the **inner process-identification state** itself.

## Decision

**Finite-recovery audit v2 does not identify HGB capacity or sample-size limitation.**

The next diagnostic must hold learner, thresholds, ODO target and samples fixed while changing only inner split geometry:

1. existing `spatial` GroupKFold;
2. deterministic `random_cell` cross-fitting, where unique cell IDs are randomly assigned to folds and repeated observations from the same cell remain in one fold.

If HGB full adequacy is restored under `random_cell`, then process identification and spatial transfer must be separated:

- Stage P: process-information identification within model-pool support;
- outer sealed spatial answer-check: transfer/generalization.

If HGB remains inadequate under `random_cell`, learner calibration/function class remains the cause.

No threshold is changed by this diagnostic and no v2 output is prospective evidence.
