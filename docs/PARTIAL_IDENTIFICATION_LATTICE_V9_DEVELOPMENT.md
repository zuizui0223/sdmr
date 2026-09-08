# Partial-identification lattice v9 — development result

Status: **development only**. The denominator is the already-consumed 60-case / 300-process-cell `15001–15010` known-truth set. These numbers are not prospective performance claims.

## Why v9 exists

v6 improved recall but promoted correlated proxy processes, especially seasonality. v7 showed that process-specific purging reduces those false attributions, but its collateral guard over-abstains. v8 fixed the intervention geometry by replacing only the target closure with `E[P | other declared processes]`, leaving every non-target predictor unchanged. That reduced false process detection to 1/170 but also reduced true-process recall to 45/130.

The v8 recall loss is not primarily a threshold problem. It exposes two different estimands:

1. **total contribution** — the process representation participates in a recoverable route;
2. **unique contribution** — contribution remains after shared information predictable from other declared processes has been retained.

A process can have total contribution without uniquely attributable contribution. Forcing such a case into a binary singleton label is exactly where proxy attribution re-enters.

## v9 state space

For each process cell, combine the frozen total-evidence state (v5) with the v8 unique conditional-knockout state:

- `unique_contributory`: v8 unique evidence is contributory;
- `shared_candidate`: total evidence is contributory but unique evidence is replaceable or unresolved;
- `replaceable`: both axes are replaceable;
- `unresolved`: all remaining combinations.

No unresolved input is promoted. No new numerical threshold is introduced.

## Consumed-development readout

On the same 60 cases / 300 process cells:

- unique singleton attribution: **45 TP, 1 FP**, true-process recall 34.6%, false-process detection 0.59%;
- unique + shared-candidate retention: **57 TP, 2 FP**, true-process candidate coverage 43.8%, false-process candidate rate 1.18%;
- state counts: **46 unique_contributory, 13 shared_candidate, 175 replaceable, 66 unresolved**.

This is not evidence that v9 has superior predictive performance. It is evidence that a single binary process-membership endpoint collapses two scientifically distinct questions. v9 therefore changes the output object: it reports singleton-identifiable processes separately from processes that remain only set-valued/shared candidates under the available representation.

## Scientific consequence

The current development sequence supports a sharper statement:

> Process attribution from occurrence-environment data is generally a partial-identification problem. Counterfactual removal can establish total contribution, and conditional shared-information knockout can establish unique contribution, but a process whose evidence resides only in information shared with competing process representations cannot be assigned to a singleton without additional separating information.

This is an identifiability boundary, not a license to declare the process absent.

## Next gate

Do **not** open fresh empirical validation yet. The next development task is to add a separating-information design for `shared_candidate` cells (for example, cross-environment decorrelation or targeted external observations) and test whether candidate sets can be shrunk prospectively without inflating singleton false attribution.
