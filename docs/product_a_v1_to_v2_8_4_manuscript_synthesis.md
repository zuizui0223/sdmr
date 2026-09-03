# Product-A v1→v2.8.4 manuscript synthesis

Status: **manuscript synthesis / no new scientific authorization**.

This document does not reopen Product-A development. It reorganizes the already frozen v1→v2.8.4 evidence into one manuscript argument. The authoritative empirical endpoint remains Product-A v2.8.4 `empirical_confirmation_not_supported`, followed by the separate `not_promoted` decision. Known-truth support remains preserved. Product B remains blocked.

## 1. Manuscript thesis

The strongest Product-A contribution is not that a new scalar tuning metric beats AUC. The full development sequence supports a narrower and more useful methodological claim:

> **Occurrence-only SDM tuning becomes an ecological identification problem when multiple fitted models or predictor representations are observationally substitutable. Prediction adequacy is necessary but does not establish ecological necessity. Defensible niche-driver inference therefore requires an explicit information barrier, falsification-first process tests, set-valued uncertainty, abstention when evidence is incomplete, and deterministic execution when discrete scientific outputs depend on numerical optimization.**

The fresh empirical endpoint then supplies an essential boundary condition rather than an embarrassing exception:

> Under the frozen 12-taxon × 3-seed × 3-M endpoint, the ecological procedure did not show strict independent ecological improvement over the AUC-selected role. This does not erase the known-truth recovery/safety evidence; it bounds the claim to identification architecture and controlled-truth recovery rather than general empirical superiority.

The paper should therefore present **methodological discovery through prospective falsification**, not a chronology of software versions and not a failed contest against AUC.

## 2. Original target and what changed

### 2.1 Original Product-A target

Product-A began as a prospective attempt to identify one reproducible full model-building protocol that would recover realized environmental niches more faithfully and transferably than conventional model-selection procedures. The complete choice included accessible-area/background specification, environmental candidate universe, predictor-selection strategy, regularization and response complexity. Discovery taxa selected the procedure; unseen taxa evaluated only the already-frozen procedure. Within taxa, whole spatial blocks were sealed before fitting or tuning.

This original formulation already contained three features that survive as core contributions:

1. **model-pool versus sealed answer-check separation**;
2. **M/background as a predeclared sensitivity condition, not a score-optimized tuning parameter**;
3. **promotion criteria frozen before outcome inspection, with non-promotion allowed as a valid scientific result**.

The part that did not survive was the assumption that the ecological question could always be reduced to one winning procedure.

### 2.2 The conceptual transition

Across v2.1–v2.3, known-truth falsification showed that three increasingly attractive winner-like claims were unsafe:

- recovering held-out occurrence environments did not guarantee recovery of the generating ecological process;
- producing a stable response surface did not guarantee correct process attribution;
- pruning to a sharper ecological Pareto set and intersecting retained process sets could manufacture false necessity and lose boundary coverage.

The scientific target therefore changed from

`Which complete protocol wins?`

to

`Which environmental information can be defended as necessary, possible/substitutable, contested, or unresolved under the declared observation and representation system?`

This is a refinement of the original niche-recovery goal, not a post-hoc replacement of the v2.8.4 endpoint.

## 3. Evidence sequence as methodological results

The manuscript should collapse the historical versions into five scientific results rather than narrating every implementation step equally.

### Result 1 — Prediction transfer and ecological attribution are separable

**Evidence basis:** Product-A v1, v2.1 and v2.2.

The v1 architecture demonstrated that occurrence evidence can be prospectively partitioned into a model pool and a sealed answer-check pool, with a second unseen-taxon barrier for procedure transfer. v2.1 then showed that canonical ecological recovery and canonical AUC could converge on the same procedure even under known truth. v2.2 showed the deeper structural problem: a procedure may recover held-out environments or a stable response surface while attributing the niche to the wrong environmental processes.

**Positive methodological result:** prediction metrics remain useful adequacy checks, but ecological identification is a distinct estimand.

**What this rules out:** a high AUC/CBI/transfer score cannot by itself justify a biological niche-driver claim.

### Result 2 — Agreement among retained models is not biological necessity

**Evidence basis:** v2.3.

v2.3 replaced the single winner with a set-valued ecological certificate, but then attempted to sharpen the set using mean ecological-recovery Pareto pruning. The resulting certificate was sharper in all three panels yet failed truth coverage and could create a false necessary-process core.

