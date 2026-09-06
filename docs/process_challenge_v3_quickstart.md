# Process challenge learner v3/v3.1 — development quickstart

> **Status:** post-outcome method development. This API is not yet prospectively validated and must not be cited as a successful performance result.

The workflow separates four questions that ordinary model selection tends to conflate:

1. **Prediction:** which frozen model specification predicts held-out records best inside the model pool?
2. **Contribution:** does removing all declared information for a process cause a material loss relative to the matched baseline, even if a weaker model remains above chance?
3. **Necessity:** does every complete process-exclusion route lose absolute adequacy?
4. **Attribution:** can the loss caused by removing process P be uniquely attributed to P, or did the removed predictors also carry information about another declared process?

The outer answer-check occurrence set remains sealed until these choices are frozen.

## 1. Fit the process challenge learner

```python
from sdmr import ModelSpec, fit_process_challenge_learner

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

The process challenge output is independent of that winner:

```python
fit.process_summary[["process", "status", "process_detected"]]
```

Possible v3 challenge statuses are:

- `replaceable_under_evidence_contract`: a process-free route is absolutely adequate and baseline-relative non-inferior;
- `contributory_under_evidence_contract`: a process-free route remains above the absolute floor, but all such routes lose materially relative to their matched baseline;
- `required_by_evidence_contract`: every complete process-free route loses absolute adequacy;
- `unresolved`: the declared challenge is incomplete.

`process_detected` is true for `contributory` and `required`. It is **not** a causal claim.

## 2. Audit whether the declared process closure is actually closed

Semantic rules alone can miss statistical proxies. Before using an outcome to revise the process registry, audit the background predictor table only:

```python
from sdmr import audit_process_proxy_reconstructability

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

The audit deliberately has no outcome column and never modifies the registry. Every candidate row is a proposal for review, not ecological truth.

The researcher can use these proposals to add scientifically defensible many-to-many links such as

```text
PET -> water / composite
PET -> thermal / composite
elevation -> thermal / proxy
```

and freeze the registry **before** a prospective outcome is used for process inference.

## 3. v3.1: separate a challenge signal from unique attribution

Even a correct knockout can be ambiguous. If removing process `seasonality` also removes a predictor that carries substantial `water` information, a performance loss does not uniquely demonstrate a seasonality contribution.

Run the shared-carrier layer with a background/environment table only:

```python
from sdmr import fit_shared_carrier_attribution

attribution = fit_shared_carrier_attribution(
    fit,
    background_predictors,
    registry,
    groups=background_spatial_groups,
    n_splits=5,
    degree=2,
    minimum_univariate_cv_r2=0.25,
    minimum_abs_spearman=0.50,
)
```

The two numerical defaults are **development heuristics**. They are not yet validated performance thresholds and must be frozen before any future prospective denominator.

Inspect:

```python
attribution.process_summary[
    [
        "process",
        "challenge_status",
        "attribution_status",
        "challenge_signal_detected",
        "shared_information_contested",
        "unique_process_evidence",
        "shared_carrier_predictors",
        "shared_with_processes",
    ]
]
```

The additional v3.1 status is:

- `contested_shared_information`: the v3 challenge detected a loss, but at least one predictor removed by that challenge is either already declared to carry another process or reconstructs another process anchor in the predictor-only audit.

Crucially, v3.1 does **not** turn `replaceable` into `contributory`, and it does not count `contested_shared_information` as unique process evidence. It only makes an existing contribution/necessity claim more conservative when attribution is ambiguous.

The evidence table is explicit:

```python
attribution.evidence[
    attribution.evidence["qualifies"]
][
    [
        "challenged_process",
        "carrier_predictor",
        "other_process",
        "evidence_source",
        "univariate_cv_r2",
        "abs_spearman",
    ]
]
```

Possible evidence sources are:

- `declared_many_to_many`: ambiguity was already present in the frozen registry;
- `predictor_only_reconstruction`: the removed predictor statistically reconstructs another process anchor without using occurrence outcomes or truth.

## 4. Recommended practical workflow

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
 shared-carrier attribution audit
                 |
                 v
 contributory/required may downgrade to contested_shared_information
        |
        v
freeze selection + attribution receipts
        |
        v
open outer answer-check once
```

## What the user still decides

The software can automate splitting, CV, fitting, knockout, proxy diagnostics, shared-carrier attribution and audit export. The user remains responsible for:

- defining the ecological process taxonomy;
- approving semantic classification rules;
- reviewing proposed proxy/composite links;
- deciding whether the declared process representation is scientifically defensible before freeze;
- freezing shared-carrier thresholds before a prospective validation or empirical claim.

This division is intentional: allowing an outcome-driven algorithm to invent or revise the process closure after seeing performance would recreate the information leakage that the framework is designed to prevent.
