# Abstention-aware process identification recovers ecological information without false attribution in prospective known-truth tests

**Working target:** Methods in Ecology and Evolution  
**Status:** positive-core manuscript v1  
**Scientific basis:** SDMR v6 prospective known-truth v2 only

## Abstract

Ecological models can predict occurrences while remaining ambiguous about the environmental processes represented by their predictors. Correlated predictors, redundant representations, shared carriers and incomplete environmental systems make a one-variable–one-process interpretation especially fragile. We developed an abstention-aware process-information framework that asks whether a declared process is replaceable, contributory, required, unresolved or unavailable, rather than forcing every fitted model into a sharp process claim. The framework separates process identification (Stage P) from geographic transfer (Stage T), preserves structurally nonseparable states as unresolved, and refuses full-system interpretation when the declared information system is inadequate. We froze the complete method, known-truth worlds, sample sizes, thresholds and six promotion gates before first opening a prospective denominator of seeds 74001–74020. Across 1,020 declared process-state cells, the method recovered 71 of 80 positive targets (0.8875), produced 0 false positives among 700 replaceable targets, over-resolved 0 of 60 unresolved targets, violated 0 of 60 structural refusals, and made no sharp or favorable calls in 120 unavailable cells. Six informative control worlds each achieved 20/20 full-system authorization, whereas the omitted-driver null control was authorized 0/20 times. All six prospective gates passed. The result demonstrates that process-information recovery can be designed around asymmetric error control: some supported processes may be missed, but unsupported attribution and unjustified resolution need not be traded for apparent decisiveness. The evidence is prospective known-truth validation, not yet an empirical ecological process claim.

## Introduction

Species-distribution and niche models are often interpreted twice. First, they are asked to predict where organisms occur. Second, their fitted environmental associations are read as evidence about the processes that constrain occurrence. These two uses need not coincide. Several predictor sets can make nearly equivalent predictions, one predictor can carry information about several processes, and a biologically real process can be represented redundantly or only indirectly.

The inferential problem is therefore not simply variable selection. The relevant question is **what process information is identified by the declared predictor system and observation design**.

A sharp binary answer creates two recurrent errors. Removing one predictor can be interpreted as removing one process even when the same process remains represented elsewhere. Conversely, a performance loss after removing a correlated predictor can be attributed to that predictor's named process even when the intervention also removed information shared with another process. Missing information creates a third problem: a process may be impossible to classify because the declared system is incomplete or because available representations are structurally nonseparable.

We address these problems with a set-valued process-information framework. For each declared environmental process, the method admits five states:

- **replaceable** — at least one adequate process-free route retains noninferior ecological reconstruction;
- **contributory** — removing the process information makes all declared adequate routes meaningfully worse while at least one process-free route remains adequate;
- **required** — all process-free routes become inadequate;
- **unresolved** — route evidence is incomplete, interval-indeterminate or structurally nonseparable;
- **unavailable** — the full declared information system itself is inadequate for process interpretation.

The design is deliberately asymmetric. It is allowed to miss a true positive process state when evidence is insufficient. It is not allowed to turn incomplete or nonseparable evidence into a sharp favorable attribution.

That asymmetry creates a methodological challenge: a conservative method can look safe simply because it rarely says anything. We therefore require positive recovery and error control simultaneously. A useful process-identification method must recover most identifiable positive process states while also preserving replaceability, unresolvedness and unavailability when those are the correct inferential states.

Here we test that requirement prospectively. We developed the framework on separate consumed known-truth systems, then froze the complete v6 pipeline before opening a fresh denominator of 20 unused seeds across eight predeclared process worlds. The worlds were chosen to separate unique information, redundant representation, shared carriers, null correlation, nonlinear interaction, observation confounding, omitted drivers and geographic transfer. Six prospective gates jointly tested denominator integrity, positive recovery, false attribution, abstention integrity, full-system authorization and spatial-transfer safety.

Our central question is simple: **can occurrence-only process inference recover positive environmental information without buying that recovery through false attribution or over-resolution?**

## Methods

### Process-information states

For one process, the method evaluates matched full-versus-process-free routes. Let delta denote the loss in ecological reconstruction after process information is removed, with positive values indicating worse reconstruction.

A process is **replaceable** when at least one complete and adequate process-free route has an uncertainty upper bound no greater than the frozen noninferiority margin.

A positive state requires stronger evidence. If every declared route is complete and all uncertainty lower bounds exceed the margin, the process is classified as contributory when at least one process-free route remains adequate and required when none does.

Incomplete route sets or interval-indeterminate comparisons remain **unresolved**.

