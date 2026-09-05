# Product-A manuscript spine

Status: **submission framing / scientific endpoint unchanged**.

Authoritative scientific endpoint: Product-A v2.8.4 `empirical_confirmation_not_supported`; separate promotion decision `not_promoted`; Product B blocked. This file changes only manuscript organization.

## One-sentence paper claim

**Occurrence-only SDM tuning should be treated as an ecological identification problem, not only as a winner-selection problem: prediction adequacy, process necessity, process-information stability, uncertainty, evidence availability and computational reproducibility must be separated prospectively because each is a distinct inferential object.**

## Critical logic boundary

Two Product-A process-level estimands must remain distinct throughout the manuscript:

1. **exclusion-based necessity** — whether an adequate explanation survives when declared information for a process is removed; this is the v2.4–v2.6 falsification branch;
2. **consensus-first process stability** — whether canonical and perturbation-robust ecological selectors support the same process information; this is the v2.7.2 stable-process-core branch.

The v2.7.2 precision `0.9889` and recall/F1 `0.9833` belong to the second estimand. They are not the precision/recall of the falsification-first necessity certificate.

## Main Results spine

### R1. Prediction transfer is not process recovery

Use Product-A v1 as the information-barrier foundation, then v2.1–v2.2 as the falsification that a predictive or stable winner can still be ecologically misattributed.

Main sentence:

> Sealed occurrence transfer and response-surface stability were insufficient to establish recovery of the generating environmental process, motivating a shift from winner selection to ecological identification.

### R2. Model agreement is not biological necessity

Use v2.3 as the anti-conservative counterexample.

Main sentence:

> Ecological Pareto pruning produced sharper certificates but lost truth coverage and could create a false necessary-process core, showing that agreement among retained fitted models cannot be read directly as biological necessity.

### R3. Falsification-first necessity inference protects truth by allowing broad or unresolved sets

Use v2.4–v2.6 as one result family, not three software iterations.

Main sentence:

> Process-exclusion certificates achieved complete true-process recall with zero false-required processes when calibration was adequate, while incomplete calibration correctly produced `unavailable` rather than a negative ecological conclusion.

Report the v2.6 limitation openly: possible-process precision remained broad at about 0.467 and calibrated intervals widened. This is not a failed attempt at the later 0.99 stable-core result; it is a distinct necessity estimator whose strength is false-necessity control.

### R4. Process information can be stable even when exact model identity is not

Use v2.7.1 as the reproducibility falsification and v2.7.2 as the positive consensus-first recovery result.

Main sentence:

> After solver/process nondeterminism was shown to alter a discrete selected-predictor result, a deterministic successor exactly reproduced all compared outputs, while the consensus-first stable process core achieved precision 0.9889 and recall/F1 0.9833 across 60 fresh known-truth cases; process-set consensus occurred in 50/60 cases versus exact-model consensus in 38/60.

Interpretation boundary:

> This result supports stable process information across canonical and perturbation-robust ecological selectors. It does not show that the exclusion-based necessity estimator itself achieved 0.9889 precision.

### R5. Fresh empirical evidence sets the external-validity boundary

Use v2.7.3–v2.8.3 only to establish why structural/technical states are not ecological outcomes. Use v2.8.4 as the only fresh empirical scientific endpoint.

Main sentence:

> The full frozen empirical denominator was evaluable and satisfied prediction and process-reproducibility safeguards, but the ecological procedure showed strict ecological improvement over the AUC role in 0/3 preregistered parts, so general empirical superiority was not supported; artifact audit further showed selector identity in 108/108 matched cells.

## Discussion spine

### D1. The estimand changed because simpler estimands were falsified

Do not write that the project “failed to find a better selector and then changed the question.” The prospective sequence supports a stronger description:

> The initial niche-recovery objective was progressively refined because known-truth tests falsified the assumption that one best fitted procedure, one stable surface, or one agreement-defined core was sufficient for ecological interpretation.

### D2. Prediction metrics remain necessary, not discredited

