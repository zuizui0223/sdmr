# SDMR v3 HGB Regularization Screen Plan

**Goal:** Select a numerically adequate nonlinear HGB profile using probability quality only, before re-testing process recovery.

**Boundary**
- exploratory development only;
- Product-A closed;
- seeds 23001–23008 already burned;
- worlds: unique_process, interaction, geographic_shift;
- sample size fixed at 180/600;
- split modes: spatial and random_cell;
- no process knockout/state/recovery metric may be used to choose the profile;
- biological margin, adequacy floor, ODO target and process closures are untouched.

## Candidate profiles

All use balanced empirical weights and random_state=0.

1. `current`
   - learning_rate=0.08
   - max_iter=200
   - max_leaf_nodes=31
   - min_samples_leaf=20
   - l2_regularization=0.001
   - early_stopping=False

2. `shallow7`
   - learning_rate=0.05
   - max_iter=100
   - max_leaf_nodes=7
   - min_samples_leaf=40
   - l2_regularization=1.0
   - early_stopping=False

3. `shallow3`
   - learning_rate=0.05
   - max_iter=100
   - max_leaf_nodes=3
   - min_samples_leaf=40
   - l2_regularization=1.0
   - early_stopping=False

4. `early7`
   - learning_rate=0.05
   - max_iter=200
   - max_leaf_nodes=7
   - min_samples_leaf=40
   - l2_regularization=1.0
   - early_stopping=True
   - validation_fraction=0.2
   - n_iter_no_change=10

## Selection estimand

Use only held-out full-model probability quality:

- primary: mean test balanced log score;
- guardrail: every world × split-mode mean test score must be at least -0.75;
- diagnostics: test AUC, balanced Brier, extreme-probability fraction, train-test log-score gap.

Profiles failing the -0.75 world guardrail are ineligible.

Among eligible profiles, choose the highest overall mean test balanced log score. If two profiles differ by <0.005 nats, choose the lower-complexity profile (fewer max leaves; then fewer max iterations).

**Forbidden for selection:** process delta, process state, positive recovery, false-positive rate, ODO agreement.

## After selection

Freeze the selected HGB profile under a new learner name. Only then run a separate finite-recovery v3 audit against frozen ODO v2 states and the unchanged 0.01 process margin.

The regularization screen itself can never be prospective performance evidence.
