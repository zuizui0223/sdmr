# SDMR v3 Finite Probability-Quality Audit Plan

**Goal:** Explain why finite HGB full-model balanced log score is catastrophically poor even after weight-scale and split-geometry corrections.

## Boundary

- Development-only; Product-A remains closed.
- Reuse only already-burned seeds 23001–23008.
- Worlds: unique_process, interaction, geographic_shift.
- Original baseline sample size only: 180 occurrences / 600 backgrounds.
- Compare learners: linear and HGB.
- Compare split modes: spatial and random_cell.
- Full model only; no process knockout or state assignment is changed.
- No margin, adequacy floor, ODO state, process closure, learner hyperparameter, sample size, or prospective data is changed.

## Metrics per fold

- train balanced log score;
- test balanced log score;
- train ROC AUC;
- test ROC AUC;
- train balanced Brier score;
- test balanced Brier score;
- mean predicted probability by true class;
- prediction q01, q05, q50, q95, q99;
- fraction predictions <0.01 or >0.99;
- train-test log-score gap.

## Interpretation

- high train AUC/log score but poor test AUC/log score: overfitting/generalization failure;
- useful test AUC but poor test log score/Brier with extreme predictions: probability calibration failure;
- poor train and test AUC: learner fitting/representation failure;
- random_cell good but spatial poor: split geometry;
- both HGB modes poor while linear remains stable: HGB route should not be the strong nonlinear learner for prospective SDMR without a separately validated calibration strategy.

No diagnostic result authorizes post-hoc probability calibration for prospective use. Any calibration method would require a new development version with nested calibration that never sees the evaluation fold.
