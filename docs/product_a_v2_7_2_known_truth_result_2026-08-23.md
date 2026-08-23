# Product-A v2.7.2 deterministic known-truth result — 2026-08-23

## Frozen execution

The deterministic successor was executed once from implementation
`9b40393dda3d03943a403d0e7875e2d616b914e7` on frozen ref
`frozen/product-a-v2-7-2-known-truth-9b40393d`.

Workflow run `32629842082` evaluated the predeclared six niche families across
unused seeds `3101–3110` (60 cases) in two independent process replicates.
The final decision artifact is `9490827277`, digest
`sha256:033b5393444f0d7365d6823d068e08778454496213f0f438188680740f846a17`.

No empirical sealed environment was read. The current v2.7.1 fresh sealed rows
were not consumed.

## Determinism gate

Decision: **passed**.

The two independent process replicates produced exactly the same discrete and
floating outputs. The frozen comparison tolerance was `rtol=1e-10`,
`atol=1e-10`, but the observed maximum absolute and relative differences were
both **0.0** in every compared table:

| output | rows | floating cells compared | max absolute difference | max relative difference |
|---|---:|---:|---:|---:|
| candidate fold metrics | 7,140 | 173,880 | 0.0 | 0.0 |
| ecological inference certificates | 60 | 360 | 0.0 | 0.0 |
| observation signal summary | 420 | 2,100 | 0.0 | 0.0 |
| selector choices | 180 | 540 | 0.0 | 0.0 |
| selector truth summary | 3 | 42 | 0.0 | 0.0 |
| truth evaluation | 180 | 5,220 | 0.0 | 0.0 |

This resolves the implementation-level reproducibility problem that falsified
v2.7.1 M-shard transport: v2.7.2 has an exact estimator/process RNG identity
across independent processes.

## Scientific non-regression gate

Decision: **supported** under the thresholds frozen before seeds 3101–3110 were
opened.

- robust ecological selector selection coverage: **1.000** (60/60);
- mean stable-process-core precision: **0.9889**;
- mean stable-process-core recall: **0.9833**;
- mean stable-process-core F1: **0.9833**;
- observation-confounded correction activation: **1.000**;
- correction activation in all other niche families: **0.000**.

Every predeclared non-regression check passed. No threshold, random seed,
candidate set or parity tolerance was changed after the outcome.

## Interpretation boundary

This result supports v2.7.2 as a deterministic successor and confirms that the
random-state correction did not erase the previously demonstrated ecological
niche-recovery behavior on new known truth.

It is **not empirical Product-A promotion**. Known truth does not replace the
required fresh plant-data confirmation. Product B therefore remains blocked.

The next empirical lane must use evidence not used in the failed v2.7.1 focal
model pool. The preferred route is the next predeclared taxon rank from the
existing outcome-blind candidate registry, with newly materialized focal and
target-group source artifacts and the v2.7.2 estimator identity frozen before
any sealed outcome is opened.
