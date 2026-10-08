# Abstention-aware process identification recovers ecological information without false attribution in prospective known-truth tests

**Article type:** Research Article  
**Target:** Methods in Ecology and Evolution

## Abstract

1. Ecological models can predict occurrence patterns while remaining ambiguous about which environmental processes their predictors represent. Correlated predictors, redundant representations, shared carriers and incomplete predictor systems make one-variable–one-process interpretations especially fragile. We developed an abstention-aware process-information framework that classifies declared processes as replaceable, contributory, required, unresolved or unavailable rather than forcing every fitted model into a sharp process claim.

2. The framework separates process identification from geographic transfer, preserves structurally nonseparable states as unresolved and refuses process interpretation when the full declared information system is inadequate. We froze the complete method, known-truth worlds, sample sizes, thresholds and six promotion gates before opening a prospective denominator of seeds 74001–74020.

3. Across 1,020 declared process-state cells, the method recovered 71/80 positive targets (0.8875), produced 0/700 favorable false positives among replaceable targets, over-resolved 0/60 unresolved targets, violated 0/60 structural-refusal cases and made no sharp or favorable calls in 120 unavailable cells. Six informative control worlds each achieved 20/20 full-system authorization, whereas an omitted-driver null was authorized 0/20 times. All six prospective gates passed.

4. Process-information recovery can therefore be designed around asymmetric error control: identifiable process information is recovered without purchasing apparent decisiveness through false attribution or unjustified resolution. The contribution is an inferential boundary for occurrence-only environmental process claims, not a claim that correlative models recover causal physiology.

**Data/Code for peer review:** An anonymized reviewer bundle containing the frozen contracts, source code, focused tests and canonical result receipts will be supplied through the submission system. The permanent public archive DOI and repository URL will be added to the accepted version.

**Keywords:** abstention; ecological niche modelling; model adequacy; process identifiability; species distribution models; variable importance

## 1. Introduction

Species-distribution and ecological niche models are often interpreted twice. First, they predict where organisms occur. Second, fitted environmental associations are read as evidence about the processes constraining those occurrences. These uses need not coincide. Presence-only and use–availability models require care in biological interpretation because fitted associations depend on the observation and availability design (Aarts, Fieberg & Matthiopoulos 2012). Collinearity can destabilize variable-level interpretation (Dormann et al. 2013), and standard variable-importance summaries can overstate evidence for individual predictors (Galipaud et al. 2014).

Recent explainability methods can quantify predictor contributions more flexibly, including Shapley-based contributions in modern SDMs (Zbinden et al. 2026). Those methods address an important but different target: how much a predictor contributes to a fitted prediction. Our target is **process-information identifiability under a declared predictor and observation system**. A process may remain represented after one variable is removed, one observed variable may carry information about several processes, and an apparently best predictor can remain uninterpretable when the required process information is absent.

A second line of prior work addresses the ambiguity of predictor importance more directly. Conditional permutation importance adjusts the variable-level perturbation to account for correlated predictors (Strobl et al. 2008), while model class reliance reports the range of feature-importance values across a prespecified set of well-performing models rather than elevating one fitted model (Fisher et al. 2019). Those approaches demonstrate why single-model importance rankings are insufficient, and are substantive conceptual comparators—not just alternative predictive metrics. Neither, by itself, defines an ecological process through **all its declared information carriers**, tests whether the full representation system is adequate, or returns the explicit process-level *unresolved* and *unavailable* states evaluated here. These distinctions concern the **inferential target and decision rule**, not an established predictive advantage over conditional importance or model class reliance.

This distinction is consistent with a broader principle of ecological model adequacy: interpretation should not exceed what the model and data can support (Getz et al. 2018). We operationalize that principle as a state space for process information.

For each declared environmental process, the framework admits five states:

- **replaceable** — at least one adequate process-free route retains noninferior reconstruction;
- **contributory** — removing process information makes all declared adequate routes meaningfully worse while at least one process-free route remains adequate;
- **required** — every complete process-free route falls below the frozen adequacy floor;
- **unresolved** — route evidence is incomplete, interval-indeterminate or structurally nonseparable;
- **unavailable** — the full declared predictor system is itself inadequate for the requested process interpretation.

The design is intentionally asymmetric. It may miss a true positive process state when evidence is insufficient, but it should not convert redundancy, nonseparability or missing information into a sharp attribution.

