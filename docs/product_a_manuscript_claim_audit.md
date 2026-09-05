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
| Complete exclusion-based certificates can achieve false-required=0 and possible-process recall=1.0 | **supported under known truth** | v2.6 | Keep possible-process precision ≈0.467 and wider calibrated intervals visible. This is a broad necessity/possibility set. |
| Consensus-first stable process information can align strongly with generating truth | **supported under known truth** | v2.7.2 | Stable-core P=0.9889, R/F1=0.9833 across 60 unused cases. This is **not** the exclusion necessity estimator. |
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

> **Prediction success is not equivalent to ecological identification. Product A shows that ecological-recovery filtering can create false necessity; an exclusion-based certificate can control false-required process claims while retaining unresolved alternatives; and a separate consensus-first certificate can recover stable process information even when exact fitted models disagree. The fresh plant endpoint did not support strict empirical advantage over AUC and instead instantiated the same model under both selection objectives.**

## Mandatory estimator separation

Use these as separate quantities:

### Exclusion necessity / possibility

- v2.6 false-required = 0;
- possible-process recall = 1.0;
- possible-process precision ≈0.467;
- interpretation = safe but broad identified set under the frozen contract.

### Consensus-first process stability

- v2.7.2 stable-core precision = 0.9889;
- recall/F1 = 0.9833;
- process-set consensus = 50/60;
- exact-model consensus = 38/60;
- interpretation = stable process information across canonical and robust ecological selectors.

**Forbidden:** comparing 0.467 and 0.9889 as successive precision values of one estimator, or calling the v2.7.2 stable core the necessary-process set.

## Endpoint classification

1. `known_truth_exclusion_false_necessity_control = supported`;
2. `known_truth_consensus_process_stability = supported`;
3. `fresh_empirical_strict_advantage_over_auc = not_supported / not_promoted`;
4. `real_data_generating_process_truth_identification = not_directly_established`.

Do not replace item 3 with `not_tested`: the empirical superiority rule was tested and failed. Do not replace item 4 with `failed`: literal empirical process truth was unavailable as an answer key.

## Submission gate

Pass only if:

- known-truth performance numbers are explicitly attached to the correct estimator;
- v2.6 breadth/precision limitation remains visible;
- no text attributes P=0.9889/R=0.9833 to falsification-first exclusion;
- no text equates `stable_process_core` with necessity;
- v2.7.1 is implementation falsification, not ecological failure;
- v2.7.3 and v2.8.3 remain structural/technical states;
- v2.8.4 remains `empirical_confirmation_not_supported` and `not_promoted`;
- no selected raster is called causal solely because selected;
- no complete proxy-closure validation is claimed;
- Product B remains blocked.