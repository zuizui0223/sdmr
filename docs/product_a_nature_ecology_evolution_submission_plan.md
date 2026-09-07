# Product A — Nature Ecology & Evolution submission track

Status: **submission-production plan; counterfactual process-identification science complete**.

## First Nature-family target

**Nature Ecology & Evolution — Article**

Current title:

**Counterfactual niche recovery identifies environmental processes beyond model selection**

## Nature-level central claim

> **Among prediction-adequate occurrence-only SDMs, environmental-process membership can be identified by the ecological niche recovery that becomes unattainable when every declared representation of that process is excluded.**

Under independently varying temperature, water and soil truth, the frozen estimator recovered complete generating-process sets in **30/35 fresh validation cases** and **65/70 unchanged independent replication cases**.

This is process membership under a declared representation registry, not physiological causation, fundamental-niche necessity or complete real-world proxy closure.

## Evidence spine

1. **Why model selection is insufficient.** Prediction and stable response surfaces can coexist with incorrect process attribution; ecological Pareto pruning can create false necessity.
2. **Stronger falsification.** With all seven non-empty temperature/water/soil process combinations, the predecessor stable-process intersection recovered only **22/35** complete process sets, below its frozen support threshold.
3. **Counterfactual estimator.** For each process, compare best attainable held-out Schoener-D niche overlap among prediction-adequate process-containing models versus models excluding all declared representations of that process, across five frozen perturbations.
4. **Fresh validation.** Thresholds calibrated only on 4201–4205 were frozen before 4301–4305; exact recovery **30/35**, with every T/W/S sensitivity/specificity gate ≥0.80.
5. **Independent replication.** Method and thresholds unchanged on 4401–4410: exact recovery **65/70**, versus AUC **56/70** and predecessor **49/70**; process truth exact **27/30** when ecological fitted models disagreed.
6. **Necessity remains separate.** The v2.6 exclusion certificate controls false-required claims but remains broad; it is a stronger/different estimand.
7. **Empirical boundary remains unfavorable.** v2.8.4 strict improvement **0/3**, `empirical_confirmation_not_supported`, `not_promoted`, and ecological/AUC selected the same model in **108/108** matched cells.

## Main positive numerical endpoint

Independent unchanged replication (`n=70`):

- complete process-set exact recovery: **65/70 = 92.9%**;
- temperature: sensitivity **1.000**, specificity **0.933**;
- water: sensitivity **1.000**, specificity **0.933**;
- soil: sensitivity **0.975**, specificity **1.000**;
- ecological fitted-model disagreement: 30/70; exact process membership **27/30 = 90.0%**.

Paired descriptive comparison against AUC:

- both exact 51;
- counterfactual only exact 14;
- AUC only exact 5;
- both wrong 0.

Do not convert the paired count into a post-outcome universal-superiority endpoint.

## Counterfactual score and threshold governance

Prediction adequacy remains a gate: mean presence-background rank ≥0.51 and mean−SEM ≥0.50.

For process `p`, calculate across each frozen perturbation:

`(best Schoener D among adequate p-containing candidates − best Schoener D among adequate p-excluded candidates) / D range among adequate candidates`.

Process aliases are collapsed before exclusion; for example, removing temperature removes both `temperature` and `temp_proxy` in the declared registry.

Discovery-only frozen thresholds:

- temperature **0.2653964368**;
- water **0.0671670999**;
- soil **0.3342415841**.

These values were frozen before fresh validation and remained unchanged in the 70-case replication.

## Relationship to predecessor Product-A evidence

### v2.3 — false necessity

Ecological model-set sharpening can remove viable alternatives and create a false necessary-process core.

### v2.6 — exclusion-based necessity safety

- false-required = 0;
- possible-process recall = 1.0;
- possible-process precision ≈0.467;
- `required_processes` empty in 9/9 validation taxa.

This protects against unsupported necessity but is not the process-membership estimator.

### v2.7.2 — predecessor proof of concept

The old stable core recovered 55/60 process sets in the original suite and corrected observation-process misattribution. But temperature and water were invariant true processes, and the stronger factorial test later reduced the predecessor to 22/35. Use v2.7.2 as developmental/mechanistic evidence, not the final performance headline.

## Fresh empirical observational equivalence

The frozen v2.8.4 endpoint remains:

- prediction guardrail passed;
- ecological nondomination 3/3;
- strict ecological improvement 0/3;
- `empirical_confirmation_not_supported`;
- `not_promoted`;
- candidate and selected-predictor identity ecological vs AUC = **108/108**.

Thus real-data process truth is not directly established in this manuscript. The new controlled-truth success must not be used to rewrite this result.

## Prior-art / novelty boundary

Do not claim novelty for prediction versus explanation, discrimination versus functional accuracy, spatial CV/tuning, collinearity/variable-importance instability, Rashomon model uncertainty or standard presence-only sampling-bias correction.

Defensible novelty now centers on:

1. showing prospectively that ecologically better model selection and even a process-intersection predecessor can fail stronger process truth;
2. defining an operational **process-specific counterfactual ecological-recovery loss** over an adequate model class rather than reading process identity from one selected model;
3. excluding all declared representations/aliases of a process before measuring lost niche recovery;
4. validating process membership prospectively on unused truth and then independently replicating the unchanged estimator;
5. preserving process membership, process necessity and unresolved empirical evidence as distinct inferential objects.

## Four main figures

1. **Prediction is not identification** — information barriers and inferential objects.
2. **Selected good models can create false necessity** — v2.3 and necessity-safety response.
3. **Counterfactual process recovery** — 30/35 validation, 65/70 replication, T/W/S sensitivity/specificity and all seven process combinations.
4. **Fresh empirical non-identification** — 108/108 selector identity plus strict improvement 0/3.

## Editorial stress test

A Nature Ecology & Evolution editor should see immediately:

1. **Concrete method:** a defined process-level counterfactual statistic, not only an argument about interpretation.
2. **Prospective falsification:** the predecessor fails 22/35 under stronger truth and is not rescued.
3. **Prospective validation and replication:** 30/35 fresh and 65/70 unchanged independent replication with process-specific operating characteristics.
4. **Ecological meaning:** the estimator asks what niche-recovery capacity disappears when a process information channel is removed.
5. **Claim discipline:** real plant process truth remains unestablished; empirical v2.8.4 remains non-supported.

## Journal ladder

1. **Nature Ecology & Evolution — Article**.
2. **Nature Communications** if rejected mainly for empirical breadth/priority.
3. **Methods in Ecology and Evolution** as strongest specialist-method fallback.

## Submission state

Scientifically complete in the repository:

- final counterfactual result document and claim spine;
- Nature Article and cover letter;
- Online Methods;
- 35-case validation and 70-case replication contracts/artifacts;
- four-main-figure workflow and committed source data;
- Extended Data plan;
- Reporting Summary and software checklist;
- Data/Code Availability and `CITATION.cff`;
- fail-closed manuscript QA.

Remaining external inputs after final CI/visual QA: final author/order/affiliations/corresponding author, CRediT/funding/competing interests/co-author approval and immutable archive DOI/release.

## Stop rule

The new counterfactual estimator has already undergone discovery, fresh validation and unchanged independent replication. **Do not retune it, add favorable seeds/process subsets or modify thresholds/candidate library/perturbations.** No new Product-A scientific endpoint is needed for this manuscript unless a future reviewer explicitly requires a genuinely new prospectively contracted experiment.
