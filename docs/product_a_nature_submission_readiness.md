# Product A — Nature Ecology & Evolution submission readiness

Status: **scientific endpoint closed; Nature submission-production gate**.

This document separates completed scientific/reporting work from the few remaining submission inputs. It does not authorize any additional Product-A experiment.

## Scientific gate — COMPLETE

- v1→v2.8.4 evidence sequence audited and compressed into four Nature-level Results;
- v2.8.4 remains `empirical_confirmation_not_supported`;
- separate Product-A decision remains `not_promoted`;
- Product B remains blocked;
- no v2.9, no retuning, no favorable-panel search, no proxy-closure rescue;
- known-truth headline preserved: stable-process-core P `0.9889`, R/F1 `0.9833` on 60 unused cases;
- exact-model consensus `38/60` versus process-set consensus `50/60`;
- fresh empirical selector identity `108/108` candidate IDs and `108/108` selected-predictor sets;
- strict ecological improvement `0/3`; mean presence-rank delta `0.0`.

## Main manuscript gate — COMPLETE

Primary file: `docs/product_a_nature_ecology_evolution_article_draft.md`.

Automated Nature-format QA currently verifies:

- abstract <= 200 words;
- main text <= 3,500 words;
- four Results headings present;
- Discussion has no topical subheadings;
- frozen headline claims remain present;
- prohibited empirical/fundamental-niche claim inflation is absent.

Latest verified reporting run before this checklist: abstract `187` words; main text `1,890` words; `FORMAT_QA=PASS`.

## Literature-positioning gate — COMPLETE FOR FIRST SUBMISSION

Verified shortlist: `docs/product_a_nature_reference_shortlist.md`.

The manuscript explicitly concedes inherited results:

- prediction versus explanation is not new;
- discrimination versus functional accuracy is not new;
- variable-importance instability under known truth is not new;
- collinearity/substitutable predictors are not new;
- spatial CV/tuning/reproducible evaluation are not new;
- Rashomon/model-set reasoning is not new.

Product-A novelty is restricted to the prospective evidence chain from false necessity under ecological sharpening to falsification-first process-information identification, explicit unresolved states, deterministic known-truth recovery, and fresh empirical selector collapse.

## Main-figure gate — COMPLETE SCIENTIFICALLY / FINAL VISUAL QA COMPLETE

Four figures are generated reproducibly by `.github/workflows/nature-product-a-reporting.yml`:

1. `nature_fig1_identification_logic` — winner selection versus protected ecological identification;
2. `nature_fig2_false_necessity` — v2.3 sharpness gain, coverage loss/false necessity and transition to exclusion logic;
3. `nature_fig3_known_truth` — six-family stable-core recovery plus process-set versus exact-model consensus;
4. `nature_fig4_empirical_identity` — 108/108 empirical model identity and 0/3 strict-improvement endpoint.

Each is emitted as 600-dpi PNG and vector PDF, with source-data CSVs. Figure 3/4 numbers are rebuilt directly from pinned frozen workflow artifacts; Figure 2 is asserted against the frozen v2.3 decision table. Figure 1 is conceptual only.

## Methods / reporting gate — COMPLETE AS DRAFT

Prepared files include:

- Nature-style cover letter;
- Online Methods;
- Extended Data plan;
- figure legends;
- Reporting Summary draft;
- software-submission checklist draft;
- Data and Code Availability draft;
- `CITATION.cff`;
- source-data tables for main and key Extended Data claims.

## CI gate — MUST BE GREEN BEFORE MERGE/SUBMISSION

A prior standard-test run failed only because the Nature-track closure status replaced the exact frozen phrase expected by `test_product_a_v2_8_4_promotion_decision.py`. The closure has now restored the required phrase:

`scientific scope closed / proceed to submission assembly`

while retaining `Nature-track manuscript production active` after it.

Submission gate: wait for a standard `tests` workflow on the current PR head to finish green together with the Nature reporting workflow. Do not waive a real failure.

## Remaining external/human inputs

These are not scientific development and cannot be inferred safely from the repository alone:

1. final author list, order, affiliations and corresponding-author identity;
2. author contributions (CRediT), funding/grant numbers, acknowledgements and competing-interest statement;
3. final repository/archive DOI (for example a Zenodo release) and immutable submission release/tag after PR merge;
4. journal portal metadata, suggested/opposed reviewers if requested, and declarations specific to the submission form;
5. final co-author approval of title, claims, figures and cover letter.

## Submission decision

If the current PR becomes green and the external author/archive fields are supplied, the package is scientifically ready for a **Nature Ecology & Evolution Article first shot**.

A desk rejection for editorial breadth/priority should transfer without new Product-A analysis to **Nature Communications**, then to **Methods in Ecology and Evolution** if needed.

## Hard stop

Do not improve journal odds by opening a new Product-A empirical endpoint, replacing taxa, changing M, changing the candidate system, relaxing thresholds, or searching for a dataset in which the ecological and AUC selectors happen to diverge. The Nature submission must stand or fall on the existing prospective evidence record.