If the full model itself fails the frozen information-adequacy gate, process interpretation is **unavailable**.

Identical process-information closures are never forced into separate sharp states. When two declared processes are structurally inseparable under the available representations, the sharp attribution is replaced by unresolved.

### Full-system authorization

Process-level states are interpreted only when the declared predictor system contains sufficient information for the ecological question. The full-system gate therefore precedes favorable process interpretation.

The v6 pipeline uses a frozen magnitude-permutation rule for full-system authorization. Omitted-driver worlds serve as a null control: the system should refuse authorization when the generating information lies outside the declared environmental representation.

This system-level refusal is distinct from process-level unresolvedness. An unresolved process can occur inside an otherwise adequate system; unavailable denotes failure of the declared system itself.

### Stage P and Stage T

We separate two estimands that are often conflated.

**Stage P** asks whether process information is identified within the declared ecological reconstruction problem.

**Stage T** asks whether the resulting process-information conclusion survives the predeclared spatial-transfer evaluation.

A Stage-P positive state is not automatically treated as evidence of geographic transfer. Stage T is evaluated separately and is allowed to remain unresolved or replaceable without retroactively changing the Stage-P result.

### Known-truth worlds

Eight frozen worlds were used:

1. **unique_process** — a process has a distinct direct representation;
2. **redundant_representation** — the same process information is available through redundant predictors;
3. **shared_carrier** — one observed carrier jointly represents thermal and water information;
4. **null_correlated** — a non-generating predictor is strongly correlated with a generating one;
5. **interaction** — suitability depends primarily on a thermal × water interaction;
6. **observation_confounded** — recording effort is environmentally confounded;
7. **omitted_driver** — the true driver is absent from the declared predictor universe;
8. **geographic_shift** — a proxy relationship changes sign outside the model-pool region.

The first, second, third, fourth, fifth and eighth worlds were the six informative controls used in the full-system authorization requirement. The observation-confounded world was report-only for that authorization subgate. The omitted-driver world was the null control.

### Prospective information barrier

All development denominators were retired before the prospective test.

The final prospective contract fixed:

- seeds 74001–74020;
- eight known-truth worlds;
- sample size and model capacity;
- the ODO process-state targets;
- process margin;
- Stage-P and Stage-T roles;
- full-system magnitude-permutation rule;
- KT-A through KT-F thresholds;
- failure handling and denominator preservation.

The seeds were opened once, after the full contract and implementation were frozen.

### Prospective denominator

Across the 20 seeds, the frozen target contained:

- 80 positive process cells;
- 700 replaceable cells;
- 60 unresolved cells;
- 120 unavailable cells;
- 60 cells with structural-refusal requirements.

These categories are not interchangeable. Positive recovery evaluates sensitivity to identifiable process information; the other denominators evaluate whether the method creates unsupported sharp states.

### Prospective gates

The method passed only if all six gates passed.

**KT-A — provenance and denominator integrity.**  
Every declared seed, world and process cell had to be present under the frozen execution identity.

**KT-B — positive recovery.**  
Stage-P recovery of positive ODO states had to be at least 0.80.

**KT-C — false-positive control.**  
Favorable positive states among ODO-replaceable cells had to remain at or below the frozen maximum.

**KT-D — abstention integrity.**  
ODO-unresolved cells and structural-refusal cells could not be sharpened beyond the frozen tolerances.

**KT-E — full-system authorization.**  
Unavailable systems could not receive sharp or favorable calls; informative control worlds had to authorize; the omitted-driver null had to remain unauthorized.

**KT-F — spatial-transfer safety.**  
Stage T had to be complete and could not create excessive contradictions or violate structural refusals.

The scientific decision was the strict conjunction of all six gates.

## Results

### Positive process information was recovered

The frozen prospective test recovered **71 of 80 positive process states**, for a Stage-P positive recovery rate of **0.8875**.

The result therefore exceeded the predeclared 0.80 positive-recovery gate while leaving nine positive targets unrecovered.

The method did not achieve its favorable result by calling every process positive.

### Replaceable processes were not falsely promoted

Among **700 ODO-replaceable cells**, favorable false-positive calls were **0/700**.

Thus the positive recovery of 71/80 did not require a corresponding increase in favorable attribution for processes that were observationally replaceable under the known-truth target.

### Unresolved and structurally nonseparable states remained unresolved

Among **60 ODO-unresolved cells**, over-resolution was **0/60**.

Among **60 structural-refusal cells**, sharp-state violations were **0/60**.

These cells are important because they distinguish abstention-aware inference from a classifier that simply shifts errors between positive and negative labels.