**Positive methodological result:** the failure identifies a specific anti-conservative operation. Neither the intersection of selected/retained fitted process sets nor the min–max spread among retained fitted models should automatically be interpreted as biological necessity or a complete uncertainty interval.

**What this rules out:** model agreement is not enough to prove process necessity.

### Result 3 — Falsification-first exclusion can protect truth, but must be allowed to abstain

**Evidence basis:** v2.4, v2.5 and v2.6.

v2.4 changed the logic from positive selection to exclusion: test whether ecological/process and response-boundary claims remain valid when information is removed under a frozen contract. The process component was already strong: all nine validation taxa had complete process certificates, zero false-required processes, and possible-process recall of 1.0. The complete process-plus-boundary product was nevertheless unavailable because discovery calibration did not cover every required response key.

v2.5 preserved the frozen minimum calibration support and refused to relax it when soil boundary keys had insufficient complete calibration taxa. Fresh validation therefore remained unopened.

v2.6 supplied the required calibration redundancy prospectively and passed the predeclared known-truth safety/coverage gate: all process and boundary certificates were complete, false-required processes were zero, and possible-process recall was 1.0. The resulting possible-process sets were deliberately broad (precision about 0.467), and calibrated response intervals were wider than complete-adequate intervals.

**Positive methodological result:** safe ecological identification requires a valid `unavailable/unresolved` state. Conservative set width is not automatically a defect when narrowing would exclude truth.

**What this rules out:** incomplete calibration support cannot be converted into negative ecological evidence, and post-outcome threshold relaxation is not an acceptable way to gain sharpness.

### Result 4 — A conservative set can become sharp without abandoning safety, provided execution is deterministic

**Evidence basis:** v2.7.1 and v2.7.2.

v2.7.1 exposed an implementation-level scientific vulnerability: independent M-shard execution changed one of 96 discrete `selected_predictors` outputs because the frozen liblinear fit did not define an explicit random-state identity. A tiny numerical/process-boundary change therefore altered a scientific variable-selection result.

v2.7.2 prospectively fixed estimator/process RNG identity and evaluated 60 unused known-truth cases from six niche families in two independent processes. Every compared floating and discrete output was exactly reproduced (observed maximum absolute and relative differences 0.0). Scientific non-regression also passed:

- robust ecological selector coverage = 1.000 (60/60);
- stable-process-core precision = 0.9889;
- stable-process-core recall = 0.9833;
- stable-process-core F1 = 0.9833;
- observation-confounded correction activation = 1.000 in the confounded family and 0.000 in all others.

**Positive methodological result:** the earlier safety–sharpness trade-off was not permanent. High-precision, high-recall process-level inference was achievable under known truth while preserving exact reproducibility.

**What this rules out:** deterministic computation is not merely software hygiene when solver drift can cross a discrete variable-selection boundary.

### Result 5 — Fresh empirical evidence bounds, rather than invalidates, the controlled-truth result

**Evidence basis:** v2.7.3 through v2.8.4.

The fresh lane introduced additional outcome-blind availability gates. v2.7.3 showed that spatial validation geometry itself can make a frozen denominator unavailable before any environmental value, model score or sealed ecological value is read. v2.8.1–v2.8.2 rebuilt a fresh cohort/source under frozen eligibility and provenance constraints. v2.8.3 reached model-pool computation but terminated at a frozen runtime boundary before sealed ecological evidence, so it is technical provenance rather than ecological evidence.

v2.8.4 preserved the v2.8.3 scientific semantics and changed only execution/runtime structure. It completed the full preregistered denominator: every one of three seed parts contained all 12 taxa and all three 150/300/500-km M specifications. The prediction guardrail passed; the ecological procedure was nondominated relative to the AUC role in 3/3 parts; process-status reproducibility passed; but strict ecological improvement occurred in 0/3 parts and the mean presence-rank delta versus AUC was 0.0. The terminal result is therefore `empirical_confirmation_not_supported` and the separate promotion decision is `not_promoted`.

**Positive methodological result:** the same prospectively sealed architecture can distinguish controlled-truth support, technical unavailability, and genuine empirical non-support without changing the denominator or thresholds after outcome inspection.

**What this rules out:** Product-A cannot claim general empirical superiority to AUC, and Product B cannot be unblocked from the current endpoint.

