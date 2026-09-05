# Ecological identification quickstart

Status: **prospective generic workflow; not part of frozen Product A**

The routine user-facing workflow is deliberately small:

```text
occurrence IDs + coordinates
        ↓
freeze model_pool / answer_check
        ↓
freeze process registry
        ↓
fit admissible model set on model_pool only
        ↓
process certificate
        ↓
open answer_check once
```

The answer-check is not a CV fold and is never used to tune the model or define the process closure.

## Recommended safe workflow

### 1. Prepare the study before model fitting

```python
import pandas as pd
from sdmr import (
    EcologicalIdentificationConfig,
    prepare_ecological_identification_study,
)

config = EcologicalIdentificationConfig(
    answer_check_fraction=0.20,
    outer_random_state=42,
)

study = prepare_ecological_identification_study(
    occurrence_index=occurrences[[
        "occurrence_id", "longitude", "latitude"
    ]],
    predictor_metadata=predictor_metadata,
    classification_rules=classification_rules,
    config=config,
)
```

At this point only occurrence identity/coordinates and predictor metadata/rules have been used. No sealed ecological outcome has been opened.

The two frozen occurrence sets are available as:

```python
study.model_pool_ids
study.answer_check_ids
```

Use `study.model_pool_ids` when constructing any occurrence-dependent accessible area (`M`), target-group/background design, or other data structure that must not use answer-check occurrences.

### 2. Fit the learner

Once the frozen feature recipe and model-pool-compatible background are ready:

```python
fit = study.fit(
    occurrence_features=occurrence_features,
    background_features=background_features,
)
```

The workflow automatically:

- filters occurrence rows to the frozen model pool;
- verifies that every frozen model-pool occurrence is present;
- creates inner grouped spatial folds;
- evaluates all predeclared base learners;
- keeps every learner passing the absolute prediction adequacy gate;
- refits each admitted learner after each process-information closure knockout;
- returns `required_by_evidence_contract`, `refuted_as_necessary`, or `unresolved` for each process;
- fits the admitted baseline model set for ensemble prediction;
- creates a deterministic selection receipt.

The main result is simply:

```python
fit.process_summary
```

### 3. Open the answer-check once

```python
answer = fit.evaluate_answer_check(
    full_occurrence_features=occurrence_features,
    answer_background=answer_background,
)
```

This is the first point at which the sealed occurrence features are used for evaluation.

## Semi-automatic process classification

Users do not need to hand-label every raster. Provide predictor metadata:

```python
predictor_metadata = pd.DataFrame([
    {"predictor": "bio1",  "source_family": "CHELSA", "units": "degC"},
    {"predictor": "gdd5",  "source_family": "CHELSA", "units": "degree_days"},
    {"predictor": "pet",   "source_family": "CHELSA", "units": "mm"},
    {"predictor": "bio12", "source_family": "CHELSA", "units": "mm"},
])
```

and a small prospective rule table:

```python
classification_rules = pd.DataFrame([
    {"rule_id": "t1", "process": "thermal", "role": "direct",    "predictor_exact": "bio1"},
    {"rule_id": "t2", "process": "thermal", "role": "derived",   "predictor_pattern": r"^gdd"},
    {"rule_id": "t3", "process": "thermal", "role": "composite", "predictor_exact": "pet"},
    {"rule_id": "w1", "process": "water",   "role": "composite", "predictor_exact": "pet"},
    {"rule_id": "w2", "process": "water",   "role": "direct",    "predictor_exact": "bio12"},
])
```

One predictor may belong to several process closures. `pet → thermal + water` is therefore valid rather than a conflict.

If a predictor is unmatched or conflicting, preparation stops with `ProcessRegistryReviewRequired`. The exception contains the full proposal:

```python
try:
    study = prepare_ecological_identification_study(...)
except ProcessRegistryReviewRequired as exc:
    flagged = exc.proposal.loc[exc.proposal["review_required"]]
    print(flagged)
```

Only those flagged cases need human review.

## Direct registry mode

If the process registry is already scientifically declared, no rules are required:

```python
registry = pd.DataFrame([
    {"predictor": "bio1", "process": "thermal", "role": "direct"},
    {"predictor": "pet",  "process": "thermal", "role": "composite"},
    {"predictor": "pet",  "process": "water",   "role": "composite"},
])

study = prepare_ecological_identification_study(
    occurrence_index,
    registry,
)
```

## One-call convenience mode

If the environmental feature recipe and background construction were already prospectively frozen independently of the answer-check outcomes:

```python
from sdmr import quick_fit_ecological_identification

fit = quick_fit_ecological_identification(
    occurrence_features,
    background_features,
    predictor_metadata,
    classification_rules=classification_rules,
)
```

For studies in which `M` or background depends on occurrence locations, the two-stage `prepare → construct background from model_pool → fit` workflow is preferred.

## Audit export

A fitted study can be exported directly:

```python
manifest = fit.export_audit_bundle("results/ecological_identification")
```

The directory contains:

- frozen occurrence role assignment;
- registry proposal and frozen process registry;
- inner spatial-group ledger;
- baseline learner adequacy table;
- process-status table;
- fold-level evidence;
- JSON manifest with SHA-256 hashes, split digest and selection receipt.

This makes a completed analysis reviewable without reconstructing hidden state from a notebook.

## What the user still decides

The software automates execution, not ecological meaning. The user/research team remains responsible for prospectively approving:

- the ecological process taxonomy;
- the metadata/rules that define direct, derived, proxy and composite representations;
- the occurrence-dependent `M`/background recipe;
- the predictive adequacy threshold;
- the base learner family and model-complexity universe.

The software then enforces those choices consistently and keeps the answer-check outside learning.
