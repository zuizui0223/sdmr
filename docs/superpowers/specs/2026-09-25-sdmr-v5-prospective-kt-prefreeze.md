# SDMR v5 prospective known-truth pre-freeze

Date: 2026-09-25
Status: **scientific contract pre-frozen / activation forbidden**

## Preconditions

This contract may be activated only if all three prerequisites pass:

1. v5 permutation-gate validation on seeds 51001–51100;
2. independent v5 permutation-gate confirmation on seeds 52001–52050;
3. full Stage-P/Stage-T v5 integration safety check using development-only evidence.

If any prerequisite fails, this prospective contract is abandoned unopened.

## Reserved prospective denominator

Seeds:

```text
53001–53020
```

Exactly 20 seeds.

No replacement after any prospective outcome access.

Expected ODO-v2 states per seed:

- positive: 4
- replaceable: 35
- unresolved: 3
- unavailable: 6
- structural refusal: 3

Totals across 20 seeds:

- positive: 80
- replaceable: 700
- unresolved: 60
- unavailable: 120
- structural refusal: 60

## Frozen Stage P

- sample size: 8x = 1440 occurrence / 4800 background
- learner: shallow3 HGB
- split: random_cell
- n_splits: 3
- process margin: 0.01
- adequacy floor: -0.75
- ODO v2 process target unchanged

### Full-system v5 authorization gate

Before process knockouts:

```text
B = 999 held-out label permutations
alpha = 0.001
RNG seed = 0
within-fold label permutation only
fold class counts preserved
models never refit during permutations
```

Authorize the full system iff:

```text
mean full score >= -0.75
AND
mean gain over -log(2) > 0
AND
permutation p <= 0.001
```

Otherwise all Stage-P process states are unavailable.

## Frozen process-state rules

For an authorized full system:

- replaceable
- contributory
- required
- unresolved
- unavailable

retain their existing SDMR v3 definitions.

Observation-confounded and identical-closure refusals remain unchanged.

## Frozen Stage T

Spatial transfer is evaluated separately.

Stage-T cannot retroactively change Stage-P process state.

## Prospective gate vector

### KT-A — denominator/provenance integrity

- all 20 seeds required;
- all W1–W8 required;
- no replacement;
- exact ODO denominator required;
- complete provenance required.

### KT-B — positive recovery

```text
Stage-P positive recovery >= 0.80
```

### KT-C — false-positive safety

```text
Stage-P positive call among ODO-replaceable <= 0.01
```

### KT-D — abstention integrity

```text
ODO-unresolved over-resolution = 0
structural-refusal violation = 0
```

### KT-E — whole-system unavailability

```text
sharp-state rate among ODO-unavailable = 0
favorable-positive rate among ODO-unavailable = 0
W7 full-system authorization = 0 / 20
non-W7 full-system authorization >= 0.95
```

### KT-F — spatial transfer

- all Stage-P positive cells receive Stage-T evaluation;
- Stage-P positive → spatial replaceable contradiction <= 0.05;
- spatial structural-refusal violation = 0;
- spatial positive retention reported but not used to erase Stage-P evidence.

## Strict conjunction

```text
KT-A & KT-B & KT-C & KT-D & KT-E & KT-F
```

Fresh empirical plant validation remains closed until this conjunction passes once.

## Non-retroactivity

- Product-A remains closed.
- prospective v3 remains terminally failed.
- v4 calibration/confirmation remain terminal records.
- v5 development panels cannot be reused as prospective evidence.
