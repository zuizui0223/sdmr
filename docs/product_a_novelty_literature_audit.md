# Product-A novelty literature audit

Status: **manuscript-positioning audit after final counterfactual validation and replication**.

## What is inherited rather than new

Do not claim novelty for:

- prediction versus ecological explanation in SDMs;
- discrimination versus functional-response accuracy;
- spatial CV, hyperparameter tuning or reproducible model evaluation;
- variable-importance failure under correlated/spatially structured predictors;
- biologically informed predictor choice;
- Rashomon/model-class uncertainty or retaining sets of good models;
- partial identification as a statistical concept;
- leave-one-variable-out/jackknife reasoning in general;
- presence-only sampling-bias correction.

These ideas are established across the SDM, variable-importance, Rashomon and statistical-inference literature represented by Elith & Leathwick, Warren et al., Smith & Santos, Kass et al., Fisher et al., Donnelly et al. and related work.

## Defensible Product-A novelty

The final novelty is not simply that model selection can mislead. Product A supplies an **ecology-specific counterfactual process-identification estimator developed through prospective falsification**.

1. **Ecological-recovery filtering can itself create false necessity.** v2.3 gives a controlled-truth counterexample in which a sharper Pareto-selected subset loses truth/boundary coverage and can manufacture a false necessary-process core.
2. **Necessity is separated from process membership.** v2.4–v2.6 explicitly exclude declared process information and ask whether an adequate explanation survives. This controls false-required claims but can remain broad; `required_processes` was empty in all nine complete v2.6 validation taxa.
3. **Consensus stability was treated as a falsifiable predecessor rather than the final answer.** v2.7.2 looked strong under its original generator suite, but temperature and water were invariant true processes. A stronger factorial truth system independently varied temperature, water and soil over all seven non-empty combinations.
4. **The predecessor failed the stronger factorial test and the failure was retained.** On seeds 4201–4205, the stable intersection recovered only **22/35 (62.9%)** complete process sets, versus **25/35 (71.4%)** for AUC-selected winners.
5. **Process membership was reformulated counterfactually.** For each declared process `p`, Product A measures the loss of achievable held-out ecological niche recovery when every declared representation of `p` is removed from the prediction-adequate candidate class. This targets the information contribution of a process rather than the identity/importance of one fitted winner.
6. **Proxy handling is process-level within a predeclared registry.** Temperature exclusion also removes `temp_proxy`; the estimator operates on declared process representations rather than literal variable names alone. It does not claim complete real-world proxy closure.
7. **Threshold development and validation are prospectively separated.** Discovery seeds 4201–4205 were used only to freeze process-specific thresholds. Unused seeds 4301–4305 then supplied a 35-case fresh validation.
8. **The final estimator passed fresh validation.** It recovered **30/35 (85.7%)** complete process sets, versus 23/35 for the predecessor stable core and 25/35 for AUC.
9. **The result independently replicated without changing the method.** On unused seeds 4401–4410, the unchanged estimator recovered **65/70 (92.9%)** complete process sets, versus **56/70 (80.0%)** for AUC and **49/70 (70.0%)** for the predecessor.
10. **Process-level operating characteristics are explicit.** In replication, temperature sensitivity/specificity were **1.000/0.933**, water **1.000/0.933**, and soil **0.975/1.000**.
11. **Model non-uniqueness does not destroy the identified process set.** Ecological fitted models disagreed in 30/70 replication cases, but counterfactual process truth remained exact in **27/30 (90.0%)**.
12. **Evidence-state discipline remains part of the method.** Scientific non-support, unresolved/unavailable evidence, technical failure and governance non-promotion are kept distinct, including the unchanged unfavorable v2.8.4 empirical endpoint.

## Closest conceptual competitors

| Literature family | Shared idea | Product-A distinction |
|---|---|---|
| SDM tuning / ENMeval | partitioning, metrics, complexity, reproducibility | process membership is estimated from counterfactual ecological-recovery loss after prediction adequacy, not from the selected winner |
| variable-importance simulation | known truth can reveal wrong importance | Product A estimates declared process membership by removing all declared representations of the process and measuring lost ecological recovery |
| leave-one-variable-out / jackknife | compare performance after deleting a predictor | Product A operates on **process groups including declared aliases/proxies**, restricts to prediction-adequate candidate classes, aggregates across frozen sampling/background perturbations, and validates against complete process-set truth |
| ensemble/Rashomon methods | multiple adequate models imply explanatory multiplicity | Product A first shows selected-model agreement can be anti-conservative, then asks a counterfactual question across the adequate class rather than summarizing winner agreement |
| partial identification | do not force unsupported point claims | Product A retains separate necessity/possibility/unresolved states while also defining a validated process-membership classifier |
| causal interpretation | prediction is not mechanism | Product A stops at process membership under a declared representation registry; it does not call the result causal/fundamental-niche necessity |

## Key distinction from ordinary variable ablation

The final estimator should not be described merely as “drop one variable and see whether accuracy decreases.” Its scientific object is different:

- the removed unit is a **declared ecological process**, not necessarily one raster;
- every declared representation/alias of that process is removed from the candidate class;
- candidates must first satisfy an independent prediction-adequacy gate;
- the quantity lost is held-out **ecological niche recovery** (Schoener-D overlap), not only predictive discrimination;
- the score is evaluated across five frozen sampling/background perturbations;
- process-specific decision thresholds are frozen on discovery data and then evaluated on disjoint validation and replication seeds;
- performance is assessed on **complete generating-process-set recovery**, not only a variable-importance rank.

## Mandatory estimator boundary

Keep these three Product-A process objects separate:

1. v2.6 exclusion-based **necessity/possibility** certificate;
2. v2.7.2 consensus-first **process stability** predecessor;
3. final **counterfactual process membership** estimator.

Do not narrate v2.6 precision≈0.467, v2.7.2 P=0.9889 and final 65/70 exact recovery as one metric improving over time. They answer different questions.

## Nature-level novelty sentence

> **Earlier work established that prediction, functional recovery and variable-importance inference can diverge. Product A goes further by prospectively falsifying model-agreement approaches to ecological process identification and then defining each process by the ecological niche recovery lost when all declared representations of that process are unavailable. After thresholds were frozen on discovery data, this counterfactual estimator recovered 30/35 complete process sets in fresh validation and 65/70 in an unchanged independent replication across all seven combinations of three independently varying environmental processes.**

## Empirical boundary

The fresh plant endpoint does not expose literal generating-process truth and does not support strict empirical superiority over AUC. Ecological and AUC roles instantiated identical candidates/predictors in 108/108 matched cells. This bounds the controlled-truth claim rather than weakening its internal validation.

## Current limitation / next-study boundary

The final factorial system contains three declared environmental process families and one declared temperature proxy. A broader future study could predeclare additional process hierarchies, richer proxy/composite closure and independently observed biological process truth. That is future validation, not a missing post hoc rescue step for Product A.