That asymmetry creates a methodological challenge: a conservative method can appear safe simply because it rarely says anything. A useful method must therefore recover positive process information and control unsupported sharpening simultaneously.

Here we evaluate that requirement prospectively using known-truth worlds. Development denominators were retired before a fresh test. The complete v6 pipeline, eight world families, sample sizes, thresholds and six promotion gates were frozen before opening seeds 74001–74020. Our question was: **can occurrence-only process inference recover positive environmental information without buying that recovery through false attribution or over-resolution?**

## 2. Materials and Methods

### 2.1 Process-information states

For one process, the method evaluates matched full-versus-process-free routes. Let delta denote the loss in ecological reconstruction after all declared information carriers for a process are removed, with positive values indicating worse reconstruction.

A process is **replaceable** when at least one complete and adequate process-free route has an uncertainty upper bound no larger than the frozen noninferiority margin.

A positive state requires stronger evidence. If every declared route is complete and all uncertainty lower bounds exceed the margin, the process is **contributory** when at least one process-free route remains adequate and **required** when none does.

Incomplete route sets or interval-indeterminate comparisons remain **unresolved**.

If the full predictor system itself fails the frozen information-adequacy gate, the process state is **unavailable**.

Identical process-information closures are not forced into separate sharp states. If two declared processes are structurally inseparable under the available representations, sharp attribution is replaced by unresolved. Figure 1 summarizes the distinction between single-predictor deletion and process-closure knockout, and the five conditional information states.

### 2.2 Full-system authorization

Process states are interpreted only when the declared predictor system contains sufficient information for the ecological question. The full-system gate therefore precedes favorable process interpretation.

The v6 pipeline uses a frozen magnitude-permutation rule. Full-system predictions are fitted on training folds, predictions remain fixed and held-out labels are permuted within folds. Authorization requires all of the following:

- mean balanced log score at least -0.75;
- positive mean gain over the random-label null;
- mean gain at least 0.01;
- permutation P <= 0.001 under 999 permutations.

An omitted-driver world serves as a null control: authorization should fail when the true generating information is outside the declared predictor system.

System-level unavailability is distinct from process-level unresolvedness. A process can be unresolved inside an otherwise adequate system; unavailable means that the declared system is not informative enough for the requested process interpretation.

### 2.3 Stage P and Stage T

We separate two estimands that are often conflated.

**Stage P — process identification** asks whether process information is identified within the declared ecological reconstruction problem.

**Stage T — geographic transfer** asks whether the Stage-P conclusion remains compatible with a frozen spatial-transfer evaluation.

A Stage-P positive state is not automatically treated as evidence of geographic transfer. Stage T cannot retroactively sharpen or rescue a Stage-P claim. Spatially structured validation is motivated by the known risk that random cross-validation understates error when ecological observations and predictors are spatially dependent (Roberts et al. 2017), but passing a spatial holdout still does not identify a biological mechanism.

### 2.4 Known-truth worlds

Eight frozen worlds were used.

1. **unique_process** — a process has distinct information unavailable elsewhere;
2. **redundant_representation** — process information can be reconstructed from alternative declared representations;
3. **shared_carrier** — one observed carrier jointly represents thermal and water information;
4. **null_correlated** — a non-generating process is strongly correlated with a generating one;
5. **interaction** — suitability depends primarily on a thermal × water interaction;
6. **observation_confounded** — recording effort is environmentally confounded;
7. **omitted_driver** — the true driver is absent from the declared predictor universe;
8. **geographic_shift** — a proxy relationship changes outside the model-pool region.

Figure 2 records the eight frozen world designs and their authorization roles. Unique process, redundant representation, shared carrier, null correlation, interaction and geographic shift were informative controls for full-system authorization. Observation confounding was report-only for that subgate. Omitted driver was the null control.

### 2.5 Prospective information barrier

The prospective contract fixed before outcome opening:

- seeds 74001–74020;
- all eight world families;
- sample size and learner capacity;
- process-state targets;
- the process margin and adequacy floor;
- the 999-permutation authorization rule;
- Stage-P and Stage-T roles;
- KT-A through KT-F thresholds;
- denominator and failure handling.

The prospective seeds were opened once after the contract and implementation were frozen.

### 2.6 Prospective denominator

Across 20 seeds, the frozen target contained:

- 80 positive process cells;
- 700 replaceable cells;
- 60 unresolved cells;
- 120 unavailable cells;
- 60 structural-refusal cells.

