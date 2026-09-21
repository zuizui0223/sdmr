# SDMR v3 finite probability-quality audit v1 — terminal diagnostic

Status: **development-only terminal result / fixed HGB route overfits catastrophically / regularization screen authorized / no prospective freeze**

## Frozen execution

- workflow run: `35605971767`
- workflow head: `7fa55985bb1137682ce465a9466fd5125b8ca1a3`
- artifact: `sdmr-v3-finite-probability-quality-audit-v1`
- artifact id: `10642578259`
- artifact digest: `sha256:58c79b962ce695b1b137245fb81ca21cb36feaf94181bf8f1388f2b4e8a7a8f0`
- config SHA-256: `80d002f0474f43c18e29ef7cdeb60b7aaa1ee3bd0b70b7033937082ddbb27ba9`
- seeds: **23001–23008**, already-burned development evidence
- worlds: unique_process, interaction, geographic_shift
- learners: linear and fixed HGB
- split modes: spatial and random_cell
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

This audit used full models only. It did not inspect process knockouts or process-recovery outcomes.

## Main result: HGB memorizes the training data

### random_cell

| metric | HGB train | HGB test | linear train | linear test |
|---|---:|---:|---:|---:|
| balanced log score | **-0.0259** | **-1.4008** | -0.6382 | -0.6594 |
| ROC AUC | **1.000** | **0.620** | 0.670 | 0.626 |
| balanced Brier | **0.00132** | **0.3597** | 0.2244 | 0.2339 |
| extreme probability fraction | **0.380** | **0.292** | ~0 | ~0 |

HGB train-test log-score gap: **1.375 nats**.

### spatial

| metric | HGB train | HGB test | linear train | linear test |
|---|---:|---:|---:|---:|
| balanced log score | **-0.0260** | **-1.4694** | -0.6381 | -0.6769 |
| ROC AUC | **1.000** | **0.605** | 0.670 | 0.604 |
| balanced Brier | **0.00134** | **0.3688** | 0.2243 | 0.2419 |
| extreme probability fraction | **0.385** | **0.291** | 0 | 0 |

HGB train-test log-score gap: **1.443 nats**.

The same pattern occurs in every focal world family. Under random_cell, HGB test scores are:

- unique_process: **-1.368**
- interaction: **-1.411**
- geographic_shift: **-1.423**

while the corresponding training scores are all approximately **-0.025 to -0.027** with AUC exactly 1.0.

## Diagnosis

The fixed HGB route is not merely weakly calibrated and is not primarily failing because of spatial extrapolation.

It is **severely overfit**:

1. near-perfect training discrimination and probability score;
2. only modest held-out discrimination (AUC about 0.60–0.64);
3. severe held-out log-score and Brier degradation;
4. roughly 29% of held-out predictions remain near 0 or 1;
5. random_cell splitting does not repair the problem.

This explains why the HGB process challenge was universally `unavailable`: its full-model probabilities themselves fail the absolute held-out adequacy requirement.

The linear route provides an important control. Its held-out AUC is similar to HGB overall, but its probabilities remain moderate and its held-out log score stays close to the null baseline rather than collapsing.

## Decision

**The current fixed HGB configuration is rejected as the prospective strong nonlinear learner.**

Do not repair this by changing the process margin, adequacy floor, ODO target, or process-state rules.

The next development step is the already-frozen HGB regularization screen:

- current;
- shallow7;
- shallow3;
- early7.

Candidate selection uses **full-model held-out probability quality only**. It is forbidden to inspect process deltas or process-recovery rates while choosing the profile.

Every world × split-mode mean test log score must be at least -0.75. Among eligible profiles, select the highest overall held-out log score, with the frozen low-complexity tie break.

Only after that selection is frozen may process recovery be retested.

No probability-quality audit output is prospective evidence.
