# SDMR v3 Phase 1 — process-information identification

## Status

Development-only implementation boundary. Product-A v2.8.4 remains closed with
`empirical_confirmation_not_supported` and `not_promoted`. No historical Product-A
endpoint, taxon panel, seed, threshold, or sealed outcome is reopened by this work.

Fresh empirical validation is **not opened** in Phase 1.

## Scientific flow

```text
declared plant process taxonomy
        ↓
many-to-many predictor/process registry
        ↓
full model vs complete process-closure knockout
        ↓
paired uncertainty-aware evidence
        ↓
replaceable / contributory / required / unresolved / unavailable
        ↓
known-truth oracle comparison
        ↓
KT-A ∧ KT-B ∧ KT-C ∧ KT-D ∧ KT-E ∧ KT-F
```

The key abstention rule is:

```text
failure to establish non-inferiority
!=
evidence of meaningful inferiority
```

An incomplete or interval-indeterminate viable route therefore cannot be promoted
to `contributory`.

## Initial plant process universe

- thermal
- water
- seasonality
- radiation/energy
- soil/substrate
- productivity

Predictors may map to multiple processes. Shared composites are removed in every
linked process closure.

## W1–W8 development worlds

1. unique process
2. redundant representation
3. shared carrier
4. null-correlated process
5. thermal × water interaction
6. observation-confounded thermal signal
7. omitted hidden driver
8. geographic proxy shift

The truth-surface oracle and occurrence-only challenge answer different questions.
For W6, for example, the truth surface may support thermal information while the
occurrence-level target remains `unresolved` because ecology and observation effort
are not separable under the declared observation architecture.

## Promotion boundary

Phase 1 code only implements the machinery. A later contract must freeze unused
prospective seeds and all KT thresholds before any prospective known-truth outcomes
are opened. Fresh empirical cohort code/identities remain prohibited until the
prospective KT-A–KT-F conjunction has passed.
