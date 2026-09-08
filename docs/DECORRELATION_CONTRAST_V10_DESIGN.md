# Decorrelation contrast v10 — frozen development design

Status: design only. No fresh scientific denominator is opened by this document.

## Problem

v9 distinguishes singleton-identifiable `unique_contributory` processes from `shared_candidate` processes whose evidence is total but not uniquely attributable under the observed process representation. The next task is to obtain **separating information** rather than force a singleton from the same correlation structure.

## Core idea

For a shared-candidate target process `P` and competing process representation `Q`, use background environments only to identify held-out environments in which the mapping `P <- Q` changes. Those environments are informative because a pure proxy relationship should not transport unchanged when the `P-Q` association shifts.

The separator therefore has two stages:

1. **contrast eligibility (outcome-blind)**
   - use environmental/background rows only;
   - partition by a pre-existing spatial/outer block definition;
   - fit `P ~ Q` on the non-held-out environments;
   - measure held-out reconstruction degradation of `P` from `Q`;
   - a block can be used as separating information only if the `P-Q` mapping is demonstrably non-transporting under a rule frozen before occurrence outcomes are scored;

2. **process evidence in the eligible contrast**
   - after eligibility is frozen, score the already-defined total and conditional process evidence in that held-out environment;
   - a shared candidate can be promoted to singleton attribution only if its evidence remains compatible with contribution while the competing proxy explanation loses transport support;
   - incomplete or indeterminate contrast evidence remains set-valued/unresolved.

## Non-negotiable constraints

- contrast eligibility must not use occurrence labels, suitability, external biological truth, fitted SDM coefficients, or generating-process truth;
- the spatial environment partition must be frozen independently of the candidate outcome;
- no shared candidate is promoted merely because the competing process becomes weak;
- existing v5 rank/density evidence thresholds remain unchanged;
- no threshold may be selected after inspecting fresh known-truth outcomes;
- the consumed `15001–15010` denominator may be used only for development diagnosis;
- fresh empirical validation remains closed until a fresh known-truth contract passes.

## First implementation target

Implement a background-only `environmental_decorrelation_audit` that, for each ordered pair `(P,Q)` and held-out environment, returns:

- train and held-out complete-row counts;
- train reconstruction score for `P <- Q`;
- held-out reconstruction score;
- reconstruction degradation and uncertainty;
- `eligible / not_eligible / incomplete` state;
- hashes of the environment partition and predictor closures.

The first development test is mechanistic, not a performance claim: determine whether known v8/v9 `shared_candidate` cells actually contain environments where their competing process mapping breaks. Only after that audit is stable should occurrence-based promotion logic be added.
