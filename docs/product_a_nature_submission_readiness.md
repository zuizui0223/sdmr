# Product A — Nature Ecology & Evolution submission readiness

Status: **scientific development complete; submission-production gate**.

This document does not authorize additional Product-A tuning, threshold changes, favorable-seed searches or empirical rescue.

## Scientific gate — COMPLETE

The final controlled-truth identification sequence is now:

1. earlier prediction/stability tests showed that predictive adequacy does not guarantee process truth;
2. v2.3 showed that ecological model-set sharpening can create false necessity;
3. v2.4–v2.6 established a separate exclusion-based necessity branch that controlled false-required claims but remained broad (`required_processes` empty in 9/9 validation taxa);
4. v2.7.2 supplied a predecessor consensus-first process-stability proof of concept, but its 55/60 exact process-set result was later stress-tested under independently varying process presence;
5. the stronger factorial truth test varied temperature, water and soil across all seven non-empty process sets and falsified the predecessor stable intersection: **22/35 exact**, versus **25/35** for the AUC winner;
6. a process-specific counterfactual niche-recovery estimator was then calibrated using discovery seeds 4201–4205 only;
7. unused validation seeds 4301–4305 passed every frozen gate: **30/35 exact complete process sets**;
8. with estimator and thresholds unchanged, unused replication seeds 4401–4410 produced **65/70 exact process sets (92.9%)**, versus **56/70 (80.0%)** for AUC and **49/70 (70.0%)** for the predecessor stable core;
9. the fresh empirical v2.8.4 endpoint remains `empirical_confirmation_not_supported` / `not_promoted`, with ecological/AUC candidate and predictor identity in **108/108** matched cells.

The supported new estimand is **process membership under the declared candidate/process representation registry**, inferred from ecological recovery lost when every declared representation of one process is excluded from the prediction-adequate candidate class. It is not physiological causation, fundamental-niche necessity or complete real-world proxy closure.

## Replicated process-identification result

Independent replication (`n=70`, seeds 4401–4410):

- counterfactual exact process-set recovery: **65/70 = 92.9%**;
- AUC winner: **56/70 = 80.0%**;
- predecessor stable core: **49/70 = 70.0%**;
- exact recovery when ecological fitted models disagreed: **27/30 = 90.0%**;
- temperature sensitivity/specificity: **1.000 / 0.933**;
- water sensitivity/specificity: **1.000 / 0.933**;
- soil sensitivity/specificity: **0.975 / 1.000**;
- paired exact sets: both exact 51, counterfactual-only 14, AUC-only 5, both wrong 0.

Authoritative replication provenance: workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

## Main manuscript gate — COMPLETE

Primary file: `docs/product_a_nature_ecology_evolution_article_draft.md`.

Current title:

**Counterfactual niche recovery identifies environmental processes beyond model selection**

Current Nature QA records:

- abstract: **197 words**;
- main text: **2,220 words**;
- abstract limit <=200;
- main-text limit <=3,500;
- required Results structure present;
- no Discussion subheadings;
- no prohibited causal/fundamental-niche or empirical-superiority claim;
- required counterfactual headline tokens and unchanged v2.8.4 boundary present.

## Figure gate — COMPLETE

1. Fig.1: predictive/model-selection logic versus ecological identification;
2. Fig.2: ecological sharpening can create false necessity;
3. Fig.3: **counterfactual process identification**, showing fresh 35-case validation, unchanged 70-case replication, process-specific sensitivity/specificity and all seven process-set results;
4. Fig.4: fresh empirical selector collapse and formal non-support.

Figure 3 was visually QA'd after moving the model-disagreement annotation away from plotted data.

## Reporting / reproducibility gate — GREEN

Current PR head validated successfully through:

- Nature Product-A reporting workflow: run `34018123641` — **success**;
- standard tests: run `34018123624` — **success** on Python 3.10, 3.11, 3.12, 3.13 and geo-rasterio;
- factorial discovery diagnostics: run `34018123657` — **success**;
- factorial process recovery: run `34018123693` — **success**;
- counterfactual fresh validation: run `34018123733` — **success**;
- unchanged counterfactual replication: run `34018123678` — **success**;
- real GBIF × CHELSA API smoke: run `34018123660` — **success**.

Nature reporting artifact: `9984569491`, digest `sha256:f7bb7a0173c459900da1874fadae34cac006d1677c58761299b22d84f314ef30`.

## Literature-positioning gate — COMPLETE

Do not claim novelty for prediction versus explanation, functional accuracy limitations, spatial cross-validation, collinearity/variable-importance instability, Rashomon/model-set uncertainty or presence-only sampling-bias correction.

The stronger contribution is now concrete: **process-specific counterfactual ecological-recovery loss was prospectively developed after a predecessor failed a factorial process-presence test, then passed a fresh validation and an unchanged independent replication.**

## Remaining external inputs

1. final author list/order/affiliations/corresponding author;
2. CRediT, funding/grants, acknowledgements and competing interests;
3. immutable release/archive DOI;
4. journal portal metadata and any reviewer suggestions/declarations;
5. co-author approval.

## Submission decision

The scientific/repository package is ready for a **Nature Ecology & Evolution Article first shot** once the external metadata and permanent archive are supplied.

A breadth/priority rejection should transfer without new Product-A science to **Nature Communications**, then **Methods in Ecology and Evolution**.

## Hard stop

Do not alter the frozen counterfactual thresholds, process sets, validation/replication seeds, candidate library or perturbations. Do not rerun or reinterpret v2.8.4 to seek empirical promotion. Product B remains outside this manuscript.
