# SDMR v3 8x Safety Audit Plan

**Goal:** Determine whether the candidate 8x shallow3 sample-size regime preserves specificity and abstention before any prospective known-truth freeze.

## Frozen inputs

- Development-only; Product-A remains closed.
- ODO v2 state target is immutable:
  - workflow `35495871747`
  - artifact `10601311224`
  - state hash `966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d`
- learner: shallow3 HGB selected by outcome-blind probability screen.
- ecological seeds: 23001–23008, already-burned development evidence.
- worlds: W1–W8.
- sample size: exactly 8x = 1440 occurrences / 4800 backgrounds.
- resampling replicates: 0,1,2.
- split modes kept separate: spatial and random_cell.
- margin = 0.01; adequacy floor = -0.75; SEM multiplier = 1.
- no threshold, process closure, ODO state, learner profile, or ecological world changes.

## Safety denominators

### ODO replaceable

Primary specificity endpoint:

`false_positive_rate = P(finite state in {contributory, required} | ODO replaceable)`.

### ODO unresolved

Primary abstention endpoint:

`overresolution_rate = P(finite state in {replaceable, contributory, required} | ODO unresolved)`.

### ODO unavailable

Fail-closed endpoint:

- no `contributory|required` favorable coercion;
- report sharp-call rate separately.

### Structural refusal subsets

Report separately:

- observation-confounded thermal;
- identical shared-carrier thermal/water.

These must remain `unresolved`; any sharp state is an explicit refusal violation.

## Secondary positive denominator

Retain ODO-positive recovery in the same 8x resamples only as a consistency check against the positive-power tail result. It cannot compensate for a safety failure.

## Output

For each split mode:
- positive recovery;
- false-positive rate;
- unresolved over-resolution rate;
- unavailable favorable-call rate;
- structural refusal violation rate;
- finite unavailable rate by ODO target class;
- state confusion table.

Also report each metric by world and process.

## Decision

No prospective threshold is defined by this audit.

If safety remains low and structural refusal violations are zero, 8x becomes the **candidate development sample-size regime** for prospective threshold design.

If safety degrades materially, do not trade specificity for sensitivity. Revisit learner stability/state aggregation instead of changing the 0.01 process margin post hoc.
