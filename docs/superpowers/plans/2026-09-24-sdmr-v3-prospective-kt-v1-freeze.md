# SDMR v3 Prospective Known-Truth v1 — Freeze Plan

Date: 2026-09-24
Status: **prospective contract freeze before Stage-P safety-v3 outcome is opened**

## Purpose

Freeze the first truly prospective SDMR v3 known-truth denominator and gate vector before using any result from the in-progress Stage-P safety-v3 development run.

This contract is executable only if the already-running Stage-P safety-v3 development audit closes without requiring a scientific-code change. If that development audit fails, prospective v1 is abandoned **without opening its seeds**.

## Unused prospective denominator

Seeds:

```text
33001–33020
```

Exactly 20 seeds. Repository search before freeze found no prior use of this seed band.

No failed seed may be replaced after outcome access.

Expected ODO-v2 process-state counts per seed under the frozen W1–W8 semantics:

- positive (`contributory|required`): 4
- replaceable: 35
- unresolved: 3
- unavailable: 6

Across 20 seeds:

- positive: **80**
- replaceable: **700**
- unresolved: **60**
- unavailable: **120**
- explicit structural-refusal cells: **60**

Any departure from the expected ODO semantic denominator is reported as a KT-A target/oracle failure, not repaired by replacing seeds.

## Why 20 seeds

At 80 positive cells, if the underlying recovery rate is 0.90, 72/80 yields a two-sided 95% Wilson lower bound of approximately **0.815**, making a prospective 0.80 recovery floor meaningfully testable.

For 60 unresolved/structural-refusal cells, observing zero violations gives a one-sided 95% binomial upper bound of approximately **0.049**. Thus 20 seeds can distinguish a near-zero abstention violation rate from a practically important >5% failure rate.

The much larger replaceable denominator (700) provides high precision for false-positive safety.

## Frozen model/data architecture

### Population target

- ODO v2 semantics and code path.
- W1–W8 unchanged.
- ODO is computed from the complete simulated observation distribution; finite results are scored against its process states.

### Stage P — primary process identification

- sample size: **8x = 1440 occurrences / 4800 backgrounds**
- learner: **shallow3 HGB**
- split: **random_cell**
- margin: **0.01**
- adequacy floor: **-0.75**
- SEM multiplier: **1.0**
- full-system information gate required:
  - full mean score >= -0.75
  - lower bound of gain over equal-prior null > 0
- observation-confounded and identical-closure refusals preserved.

### Stage T — separate spatial transfer

- uses the same sampled data and frozen Stage-P process decisions;
- spatial split is evaluated separately;
- Stage-T does not retroactively change Stage-P process states.

## Prospective KT gate vector

### KT-A — target/oracle integrity

All are required:

- exactly 20 declared seeds;
- no replacement;
- all W1–W8 evaluated;
- ODO target counts equal the declared semantic denominator;
- no ODO numerical/unavailable state outside the designed W7 unavailable cells;
- provenance/state hashes complete.

### KT-B — Stage-P positive recovery

```text
positive recovery >= 0.80
```

Denominator: all 80 ODO-positive cells.

### KT-C — Stage-P false-positive safety

```text
false-positive rate among ODO-replaceable <= 0.01
```

Denominator: 700 ODO-replaceable cells.

### KT-D — abstention integrity

Both exact conditions:

```text
over-resolution among ODO-unresolved = 0
structural-refusal violation = 0
```

No positive recovery can compensate for either violation.

### KT-E — whole-system unavailability

Both exact conditions:

```text
sharp-state rate among ODO-unavailable = 0
favorable-positive rate among ODO-unavailable = 0
```

Additionally:

```text
non-W7 full-system information adequacy >= 0.95
W7 full-system information adequacy = 0
```

This prevents a no-information world from being converted into a process-specific negative answer.

### KT-F — spatial-transfer safety

Stage-T is not a second process-identification gate. It is a frozen transfer diagnostic.

Requirements:

- every Stage-P positive process receives a spatial transfer evaluation;
- Stage-P-positive → spatial-`replaceable` contradiction rate <= 0.05;
- structural-refusal violations under spatial evaluation = 0.

Positive spatial retention rate is reported but not used to retroactively erase Stage-P evidence.

## Strict conjunction

Prospective process-identification promotion requires:

```text
KT-A & KT-B & KT-C & KT-D & KT-E & KT-F
```

No averaging or compensating trade-off is allowed.

## Fresh empirical barrier

Fresh plant validation remains unopened until this complete prospective KT conjunction passes once.

If prospective KT v1 fails:

- no threshold is changed;
- no seed is replaced;
- no failed world is dropped;
- the result is terminal for v1;
- any redesign requires a new version and a new unused seed denominator.

## Non-retroactivity

Product-A v2.8.4 remains closed:

- `empirical_confirmation_not_supported`
- `not_promoted`

Prospective v1 cannot rescue or reinterpret Product-A.
