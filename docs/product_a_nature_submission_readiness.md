# Product A — Nature Ecology & Evolution submission readiness

Status: **scientific endpoint closed; Nature submission-production gate**.

This document does not authorize any additional Product-A experiment.

## Scientific gate — COMPLETE AFTER LOGIC AUDIT

The manuscript now uses five Nature-level Results and explicitly separates two positive process-level estimands:

1. prediction/stability does not guarantee process truth;
2. ecological Pareto sharpening can create false necessity;
3. **exclusion-based necessity:** v2.6 controls false-required claims (false-required=0, possible-process recall=1.0) but leaves a broad possible-process set (precision≈0.467);
4. **consensus-first process stability:** v2.7.2 stable process core has P=0.9889, R/F1=0.9833 across 60 unused cases, with process-set consensus 50/60 versus exact-model consensus 38/60;
5. fresh empirical v2.8.4 remains `empirical_confirmation_not_supported` / `not_promoted`, with strict improvement 0/3 and ecological/AUC candidate+predictor identity 108/108.

The v2.7.2 stable process core is not the v2.6 process-exclusion necessary set. Repository logic audit: `docs/product_a_nature_logic_consistency_audit.md`.

## Main manuscript gate

Primary file: `docs/product_a_nature_ecology_evolution_article_draft.md`.

Automated Nature QA now checks:

- abstract <=200 words;
- main text <=3,500 words;
- five corrected Results headings;
- Discussion has no topical subheadings;
- frozen headline evidence remains present;
- explicit token that the stable core is `not a process-exclusion necessity set`;
- no prohibited empirical/fundamental-niche overclaim;
- no direct attribution of 0.9889/0.9833 to falsification-first exclusion.

The exact word count must be revalidated on the current head after the logic correction.

## Literature-positioning gate — COMPLETE

The manuscript concedes the inherited literature on prediction versus explanation, discrimination versus functional accuracy, collinearity, variable-importance instability, spatial CV/tuning and Rashomon/model-class reasoning.

Novelty is now restricted to:

- prospective ecological-recovery sharpening → false necessity;
- exclusion-based necessity with protected unresolved states;
- a separate consensus-first process-stability result that exceeds exact-model stability;
- observation/evidence-state and deterministic-execution safeguards;
- fresh empirical observational equivalence preserved without rescue.

## Figure gate — COMPLETE SCIENTIFICALLY

1. Fig.1: winner selection versus ecological-identification objects;
2. Fig.2: ecological sharpening → false necessity → exclusion-based replacement;
3. Fig.3: **consensus-first process stability** across six families, not necessity precision;
4. Fig.4: empirical selector collapse and formal non-support.

Figure legends and Extended Data now carry the same estimator separation.

## Methods / reporting gate — COMPLETE AS DRAFT

Prepared:

- Nature cover letter;
- Online Methods;
- Extended Data/source-data plan;
- figure legends;
- Reporting Summary and software checklist drafts;
- Data/Code Availability;
- `CITATION.cff`;
- source-data tables;
- corrected claim audit and logic-consistency audit.

## CI gate — REVALIDATE CURRENT HEAD

Previous head was fully green across Python 3.10–3.13, geo-rasterio, Nature reporting and real-API smoke. The current head contains reporting-only logic corrections and must again finish green; no scientific failure may be waived.

## Remaining external inputs

1. final author list/order/affiliations/corresponding author;
2. CRediT, funding/grants, acknowledgements and competing interests;
3. immutable release/archive DOI;
4. journal portal metadata and any reviewer suggestions/declarations;
5. co-author approval.

## Submission decision

If current-head QA/CI is green and external metadata are supplied, the package is scientifically ready for a **Nature Ecology & Evolution Article first shot**.

A breadth/priority rejection should transfer without new Product-A analysis to **Nature Communications**, then **Methods in Ecology and Evolution**.

## Hard stop

No new empirical endpoint, taxon replacement, M/candidate/threshold change, selector-divergence search, retroactive proxy closure or Product-B insertion.