# Product A — Nature Ecology & Evolution submission track

Status: **submission-production plan; Product-A scientific hard stop remains in force**.

## First Nature-family target

**Nature Ecology & Evolution — Article**

This is the appropriate Nature-family first shot because the paper's main contribution is an ecological inference principle, not a broadly cross-life-science computational platform. The paper should be submitted as an Article, not as a methods-only content type.

Current journal format to target:

- abstract <= 200 words;
- main text <= 3,500 words, excluding Methods, references and legends;
- <= 6 main display items;
- Introduction without heading, approximately 500 words;
- Results with topical subheadings;
- Discussion without subheadings;
- Online Methods containing reproducible scientific detail;
- up to 10 Extended Data items.

## Nature-level central claim

Do not lead with SDMR as a better tuner.

Lead with the field-level inference problem:

> **Predictive success does not identify ecological necessity. In occurrence-only species distribution models, necessity must be challenged against adequate alternative explanations rather than inferred from the winning model.**

`ecological necessity` is operationally scoped to **process-information necessity under the declared representation/evidence registry**; it is not a claim of complete causal mechanism.

Product A supplies the evidence sequence needed to establish that principle:

1. prediction transfer / stable surfaces can coexist with wrong process attribution;
2. filtering to ecologically better models can create false necessary-process claims;
3. falsification-first process exclusion plus explicit unresolved states protects generating truth;
4. a deterministic successor is both sharp and safe across six controlled niche families;
5. fresh empirical evidence shows a second identification limit: ecological and AUC selection can collapse to the same fitted candidate, leaving no realized selector contrast even under a complete preregistered endpoint.

## Strongest Nature-track evidence recovered from frozen artifacts

### Controlled-truth breadth

The v2.7.2 pooled precision/recall result is not driven by one generator. Family-level reporting from the frozen artifact gives:

- asymmetric: P/R = 1.00/1.00;
- gaussian: 1.00/1.00;
- interaction: 1.00/1.00;
- observation-confounded: 1.00/1.00;
- omitted-driver: 1.00/0.90;
- soft-threshold: 0.933/1.00.

Exact model consensus was 38/60, whereas process-set consensus was 50/60. This supports the process-identification claim: declared process information can remain stable when exact model identity does not.

### Empirical observational equivalence

The v2.8.4 finalized artifacts contain 108 matched taxon × M × seed cells. Ecological and AUC roles have:

- candidate ID identity: 108/108;
- selected-predictor identity: 108/108;
- the same candidate in every cell: `all|logit_l2_C0.1_degree1_rs0`.

Therefore the formal empirical superiority claim remains tested and not supported, but the endpoint also reveals why: the realized selector contrast was exactly zero. The empirical data did not furnish the counterfactual situation in which ecological and predictive selectors disagree.

Nature-level connection:

> controlled truth shows that predictive or even ecological-recovery selection does not establish process necessity; fresh empirical data show that distinct selection objectives can themselves become observationally indistinguishable.

## Prior-art boundary now fixed

The manuscript no longer claims novelty for `prediction ≠ explanation`, spatial CV, tuning, collinearity effects, sampling-bias correction or Rashomon/model-class uncertainty. These are explicitly positioned against Elith & Leathwick, Warren et al., ENMeval, Dormann et al., Roberts et al., Phillips/Fithian and model-class-reliance work in `docs/product_a_nature_reference_boundary.md`.

The novelty begins at the stronger result:

> **even model sets selected for better ecological recovery can create false process necessity, so process-information necessity requires prospective falsification against adequate alternatives rather than agreement among selected models.**

## Four main figures

### Figure 1 — Prediction is not identification

Conceptual panel plus early known-truth counterexample. Show predictive adequacy / functional environmental recovery / process-information necessity as different inferential objects, behind the prospective model-pool/sealed barrier.

### Figure 2 — Why ecological winner agreement creates false certainty

v2.3 → v2.6 transition. Show complete adequate model set, Pareto-pruned set, false necessary core, then falsification-first process exclusion and explicit unresolved state.

### Figure 3 — Falsification-first identification is safe and sharp under controlled truth

Six-family v2.7.2 panel. Plot precision and recall by niche family; overlay process-set consensus versus exact-model consensus. Add observation-correction specificity and exact independent-process determinism as compact annotations.

### Figure 4 — Fresh data reveal observational equivalence, not empirical superiority

Show all 108 matched cells as ecological-versus-AUC candidate/metric identity, with 108/108 candidate and predictor identity. Alongside it report formal endpoint: prediction guardrail pass, nondominated 3/3, strict improvement 0/3, `empirical_confirmation_not_supported`, `not_promoted`.

Use Extended Data for v1 information barriers, calibration availability, v2.7.1 determinism failure, provenance receipts and full metric tables. Detailed plan: `docs/product_a_nature_extended_data_plan.md`.

## Editorial stress test

A Nature Ecology & Evolution editor must be able to answer yes to all four:

1. **Advance:** does the paper change how ecologists interpret model-selected environmental drivers rather than merely improve SDM software?
2. **Evidence:** are false necessity, recovered process cores and empirical collapse demonstrated with prospectively protected evidence rather than retrospective examples?
3. **Breadth:** does the inference problem apply beyond the 12 empirical plant taxa to observational ecological models with correlated/substitutable representations?
4. **Accessibility:** can a community ecologist, evolutionary biologist or conservation scientist understand the inference problem without knowing SDM implementation details?

Current detailed gate: `docs/product_a_nature_editorial_readiness_2026-09-04.md`.

## Journal ladder

1. **Nature Ecology & Evolution — Article**: first formal submission after Nature-format completion.
2. **Nature Communications**: immediate Nature-family transfer/fallback if the editorial objection is breadth/significance rather than validity.
3. **Methods in Ecology and Evolution**: strongest specialist-method fallback; no additional favorable-data search before transfer.

**Nature Methods is not the preferred current route.** The evidence is ecology-specific and lacks the broad cross-life-science practical application expected there.

## Completion gates before Nature Ecology & Evolution submission

### Completed

- [x] exact six-family v2.7.2 reporting audit;
- [x] exact 108/108 v2.8.4 selector-collapse audit;
- [x] Nature Article draft with abstract below 200 words (current draft: 183 words);
- [x] explicit process-information/causal-claim boundary;
- [x] focused prior-art/novelty boundary;
- [x] Nature-style cover letter;
- [x] Online Methods draft;
- [x] Extended Data plan (10 items maximum);
- [x] Data and Code Availability draft;
- [x] reporting figure builder with frozen-value assertions;
- [x] `CITATION.cff` for archival preparation;
- [x] editorial-readiness gate.

### Remaining submission production

1. render and visually QA four main figures from pinned frozen evidence;
2. generate and freeze main/Extended Data source-data tables;
3. integrate the final verified numbered reference list into the Article file;
4. run exact main-text word-count and format QA, maintaining <=3,500 words;
5. archive the exact submission branch/code/source-data state with a permanent DOI;
6. complete Nature Portfolio reporting summary and software submission checklist;
7. add final authorship metadata: affiliations, contributions, acknowledgements, competing interests and corresponding-author details.

## Stop rule

Do not create v2.9, change the empirical denominator, hunt for a taxon panel that makes the ecological selector diverge, or expand proxy closure using already opened empirical outcomes. A Nature submission is earned by clearer inference and stronger reporting of the existing prospective record, not by favorable-data rescue.