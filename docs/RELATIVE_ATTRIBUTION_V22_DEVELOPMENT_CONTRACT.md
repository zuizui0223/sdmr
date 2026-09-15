# Relative attribution v22 — development contract

## Scope

Development only on consumed v21 seeds 17001–17010. This stage cannot authorize fresh empirical validation.

## Frozen denominator

The pair denominator is derived mechanically from the authoritative v21 terminal artifact (run `34671264361`, artifact `10291023518`, digest `sha256:42b6057d950e0b5ec29d996db6d4630ff0acac06947082681d0591af3cb6ae8a`). A target context enters v22 only when at least two processes were already `supported` in v21. Generating truth is not used to choose contexts or pairs.

The frozen v21 readout implies 1920 context-process rows, 122 co-supported target contexts and 152 unordered supported-process pairs. Any denominator drift fails closed.

## Symmetric estimand

For an unordered supported pair P,Q in one target spatial context:

- P conditional contribution: compare the Q-only knockout route with the P+Q knockout route;
- Q conditional contribution: compare the P-only knockout route with the P+Q knockout route.

The two directions are exact mirrors. No process name receives a special rule.

The target block remains held out. Each other spatial block is omitted from training in turn. Frozen ModelSpecs are averaged within a source perturbation; source perturbations are the uncertainty units. At least three complete source perturbations are required.

Absolute adequacy reuses the v5 prediction + observation-corrected ecological rank contract. Conditional contribution reuses rank margin 0.02, density margin 0.01 and the one-SEM rule.

## Pair states

- `P_favored`: P contributes conditional on Q removal; Q does not contribute conditional on P removal.
- `Q_favored`: mirror case.
- `coessential`: both directions show conditional contribution.
- `exchangeable`: neither direction shows revealed conditional contribution while both directions are adequate.
- `unresolved`: either direction is incomplete or inadequate.

## Forbidden changes

No seasonality-specific penalty, process-name-specific threshold, post-truth threshold tuning, or fresh empirical claim is allowed in v22.

Known truth may be opened only after the symmetric pair statuses are frozen, and only to score the consumed-development readout: false-seasonality demotion, true temperature/water retention, directional accuracy, and unresolved rate.
