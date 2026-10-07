# SDMR fresh empirical v5 — model-pool failure diagnosis

This is a **post-terminal diagnostic**. It does not rescue fresh v5 and does not alter the frozen EMP-D failure.

## Where the failure occurs

v5 solved the environmental-availability problem prospectively:

- 79/120 candidates passed geometry + all-46 preeligibility;
- the first 50 were frozen;
- all 50 passed the numeric 46-layer feature gate.

The failure appears when the frozen process-identification system is applied to model-pool data.

## Full-system authorization

| route | authorized | unavailable |
|---|---:|---:|
| shallow3 HGB | 32 | 18 |
| penalized logistic | 10 | 40 |
| both routes | 10 | 40 |

Thus 22 taxa contain enough information for the HGB full-system gate but not for the logistic stability route.

Because the frozen stability rule maps an unavailable state on either learner to stable unavailable, these 22 taxa contribute 132 unavailable process cells before route-state agreement is considered.

## Process-state sharpness

Across all 300 taxon × process cells:

- HGB sharp: **125/300 = 0.417**
- logistic sharp: **32/300 = 0.107**
- stable sharp under both routes: **16/300 = 0.0533**

Conditional on each learner's full-system authorization:

- HGB: **125/192 = 0.651** sharp
- logistic: **32/60 = 0.533** sharp

## What happens when both learners authorize

Only 10 taxa are authorized by both routes, giving 60 process cells.

Stable state counts within those 60 cells:

- replaceable: **15**
- contributory: **1**
- unresolved after cross-learner stability: **44**

The largest sources of nonagreement are logistic unresolved / HGB replaceable (15), logistic replaceable / HGB unresolved (10), both unresolved (10), logistic contributory / HGB replaceable (4), and logistic unresolved / HGB contributory (3).

## Important non-rescue result

Dropping the logistic route after seeing this result would be invalid, but it would not rescue EMP-D anyway.

Even HGB alone yields only **125/300 = 0.417** sharp process cells over the declared denominator, still far below the frozen **0.80** EMP-D requirement.

The defensible conclusion is:

> fresh v5 does not support broad stable process attribution in this real 50-taxon cohort under the frozen process-information system.

This does not imply that thermal, water, seasonality, radiation, soil or productivity processes are absent. It means that sharp process-information states are not identified sufficiently often by the declared occurrence–environment representation and evidence rules.

## Consequence for future development

Any successor must be a **new method-development programme**, not a repair of v5. The main open technical question is why route evidence remains interval-indeterminate or learner-dependent in real data despite strong known-truth performance.
