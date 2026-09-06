# Product A Nature submission package index

Status: **scientific and reporting package complete on current manuscript branch**

Target: **Nature Ecology & Evolution — Article**

Authoritative scientific logic: `docs/product_a_final_claim_spine.md`

Authoritative counterfactual result: `docs/product_a_counterfactual_process_recovery_result_2026-09-06.md`

## Core manuscript files

- `docs/product_a_nature_ecology_evolution_article_draft.md` — Nature Article draft.
- `docs/product_a_nature_ecology_evolution_online_methods.md` — Online Methods.
- `docs/product_a_nature_ecology_evolution_cover_letter.md` — cover-letter draft.
- `docs/product_a_nature_figure_legends.md` — main-figure and Extended Data legends.
- `docs/product_a_nature_extended_data_plan.md` — Extended Data/source-data structure.
- `docs/product_a_nature_reporting_summary_draft.md` — Nature reporting-summary draft.
- `docs/product_a_nature_software_checklist_draft.md` — software-checklist draft.
- `docs/product_a_nature_data_code_availability.md` — Data/Code Availability draft.
- `CITATION.cff` — software citation metadata.

## Claim, novelty and readiness controls

- `docs/product_a_final_claim_spine.md` — authoritative claim hierarchy.
- `docs/product_a_manuscript_claim_audit.md` — claim ceiling and prohibited overreach.
- `docs/product_a_nature_logic_consistency_audit.md` — estimator/estimand separation, including the counterfactual successor.
- `docs/product_a_novelty_literature_audit.md` — novelty boundary.
- `docs/product_a_nature_reference_boundary.md` and `docs/product_a_nature_reference_shortlist.md` — verified literature positioning.
- `docs/product_a_nature_submission_readiness.md` — current submission gate.
- `docs/product_a_nature_editorial_readiness_2026-09-04.md` and `docs/product_a_nature_editorial_gate_audit.md` — editorial stress tests.

## Final scientific spine

1. Prediction and stable environmental recovery do not by themselves identify generating process membership.
2. Ecological Pareto/model-set sharpening can create false necessity.
3. Exclusion-based necessity (v2.4–v2.6) controls false-required claims but may remain broad; it is a separate, stronger necessity estimand.
4. The v2.7.2 consensus-first stable core was a useful predecessor proof of concept, but a stronger factorial test with independently varying temperature/water/soil presence reduced predecessor exact recovery to **22/35**.
5. Product A therefore moved to **process-specific counterfactual niche recovery**: measure how much prediction-adequate ecological recovery is lost when all declared representations of one process are removed.
6. Fresh validation on unused seeds 4301–4305 recovered **30/35** complete process sets.
7. With method and thresholds unchanged, independent replication on unused seeds 4401–4410 recovered **65/70 (92.9%)** complete process sets versus **56/70 (80.0%)** for AUC-selected winners and **49/70 (70.0%)** for the predecessor stable core.
8. Fresh empirical v2.8.4 remains `empirical_confirmation_not_supported` / `not_promoted`; ecological and AUC roles instantiated identical candidates and predictors in **108/108** matched cells.

## Counterfactual process-identification implementation

- `src/sdmr/counterfactual_process_recovery.py` — truth-free process-specific counterfactual score/classification.
- `src/sdmr/factorial_process_recovery_experiment.py` — seven-process-set factorial known-truth generator/evaluation.
- `src/sdmr/counterfactual_process_validation.py` — fresh 35-case validation.
- `src/sdmr/counterfactual_process_replication.py` — unchanged 70-case independent replication.
- `configs/product_a_factorial_process_recovery_contract.json` — predecessor falsification/factorial contract.
- `configs/product_a_counterfactual_process_validation_contract.json` — frozen thresholds and fresh validation gate.
- `configs/product_a_counterfactual_process_replication_contract.json` — unchanged replication contract.
- `tests/test_counterfactual_process_recovery.py` and `tests/test_factorial_process_recovery_experiment.py` — scientific-contract tests.

Frozen process thresholds:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

## Reproducible reporting

- `.github/workflows/nature-product-a-reporting.yml` — Nature reporting/figure workflow.
- `scripts/check_nature_manuscript_format.py` — fail-closed Article format and headline-claim QA.
- `scripts/build_nature_product_a_concept_figures.py` — Figs.1–2.
- `scripts/build_nature_product_a_figures.py` — predecessor/empirical reporting reconstruction, including Fig.4.
- `scripts/render_nature_fig3_counterfactual.py` — final counterfactual Fig.3.

## Main source-data files

- `source_data/nature_fig2_v23.csv`
- `source_data/nature_fig3_counterfactual_methods.csv`
- `source_data/nature_fig3_counterfactual_process_summary.csv`
- `source_data/nature_fig3_counterfactual_process_sets.csv`
- `source_data/nature_fig4_full.csv`
- `source_data/nature_fig4_summary.csv`
- predecessor/supporting v2.6/v2.7.2/v2.7.3 tables under `source_data/nature_extended_*` and `source_data/nature_v272_*`.

## Frozen scientific/reporting provenance

### Counterfactual fresh validation

- validation seeds: 4301–4305;
- complete denominator: 35 cases;
- exact process sets: **30/35**;
- no post-outcome threshold change permitted.

### Counterfactual independent replication

- authoritative workflow: `34015900603`;
- artifact: `9983940439`;
- digest: `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`;
- seeds: 4401–4410;
- complete denominator: 70 cases;
- exact process sets: **65/70**;
- AUC exact: **56/70**;
- predecessor exact: **49/70**;
- exact counterfactual recovery under ecological-model disagreement: **27/30**;
- method changed after fresh validation: **false**.

### Fresh empirical boundary

- v2.8.4 terminal decision: `empirical_confirmation_not_supported`;
- separate promotion decision: `not_promoted`;
- ecological/AUC candidate and selected-predictor identity: **108/108**.

## Current validated branch state

Current submission-facing validation is green:

- Nature Product-A reporting — run `34018123641`, **success**;
- standard tests — run `34018123624`, Python 3.10/3.11/3.12/3.13 and geo-rasterio all **success**;
- factorial discovery diagnostics — run `34018123657`, **success**;
- factorial process recovery — run `34018123693`, **success**;
- counterfactual fresh validation — run `34018123733`, **success**;
- counterfactual independent replication — run `34018123678`, **success**;
- real GBIF × CHELSA API diagnostic smoke — run `34018123660`, **success**.

Nature reporting artifact `9984569491`, digest `sha256:f7bb7a0173c459900da1874fadae34cac006d1677c58761299b22d84f314ef30`.

Article QA: abstract **197 words**, main text **2,220 words**, `FORMAT_QA=PASS`.

## Scientific hard stop

Scientific development is complete. Do not change counterfactual thresholds, process sets, discovery/validation/replication seeds, candidate library, perturbations or v2.8.4 empirical definitions after these outcomes. Product B remains separate.

## Remaining submission inputs

Only external/human submission metadata remain:

- final author list/order, affiliations and corresponding author;
- CRediT contributions;
- funding/grants and acknowledgements;
- competing-interests declaration;
- co-author approval if applicable;
- immutable release/permanent archive DOI;
- journal-portal metadata and reviewer declarations/suggestions as required.
