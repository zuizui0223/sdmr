# Product-A manuscript claim audit

Status: **submission-validation document after factorial falsification and counterfactual replication**.

Purpose: ensure every Nature claim is attached to the correct prospective evidence and that process membership, process necessity and empirical non-identification remain distinct.

## Claim classes

| Claim | Status | Evidence basis | Required boundary |
|---|---|---|---|
| Prediction adequacy does not imply correct process attribution | **supported under controlled truth** | v2.1–v2.2 | Prediction remains an adequacy layer. |
| Ecological Pareto sharpening can create false necessity | **supported under controlled truth** | v2.3 | Do not generalize to every ensemble/set construction. |
| Exclusion-based necessity can control false-required claims | **supported under controlled truth** | v2.4–v2.6 | v2.6 false-required=0, possible recall=1.0, precision≈0.467; `required_processes` empty 9/9. Safety result only. |
| Earlier stable-process intersection performs strongly in original six-family suite | **supported predecessor evidence** | v2.7.2 | 55/60 exact, but T/W true in all 60; not final presence/absence validation. |
| Stable-process predecessor generalizes to independently varying T/W/S membership | **not supported** | factorial 4201–4205 | Exact process set only 22/35; retain non-support. |
| Counterfactual recovery score can classify process membership on unused truth | **supported** | fresh validation 4301–4305 | Exact 30/35; every T/W/S sens/spec ≥0.80. Thresholds frozen before validation. |
| Counterfactual process membership replicates unchanged | **supported** | replication 4401–4410 | Exact 65/70; no method/threshold change after validation. |
| Counterfactual process membership remains identifiable despite fitted-model disagreement | **supported** | replication | Ecological models disagree 30/70; exact process set 27/30. |
| Replication temperature membership classification is strong | **supported** | replication | TP40/FN0/TN28/FP2; sens1.000/spec0.933. |
| Replication water membership classification is strong | **supported** | replication | TP40/FN0/TN28/FP2; sens1.000/spec0.933. |
| Replication soil membership classification is strong | **supported** | replication | TP39/FN1/TN30/FP0; sens0.975/spec1.000. |
| Counterfactual estimator is universally superior to AUC | **not established / prohibited** | paired reporting | Same 70 cases: counterfactual65/70 vs AUC56/70; paired 14 counterfactual-only,5 AUC-only. No preregistered universal-superiority endpoint. |
| Observation-process separation can prevent observation-only ecological misattribution | **supported in evaluated controlled family** | v2.7.2 | AUC observer_only5/10 with driver F1=0; Product A T+W10/10. Mechanism evidence, not universal rate. |
| Fresh empirical ecological selection is strictly superior to AUC | **not supported** | v2.8.4 | strict improvement0/3; `not_promoted`. |
| Ecological and AUC roles selected same model in fresh empirical endpoint | **supported reporting fact** | v2.8.4 audit | candidate/predictor identity108/108. |
| Product A identifies true ecological processes in real GBIF data | **not established** | empirical boundary | Real occurrence data have no literal generating-process answer key. |
| Counterfactual score proves physiological/causal necessity | **not established / prohibited** | claim boundary | It estimates process membership under frozen registry. |
| Every real-world proxy/composite channel is excluded | **not established** | registry boundary | Only declared aliases/representations are excluded. |

## Core claim approved for Abstract/Discussion

> **After a stronger factorial truth test falsified the preceding model-intersection rule (22/35 exact process sets), Product A reformulated process identification as counterfactual ecological-recovery loss under complete declared process exclusion. Thresholds calibrated on discovery-only truth generalized to 30/35 fresh validation cases and, without any method or threshold change, to 65/70 independent replication cases. Replication sensitivity was 0.975–1.000 and specificity 0.933–1.000 across independently varying temperature, water and soil; process truth remained exact in 27/30 cases despite ecological-model disagreement. Fresh plant process truth remains unestablished and the frozen empirical endpoint remains not supported/not promoted.**

## Mandatory evidence sequence

### 1. Predecessor falsification

Factorial discovery (`4201`–`4205`, n=35):

- stable-core exact=22/35;
- AUC exact=25/35;
- stable exact under model disagreement=12/20;
- T sens/spec1.00/0.667;
- W0.70/0.867;
- S1.00/0.867.

Do not hide or pool this failure into later validation.

### 2. Counterfactual estimator definition

For each process, among candidates clearing the existing prediction gate, quantify the best held-out Schoener-D overlap lost when all declared representations of the process are excluded. Average the normalized gap across five frozen sampling/background perturbations.

Frozen discovery-only thresholds:

- T 0.2653964368;
- W 0.0671670999;
- S 0.3342415841.

### 3. Fresh validation

Seeds4301–4305, n=35, no discovery-seed reuse:

- counterfactual exact=30/35;
- predecessor=23/35;
- AUC=25/35;
- exact under model disagreement=15/18;
- all per-process sensitivity/specificity gates pass.

### 4. Independent unchanged replication

Seeds4401–4410, n=70, method unchanged:

- counterfactual exact=65/70;
- AUC=56/70;
- predecessor=49/70;
- exact under model disagreement=27/30;
- T 40/0/28/2;
- W 40/0/28/2;
- S 39/1/30/0.

Exact by true set: T8/10, W8/10, S10/10, T+W10/10, T+S10/10, W+S10/10, T+W+S9/10.

## Necessity / membership separation

**Process membership**: counterfactual degradation of attainable ecological recovery when the process is made unavailable, classified with thresholds prospectively calibrated on discovery truth.

**Process necessity**: stronger exclusion-based claim about whether any adequate explanation survives process exclusion under the necessity contract.

The v2.6 necessity result is broad and has no positively required process in its nine validation taxa. Therefore:

- never call 65/70 a necessity-recovery rate;
- never call the counterfactual threshold a causal-effect threshold;
- never merge v2.6 precision0.467 with counterfactual process classification.

## AUC boundary

The replication comparison (65/70 counterfactual vs56/70 AUC; paired 51 both exact,14 counterfactual-only,5 AUC-only,0 both wrong) is useful descriptive evidence. It does **not** authorize the statement “Product A is universally statistically superior to AUC,” because such a comparative hypothesis/threshold was not preregistered after the counterfactual estimator was created.

The old frozen empirical superiority endpoint remains a separate result and was not supported.

## Endpoint classification

1. `factorial_predecessor_process_membership = not_supported (22/35)`;
2. `counterfactual_fresh_process_membership_validation = supported (30/35; all process gates pass)`;
3. `counterfactual_unchanged_independent_replication = supported (65/70; all process gates pass)`;
4. `known_truth_exclusion_false_necessity_control = supported but broad`;
5. `fresh_empirical_strict_advantage_over_auc = not_supported / not_promoted`;
6. `real_data_generating_process_truth_identification = not_directly_established`.

## Submission gate

Pass only if:

- 22/35 predecessor failure is visible before the successor result;
- discovery, fresh validation and independent replication seed sets are explicit and disjoint;
- thresholds are described as discovery-calibrated and frozen before validation;
- 30/35 and 65/70 are attached to **process membership**, not necessity;
- T/W/S replication sensitivity/specificity and the five-error failure envelope remain visible;
- no text turns the descriptive AUC comparison into universal superiority;
- v2.6 remains false-necessity safety with `required_processes` empty9/9;
- v2.8.4 remains `empirical_confirmation_not_supported` and `not_promoted`;
- no selected raster/process label is called causal solely because identified;
- no complete real-world proxy closure is claimed;
- no post-outcome retuning or favorable process/seed subset is introduced.