These denominators test different failure modes. Positive recovery measures sensitivity to identifiable process information. The remaining denominators test whether the method manufactures sharp process claims where the known truth says it should not.

### 2.7 Prospective promotion gates

The method passed only if all six gates passed.

**KT-A — provenance and denominator integrity.** Every declared seed, world and process cell had to be present under the frozen execution identity.

**KT-B — positive recovery.** Stage-P recovery of positive target states had to be at least 0.80.

**KT-C — false-positive control.** Favorable positive states among replaceable cells had to remain at or below the frozen maximum of 0.01.

**KT-D — abstention integrity.** Over-resolution of unresolved cells and violations of structural refusals had to remain zero.

**KT-E — full-system authorization.** Unavailable systems could not receive sharp or favorable calls; each informative control had to authorize in at least 95% of seeds; the omitted-driver null could never authorize.

**KT-F — spatial-transfer safety.** Stage-T evaluation had to be complete, with positive-to-spatial-replaceable contradiction rate <=0.05 and zero structural-refusal violations.

The scientific endpoint was the strict conjunction of KT-A through KT-F.

## 3. Results

### 3.1 Positive process information was recovered

The prospective test recovered **71 of 80 positive process states**, giving Stage-P positive recovery of **0.8875**. This exceeded the frozen 0.80 threshold while leaving nine positive targets unrecovered (Figure 3).

### 3.2 Replaceable processes were not falsely promoted

Among **700 replaceable cells**, favorable false-positive calls were **0/700**. Positive recovery was therefore not obtained by broadly calling processes contributory or required.

### 3.3 Unresolved and structurally nonseparable states remained bounded

Among **60 unresolved cells**, over-resolution was **0/60**. Among **60 structural-refusal cells**, sharp-state violations were **0/60**.

These denominators distinguish abstention-aware inference from a classifier that merely trades false positives for false negatives.

### 3.4 Unavailable systems did not produce process claims

Across **120 unavailable cells**, favorable calls were **0/120** and sharp calls were **0/120**.

The omitted-driver null world was authorized **0/20** times.

Each informative control achieved full-system authorization in **20/20** seeds (Figure 4):

- unique_process;
- redundant_representation;
- shared_carrier;
- null_correlated;
- interaction;
- geographic_shift.

The observation-confounded world authorized in 1/20 seeds but was predeclared report-only for this subgate.

### 3.5 Process identification remained separate from geographic transfer

Stage-T evaluation was complete across the prospective denominator. No Stage-P positive cell became a spatially replaceable contradiction, and spatial structural-refusal violations were zero.

### 3.6 All prospective gates passed

KT-A through KT-F all passed under the strict frozen conjunction. The endpoint therefore closed as **prospective_known_truth_passed** with no post-opening change to thresholds, seeds, worlds or denominators.

## 4. Discussion

### 4.1 The main result is asymmetric error control, not perfect recovery

The method missed 9/80 positive targets. That sensitivity loss is part of the result, not a defect to hide.

The key prospective combination was:

- positive recovery = **0.8875**;
- false favorable attribution = **0/700**;
- unresolved over-resolution = **0/60**;
- structural-refusal violations = **0/60**;
- sharp calls under unavailable systems = **0/120**.

This supports a simple design principle: allow missed conclusions when the information needed for attribution is insufficient, but do not manufacture specificity from redundancy, shared carriers or absent information.

### 4.2 Predictor importance and process information are different objects

Variable-importance methods ask how much a fitted prediction depends on a predictor. That is valuable for explanation, and modern methods can quantify such contributions robustly (e.g. Zbinden et al. 2026). The present framework asks a different question: whether **process information** remains when all declared carriers of a process are challenged.

This distinction matters under correlated predictors. Collinearity can make coefficients and variable rankings unstable (Dormann et al. 2013), but redundancy is not merely a nuisance to remove. If two predictors are both declared carriers of the same ecological process, deleting either predictor alone does **not** establish that the process is replaceable: the other carrier remains. Only after excluding the **entire declared process-information closure** can noninferior reconstruction from process-free routes support a replaceable process-information state. Conversely, a variable declared outside that closure may still act as a correlated proxy for its information, a limitation of the chosen registry and observation system rather than proof that the biological process is unnecessary.

Likewise, a shared carrier creates the opposite problem. One predictive variable can support more than one named process, so variable-level importance does not imply unique process attribution.

