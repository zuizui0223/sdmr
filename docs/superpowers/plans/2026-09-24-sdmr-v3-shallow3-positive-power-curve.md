# SDMR v3 Shallow3 Positive-Recovery Power Curve Plan

**Goal:** Determine whether the remaining unresolved ODO-positive cells are primarily finite-sample/power limited after selecting the probability-adequate shallow3 nonlinear learner.

## Frozen inputs

- Development-only; Product-A remains closed.
- ODO v2 is the population target:
  - workflow: 35495871747
  - artifact: 10601311224
  - state hash: 966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d
- HGB profile is frozen to shallow3 by the probability-quality-only screen:
  - workflow: 35608090218
  - artifact: 10644928842
- ecological seeds 23001–23008 are already-burned development evidence.
- margin = 0.01; adequacy floor = -0.75; SEM multiplier = 1.0.
- process closures and W1–W8 definitions unchanged.
- no prospective seeds or fresh empirical data are opened.

## Positive denominator

Use only ODO `contributory|required` cells.

Current denominator: 32 cells:
- unique_process thermal: 8
- interaction thermal: 8
- interaction water: 8
- geographic_shift thermal: 8

No truth-surface state is used to redefine this denominator.

## Sample-size curve

For every ODO-positive world × seed × process:

- 1x: 180 occurrences / 600 backgrounds
- 2x: 360 / 1200
- 4x: 720 / 2400
- deterministic resampling replicates: 0, 1, 2
- finite learner: shallow3 HGB only
- split modes kept separate:
  - spatial
  - random_cell

Resampling uses the exact occurrence/background distributions with replacement and preserves ecology/process registry unchanged.

## Metrics

For each split mode × multiplier:

- positive recovery
- unresolved rate
- replaceable rate
- unavailable rate
- mean paired delta
- mean delta SEM
- mean full-model balanced log score
- number of rows

Also report by world/process.

## Interpretation

- **power-limited:** recovery rises materially with multiplier while SEM falls.
- **interval-rule-limited:** mean delta remains above 0.01 and SEM shrinks, but recovery plateaus because intervals still cross the margin.
- **population-gap-small:** mean delta itself remains near/below 0.01 as n grows.
- **learner-limited:** full-model adequacy deteriorates or unavailable rate rises despite more data.

No threshold is tuned using this curve.

## Follow-up safety rule

This curve does not re-estimate false positives because it focuses only on the positive denominator. If one multiplier is later chosen as a candidate prospective sample size, a separate development-only safety audit must re-run ODO-replaceable/unresolved cells at that exact sample size before any prospective freeze.
