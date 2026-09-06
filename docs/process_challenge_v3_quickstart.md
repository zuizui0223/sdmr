# Process challenge learner v3 — development quickstart

> **Status:** post-outcome method development. This API is not yet prospectively validated and must not be cited as a successful performance result.

The v3 workflow separates three questions that ordinary model selection tends to conflate:

1. **Prediction:** which frozen model specification predicts held-out records best inside the model pool?
2. **Contribution:** does removing all declared information for a process cause a material loss relative to the matched baseline, even if a weaker model remains above chance?
3. **Necessity:** does every complete process-exclusion route lose absolute adequacy?

The outer answer-check occurrence set remains sealed until these choices are frozen.

## 1. Fit the process challenge learner

```python
from sdmr.model import ModelSpec
from sdmr.process_challenge_learner import fit_process_challenge_learner

fit = fit_process_challenge_learner(
    model_pool_occurrences,
    background,
    presence_groups,
    background_groups,
    ecological_predictors=("bio1", "bio12", "pet", "soil_n"),
    observation_predictors=("sampling_effort",),
    process_registry=registry,
    process_universe=("thermal", "water", "soil"),
    model_specs=(
        ModelSpec(C=0.1, degree=1, random_state=0),
        ModelSpec(C=1.0, degree=1, random_state=0),
        ModelSpec(C=1.0, degree=2, random_state=0),
    ),
    occurrence_split=frozen_occurrence_split,
    occurrence_id_col="occurrence_id",
)
```

The prediction output uses one canonical inner-CV winner:

```python
fit.prediction_model_label
prediction = fit.predict_relative_suitability(new_frame)
```

The process output is set-valued and independent of that winner:

```python
fit.process_summary[["process", "status", "process_detected"]]
```

Possible statuses are:

- `replaceable_under_evidence_contract`: a process-free route is absolutely adequate and baseline-relative non-inferior;
- `contributory_under_evidence_contract`: a process-free route remains above the absolute floor, but all such routes lose materially relative to their matched baseline;
- `required_by_evidence_contract`: every complete process-free route loses absolute adequacy;
- `unresolved`: the declared challenge is incomplete.

`process_detected` is true for `contributory` and `required`. It is **not** a causal claim.

## 2. Audit whether the declared process closure is actually closed

Semantic rules alone can miss statistical proxies. Before fitting an outcome model, audit the background predictor table only:

```python
from sdmr.process_proxy_audit import audit_process_proxy_reconstructability

audit = audit_process_proxy_reconstructability(
    background_predictors,
    registry,
    process_universe=("thermal", "water", "soil"),
    predictor_universe=("bio1", "bio12", "pet", "elevation", "soil_n"),
    groups=background_spatial_groups,
    n_splits=5,
    degree=2,
)
```

`audit.process_summary` asks how well the **remaining predictor set** can reconstruct each process's declared direct anchors after the current closure is removed.

```python
audit.process_summary[
    ["process", "mean_anchor_reconstruction_cv_r2", "max_anchor_reconstruction_cv_r2"]
]
```

`audit.candidate_summary` ranks individual retained predictors that may carry the excluded process information:

```python
audit.candidate_summary.head(20)
```

The audit deliberately has no outcome column and never modifies the registry. Every candidate row contains:

```text
auto_frozen = False
requires_human_review = True
```

The researcher therefore reviews only flagged/high-reconstruction candidates, adds scientifically defensible many-to-many links such as

```text
PET -> water / composite
PET -> thermal / composite
elevation -> thermal / proxy
```

and freezes the registry **before** any occurrence outcome is used for process inference.

## 3. Recommended practical workflow

```text
occurrence ID + coordinates
        |
        v
freeze model_pool / answer_check
        |
        +--> predictor metadata + semantic rules
        |          |
        |          v
        |   preliminary process registry
        |          |
        |          v
        |   predictor-only proxy audit
        |          |
        |          v
        |   human review of exceptions/proxies
        |          |
        |          v
        |     freeze closure
        |
        v
model_pool-only inner spatial CV
        |
        +--> canonical prediction winner
        |
        +--> baseline-relative process challenges
                 |
                 v
 replaceable / contributory / required / unresolved
        |
        v
freeze selection receipt
        |
        v
open outer answer-check once
```

## What the user still decides

The software can automate splitting, CV, fitting, knockout, proxy diagnostics and audit export. The user remains responsible for:

- defining the ecological process taxonomy;
- approving semantic classification rules;
- reviewing proposed proxy/composite links;
- deciding whether the declared process representation is scientifically defensible before freeze.

This division is intentional: allowing an outcome-driven algorithm to invent the process closure after seeing performance would recreate the information leakage that the framework is designed to prevent.
