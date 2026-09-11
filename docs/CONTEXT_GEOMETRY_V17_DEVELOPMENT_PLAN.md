# Context geometry v17 development plan

## Scope
Development-only successor to v16 using only consumed seeds 15001–15010 and the frozen 9-cell / 72-context v16 denominator. No fresh known-truth or empirical validation is authorized.

## Motivation
v16 showed that process attribution varies primarily with held-out target context rather than the source context used to learn the conditional alignment. v17 asks whether those context states can be anticipated from target-environment geometry before occurrence-based process evidence is inspected.

## Frozen representation
For each held-out target background block, compute only background-derived features:

1. conditional residual shift of process closure P after predicting P from non-P ecological predictors on non-target background rows;
2. conditional residual scale ratio;
3. held-out target conditional reconstruction R2;
4. P-closure support shift;
5. conditioning-predictor support shift.

No occurrence labels, suitability scores, v16 reproduction outcomes, or generating-process truth enter feature construction. Context labels are joined only after geometry has been computed.

## Evaluation contract
- cell-disjoint holdout of all target blocks from one `(family, seed, target_process)` cell;
- fixed `StandardScaler + LogisticRegression(penalty="l2", C=1.0, max_iter=5000)`;
- 3-class macro-F1 over `context_contributory`, `context_replaceable`, and `context_unresolved`;
- `insufficient` contexts excluded from supervised fit/scoring;
- majority-class prediction computed independently inside each training fold;
- separate clear-state contributory-vs-replaceable readout;
- no feature, threshold, or classifier tuning after inspecting consumed outcomes.

## Implementation note fixed before outcome readout
The first family execution exposed an implementation-only singleton-closure shape bug: pandas tuple column selection produced 1D target arrays for one-predictor process closures, while Ridge predictions were 2D, causing `(n, n)` broadcasting. This was repaired by enforcing list-like DataFrame column selection and explicit two-dimensional arrays, with a dedicated singleton-process regression test. No scientific feature, threshold, denominator, or classifier rule changed.

## Promotion boundary
This consumed-development experiment can only establish whether the frozen background geometry representation is worth a fresh prospective test. It cannot support prospective performance claims or empirical process-identification claims.
