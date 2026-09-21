# SDMR v3 Finite-Recovery v3 — Selected Nonlinear Learner Retest Plan

**Goal:** Re-test process recovery only after the HGB probability-quality screen has selected and frozen one numerically adequate nonlinear profile.

## Hard gate before execution

This plan is inert until all of the following exist:

1. the HGB regularization screen workflow completes successfully;
2. its `selection.json` names exactly one `selected_profile`;
3. that profile passes the frozen `-0.75` mean test-log-score guardrail in every world × split-mode cell;
4. the selected profile is recorded in a terminal screen-result document with artifact digest.

No process-recovery outcome may be consulted during HGB profile selection.

## Frozen scientific target

- ODO v2 remains the occurrence-distribution population target.
- Positive denominator: ODO `contributory|required` cells.
- Safety denominators:
  - ODO `replaceable` for false positives;
  - ODO `unresolved` for over-resolution.
- Product-A remains closed.
- No prospective or fresh empirical data are opened.
- Margin = 0.01, adequacy floor = -0.75, SEM multiplier = 1.0.
- Process closure and W1–W8 definitions unchanged.

## Learner comparison

At baseline sample size 180 occurrence / 600 background:

- linear logistic;
- quadratic logistic;
- selected screened HGB profile.

Evaluate both finite split modes separately:

- `spatial`;
- `random_cell`.

Do not average split modes into one state. They answer different questions:

- `random_cell`: within-support process-information identification;
- `spatial`: process-information transfer under geographic holdout.

## Primary development metrics

For each learner × split mode:

- positive recovery among ODO-positive cells;
- positive `unavailable` rate;
- positive `unresolved` rate;
- false-positive rate among ODO-replaceable cells;
- over-resolution among ODO-unresolved cells;
- mean paired delta and SEM;
- full-model mean balanced log score.

## Interpretation

- If selected HGB improves positive recovery under random_cell while spatial remains weaker:
  Stage-P identification and spatial transfer should be explicitly separated.
- If selected HGB is adequate but recovery remains low under both splits:
  finite information / interval evidence is the remaining bottleneck.
- If selected HGB adds false positives or over-resolution:
  nonlinear flexibility is not scientifically promotable despite probability adequacy.
- If linear remains best:
  retain learner disagreement as an explicit stability dimension rather than forcing nonlinear promotion.

## No prospective promotion

This retest remains burned-development evidence. It may determine the learner panel and the later prospective gate, but cannot itself establish scientific superiority.
