# SDMR v3 selected nonlinear recovery v1 — terminal development result

Status: **development-only terminal result / shallow3 recovers positive process information / finite-sample uncertainty remains limiting / no prospective freeze**

## Frozen execution

Primary full execution:

- workflow run: `35946188585`
- workflow head: `4e1853b46235ced24f57fc72b10d70e906284c54`
- artifact: `sdmr-v3-selected-nonlinear-recovery-v1`
- artifact id: `10787697930`
- artifact digest: `sha256:c37d027f1286e0d2a8c45a09ae58c57c03dd2ce65808f64358e53ce0267bda76`
- config SHA-256: `999363f4096627aa3297352ce2b8de67f89e650448c75985a4b993a3e3e9738f`
- ODO v2 state hash: `966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d`
- HGB probability-quality-selected profile: **shallow3**
- screen workflow: `35608090218`
- screen artifact: `10644928842`
- screen artifact digest: `sha256:1a07609267cfba8ef443f3a956cf7015a2caf8db65a7af9e63b0a48c3157edaf`
- process recovery was forbidden during profile selection
- seeds: **23001–23008**, already-burned development evidence
- worlds: all W1–W8
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

A later sharded duplicate execution (`35947953779`) reproduced each learner × split result and is treated as an execution duplicate, not an independent denominator.

## Main result

The probability-quality-screened nonlinear learner is the first finite learner to recover a substantial fraction of ODO-positive process information.

There are **32 ODO-positive process cells**.

| learner | split | positive recovery | unresolved among positives | unavailable among positives | false-positive rate | over-resolution |
|---|---|---:|---:|---:|---:|---:|
| shallow3 HGB | spatial | **13/32 = 0.40625** | 0.53125 | 0.000 | 0.01786 | 0.000 |
| shallow3 HGB | random_cell | **8/32 = 0.25000** | 0.68750 | 0.000 | 0.00357 | 0.000 |
| linear | spatial | 2/32 = 0.06250 | 0.37500 | 0.000 | 0.00357 | 0.000 |
| linear | random_cell | 7/32 = 0.21875 | 0.25000 | 0.000 | 0.00000 | 0.000 |
| quadratic | spatial | 0/32 = 0.00000 | 0.46875 | 0.15625 | 0.00000 | 0.000 |
| quadratic | random_cell | 3/32 = 0.09375 | 0.40625 | 0.000 | 0.00000 | 0.000 |

The selected HGB profile therefore changes the earlier conclusion: nonlinear process recovery is possible once the probability model is regularized using an outcome-blind full-model screen.

## HGB process-specific recovery

### Spatial split

- unique-process thermal: **3/8 = 0.375**
- interaction thermal: **2/8 = 0.250**
- interaction water: **5/8 = 0.625**
- geographic-shift thermal: **3/8 = 0.375**

### Random-cell split

- unique-process thermal: **2/8 = 0.250**
- interaction thermal: **2/8 = 0.250**
- interaction water: **3/8 = 0.375**
- geographic-shift thermal: **1/8 = 0.125**

The nonlinear gain is therefore not confined to the interaction world: shallow3 also recovers unique-process and geographic-shift thermal information.

## Evidence scale

For ODO-positive cells, shallow3 HGB produced:

- spatial mean paired delta: **0.01851**, mean SEM **0.01018**
- random_cell mean paired delta: **0.01616**, mean SEM **0.01100**

The biological margin remains **0.01**.

These values explain the remaining failure pattern. The average effect is above the margin, but uncertainty is of the same order as the excess above the margin. Consequently:

- spatial: **17/32** positives remain unresolved;
- random_cell: **22/32** remain unresolved.

This is now primarily an interval/power problem rather than a universal learner-adequacy failure.

## Safety

Shallow3 did not over-resolve any of the **24 ODO-unresolved cells**.

False positives among **280 ODO-replaceable cells** were:

- spatial: **5/280 = 0.01786**
- random_cell: **1/280 = 0.00357**

This is higher than linear under spatial splitting but still low in absolute terms. It must remain an explicit prospective safety gate; it cannot be averaged away in exchange for higher positive recovery.

## Split interpretation

The spatial and random-cell results must not be collapsed into one score.

- `random_cell` estimates within-support finite process identification.
- `spatial` additionally challenges geographic transfer.

Unexpectedly, shallow3 recovery is higher under the frozen spatial denominator than random_cell. This is a development property of these finite seeds, not evidence that spatial splitting is intrinsically easier. The two remain separate design axes.

## Decision

**The selected shallow3 HGB route is retained in the candidate learner panel.**

The following development conclusions are now supported:

1. the old HGB failure was caused by an overfit learner profile, not by nonlinear learners as a class;
2. outcome-blind probability-quality screening can produce a numerically adequate nonlinear route;
3. that route recovers substantially more ODO-positive process information than the previous HGB and, under the spatial denominator, more than the linear/quadratic controls;
4. remaining failures are dominated by unresolved positive cells with paired deltas near or above the 0.01 margin but uncertainty of comparable magnitude.

The method is **not yet ready for prospective freezing** because positive recovery is still only 0.406 spatial / 0.250 random_cell at the baseline sample size.

## Next admissible diagnostic

Run a **shallow3-only sample-size curve** against the frozen ODO v2 target, separately for spatial and random_cell splits:

- 1x = 180 occurrences / 600 backgrounds;
- 2x = 360 / 1200;
- 4x = 720 / 2400;
- fixed development-only resampling replicates;
- unchanged margin, floor, closure, ODO state and shallow3 profile.

Primary question:

> Does positive recovery increase as SEM falls, while false-positive and over-resolution guardrails remain controlled?

If recovery rises strongly with n, the remaining limitation is finite information/power and the prospective design can be powered accordingly. If recovery plateaus despite shrinking SEM, the evidence/state rule or process gap itself remains limiting.

No current result is prospective evidence.
