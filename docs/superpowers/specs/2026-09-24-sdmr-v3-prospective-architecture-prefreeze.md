# SDMR v3 prospective architecture — pre-freeze design record

Date: 2026-09-24
Status: **pre-freeze architecture; sample size and numerical promotion thresholds not yet frozen**

## 1. What is now fixed by development evidence

### Population target

Occurrence-only process identification is evaluated against **Occurrence-Distribution Oracle v2 (ODO v2)**, not directly against generating-process membership or the truth-surface oracle.

The hierarchy is:

```text
generating process
        ↓
truth-surface process information
        ↓
occurrence-distribution process information (ODO v2)
        ↓
finite-sample process identification
        ↓
sealed spatial transfer
```

Each transition is a distinct estimand.

### Process state space

The finite procedure returns only:

- `replaceable`
- `contributory`
- `required`
- `unresolved`
- `unavailable`

Failure to establish non-inferiority is never converted into positive contribution evidence.

### Observation boundary

Processes declared nonseparable from the observation process remain `unresolved` even if numerical removal scores appear favorable.

Identical process-information closures remain `unresolved` for all otherwise sharp process-specific states.

### Nonlinear learner

The old `current` HGB profile is rejected because it catastrophically overfits.

The only screened nonlinear profile authorized for subsequent development is:

```text
shallow3
learning_rate = 0.05
max_iter = 100
max_leaf_nodes = 3
min_samples_leaf = 40
l2_regularization = 1.0
early_stopping = false
random_state = 0
```

It was selected from a probability-quality-only screen before process recovery was reopened.

Linear logistic remains a reference learner. Quadratic logistic remains a development comparator but is not currently the preferred nonlinear route.

## 2. Stage-P versus Stage-T separation

Development showed that process identification and geographic transfer must not be collapsed into one cross-validation estimand.

### Stage P — process-information identification

Primary inner evidence geometry:

`random_cell`

- unique cells are deterministically cross-fitted;
- duplicate records from one cell remain in one fold;
- purpose: estimate process information within the model-pool support.

Primary learner routes:

- balanced penalized linear logistic;
- screened shallow3 HGB.

Learner disagreement remains explicit. A future stability rule may return `unresolved` rather than average contradictory states.

### Stage T — geographic transfer

`spatial` evaluation is retained as a separate downstream guardrail.

It asks whether the frozen process/representation conclusion survives geographic holdout.

A Stage-P positive state is not retroactively changed merely because spatial transfer is weak; instead the result is reported as process-supported but transfer-limited.

This preserves the distinction between:

```text
information identifiable in the occurrence system
!=
information geographically transferable
```

## 3. Fixed source provenance

### ODO v2

- workflow run: `35495871747`
- artifact id: `10601311224`
- artifact digest: `sha256:bc67412ccf10e40cd5039f204410bf31f96773de4d0f808268e2773e9192488c`
- canonical state hash: `966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d`

### HGB probability-quality screen

- workflow run: `35608090218`
- artifact id: `10644928842`
- artifact digest: `sha256:1a07609267cfba8ef443f3a956cf7015a2caf8db65a7af9e63b0a48c3157edaf`
- selected profile: `shallow3`
- selection used process recovery: **false**

### Selected nonlinear recovery

- workflow run: `35946188585`
- artifact id: `10787697930`
- artifact digest: `sha256:c37d027f1286e0d2a8c45a09ae58c57c03dd2ce65808f64358e53ce0267bda76`
- baseline shallow3 positive recovery:
  - spatial: 0.40625
  - random_cell: 0.25000

### Positive power curve v1

- workflow run: `35976809272`
- ODO target hash unchanged
- sample multipliers: 1x, 2x, 4x
- random_cell recovery: 0.375 → 0.583 → 0.719
- spatial recovery: 0.396 → 0.438 → 0.615
- 8x tail diagnostic is separate development evidence and is not yet part of this record.

## 4. What remains intentionally unfrozen

The following are **not** fixed by this design record:

- prospective known-truth seed set;
- final occurrence/background sample size;
- minimum positive-recovery threshold;
- maximum false-positive threshold;
- maximum over-resolution threshold;
- minimum spatial-transfer threshold;
- fresh empirical taxon cohort;
- exact fresh empirical denominator;
- Stage-R representation-selection threshold.

None may be back-filled as if it had been prospectively declared before the current burned development outcomes.

## 5. Next freeze order

After the 8x tail diagnostic closes:

1. choose a development-supported sample-size regime or explicitly declare recovery plateau;
2. run a safety audit at the selected sample size on ODO-replaceable and ODO-unresolved cells;
3. use development evidence/power analysis to set one prospective KT threshold vector;
4. draw a completely unused prospective seed denominator;
5. freeze the full KT contract;
6. execute KT once;
7. open fresh empirical plant validation only if the complete KT conjunction passes.

## 6. Non-retroactivity

Product-A v2.8.4 remains closed:
- `empirical_confirmation_not_supported`
- `not_promoted`

No SDMR v3 development result rescues or reinterprets that endpoint.

Fresh empirical data remain unopened.


## 7. Full-system information adequacy correction

Before any Stage-P process-specific state is assigned, the complete declared predictor system must itself contain held-out information above the equal-prior null model.

For the same Stage-P `random_cell` folds used by the full model, define:

```text
gain_k = full_balanced_log_score_k - (-log 2)
```

and summarize:

```text
lower_gain = mean(gain_k) - 1 × SEM(gain_k)
```

The full system is information-adequate only if:

```text
mean full score >= -0.75
AND
lower_gain > 0
```

If this conjunction fails, every process-specific Stage-P state for that taxon/world is `unavailable` before process knockout interpretation.

This gate uses the natural zero-information boundary and the already-frozen 1×SEM convention. It does not introduce a fitted biological threshold.

The gate applies to **Stage P**. Stage T spatial evaluation remains a separate transfer endpoint and does not redefine process availability.

Consequences:

```text
full system not informative
→ unavailable

full system informative
→ proceed to process closure
→ replaceable / contributory / required / unresolved
```

This correction is motivated by the W7 omitted-driver failure mode, where the previous -0.75 absolute floor allowed a no-information model near -log(2) to generate a false sharp negative (`replaceable`).