### Unavailable systems did not produce favorable process claims

Across **120 unavailable cells**:

- favorable positive calls: **0/120**;
- sharp-state calls: **0/120**.

The omitted-driver null world was authorized **0/20** times.

By contrast, every one of the six informative controls achieved full-system authorization in **20/20** prospective seeds:

- unique_process 20/20;
- redundant_representation 20/20;
- shared_carrier 20/20;
- null_correlated 20/20;
- interaction 20/20;
- geographic_shift 20/20.

The observation-confounded world had a report-only authorization rate of 1/20 and did not enter the strict informative-control minimum.

### Process identification remained separated from geographic transfer

Stage-T evaluation was complete for the entire prospective denominator.

No Stage-P positive cell was converted into a spatially replaceable contradiction in the final prospective run, and spatial structural-refusal violations were zero.

Thus the method preserved the distinction between identifying process information and demonstrating its spatial transfer.

### All prospective gates passed

KT-A through KT-F all passed under the predeclared strict conjunction.

The prospective endpoint therefore closed as **prospective_known_truth_passed**.

No threshold, seed, family, world or denominator was changed after outcome opening.

## Discussion

### The main result is asymmetric error control, not perfect recovery

The method deliberately does not recover every positive process state. Nine of 80 positive targets were missed.

That loss of sensitivity is the cost of refusing unsupported attribution.

The important prospective result is the combination:

- positive recovery = **0.8875**;
- favorable false attribution = **0/700**;
- unresolved over-resolution = **0/60**;
- structural-refusal violation = **0/60**;
- sharp calls under unavailable systems = **0/120**.

This pattern supports a design principle for ecological process inference: **permit missed conclusions when the available information does not identify a process, but do not manufacture specificity from redundancy, shared carriers or absent information.**

### Predictor importance and process information are different objects

The known-truth worlds show why a process cannot be equated with one predictor.

In the redundant-representation world, the process remains identifiable even when one representation can substitute for another.

In the shared-carrier world, thermal and water information cannot be safely split merely because one predictor has a statistical effect.

In the null-correlated world, strong correlation with a generating predictor does not make the correlated process generating.

The object of inference is therefore the process-information closure represented by the declared predictor system, not a list of independently interpreted coefficients.

### Unavailability is a scientific result

The omitted-driver control illustrates a boundary that conventional variable-importance workflows often hide.

When the process that generated occurrence patterns lies outside the declared predictor system, the appropriate result is not “all included processes are unimportant” and not “the best remaining variable is causal.” It is that the declared system is insufficient for the requested process interpretation.

The v6 full-system gate recognized this case prospectively: omitted-driver authorization was 0/20.

### Process inference and transfer should remain separate

A process can be identifiable in the model-pool ecology without being safely transferable to a new geographic context.

The explicit Stage-P / Stage-T split prevents spatial generalization from being smuggled into a process-identification claim. This distinction is particularly important under proxy shift, where predictor relationships can reverse outside the model-pool region.

### What the result does not establish

This study is a prospective known-truth validation.

It does not establish that the inferred states correspond to causal physiological mechanisms in real species.

It does not establish that the same performance will hold with incomplete biodiversity data, imperfect environmental rasters or different process registries.

It does not establish universal superiority over every variable-selection method.

The result instead establishes a narrower methodological fact: under a frozen synthetic system containing redundancy, correlation, interaction, confounding, missing drivers and geographic shift, an occurrence-only process-information procedure recovered most positive states while preserving replaceability, unresolvedness and unavailability.

Fresh empirical evaluation is therefore a separate next step rather than evidence that can be backfilled into the known-truth result.

## Conclusion

A useful ecological process-identification method should be judged by more than how often it returns a process label. It must also demonstrate that it can refuse labels that the available information does not support.

In a prospectively frozen known-truth test, SDMR recovered 88.75% of positive process states while producing no favorable false attribution among 700 replaceable states and no over-resolution among unresolved, structurally nonseparable or unavailable states.

The central methodological result is consequently not maximal decisiveness. It is **evidence-bounded process identification: recover process information when it is identified, and preserve uncertainty when it is not.**

## Reproducibility

Canonical prospective endpoint:

- workflow run: 36212033498
- artifact: 10896590112
- digest: sha256:7c0c3dd6f12a0478abcd0fadabdb013a26356ac7ac6dacca7bc2cbdabee7fe68
- prospective seeds: 74001–74020

The canonical code, frozen contracts, focused tests and result receipts are on the repository main branch following the M5 promotion merge.

The unrelated failed `development/proxy-closed-route-evidence-v6` programme is not part of this manuscript.
