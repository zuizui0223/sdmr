# SDMR v3 HGB regularization screen v1 — terminal result

Status: **development-only terminal selection / shallow3 selected / process recovery still unopened at selection time / no prospective freeze**

## Frozen execution

- workflow run: `35608090218`
- workflow head: `882ec259f5801c69575d5edc1daefef70203a27b`
- artifact: `sdmr-v3-hgb-regularization-screen-v1`
- artifact id: `10644928842`
- artifact digest: `sha256:1a07609267cfba8ef443f3a956cf7015a2caf8db65a7af9e63b0a48c3157edaf`
- config SHA-256: `1a48a975ba0fc3fa0a3dec581b251c2f099f887ea4df8bea97ad11ac56acf0a6`
- seeds: **23001–23008**, already-burned development evidence
- worlds: unique_process, interaction, geographic_shift
- split modes: spatial, random_cell
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**
- process recovery used for selection: **false**

## Selection

Probability-quality-only screen result:

| profile | overall mean held-out balanced log score | eligible |
|---|---:|---|
| current | -1.43510 | no |
| shallow7 | -0.70831 | yes |
| shallow3 | **-0.66604** | **yes** |
| early7 | -0.66875 | yes |

Selected profile: **`shallow3`**.

The frozen selection guardrail required every world × split-mode mean test balanced log score to be at least -0.75. `shallow3` passed all six cells:

- random_cell / geographic_shift: -0.64959
- random_cell / interaction: -0.67549
- random_cell / unique_process: -0.64607
- spatial / geographic_shift: -0.67125
- spatial / interaction: -0.69697
- spatial / unique_process: -0.65688

It also had the best overall mean held-out log score. `early7` was within the 0.005-nat tie margin, but `shallow3` is lower complexity and therefore also wins the frozen tie-break.

## Probability-quality repair

Relative to the rejected current HGB route, shallow3 removed the catastrophic overfitting pattern:

- current overall held-out score: about -1.435
- shallow3 overall held-out score: about **-0.666**
- shallow3 extreme-probability fraction: **0** in every world × split cell
- shallow3 train-test log-score gaps: about **0.10–0.12 nats**, rather than about 1.4 nats for current HGB

The selected nonlinear route is therefore numerically adequate for a process-recovery retest.

## Decision

The HGB profile is frozen for the next development retest as:

```text
name = shallow3
learning_rate = 0.05
max_iter = 100
max_leaf_nodes = 3
min_samples_leaf = 40
l2_regularization = 1.0
early_stopping = false
random_state = 0
```

No process-delta, process-state, positive-recovery, false-positive or ODO-agreement result was used to select this profile.

The next admissible step is the already-specified selected-nonlinear recovery retest against frozen ODO v2, with linear and quadratic controls and spatial/random_cell results kept separate.

This screen is development evidence only and cannot establish prospective superiority.
