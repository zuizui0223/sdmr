# Product A Nature submission package index

Status: **scientific/reporting package synchronized to the completed frozen real positive-control audit; external submission metadata/archive still required**

Target: **Nature Ecology & Evolution — Article**

Authoritative scientific logic: `docs/product_a_final_claim_spine.md`

Authoritative controlled-truth result: `docs/product_a_counterfactual_process_recovery_result_2026-09-06.md`

Authoritative real positive-control result: `docs/product_a_real_positive_control_result_2026-09-07.md`

## Core manuscript files

- `docs/product_a_nature_ecology_evolution_article_draft.md` — main Article draft with real positive-control non-support integrated.
- `docs/product_a_nature_ecology_evolution_online_methods.md` — Online Methods including both frozen empirical endpoints and the inner-CV/outer-transfer boundary.
- `docs/product_a_nature_ecology_evolution_cover_letter.md` — cover letter stating both the controlled-truth success and empirical non-support.
- `docs/product_a_nature_figure_legends.md` — main/Extended Data legends.
- `docs/product_a_main_figure_evidence_spec.md` — frozen figure contract.
- `docs/product_a_nature_reporting_summary_draft.md` — reporting-summary draft.
- `docs/product_a_nature_software_checklist_draft.md` — software checklist.
- `docs/product_a_nature_data_code_availability.md` — Data/Code Availability draft.
- `CITATION.cff` — software citation metadata.

## Claim, novelty and readiness controls

- `docs/product_a_final_claim_spine.md` — authoritative claim hierarchy.
- `docs/product_a_manuscript_claim_audit.md` — explicit controlled-truth versus empirical claim ceiling.
- `docs/product_a_nature_editorial_gate_audit.md` — Nature-level editorial stress test with real positive-control non-support.
- `docs/product_a_nature_submission_readiness.md` — current submission gate.
- `docs/product_a_novelty_literature_audit.md`, `docs/product_a_nature_reference_boundary.md`, `docs/product_a_nature_reference_shortlist.md` — literature/novelty boundary.

## Final scientific spine

1. Prediction and stable response recovery do not by themselves identify generating process membership.
2. Ecological model-set sharpening can create false necessity.
3. Exclusion-based necessity (v2.4–v2.6) is a separate stronger estimand and remained broad.
4. The v2.7.2 stable-process predecessor looked strong in a suite where T/W were invariant, then failed a stronger factorial ON/OFF test: **22/35 exact**.
5. Product A therefore moved to **process-specific counterfactual ecological recovery** under complete declared process exclusion.
6. Fresh unused validation recovered **30/35** complete process sets.
7. Unchanged independent replication recovered **65/70 = 92.9%**, versus **56/70** for AUC and **49/70** for the predecessor; process sets remained exact in **27/30** cases despite ecological-model disagreement.
8. v2.8.4 remained `empirical_confirmation_not_supported` / `not_promoted`, with ecological/AUC candidate/predictor identity in **108/108** cells.
9. A stronger frozen real positive-control audit also failed: **plants 2/4**, **nonplants 1/4**, **water 0/4**; 24/24 pipelines completed, 21/24 had an adequate candidate, 17/24 had two-sided comparisons.
10. Therefore the paper supports a controlled-truth process-membership estimator and retains **general real-data process identification as unvalidated/not supported by the current empirical system**.

## Counterfactual implementation

- `src/sdmr/counterfactual_process_recovery.py`
- `src/sdmr/factorial_process_recovery_experiment.py`
- `src/sdmr/counterfactual_process_validation.py`
- `src/sdmr/counterfactual_process_replication.py`
- frozen contracts under `configs/product_a_*counterfactual*` and `configs/product_a_factorial_process_recovery_contract.json`.

Frozen thresholds:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

## Real positive-control audit

- `docs/product_a_real_positive_control_result_2026-09-07.md` — authoritative interpretation.
- `scripts/audit_real_positive_control_results.py` — no-refit result audit.
- `source_data/real_positive_control_v1_taxon_audit.csv` — eight taxon outcomes.
- `source_data/real_positive_control_v1_cell_audit.csv` — 24 taxon × M cells.

The audit preserves unavailable/empty adequate classes and boundary-coded scores rather than converting them into favorable complete ecological losses. Positive-only controls do not estimate specificity. Process scoring for this endpoint is inner spatial CV, not demonstrated outer-sealed transfer.

## Reproducible reporting

- `.github/workflows/nature-product-a-reporting.yml` — reporting/figure workflow.
- `scripts/check_nature_manuscript_format.py` — fail-closed format/claim QA.
- `scripts/build_nature_product_a_concept_figures.py` — Figs. 1–2.
- `scripts/render_nature_fig3_counterfactual.py` — Fig. 3.
- `scripts/render_nature_fig4_empirical.py` — integrated empirical Fig. 4.

Main Fig. 4 combines the older 108/108 selector-collapse endpoint with the frozen eight-taxon positive-control result and evidence-availability boundary.

## Frozen provenance

### Controlled-truth replication

- workflow `34015900603`;
- artifact `9983940439`;
- digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`;
- exact process sets **65/70**;
- AUC **56/70**;
- predecessor **49/70**;
- exact under model disagreement **27/30**.

### Frozen empirical boundaries

v2.8.4:

- `empirical_confirmation_not_supported`;
- `not_promoted`;
- same candidate/predictors **108/108**.

Real positive controls:

- plants **2/4**;
- nonplants **1/4**;
- temperature **3/4**;
- water **0/4**;
- 24/24 pipelines, 21/24 with adequate candidate, 17/24 two-sided expected-process comparisons.

## Last verified reporting payload

On scientific parent head `f95aee599654bf9a1074610dda2a201abac59fef`:

- Nature Product-A reporting — run `34097696742`, **success**;
- Article QA — abstract **188 words**, main text **2,632 words**, `FORMAT_QA=PASS`;
- integrated Fig. 4 frozen-value checks — **PASS**;
- reporting artifact `10009246095`;
- artifact digest `sha256:76c4b7b6d41f0d35ff6c823b65145b7fe354850a2956842f2e283a1aeb471a92`.

The associated duplicate-execution guard succeeded and cancelled all four consumed real-control workflows triggered by reporting edits. Those cancellations are intentional and are not scientific failures.

## Scientific hard stop

Do not change counterfactual thresholds, process sets, discovery/validation/replication seeds, candidate library, perturbations, v2.8.4 definitions or the eight real positive-control labels/rules after outcome. Any empirical successor is separate and requires a new frozen validation panel.

## Remaining submission inputs

- final author list/order, affiliations and corresponding author;
- CRediT contributions;
- funding/grants and acknowledgements;
- competing interests;
- co-author approval;
- immutable release/permanent archive DOI;
- journal-portal metadata and reviewer declarations/suggestions.
