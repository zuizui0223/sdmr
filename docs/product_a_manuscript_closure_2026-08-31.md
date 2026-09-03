# Product-A manuscript closure

Status: **scientific scope closed / Nature-track manuscript production active**.

## Submission route

1. **Nature Ecology & Evolution — Article**: first formal submission.
2. **Nature Communications**: immediate Nature-family fallback/transfer if the first decision is based on breadth or editorial priority rather than scientific validity.
3. **Methods in Ecology and Evolution**: specialist-method fallback without any favorable-data search or Product-A rerun.

Do not collect, retune or search for additional favorable Product-A evidence to alter this route.

## Authoritative scientific endpoint

The endpoint is unchanged:

- Product-A v2.8.4: `empirical_confirmation_not_supported`;
- separate promotion decision: `not_promoted`;
- known-truth support: preserved;
- Product B: blocked;
- additional Product-A scientific experiment: forbidden.

The Nature-track rewrite is a reporting and synthesis change only.

## Nature-level manuscript claim

> **Predictive success does not identify ecological necessity. In occurrence-only species distribution models, ecological necessity must be challenged against adequate alternative explanations rather than inferred from a winning model.**

The full v1→v2.8.4 evidence sequence supports this bounded methodological claim through prospective falsification:

1. prediction transfer and stable response surfaces can coexist with incorrect process attribution;
2. agreement among ecologically better retained models can create false necessary-process claims;
3. falsification-first exclusion plus explicit unresolved/unavailable states protects generating truth;
4. deterministic set-valued inference can become both safe and sharp under controlled truth;
5. fresh empirical occurrence data can leave different selection objectives observationally indistinguishable.

This does **not** establish a universal biological driver set, a fundamental niche, demographic fitness, dispersal history or biotic interactions. It does not establish that AUC is the ecological truth criterion.

## Strongest positive result

The v2.7.2 deterministic successor evaluated 60 unused known-truth cases across six niche families in two independent processes.

- robust ecological selector coverage: `60/60`;
- stable-process-core precision: `0.9889`;
- stable-process-core recall: `0.9833`;
- stable-process-core F1: `0.9833`;
- maximum absolute and relative cross-process drift: `0.0` in every compared table;
- observation correction activation: `10/10` in the observation-confounded family and `0/50` elsewhere.

Family-level reporting from the frozen artifact further shows:

| niche family | precision | recall |
|---|---:|---:|
| asymmetric | 1.000 | 1.000 |
| gaussian | 1.000 | 1.000 |
| interaction | 1.000 | 1.000 |
| observation-confounded | 1.000 | 1.000 |
| omitted-driver | 1.000 | 0.900 |
| soft-threshold | 0.933 | 1.000 |

Exact fitted-model consensus occurred in `38/60`, whereas process-set consensus occurred in `50/60`. This is direct evidence that process information can be more identifiable than exact model identity.

Source: `docs/product_a_v2_7_2_family_level_reporting_audit.md`.

## Fresh empirical boundary and observational equivalence

The v2.8.4 full denominator completed all three seeds, all 12 taxa and all 150/300/500 km M specifications. Prediction guardrail and process-status reproducibility passed, but strict ecological improvement occurred in `0/3` parts and mean presence-rank delta versus AUC was `0.0`. The formal endpoint therefore remains `empirical_confirmation_not_supported`.

A reporting-only audit of the pinned finalized artifacts now establishes the realized selector contrast exactly:

- matched taxon × M × seed cells: `108`;
- ecological versus AUC candidate identity: `108/108`;
- ecological versus AUC selected-predictor identity: `108/108`;
- ecological candidate ID in all 108 cells: `all|logit_l2_C0.1_degree1_rs0`.

Thus the formal empirical superiority claim was tested and not supported, while the stronger empirical question of process-identification performance **when predictive and ecological selectors genuinely disagree** was not identified by this endpoint because no realized disagreement occurred.

Source: `docs/product_a_v2_8_4_selector_contrast_reporting_audit.md`.

## Main-text Results structure

Do not write a software-version diary. Compress the history into four Nature-level results:

### Result 1 — Prediction is not process identification

Use v1 as the protected information-boundary foundation and v2.1–v2.2 as the controlled-truth demonstration that prediction/stability and process truth are separable.

### Result 2 — Model-set agreement can create false necessity

Use v2.3 as the anti-conservative counterexample, then introduce falsification-first necessity.

### Result 3 — Falsification-first inference is safe and can be sharp

Use v2.4–v2.6 to establish abstention and safety; use v2.7.1–v2.7.2 to establish determinism, sharpness and family-level recovery.

### Result 4 — Fresh data expose observational equivalence

Use v2.7.3/v2.8.3 only as provenance for structural/technical states. Use v2.8.4 as the sole fresh scientific endpoint, including the 108/108 exact selector-collapse audit.

## Nature Ecology & Evolution production target

Follow the current Article format:

- abstract <= `200` words;
- main text <= `3,500` words excluding Methods, references and legends;
- <= `6` main display items;
- Introduction around `500` words without a heading;
- concise topical Results;
- Discussion without subheadings;
- Online Methods sufficient for replication;
- <= `10` Extended Data items.

Primary Nature draft: `docs/product_a_nature_ecology_evolution_article_draft.md`.

Cover letter: `docs/product_a_nature_ecology_evolution_cover_letter.md`.

Submission strategy: `docs/product_a_nature_ecology_evolution_submission_plan.md`.

## Four main figures

1. **Prediction ≠ identification** — conceptual distinction plus the controlled-truth failure of prediction/stability as process proof.
2. **Agreement ≠ necessity** — Pareto sharpening creates false certainty; process exclusion and unresolved states replace agreement-based necessity.
3. **Safe and sharp under known truth** — six-family v2.7.2 precision/recall, process-set versus exact-model consensus, observation correction specificity and deterministic identity.
4. **Fresh observational equivalence** — 108/108 ecological–AUC candidate identity, formal `0/3` strict-improvement result, `empirical_confirmation_not_supported`, `not_promoted`.

Put information-barrier details, calibration support, v2.7.1 parity failure, workflow/artifact receipts and full metric tables in Extended Data / Supplement.

## Nature editorial risk

The main weakness is explicit and must not be repaired post hoc: the fresh empirical endpoint did not produce different biological conclusions from two different fitted selectors because the selectors collapsed to the same candidate. The manuscript must therefore sell **observational equivalence as an identification limit**, not invent an empirical biological divergence that does not exist.

The Nature-level advance is the inference principle and its prospective evidence sequence, not a claim that SDMR empirically beat AUC.

## Hard stop

Do not create v2.9. Do not change taxa, seed, M, sealed fraction, thresholds, candidate library, predictor universe, denominator, source or provider. Do not rerun, retune, rescue or replace the consumed v2.8.4 endpoint. Do not use the current hierarchy to perform post-outcome empirical reselection. Do not unblock Product B.

From here, all Product-A work is manuscript compression, figure production, literature positioning, provenance packaging, code/data availability and submission.