Conditional permutation importance (Strobl et al. 2008) addresses dependence in variable-level importance calculations. Model class reliance (Fisher et al. 2019) explicitly respects the possibility that different well-performing models attribute different importance to the same feature. Both are more relevant precedents than AUC or a single unadjusted ranking. Our framework instead challenges the complete, predeclared carrier closure of a *named ecological process*, then distinguishes replaceability from positive, unresolved and unavailable **information states**. MaskSDM (Zbinden et al. 2026) can evaluate flexible feature subsets and Shapley contributions, including groups; that capability is compatible with, but does not by itself supply, a process-adequacy or abstention certificate. Process labels and carrier sets here remain **researcher-declared modelling assumptions**, not biologically verified causes.

### 4.3 Unavailability is a scientific result

The omitted-driver world makes the boundary explicit. When the true generating information lies outside the declared predictor universe, the appropriate process result is not that all included processes are unimportant, nor that the strongest remaining predictor is mechanistic. The declared information system is simply insufficient for the requested process interpretation.

This operationalizes model adequacy as an inferential state rather than only a diagnostic recommendation (Getz et al. 2018).

### 4.4 Process inference and transfer should remain separate

Process information identified in a model-pool region need not transfer geographically. Proxy relationships can change outside that region, and predictive stability can fail even when the original process-information claim was valid locally.

The Stage-P/Stage-T separation prevents geographic generalization from being smuggled into a process-identification claim.

### 4.5 Scope and limitations

This study is prospective known-truth validation.

It does **not** establish causal physiological mechanism recovery in real species, empirical performance across biodiversity databases or universal superiority over every SDM and variable-selection approach. No head-to-head benchmark against conditional variable importance, model class reliance or MaskSDM was conducted; their different inferential outputs preclude a simple numerical performance ranking without designing a common target. The observed zero error counts are finite-sample outcomes under the declared dependent world/seed structure, **not** universal zero-error guarantees.

The result is narrower: under a frozen system containing redundancy, correlation, interaction, observation confounding, missing drivers and geographic shift, an occurrence-only process-information procedure recovered most positive states while preserving replaceability, unresolvedness and unavailability.

**Empirical applicability was also tested separately, and the result limits generalization.** In the final programme of a sequentially developed series of separately frozen real-plant tests, all 50 taxa passed the 46-predictor feature-completeness gate, but only 10/50 had an available process-first prediction route and only 16/300 taxon-by-process cells (5.33%) received a stable sharp state across the two learner routes. This failed the predeclared 80% stability requirement *before* the sealed answer-check was opened. A subsequently completed, explicitly post-terminal predictive characterization also failed to establish superiority over a matched flat selector (mean balanced-log-score difference −0.00386; taxon-bootstrap 95% interval [−0.01117, +0.00289]). None of these results was used to modify or re-promote the real-data programme.

Earlier fresh-real attempts also stopped at predeclared gates: v2 at 37/50 complete taxa after structural source decoding, v3 at 48/50 complete taxa and v4 at 89/90 candidates meeting the fixed 300-km background requirement. The programme sequence, including design changes made between attempts, is disclosed in the Supporting Information (`PROCESS_INFORMATION_EMPIRICAL_ATTEMPTS_SI_V1.md`); these attempts are not pooled or portrayed as independent confirmatory replications.

The real-data failure was not reducible to missing raster layers. In the model-pool-only analysis, the full-system gate authorized **32/50** taxa under shallow-depth HGB but only **10/50** under penalized logistic regression; all 10 logistic-authorized taxa were also HGB-authorized. Even among those jointly authorized taxa, only **16/60** process states were stably sharp across both learners. HGB alone produced **125/300** sharp states on the prespecified complete denominator, well below the 80% threshold. These descriptive diagnostics separate a learner-specific authorization bottleneck from disagreement over process states; they do **not** establish whether either originates in ecological nonidentifiability, model representation or sampling. The unchanged archived receipts are included in the anonymous evidence bundle for verification.

The known-truth validation therefore establishes error control **under its frozen generating conditions**, not transport of that performance to real environmental representations. The real-data failure is consistent with inadequate process identifiability or learner-dependent representation, but does not identify a unique biological cause and is not evidence that the ecological processes are absent. It is kept as a separately audited applicability boundary rather than incorporated as positive empirical evidence for the present method.