## 4. The paper’s main conceptual model

The final paper should organize SDMR around four separations.

### 4.1 Prediction versus ecological identification

Prediction asks whether a fitted surface ranks or transfers occurrence evidence adequately. Ecological identification asks which environmental information is defensible as part of the realized niche interpretation. Prediction is a guardrail, not a synonym for ecological truth.

### 4.2 Model versus process versus representation

A raw raster, an ecological process and a substitutable representation are different objects. The Chapter-1 hierarchy should therefore be used as an interpretation framework:

`geophysical template → direct environmental field → integrated biological exposure → composite summary representation`

Predictor roles should remain explicit: spatial geometry, substrate, direct environment, derived exposure, proxy and composite summary. A selected raster is not automatically a causal driver.

### 4.3 Positive selection versus falsification

A process should not be called necessary merely because it appears in the best or most stable fitted models. The stronger question is whether the ecological certificate remains viable when the declared information carried by that process is prospectively unavailable.

For future work, this implies that exclusion must eventually operate on a predeclared **process-information/proxy closure**, not only on one process-labelled raster at a time. That prospective extension is a future design implication, not evidence already validated by Product-A v2.8.4.

### 4.4 Non-support versus unavailability

The manuscript must keep four states distinct:

- supported under the frozen criterion;
- scientifically not supported under complete evidence;
- unavailable/unresolved because the required evidence product is incomplete;
- technical execution failure before the scientific outcome exists.

Collapsing these states would erase one of the strongest methodological contributions of the development sequence.

## 5. What is genuinely novel

The novelty claim should not be “we invented a better SDM score.” The strongest defensible novelty is the integration of the following into one prospective ecological-identification workflow:

1. **sealed-before-tuning information barriers** at both spatial-block and unseen-taxon levels;
2. **explicit separation of record-prediction criteria from ecological niche-recovery targets**;
3. **set-valued process inference that preserves contested/substitutable alternatives instead of forcing one winner**;
4. **falsification-first necessity logic with abstention when calibration or boundary evidence is incomplete**;
5. **observation-process correction applied to both model predictions and the held-out occurrence target, recognizing that the answer-check occurrence distribution itself can be observation-biased**;
6. **deterministic execution as part of scientific reproducibility when floating differences can alter discrete selected predictors**;
7. **prospective distinction between scientific non-support and technical/unavailable states**;
8. **a full-denominator empirical endpoint that preserves the negative result rather than retuning the dataset or criterion**.

Individual ingredients have precedents in SDM, model selection, partial identification, robustness analysis and reproducible computation. The manuscript should claim novelty in their ecological-identification synthesis and in the falsification sequence that demonstrates why each separation is needed.

## 6. Claim hierarchy for the manuscript

### Strong claims supported now

- Prediction adequacy and ecological process recovery can diverge under known truth.
- Stable or high-performing fitted models can still support the wrong generating process.
- Pareto sharpening / retained-model agreement can become anti-conservative for process necessity and boundary uncertainty.
- Falsification-first set-valued certificates can achieve zero false-required processes and complete true-process recall under known truth when calibration is adequate.
- The deterministic successor recovered stable process cores with approximately 0.99 precision and 0.98 recall across fresh known-truth cases.
- Observation-process confounding can be detected/corrected in controlled truth without indiscriminate correction activation.
- Numerical process identity can be scientifically material for discrete predictor selection.
- Fresh empirical confirmation can be prospectively evaluated without converting technical failures or incomplete evidence into ecological outcomes.

### Claims explicitly not supported

- General empirical superiority of the Product-A ecological procedure over AUC.
- A universal claim that AUC is optimal.
- Recovery of the fundamental niche, demographic fitness, dispersal history or biotic interactions from the current empirical endpoint.
- Causal interpretation of any selected raster solely because it was selected.
- A validated universal plant-driver core (Product B remains blocked).

### Future implication, not current result

A hierarchy-aware successor could test **process-information indispensability under a predeclared representation/proxy registry**. Such a study would need a new prospective contract and independent evidence and must not be used to reinterpret or rescue the consumed v2.8.4 endpoint.

## 7. Recommended manuscript structure

### Introduction

**Problem:** SDM variable/model tuning is often evaluated as a prediction-selection problem, but ecological interpretation asks a stronger identification question. Correlated/substitutable environmental representations, observation bias and spatial transfer can let multiple procedures predict similarly while implying different environmental mechanisms.