AUC, CBI/Boyce, OR10 and AICc should be positioned as model-evaluation or model-selection criteria with valid roles. The claim is only that none, by itself, supplies a proof of ecological process necessity.

### D3. Necessity and stability are complementary, not synonymous

Exclusion answers: **does the claim fail when process information is removed?**

Consensus answers: **does the same process information persist across defensible ecological selectors?**

A process can be stable across selectors without being proven necessary, and a process can remain possible under exclusion without being part of a narrow stable core. The manuscript must preserve this distinction.

### D4. Set width and abstention are results

A broad admissible process set means the available evidence does not identify a narrower necessity claim under the declared contract. `Unavailable` means the required evidence product does not exist. Neither should be silently converted into absence.

### D5. Observation bias can contaminate both model and answer-check distribution

Emphasize the conceptual point uncovered during development: marginalizing nuisance predictors from the fitted surface is insufficient if the withheld occurrence environments are themselves observation-biased. This justifies candidate-independent correction of the held-out ecological target when nuisance evidence is independently supported.

### D6. Reproducibility belongs inside the scientific estimand

If floating/process differences can flip a discrete predictor-selection result, exact estimator and RNG identity are not merely engineering details. They are part of the definition of the reported scientific procedure.

### D7. v2.8.4 is a boundary, not a refutation of the architecture

State all three together:

- exclusion-based false-necessity control is supported under known truth;
- consensus-first process stability is supported under known truth;
- fresh empirical strict advantage over AUC is not supported in the frozen corpus and realized selector contrast collapsed to zero.

Therefore the paper claims an ecological-identification architecture and its demonstrated controlled-truth behavior, not a universally superior empirical selector.

## Manuscript title direction

Preferred conceptual title:

**Predictive success does not identify ecological necessity in species distribution models**

Alternative:

**From model selection to ecological identification in occurrence-only species distribution models**

Avoid a title that calls the whole framework “falsification-first” because the high-precision v2.7.2 stable-core result is consensus-first rather than exclusion-based.

## Abstract logic

1. **Background:** predictive SDM tuning does not automatically identify the environmental information that defines a realized niche.
2. **Failure evidence:** prediction/stability can miss process truth; ecological Pareto sharpening can create false necessity.
3. **Necessity branch:** exclusion-based certificates control false-required claims but may remain broad/unresolved.
4. **Stability branch:** a separate consensus-first certificate recovers stable process information at ~0.99 precision/~0.98 recall despite exact-model disagreement.
5. **Empirical boundary:** the full 12-taxon × 3-seed × 3-M fresh endpoint did not support strict improvement over AUC and produced identical selectors in 108/108 matched cells.
6. **Conclusion:** ecological identification requires separating prediction, necessity, process stability and unresolved evidence.

## Figure order

1. **Conceptual identification framework** — conventional winner selection versus separate process-necessity and process-stability questions.
2. **Necessity falsification** — v2.3 false certainty → v2.4–v2.6 exclusion + abstention → safe but broad set.
3. **Process stability without model uniqueness** — v2.7.2 family-level stable-core precision/recall and 50/60 versus 38/60 consensus.
4. **Fresh empirical boundary** — 108/108 selector identity, strict improvement 0/3, `not_promoted`.

## Non-negotiable wording boundaries

Do not write:

- “SDMR outperforms AUC on empirical plants.”
- “AUC is an invalid SDM metric.”
- “The stable process core proves causal drivers in GBIF data.”
- “v2.8.4 validates the set-valued method empirically.”
- “Technical/unavailable generations are negative ecological results.”
- “Falsification-first process exclusion achieved precision 0.9889 and recall 0.9833.”
- “The v2.7.2 stable process core is the necessary-process set.”

Do write:

- “exclusion-based necessity inference achieved zero false-required processes and complete true-process recall under the frozen known-truth criterion, with broad possible-process sets”;
- “the separate consensus-first stable process core achieved precision 0.9889 and recall 0.9833”;
- “process information was more stable than exact model identity in the frozen known-truth test”;
- “fresh empirical strict advantage was not supported”;
- “selected rasters are representations and are not automatically causal drivers.”