## 5. Conclusions

A useful process-identification method should be judged by more than how often it returns a process label. It must also demonstrate that it can refuse labels the available information does not support.

In a prospectively frozen known-truth test, the framework recovered 88.75% of positive process states while producing no favorable false attribution among 700 replaceable targets and no over-resolution among unresolved, structurally nonseparable or unavailable states.

The methodological contribution is therefore **evidence-bounded process identification: recover process information when it is identified, and preserve uncertainty when it is not.**

## References

Aarts, G., Fieberg, J. & Matthiopoulos, J. (2012). Comparative interpretation of count, presence–absence and point methods for species distribution models. *Methods in Ecology and Evolution*, 3, 177–187. https://doi.org/10.1111/j.2041-210X.2011.00141.x

Dormann, C.F., Elith, J., Bacher, S., Buchmann, C., Carl, G., Carré, G. et al. (2013). Collinearity: a review of methods to deal with it and a simulation study evaluating their performance. *Ecography*, 36, 27–46. https://doi.org/10.1111/j.1600-0587.2012.07348.x

Fisher, A., Rudin, C. & Dominici, F. (2019). All models are wrong, but many are useful: Learning a variable's importance by studying an entire class of prediction models simultaneously. *Journal of Machine Learning Research*, 20(177), 1–81. https://jmlr.org/papers/v20/18-760.html

Galipaud, M., Gillingham, M.A.F., David, M. & Dechaume-Moncharmont, F.-X. (2014). Ecologists overestimate the importance of predictor variables in model averaging: a plea for cautious interpretations. *Methods in Ecology and Evolution*, 5, 983–991. https://doi.org/10.1111/2041-210X.12251

Getz, W.M., Marshall, C.R., Carlson, C.J., Giuggioli, L., Ryan, S.J., Romañach, S.S. et al. (2018). Making ecological models adequate. *Ecology Letters*, 21, 153–166. https://doi.org/10.1111/ele.12893

Roberts, D.R., Bahn, V., Ciuti, S., Boyce, M.S., Elith, J., Guillera-Arroita, G. et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, 40, 913–929. https://doi.org/10.1111/ecog.02881

Strobl, C., Boulesteix, A.-L., Kneib, T., Augustin, T. & Zeileis, A. (2008). Conditional variable importance for random forests. *BMC Bioinformatics*, 9, 307. https://doi.org/10.1186/1471-2105-9-307

Zbinden, R., van Tiel, N., Sumbul, G., Vanalli, C., Kellenberger, B. & Tuia, D. (2026). MaskSDM with Shapley values to improve flexibility, robustness and explainability in species distribution modelling. *Methods in Ecology and Evolution*, 17, 188–206. https://doi.org/10.1111/2041-210X.70200

## Figure captions

**Figure 1. Declared process-information closures and abstention-aware state decisions.** Panel A is a schematic many-to-many registry: temperature and elevation proxy carry thermal information, and a shared PET representation is declared to carry both thermal and water information. Deleting a single thermal predictor leaves other thermal carriers in place; evaluating process replaceability requires excluding the whole declared thermal closure. Panel B shows the logical distinctions between unavailable, unresolved, replaceable, contributory and required process-information states. These are conditional statements about declared information and model adequacy, not causal physiological identification.

**Figure 2. Eight prospective known-truth world families and their frozen validation roles.** The schematic inventory summarizes the generating signals, environmental representations or observation structures, and prespecified roles in full-system authorization. Six worlds were informative controls; observation confounding was report-only and omitted driver was the null. This figure presents benchmark design, not development-seed or sealed-test outcomes.

**Figure 3. Prospective known-truth denominators and observed state outcomes.** Of 80 declared positive process targets, 71 were recovered and 9 remained unrecovered. No favorable false call occurred among 700 replaceable targets, no over-resolution among 60 unresolved targets, no sharp call among 120 unavailable targets, and no structural-refusal violation among 60 structural cases. Bars show mutually exclusive cells within each target-state denominator; they do not imply independent observations across worlds and seeds.

**Figure 4. Full-system authorization rates across known-truth worlds.** Each of the six prespecified informative control worlds authorized 20/20 prospective seeds. The omitted-driver null authorized 0/20; the observation-confounded world authorized 1/20 and was report-only for this gate. This figure is not a spatial-transfer panel: Stage-P/Stage-T separation and spatial contradiction checks are reported in the Results text.