**Gap:** existing performance criteria can quantify discrimination, calibration, omission or parsimony, but no scalar criterion by itself establishes which environmental information is necessary for niche interpretation.

**Aim:** develop and prospectively falsify an occurrence-only ecological-identification workflow that separates prediction adequacy from process recovery and reports necessity, possibility/substitutability, contestation and unresolved evidence without outcome-driven retuning.

### Methods

Organize by scientific objects, not version numbers:

1. information barrier and frozen evidence;
2. candidate model-building procedures and conventional comparators;
3. ecological audit space and known-truth generators;
4. set-valued ecological certificates;
5. falsification-first process/boundary exclusion and calibration;
6. observation-process separation;
7. deterministic execution/parity gate;
8. fresh empirical full-denominator confirmation and decision rule.

Version identifiers belong in a provenance table/supplement.

### Results

Use the five Results above:

1. prediction transfer does not guarantee process recovery;
2. retained-model agreement can create false necessity;
3. falsification-first certificates protect truth but sometimes require abstention;
4. deterministic set-valued inference becomes both safe and sharp on fresh known truth;
5. complete fresh empirical confirmation does not show strict improvement over AUC.

### Discussion

Lead with the positive synthesis:

> The principal result is not a universally superior selector, but a change in what an interpretable tuning procedure must prove. When observationally substitutable models fit the same occurrence evidence, choosing one best model is weaker than establishing which environmental information survives prospective falsification.

Then discuss:

- why prediction metrics remain necessary but insufficient;
- why conservative sets/abstention are scientifically informative;
- why representation hierarchy/proxy closure is the next identification problem;
- why v2.8.4 bounds external validity rather than negating known-truth architecture;
- presence-only limitations and no causal/fundamental-niche claim.

### Conclusion

A concise closing claim:

> SDM tuning should not automatically force ecological interpretation into a single winning predictor set. Prospectively sealed occurrence evidence, falsification-first process exclusion and explicit set-valued uncertainty can recover ecological process structure accurately under controlled truth while exposing when empirical data do not distinguish the proposed ecological procedure from a conventional AUC-selected comparator. The resulting contribution is therefore an identification framework—and a disciplined account of its limits—rather than a claim of universal predictive superiority.

## 8. Figures that make the argument visually obvious

### Figure 1 — From model selection to ecological identification

Left: conventional `candidate models → scalar score → winner`.

Right: SDMR `model pool → prediction adequacy → ecological admissible set → process falsification → necessary / possible / contested / unresolved → sealed answer-check`.

### Figure 2 — Falsification sequence

Show the methodological lessons, not software versions:

`winner transfer` → `prediction ≠ process` → `agreement ≠ necessity` → `exclusion + abstention` → `safe broad set` → `deterministic sharp process core` → `fresh empirical boundary`.

Version labels can sit underneath each stage.

### Figure 3 — Known-truth recovery

Panel A: v2.3 sharpening versus coverage loss.

Panel B: v2.6 false-required = 0, recall = 1.0 but broad precision.

Panel C: v2.7.2 stable-core precision 0.9889, recall/F1 0.9833, exact process parity.

### Figure 4 — Evidence-state funnel

`known truth supported` → `fresh cohort structurally screened` → `technical states kept separate` → `v2.8.4 full denominator complete` → `strict improvement 0/3` → `not promoted`.

This figure makes the non-support endpoint an integrity result rather than a hidden footnote.

## 9. What should move to supplement

Move most version-by-version implementation chronology, workflow IDs, recovery attempts and artifact details to a provenance supplement. Keep in the main text only a compact development/falsification table with columns:

`question → prospectively frozen test → result → methodological consequence`.

The main paper should not read like a GitHub changelog.

## 10. Final manuscript position

The v1→v2.8.4 sequence supports a coherent endpoint:

**Product A did not establish a generally superior empirical winner. It established why niche-driver tuning cannot safely be treated only as winner selection, implemented an alternative falsification/set-valued architecture, demonstrated high process recovery and exact reproducibility under fresh controlled truth, and then prospectively showed the boundary of that advantage in fresh occurrence data.**

That combination—positive controlled-truth identification, explicit failure modes, abstention semantics, reproducibility, and an unrepaired empirical non-support endpoint—is the manuscript story to submit.
