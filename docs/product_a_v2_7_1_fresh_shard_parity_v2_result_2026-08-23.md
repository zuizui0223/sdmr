# Product-A v2.7.1 fresh sharded parity v2 result — 2026-08-23

## Frozen technical result

The second sealed-blind sharded parity run `32614371301` executed from
`3e578e14f2949662b64206ee959ee571e52cced2` on frozen ref
`frozen/product-a-v2-7-1-fresh-sharded-parity-v2-3e578e14`.

All three M-specific shard jobs completed successfully for the predeclared
reference worker (`taxon10`, seed `2026082201`, sealed fraction `0.30`). The
shared predictor-coverage, evidence-balanced partition, audit-space and row-to-
fold ledgers remained exact. No sealed environmental value was opened.

The aggregate comparison nevertheless failed under the predeclared parity-v2
contract. The failure was **not** a floating value outside the fixed `5e-4`
envelope. A nonnumeric scientific output changed: one of 96 compared fold rows
had a different `selected_predictors` value. The first reported difference was:

- reference: `ngd5,bio2,bio16,bio6,ngd10,scd,rsds`
- independent-shard reconstruction: `ngd5,bio2,bio16,bio6,ngd10,scd`

Thus independent M-process execution can change a forward-selection decision in
the frozen v2.7.1 implementation.

## Interpretation

The frozen fitting helper uses scikit-learn `liblinear` with
`random_state=None`. The first parity experiment had already shown small
floating model-output differences across independent processes. The second
experiment now demonstrates that those differences can cross a selection
boundary and change a discrete predictor set.

Therefore the hypothesis that M-sharding is a purely technical, semantics-
preserving transport of the original v2.7.1 worker is falsified.

## Stop rule

Do not rescue v2.7.1 by:

- widening the numerical parity tolerance;
- treating selected-predictor differences as ignorable;
- selectively rerunning only timed-out primary workers;
- launching the proposed 216-shard build under an unchanged-science claim;
- changing the estimator and then opening the already prepared v2.7.1 fresh
  sealed outcomes.

The fresh v2.7.1 empirical lane is frozen as a **sealed-unopened technical
failure**. It neither supports nor rejects the ecological niche-recovery method,
does not promote Product A and does not unblock Product B.

## Successor

Product-A v2.7.2 separately freezes an explicit estimator random state while
preserving historical unseeded ModelSpec behavior for earlier frozen versions.
The deterministic successor must first pass a new known-truth reproducibility
and ecological non-regression gate on unused seeds, then obtain genuinely new
empirical confirmation evidence before any promotion claim.
