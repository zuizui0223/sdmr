# SDMR v3 full-system information adequacy gate — development design

Date: 2026-09-24
Status: development-only design; prospective freeze remains blocked

## Motivation

The 8x safety audit showed perfect positive specificity and refusal preservation but a systematic failure on ODO-unavailable omitted-driver worlds:

```text
ODO unavailable -> finite replaceable
```

The finite method currently asks only whether the full model exceeds an absolute log-score floor (-0.75). Under equal class priors, however, a no-information model has balanced log score

[
S_0 = -\log 2 \approx -0.693147.
]

Thus a full model can pass -0.75 while containing no usable information above the null.

## Gate estimand

For each frozen finite learner route and inner split, compute fold-level full-model information gain

[
g_f = S_{full,f} - S_{null,f}.
]

With the existing uncertainty convention,

[
G = \bar g - k\,SE(g), \qquad k=1.
]

Full-system information is adequate only when

[
G > 0.
]

Zero is a structural information boundary, not a fitted biological effect threshold.

## State precedence

1. explicit observation nonseparability remains `unresolved`;
2. identical process closures remain `unresolved`;
3. otherwise, if the full-system information gate fails, the process state is `unavailable`;
4. only then apply process-specific replaceable/contributory/required/unresolved logic.

This keeps known structural refusal semantics separate from lack of full-system information.

## Development test

Use only already-burned seeds 23001–23008 at the frozen 8x shallow3 regime.

For both random_cell and spatial:

- all W1–W8;
- three fixed resampling replicates;
- unchanged sample size, process margin, floor, learner and ODO target.

Primary diagnostic:

- full-information adequacy rate by world;
- ODO-unavailable W7 rejection rate;
- non-W7 availability rate;
- especially W6 observation-confounded availability, because its structural refusal must remain unresolved even if the full gate is weak.

No process knockout outcome is needed to select or tune this gate.

## Decision

The gate may enter the next safety-state retest only if it:

- rejects omitted-driver full systems consistently;
- does not create broad unavailability in ordinary process-identifiable worlds;
- uses the exact zero-information boundary without post-hoc tuning.

This development result cannot be prospective evidence.
