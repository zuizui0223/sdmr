# Product-A novelty literature audit

Status: **manuscript-positioning audit / no scientific endpoint change**.

## What is inherited rather than new

Do not claim novelty for:

- prediction versus ecological explanation in SDMs;
- discrimination versus functional-response accuracy;
- spatial CV, hyperparameter tuning or reproducible model evaluation;
- variable-importance failure under correlated/spatially structured predictors;
- biologically informed predictor choice;
- Rashomon/model-class uncertainty or retaining sets of good models;
- partial identification as a statistical concept;
- presence-only sampling-bias correction.

These are established in the literature represented by Elith & Leathwick, Warren et al., Smith & Santos, Harisena et al., Kass et al., Fisher et al., Donnelly et al. and related work.

## Defensible Product-A novelty

The strongest novelty is the **ecology-specific identification decomposition plus prospective falsification evidence**:

1. **Ecological-recovery filtering can create false necessity.** v2.3 provides a prospective known-truth counterexample: a sharper Pareto-selected model subset can lose truth coverage and manufacture a false necessary-process core.
2. **Necessity is operationalized by falsification, not agreement.** The v2.4–v2.6 branch excludes declared process information and asks whether an adequate explanation survives. Missing evidence remains unresolved/unavailable.
3. **Safe necessity inference can remain broad.** v2.6 achieved false-required=0 and possible-process recall=1.0 but possible-process precision≈0.467; the framework keeps that uncertainty rather than pruning it after seeing truth.
4. **Process stability is evaluated separately from necessity.** v2.7.2 uses a consensus-first stable process core defined by agreement between canonical and perturbation-robust ecological selectors. It is not the process-exclusion necessary set.
5. **Process information can be more stable than exact model identity.** Under 60 unused known-truth cases, the consensus-first stable core had P=0.9889 and R/F1=0.9833, with process-set consensus 50/60 versus exact-model consensus 38/60.
6. **Observation-target bias is part of the inferential problem.** Product A recognizes that nuisance sampling can bias both fitted predictions and the withheld occurrence-environment target.
7. **Computational identity can be scientifically material.** v2.7.1 demonstrated a discrete predictor-selection change across process boundaries; v2.7.2 then achieved exact audited parity after prospective RNG definition.
8. **Evidence states remain distinct.** scientific non-support, unresolved/unavailable evidence, technical failure and governance non-promotion are not collapsed.
9. **The unfavorable empirical endpoint is retained.** v2.8.4 strict ecological improvement remained 0/3 and Product A was not promoted; reporting audit showed ecological/AUC selector identity 108/108 rather than an unreported favorable subset.

## Closest conceptual competitors

| Literature family | Shared idea | Product-A distinction |
|---|---|---|
| SDM tuning / ENMeval | partitioning, metrics, complexity, reproducibility | ecological identification is decomposed beyond predictive winner selection |
| variable-importance simulation | known truth can reveal wrong importance | necessity is challenged by process-information exclusion, with unresolved states |
| ecological predictor-selection literature | biological meaning and representation matter | declared process claims are tested rather than accepted from expert labels alone |
| ensemble/Rashomon methods | many good models imply explanation multiplicity | v2.3 shows agreement within a selected good-model set can itself create false necessity |
| partial identification | do not force a point answer | Product A gives process-level occurrence-only states plus protected calibration/availability logic |
| causal interpretation | prediction is not mechanism | Product A deliberately stops at contract-relative process information, not causal/fundamental-niche proof |

## Mandatory two-estimand boundary

Never write:

> falsification-first set-valued inference achieved P=0.9889/R=0.9833.

Correct:

> exclusion-based necessity controlled false-required claims but remained broad; independently, a consensus-first stable process core achieved P=0.9889/R=0.9833 and was more stable than exact fitted-model identity.

The 0.467 v2.6 possible-process precision and 0.9889 v2.7.2 stable-core precision refer to different sets and cannot be narrated as one estimator improving.

## Nature-level novelty sentence

> **Earlier work established that prediction, functional recovery and variable-importance inference can diverge and that many well-performing models may support different explanations. Product A prospectively shows the next problem: ecological-recovery filtering can itself create false process necessity. It therefore separates exclusion-based tests of necessity from consensus-based tests of process stability, preserves unresolved evidence, and demonstrates under controlled truth that process information can remain stable even when exact model identity does not.**

## Empirical boundary

The fresh plant endpoint does not establish empirical process truth or strict superiority over AUC. Instead, ecological and AUC selection instantiated the same candidate/predictors in 108/108 matched cells, exposing observational equivalence as an empirical identification limit.

## Future implication only

A new independent study could predeclare full process-information/proxy closure and external ecological truth. That is not current Product-A evidence and must not be used as a retrospective rescue.