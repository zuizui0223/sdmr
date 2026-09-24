# SDMR v5 full-pipeline integration pre-freeze

Date: 2026-09-25
Status: **development integration contract frozen before permutation-gate validation outcome**

## Preconditions

This integration panel may be opened only if:

1. v5 permutation-gate validation on 51001–51100 passes;
2. independent permutation-gate confirmation on 52001–52050 passes.

If either prerequisite fails, this integration contract is abandoned unopened.

## Development integration seeds

```text
61001–61020
```

Exactly 20 fresh development-only seeds.

Repository search before freeze found no prior use of this seed band.

## Frozen architecture

### Stage P

- 8x sample = 1440 occurrence / 4800 background
- shallow3 HGB
- random_cell
- 3 folds
- process margin 0.01
- adequacy floor -0.75
- ODO v2 target
- permutation full-system gate:
  - B=999
  - alpha=.001
  - RNG seed=0
  - within-fold held-out label permutation
  - score >= -0.75
  - gain over -log(2) > 0
  - p <= .001

If full-system gate fails:
- every process state unavailable.

If gate passes:
- existing process-closure state engine is used unchanged.

### Stage T

- same finite sampled rows
- spatial split
- full-system permutation authorization is not used to redefine Stage-P state
- transfer outcome reported separately.

## Expected ODO denominator

Per seed:
- positive 4
- replaceable 35
- unresolved 3
- unavailable 6
- structural refusal 3

Across 20 seeds:
- positive 80
- replaceable 700
- unresolved 60
- unavailable 120
- structural refusal 60

Any ODO denominator drift is a hard integration failure.

## Frozen integration gate

Strict conjunction:

### INT-A — provenance/denominator
- all 20 seeds;
- all W1–W8;
- exact expected ODO counts;
- no replacement.

### INT-B — Stage-P positive recovery
```text
>= 0.80
```

### INT-C — false-positive safety
```text
<= 0.01 among ODO-replaceable
```

### INT-D — abstention
```text
ODO-unresolved over-resolution = 0
structural-refusal violation = 0
```

### INT-E — unavailability
```text
ODO-unavailable sharp-state rate = 0
ODO-unavailable favorable-positive rate = 0
W7 full-system authorization = 0/20
non-W7 full-system authorization >= 0.95
```

### INT-F — spatial transfer
```text
Stage-P positive -> spatial replaceable contradiction <= 0.05
spatial structural-refusal violation = 0
```

No integration endpoint may be traded against another.

## Prospective barrier

Reserved prospective seeds 53001–53020 remain unopened until the entire INT-A–INT-F conjunction passes.

Fresh empirical plant validation remains closed until the subsequent prospective KT conjunction passes.
