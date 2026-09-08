# v10 decorrelation contrast — development plan

## Current problem

v9 distinguishes unique contribution from shared-candidate contribution, but shared candidates remain only partially identified. v10 asks whether an outcome-blind environmental block exists in which the mapping between a target process P and a competing process Q breaks down.

## Frozen separator rule

For every shared-candidate P and competitor Q:

1. use background environments only;
2. use pre-existing spatial block labels;
3. fit P-closure from Q-closure on all but one block;
4. score held-out multivariate R2;
5. call a held-out block a separator candidate only when its R2 is at least 0.10 below the median of the other held-out blocks plus 1 SEM.

No occurrence outcome, suitability score, external biological label, or generating-process truth enters separator selection.

## Development denominator

Seeds 15001–15010 are already consumed by the v6 endpoint and are used only to diagnose separator availability. No number produced here is eligible for prospective performance claims.

## Promotion sequence

1. verify separator availability on consumed cases;
2. only if separators exist, define a contrast that evaluates P and Q within those preselected blocks;
3. freeze the contrast before opening any fresh known-truth denominator;
4. fresh empirical validation remains unauthorized until fresh known-truth validation passes.
