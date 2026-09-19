# SDMR v3 Positive-Evidence Audit Plan

**Goal:** Diagnose why the occurrence-only process challenge fails to recover the 30 oracle-positive development cells before designing another method version.

**Boundary:** Diagnostic only. Product-A remains closed. Seeds 23001–23008 are already burned development evidence. No prospective thresholds, seeds, or fresh empirical data are opened.

## Inputs

- W1 unique_process, W5 interaction, W8 geographic_shift
- seeds 23001–23008
- unchanged simulator/oracle settings from development v3
- unchanged occurrence margin 0.01
- unchanged adequacy floor -0.75
- unchanged class_weight=balanced
- compare learners: linear and quadratic

## Outputs

For every target-positive world × seed × process × learner:
- target state
- final occurrence state/reason
- full mean balanced log score
- process-free mean balanced log score
- paired delta mean and SEM
- lower/upper interval
- full adequacy
- process-free adequacy
- diagnostic boundary class

Fold-level matched evidence is exported separately.

## Diagnostic boundary classes

- `full_inadequate`
- `process_free_noninferior_witness`
- `interval_indeterminate`
- `positive_contribution_evidence`
- `positive_required_evidence`
- explicit existing refusal reason when attribution is blocked upstream

No class changes the scientific state. It only explains it.

## Stop rule

Do not design v4 until the complete audit is recorded. Any subsequent change must address the dominant diagnosed boundary and must remain development-only until a new untouched prospective denominator is frozen.
