# Generic process-information closure

Status: **generic implementation / not a new Product-A scientific experiment**

This API generalizes the ecological-identification logic without reopening any frozen Product-A endpoint.

The core distinction is:

- **predictive/model learning**: fit any chosen learner on the allowed training data and retained predictors;
- **process necessity**: does an adequate alternative survive after every *declared* representation carrying a process is excluded?;
- **process stability**: do independent ecological analyses support the same process information even when they select different fitted models?

These are separate tasks and estimands.

## 0. What is actually learned?

The process-information layer is **model-agnostic**. It does not replace GLM, GAM, MaxEnt/logistic regression, boosted trees, random forests or other ecological learners.

A normal use is:

1. freeze the process taxonomy, representation rules, data splits and adequacy rule before outcome inspection;
2. fit the chosen learner on the model-pool/training data;
3. for each process knockout, refit the same learner using only the retained predictors;
4. evaluate each frozen route in every predeclared validation context;
5. write a route ledger containing `candidate`, `context`, `complete` and `adequate`;
6. classify necessity from that ledger;
7. measure process stability separately across independently defined analyses/selectors if desired.

The learner can therefore be simple or complex. The important scientific constraint is that the **adequacy criterion and information barriers are frozen before the process claim is evaluated**.

For example, in an SDM the learner could be penalized logistic regression or MaxEnt. In phenology it could be a GAM. In trait–environment work it could be a phylogenetic regression or tree-based learner. The closure API only needs the final complete/adequate evidence for each frozen knockout route.

Do not learn the process taxonomy from the same outcome, fitted coefficients or variable importance that will later be used to test necessity. That would make the information closure outcome-dependent.

## 1. Semi-automatic classification: users do not need to label every predictor row

The scientifically required human input is **not** a manual label on every raster. The recommended review unit is:

- the process taxonomy (`thermal`, `water`, `soil`, ...);
- an auditable rule table based on predictor names and external metadata;
- only the unmatched or conflicting cases flagged by the software.

The rule table can use:

- exact predictor names;
- regular-expression name families;
- source family (for example CHELSA or SoilGrids);
- units;
- any combination of those fields.

Example metadata:

```python
import pandas as pd

predictors = pd.DataFrame([
    {"predictor": "bio1",  "source_family": "CHELSA",   "units": "degC"},
    {"predictor": "gdd5",  "source_family": "CHELSA",   "units": "degree_days"},
    {"predictor": "pet",   "source_family": "CHELSA",   "units": "mm"},
    {"predictor": "bio12", "source_family": "CHELSA",   "units": "mm"},
    {"predictor": "soil_n","source_family": "SoilGrids","units": "cg/kg"},
])
```

Example predeclared rules:

```python
rules = pd.DataFrame([
    {"rule_id": "thermal_bio1", "process": "thermal", "role": "direct",    "predictor_exact": "bio1"},
    {"rule_id": "thermal_gdd",  "process": "thermal", "role": "derived",   "predictor_pattern": r"^gdd", "source_family": "CHELSA"},
    {"rule_id": "thermal_pet",  "process": "thermal", "role": "composite", "predictor_exact": "pet"},
    {"rule_id": "water_pet",    "process": "water",   "role": "composite", "predictor_exact": "pet"},
    {"rule_id": "water_bio12",  "process": "water",   "role": "direct",    "predictor_exact": "bio12", "units_pattern": r"^mm$"},
    {"rule_id": "soil_source",  "process": "soil",    "role": "direct",    "source_family": "SoilGrids"},
])
```

Apply them automatically:

```python
from sdmr.process_registry_proposal import (
    propose_process_information_registry,
    freeze_process_registry_proposal,
)

proposal = propose_process_information_registry(predictors, rules)
```

If every predictor is covered consistently, `review_required` is false and the whole proposal can be frozen in one step:

```python
registry = freeze_process_registry_proposal(
    proposal,
    expected_predictors=tuple(predictors["predictor"]),
)
```

If a predictor is not matched, it is returned as `status='unmatched'`. If two rules assign incompatible representation roles to the same predictor-process link, it is returned as `status='conflict'`. Those cases block freezing until the rule table is revised.

Multiple *processes* for one predictor are not a conflict. They are how shared composites are represented. For example, `pet` can be proposed as both `thermal/composite` and `water/composite`.

Thus the user normally reviews **the taxonomy, the rule table, and flagged exceptions**, rather than hand-classifying every variable.

A future LLM/ontology classifier could be used to propose rules or labels from variable descriptions and literature, but it should remain proposal-only and must not inspect the ecological outcome used for the later necessity test.

## 2. Declare a many-to-many process-information registry

One predictor may carry more than one process. This is the key difference from a one-predictor/one-process alias table.

```python
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

## 3. Inspect the declared closure

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

## 4. Freeze closure-aware knockout routes

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

The output is a complete base-candidate × process registry with deterministic knockout labels. Each row tells the fitting code exactly which predictors remain for that model refit.

## 5. Learn/refit each route and classify necessity

The package intentionally does not force one estimator. A caller loops over the frozen route registry and fits its selected learner using `retained_ecological_predictors` for every required context.

After each route is evaluated, provide a ledger with:

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

## 6. Measure process stability separately

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

## 7. SDM example

Question:

> Is water information necessary to explain the species distribution under the declared model/data system?

Declare all direct, derived, proxy and composite water representations before evaluation. Knock them out together. Refit the same SDM learner using the retained predictor set in every frozen context. If an adequate alternative model survives across all required spatial/data perturbations, water necessity is refuted under the contract. If all frozen water-knockout routes are complete and fail adequacy, water is required under the evidence contract. If valid route evidence is incomplete, return `unresolved`.

This is stronger than asking whether `bio12` has high variable importance because the process closure can include `bio12`, aridity indices, moisture balance and mixed composites together.

## 8. Phenology example

For flowering date, a thermal closure could include spring temperature (`direct`), GDD (`derived`), elevation (`proxy`) and a hydrothermal index (`composite`). The fitting learner might be a GAM. The same closure API tests whether thermal information is indispensable after those representations are removed together.

## 9. Trait–environment example

For SLA or leaf economics, a dryness closure could combine precipitation fields, aridity/VPD derivatives, topographic moisture proxies and climate-water composites. The fitting learner could be a phylogenetic regression, mixed model or machine-learning model. Necessity and stability are then reported separately rather than inferred from one selected regression or variable-importance score.

## Scope boundary

The implementation provides a **declaration and inference framework**, not an automatic discovery of all real-world proxies. A scientifically strong application must justify the taxonomy/rules prospectively. Complete proxy/composite closure remains an empirical design problem, not something the software can infer safely from the same outcome used for testing.
