# Product-A manuscript claim audit

Status: **submission-validation document / no scientific endpoint change**.

Purpose: verify that the v1→v2.8.4 manuscript makes only claims directly supported by frozen evidence and does not conflate exclusion-based necessity with consensus-first process stability.

## Claim classes

| Claim | Status | Evidence basis | Required wording boundary |
|---|---|---|---|
| Prediction adequacy does not imply correct ecological-process identification | **supported under known truth** | v2.1–v2.2 | Predictive metrics remain adequacy/guardrail evidence. |
| Stable response surfaces do not guarantee correct process attribution | **supported under known truth** | v2.2 | Restrict to controlled designs evaluated. |
| Agreement among retained fitted models is not sufficient evidence of biological necessity | **supported under known truth** | v2.3 | Demonstrated for retained-set intersection after ecological Pareto sharpening. |
| Between-model min–max spread is not automatically a complete uncertainty interval | **supported under known truth** | v2.3 | Do not generalize to every ensemble interval construction. |
| Falsification-first process exclusion can control false-required claims | **supported under known truth** | v2.4–v2.6 | v2.4/v2.5 include unavailable states; first complete supported exclusion certificate is v2.6. |
| Complete exclusion-based certificates can achieve false-required=0 and possible-process recall=1.0 | **supported under known truth** | v2.6 | Keep possible-process precision ≈0.467, wider intervals and the fact that `required_processes` was empty in all 9 validation taxa visible. This is a safety result, not positive driver discovery. |
| Consensus-first stable process core exactly recovers the full hidden process set in most cases | **supported under known truth** | v2.7.2 frozen artifact audit | Exact stable-core truth match 55/60 overall and 19/22 when fitted models disagree. This is the clearest positive process-identification result. |
| Consensus-first stable process information can align strongly with generating truth | **supported under known truth** | v2.7.2 | Stable-core P=0.9889, R/F1=0.9833 across 60 unused cases. Treat these pooled means as secondary because temperature and water were true in all 60 cases. |
| Soil supplies the selective presence-versus-absence process test in v2.7.2 | **supported reporting fact** | v2.7.2 frozen artifact audit | Soil truth present 10/60: stable 7, contested 3, absent from both 0. Soil truth absent 50/60: stable 2, contested 7, absent from both 41. Do not generalize this selective accuracy to many independently varying drivers. |
| Process-set identity can be more stable than exact fitted-model identity | **supported under known truth** | v2.7.2 | Process-set consensus 50/60 versus exact-model consensus 38/60. Do not convert stability into necessity. |
| Observation-process correction can activate selectively rather than automatically | **supported under evaluated known-truth families** | v2.7.2 | 10/10 in confounded family; 0/50 elsewhere; no universal sensitivity/specificity claim. |
| Numerical/process nondeterminism can change a discrete selected-predictor result | **directly observed** | v2.7.1 | One of 96 compared fold rows changed selected predictors. |
| Deterministic execution can exactly reproduce frozen outputs | **supported for v2.7.2** | v2.7.2 | Max abs/rel difference 0.0; implementation identity is not ecological truth. |
| Structural validation availability can be diagnosed before environmental outcomes | **supported** | v2.7.3 | Presealed unavailability is geometry/evidence-support state, not ecological evidence. |
| Technical terminal states can be separated from scientific non-support | **supported** | v2.8.3 vs v2.8.4 | v2.8.3 is not a null/negative ecological result. |
| Fresh empirical ecological selection was strictly superior to AUC | **not supported** | v2.8.4 | Strict improvement 0/3; mean presence-rank delta 0.0; `not_promoted`. |
| Fresh empirical endpoint was fully evaluable | **supported** | v2.8.4 | Full 3/3 denominator; all 12 taxa × 3 M per part; sealed metrics finite. |
| Ecological and AUC selectors instantiated the same model in the fresh endpoint | **supported reporting fact** | frozen v2.8.4 artifact audit | Candidate and selected-predictor identity 108/108; reporting audit does not alter formal endpoint. |
| Product A identifies true ecological processes in real GBIF data | **not established** | empirical boundary | Real occurrence data do not expose literal generating-process truth. |
| AUC is generally optimal for ecological inference | **not supported / prohibited** | v2.8.4 boundary | Non-support for SDMR strict advantage is not universal support for AUC. |
| Every real-world proxy/composite channel was excluded | **not established** | current registry / future hierarchy | Exclusion is relative to the declared frozen representation system; full proxy closure is future work. |
| A selected raster is a causal environmental driver | **not established** | Chapter-1 hierarchy | Keep raster, process, proxy and composite representation distinct. |

## Core claim approved for Abstract/Discussion

> **Product A does more than identify a problem: under unused controlled truth, a consensus-first process certificate exactly recovered the complete generating-process set in 55/60 cases and in 19/22 cases where the fitted models themselves disagreed. The process-exclusion branch separately controlled false necessity but did not positively require a driver in its nine validation taxa. Selective discrimination in the frozen v2.7.2 generator suite was concentrated on soil, while temperature and water were invariant true processes. Fresh empirical strict advantage over AUC remained not supported.**

## Mandatory estimator separation

### Exclusion necessity / possibility

- v2.6 false-required = 0;
- possible-process recall = 1.0;
- possible-process precision ≈0.467;
- `required_processes` empty in 9/9 validation taxa;
- interpretation = false-necessity control with a broad identified set, not positive driver discovery.

### Consensus-first process recovery

- exact hidden process-set recovery = 55/60;
- exact recovery when canonical and robust fitted models disagree = 19/22;
- canonical selector exact process-set recovery = 52/60;
- robust selector exact process-set recovery = 54/60;
- stable-core precision = 0.9889;
- recall/F1 = 0.9833;
- process-set consensus = 50/60;
- exact-model consensus = 38/60.

### Process-specific discrimination boundary

Temperature and water were true in all 60 cases and stable in all 60; they test retention, not absence/presence discrimination.

Soil was true in 10 cases and false in 50:

- true soil: stable 7, contested 3, absent from both 0;
- false soil: stable 2, contested 7, absent from both 41;
- stable-soil precision = 7/9 = 77.8%; recall = 7/10 = 70%; specificity = 48/50 = 96%.

**Forbidden:** describing pooled P/R as though three independently varying process presences were classified at ~0.99 accuracy.

## Endpoint classification

1. `known_truth_exclusion_false_necessity_control = supported`;
2. `known_truth_exact_process_set_recovery = 55/60`;
3. `known_truth_model_disagreement_exact_process_recovery = 19/22`;
4. `fresh_empirical_strict_advantage_over_auc = not_supported / not_promoted`;
5. `real_data_generating_process_truth_identification = not_directly_established`.

Do not replace item 4 with `not_tested`: the empirical superiority rule was tested and failed. Do not replace item 5 with `failed`: literal empirical process truth was unavailable as an answer key.

## Submission gate

Pass only if:

- the positive Results section reports exact process-set recovery, not only pooled P/R;
- the manuscript states that selective process truth varied only for soil in the frozen v2.7.2 suite;
- v2.6 is presented as false-necessity control, with `required_processes` empty in all nine validation taxa;
- no text attributes P=0.9889/R=0.9833 to falsification-first exclusion;
- no text equates `stable_process_core` with necessity;
- v2.7.1 is implementation falsification, not ecological failure;
- v2.7.3 and v2.8.3 remain structural/technical states;
- v2.8.4 remains `empirical_confirmation_not_supported` and `not_promoted`;
- no selected raster is called causal solely because selected;
- no complete proxy-closure validation is claimed;
- Product B remains blocked.
