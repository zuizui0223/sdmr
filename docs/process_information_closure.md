# Generic process-information closure

Status: **generic implementation / not a new Product-A scientific experiment**

This API generalizes the ecological-identification logic without reopening any frozen Product-A endpoint.

The core distinction is:

- **process necessity**: does an adequate alternative survive after every *declared* representation carrying a process is excluded?
- **process stability**: do independent ecological analyses support the same process information even when they select different fitted models?

These are separate estimands.

## 1. Declare a many-to-many process-information registry

One predictor may carry more than one process. This is the key difference from a one-predictor/one-process alias table.

```python
import pandas as pd

registry = pd.DataFrame([
    {"predictor": "bio1",      "process": "thermal", "role": "direct"},
    {"predictor": "gdd5",      "process": "thermal", "role": "derived"},
    {"predictor": "elevation", "process": "thermal", "role": "proxy"},
    {"predictor": "pet",       "process": "thermal", "role": "composite"},
    {"predictor": "bio12",     "process": "water",   "role": "direct"},
    {"predictor": "cmi",       "process": "water",   "role": "derived"},
    {"predictor": "pet",       "process": "water",   "role": "composite"},
    {"predictor": "soil_n",    "process": "soil",    "role": "direct"},
])
```

Here `pet` belongs to both the thermal and water closures. Therefore it is removed in both knockouts.

Allowed representation roles are:

- `direct`
- `derived`
- `proxy`
- `composite`

The classification is scientific metadata and should be frozen before outcome inspection.

## 2. Inspect the declared closure

```python
from sdmr.process_information_closure import (
    process_information_closure,
    summarize_process_information_closures,
)

water = process_information_closure(registry, "water")
# ('bio12', 'cmi', 'pet')

summary = summarize_process_information_closures(
    registry,
    process_universe=("thermal", "water", "soil"),
)
```

This is the auditable answer to: **what information are we claiming to remove when we knock out this process?**

It is not an automated causal-discovery step. If a real proxy is omitted from the registry, the knockout is only as complete as the declared closure.

## 3. Freeze closure-aware knockout routes

```python
from sdmr.process_information_closure import (
    freeze_process_information_knockout_registry,
)

knockouts = freeze_process_information_knockout_registry(
    base_candidates=("glm", "gam"),
    ecological_predictors=(
        "bio1", "gdd5", "elevation", "pet",
        "bio12", "cmi", "soil_n",
    ),
    process_registry=registry,
    process_universe=("thermal", "water", "soil"),
    observation_predictors=("recording_bias",),
)
```

For the water knockout, `bio12`, `cmi` and `pet` are removed together. `recording_bias` is retained because observation-process variables are not ecological process representations.

The output is a complete base-candidate × process registry with deterministic knockout labels.

## 4. Classify necessity from complete route evidence

After each frozen knockout route is evaluated in all predeclared contexts, provide a ledger with:

- `candidate`
- `context`
- `complete`
- `adequate`

For example:

```python
from sdmr.process_information_closure import classify_process_necessity

necessity = classify_process_necessity(
    evidence,
    knockouts,
    expected_contexts=("spatial_split_a", "spatial_split_b"),
)
```

The three scientific states are:

- `refuted_as_necessary`: at least one complete process-knockout route remains adequate in every required context;
- `required_by_evidence_contract`: every declared route is complete and none provides an adequate witness;
- `unresolved`: the declared routes are valid but evidence is incomplete or missing.

Malformed evidence is not silently converted to `unresolved`. Missing boolean flags, undeclared candidates and undeclared contexts fail closed with an exception, while duplicate/missing required route contexts prevent that route from being treated as complete.

`required_by_evidence_contract` is deliberately **not** a causal, physiological or fundamental-niche necessity claim.

## 5. Measure process stability separately

```python
from sdmr.process_information_closure import build_process_stability_certificate

stability = build_process_stability_certificate({
    "canonical": ("thermal", "water"),
    "robust": ("water", "soil"),
})

stability.stable_process_core
# ('water',)

stability.contested_processes
# ('soil', 'thermal')
```

This certificate says which process information persists across independently defined analyses. It does **not** say that the stable core is necessary.

## 6. SDM example

Question:

> Is water information necessary to explain the species distribution under the declared model/data system?

Declare all direct, derived, proxy and composite water representations before evaluation. Knock them out together. If an adequate alternative model survives across all required spatial/data perturbations, water necessity is refuted under the contract. If all frozen water-knockout routes are complete and fail adequacy, water is required under the evidence contract. If valid route evidence is incomplete, return `unresolved`.

This is stronger than asking whether `bio12` has high variable importance because the process closure can include `bio12`, aridity indices, moisture balance and mixed composites together.

## 7. Phenology example

For flowering date, a thermal closure could include spring temperature (`direct`), GDD (`derived`), elevation (`proxy`) and a hydrothermal index (`composite`). The same API tests whether thermal information is indispensable after those representations are removed together.

## 8. Trait–environment example

For SLA or leaf economics, a dryness closure could combine precipitation fields, aridity/VPD derivatives, topographic moisture proxies and climate-water composites. Necessity and stability are then reported separately rather than inferred from one selected regression or machine-learning model.

## Scope boundary

The implementation provides a **declaration and inference framework**, not an automatic discovery of all real-world proxies. A scientifically strong application must justify the registry prospectively. Complete proxy/composite closure remains an empirical design problem, not something the software can infer safely from the same outcome used for testing.
