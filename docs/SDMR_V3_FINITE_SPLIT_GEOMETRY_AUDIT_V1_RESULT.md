# SDMR v3 finite split-geometry audit v1 — terminal diagnostic

Status: **development-only terminal result / spatial-extrapolation hypothesis rejected / HGB probability quality remains the bottleneck / no prospective freeze**

## Frozen execution

- workflow run: `35598252892`
- workflow head: `57fa5d0e3729a1fb9a27fab339967c99add24443`
- artifact: `sdmr-v3-finite-split-geometry-audit-v1`
- artifact id: `10638419419`
- artifact digest: `sha256:402a0baafcd5f967c9b1fd3d434ee07bf8e61b2aef954a7e515d176c8a15dc1f`
- config SHA-256: `5239aa3b56b308c8bd2771b92b93239ea28e2606a9c52f7e9032b41d37eeb92f`
- ODO target: v2, random cross-fit population oracle
- seeds: **23001–23008**, already-burned development evidence
- worlds: unique_process, interaction, geographic_shift
- learner: HGB only
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

The audit changed only the finite inner split geometry.

## Result

| split mode | positive recovery | unavailable | mean full log score | mean delta | mean delta SEM |
|---|---:|---:|---:|---:|---:|
| spatial | 0.000 | 1.000 | -1.458 | -0.0309 | 0.0970 |
| random_cell | 0.000 | 1.000 | -1.404 | -0.0438 | 0.0590 |

Random-cell splitting modestly reduced uncertainty and slightly improved the HGB full score, but **all 32 ODO-positive process cells remained unavailable** under both split geometries.

World-wise random-cell mean full scores were:

- unique_process: **-1.368**
- interaction: **-1.411**
- geographic_shift: **-1.423**

All remain far below the unchanged finite adequacy floor **-0.75**.

## Interpretation

The hypothesis that HGB failed mainly because spatial GroupKFold imposed extrapolation was rejected.

HGB full-model probability quality remains catastrophically worse than the linear and quadratic routes. Earlier finite-recovery audit v2 gave mean full scores near:

- linear: **-0.689**
- quadratic: **-0.720**
- HGB: **-1.458**

Changing only split geometry does not close that gap.

Because balanced log score is a strictly proper probability score, a score around -1.4 can arise from at least two qualitatively different failures:

1. the HGB ranking/discrimination itself is poor on held-out data;
2. discrimination exists but predicted probabilities are overconfident or badly calibrated, causing severe log-loss penalties.

The current audit cannot distinguish these.

## Decision

**Do not change learner hyperparameters, biological margin, adequacy floor, ODO state, or sample size yet.**

The next development step is a probability-quality diagnostic on the same burned HGB fits. It must record, for full models under both spatial and random_cell splits:

- train and test balanced log score;
- test ROC AUC;
- test balanced Brier score;
- prediction quantiles and fraction near 0 or 1;
- class-wise mean predicted probability;
- train-test score gap.

Interpretation:

- high train score + poor test score + poor AUC => ordinary overfit/function-class failure;
- useful AUC + poor log score/Brier + extreme predictions => calibration failure;
- poor AUC under both train and test => representation/fitting failure;
- strong random_cell but weak spatial => split geometry would be reconsidered, but current aggregate evidence does not support this.

No current split-geometry result may be used as prospective evidence.
