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

Product A then supplies the evidence sequence needed to establish that principle:

1. prediction transfer / stable surfaces can coexist with wrong process attribution;
2. filtering to ecologically better models can create false necessary-process claims;
3. falsification-first process exclusion plus explicit unresolved states protects generating truth;
4. a deterministic successor is both sharp and safe across six controlled niche families;
5. fresh empirical evidence shows a second identification limit: ecological and AUC selection can collapse to the same fitted candidate, leaving no realized selector contrast even under a complete preregistered endpoint.

## Strongest new Nature-track evidence recovered from frozen artifacts

### Controlled-truth breadth

The v2.7.2 pooled precision/recall result is not driven by one generator. Family-level reporting from the frozen artifact gives:

- asymmetric: P/R = 1.00/1.00;
- gaussian: 1.00/1.00;
- interaction: 1.00/1.00;
- observation-confounded: 1.00/1.00;
- omitted-driver: 1.00/0.90;
- soft-threshold: 0.933/1.00.

Exact model consensus was 38/60, whereas process-set consensus was 50/60. This supports a stronger ecological-identification claim: process information can remain stable when exact model identity does not.

### Empirical observational equivalence

The v2.8.4 finalized artifacts contain 108 matched taxon × M × seed cells. Ecological and AUC roles have:

- candidate ID identity: 108/108;
- selected-predictor identity: 108/108;
- the same candidate in every cell: `all|logit_l2_C0.1_degree1_rs0`.

Therefore the formal empirical superiority claim remains tested and not supported, but the endpoint also reveals why: the realized selector contrast was exactly zero. The empirical data did not furnish the counterfactual situation in which ecological and predictive selectors disagree.

This is the Nature-level connection between the simulation and empirical lanes:

> controlled truth shows that predictive agreement does not guarantee process truth; fresh empirical data show that different selection objectives can be observationally indistinguishable.

## Four main figures

### Figure 1 — Prediction is not identification

Conceptual panel plus the v2.1/v2.2 known-truth counterexample. Show predictive adequacy / response-surface stability on one axis and process correctness on the other. The figure should establish that the objects are logically and empirically separable.

### Figure 2 — Why winner agreement creates false certainty

v2.3 → v2.6 transition. Show complete adequate model set, Pareto-pruned set, false necessary core, then falsification-first process exclusion and explicit unresolved state. This is the inferential innovation figure.

### Figure 3 — Falsification-first identification is safe and sharp under controlled truth

Six-family v2.7.2 panel. Plot precision and recall by niche family; overlay process-set consensus versus exact-model consensus. Add observation-correction specificity and exact independent-process determinism as compact annotations.

### Figure 4 — Fresh data reveal observational equivalence, not empirical superiority

Show all 108 matched cells as ecological-versus-AUC candidate identity, with 108/108 identity and the single common candidate. Alongside it report formal endpoint: prediction guardrail pass, nondominated 3/3, strict improvement 0/3, `empirical_confirmation_not_supported`, `not_promoted`.

Use Extended Data for v1 information barriers, calibration availability, v2.7.1 determinism failure, provenance receipts, and full metric tables.

## Editorial stress test

A Nature Ecology & Evolution editor must be able to answer yes to all four:

1. **Advance:** does the paper change how ecologists interpret model-selected environmental drivers rather than merely improve SDM software?
2. **Evidence:** are false necessity, recovered process cores and empirical collapse demonstrated with prospectively protected evidence rather than retrospective examples?
3. **Breadth:** does the argument apply beyond the 12 empirical plant taxa to a general class of observational ecological models with correlated/substitutable representations?
4. **Accessibility:** can a community ecologist, evolutionary biologist or conservation scientist understand the inference problem without knowing MaxEnt/SDM implementation details?

The manuscript should be revised until the answer is yes without adding new Product-A experiments.

## Journal ladder

1. **Nature Ecology & Evolution — Article**: first formal submission after Nature-format completion.
2. **Nature Communications**: immediate Nature-family transfer/fallback if the editorial objection is breadth/significance rather than validity. Its criterion of an important advance for specialists is compatible with a strong ecological-method paper.
3. **Methods in Ecology and Evolution**: strongest specialist-method fallback; no additional favorable-data search before transfer.

**Nature Methods is not the preferred current route.** Although computational/statistical biological methods are in scope, the present evidence is ecology-specific and lacks the broad cross-life-science practical application expected there.

## Completion gates before Nature Ecology & Evolution submission

No new scientific endpoint is required. Complete these reporting/production gates:

1. integrate the exact 6-family v2.7.2 breakdown and 108/108 v2.8.4 selector-collapse result into the main text;
2. reduce the main manuscript to <=3,500 words and the abstract to <=200 words;
3. render four main figures from pinned frozen evidence only;
4. build Extended Data / Supplement with the complete prospective evidence ledger and failure-state taxonomy;
5. complete a focused literature boundary demonstrating what is inherited versus new;
6. write a Nature-style cover letter around the broad ecological inference advance;
7. ensure code/data availability and reproducibility statements point to immutable repository artifacts/DOIs where possible;
8. preserve `empirical_confirmation_not_supported`, `not_promoted`, and Product-B block verbatim in the evidence record.

## Stop rule

Do not create v2.9, change the empirical denominator, hunt for a taxon panel that makes the ecological selector diverge, or expand proxy closure using already opened empirical outcomes. A Nature submission is earned by clearer inference and stronger reporting of the existing prospective record, not by favorable-data rescue.
