# Product-A novelty literature audit

Status: **manuscript-positioning audit / literature checked 2026-09-03 / no scientific endpoint change**.

Purpose: identify which parts of the Product-A argument are already established in adjacent SDM, model-uncertainty and statistical-identification literature, and isolate the defensible novelty of the current paper.

## What is not new by itself

### Explanation and prediction are different aims in SDMs

Elith & Leathwick (2009) already distinguished ecological explanation and prediction in species distribution modelling and emphasized predictor relevance, model selection/evaluation, extrapolation and model uncertainty as core challenges.

**Implication for SDMR:** do not claim to discover for the first time that prediction and explanation differ. The new claim must concern an operational identification framework and the prospective evidence showing why its components are required.

### Standard SDM tuning and reproducible model evaluation are established

ENMeval 2.0 (Kass et al. 2021) makes quantitative model tuning, data partitioning, custom performance metrics, metadata and reproducible model evaluation accessible and explicitly discusses shortcomings in reporting and tuning practice.

**Implication for SDMR:** information barriers, tuning and reproducibility alone are not enough for novelty. SDMR must distinguish evaluation of model performance from identification of defensible environmental-process claims.

### Variable importance can fail to recover true environmental influence

Smith & Santos (2020) used simulations with known truth to test whether SDMs can infer variable importance and showed that reliability deteriorates under several data conditions, including strong predictor correlation. Harisena et al. (2021) further showed that spatial autocorrelation and response form can bias variable-importance estimates.

**Implication for SDMR:** do not claim first evidence that SDM variable importance can be wrong. SDMR goes beyond ranking/importance bias by asking whether a process can be called necessary after alternative adequate explanations are allowed.

### Ecological relevance/proximal-versus-distal predictor choice is established

Existing SDM variable-selection work already argues that biological relevance, representation choice and proximal/distal predictor meaning matter, and that variable selection can be constrained by the available data.

**Implication for SDMR:** the Chapter-1 predictor-role hierarchy is important but not a stand-alone novelty claim.

### Sets of equally good models / Rashomon effects are established in statistics and machine learning

Model class reliance and Rashomon-set work explicitly recognizes that many well-performing models may give different variable-importance conclusions and proposes ranges or distributions across sets of good models.

**Implication for SDMR:** `retain a set of good models rather than one winner` is not sufficient novelty. In fact, Product-A v2.3 supplies an important ecological counterpoint: even a sharpened retained set can be anti-conservative if set intersection is converted directly into biological necessity.

### Partial identification is an established statistical idea

Other fields have used partial identification to avoid collapsing structurally uncertain model ensembles to a point estimate when the data do not uniquely determine the target.

**Implication for SDMR:** do not claim invention of partial identification. Use it as conceptual context for why unresolved/set-valued ecological outputs are scientifically legitimate.

## Defensible novelty after the audit

The strongest novelty is the **ecology-specific identification synthesis and its prospective falsification sequence**:

1. **Target redefinition:** the inferential target is not variable importance in one model or the identity of one best model; it is the status of environmental-process claims (necessary, substitutable/possible, contested, unresolved) under occurrence-only evidence.
2. **Necessity by falsification rather than agreement:** a process is not necessary because all retained good models contain it. Product A directly demonstrated that ecological Pareto sharpening can create false necessity, then replaced intersection logic with prospective process-exclusion tests.
3. **Protected answer-check architecture:** process claims are constructed behind model-pool/sealed spatial barriers and unseen-taxon barriers, while M/background is a sensitivity condition rather than an optimized outcome.
4. **Explicit evidence-state semantics:** `not_supported`, `unavailable/unresolved` and `technical failure` are different states and are prospectively kept separate. Missing calibration/support is not converted into ecological absence.
5. **Observation-target correction:** Product A treats observation bias as affecting not only model predictions but potentially the held-out occurrence-environment target used for ecological checking.
6. **Scientific execution identity:** deterministic computation is treated as part of the estimator when process-dependent numerical drift can change the selected predictor set.
7. **Positive controlled-truth performance:** the final known-truth successor recovered stable process cores with precision 0.9889 and recall 0.9833 across 60 unused cases while exactly reproducing compared outputs across independent processes.
8. **Unrescued empirical boundary:** the same research programme retained a complete fresh empirical non-support endpoint (strict ecological improvement 0/3; mean presence-rank delta vs AUC 0.0) rather than tuning until a favorable result emerged.

## Closest conceptual competitors and how to distinguish them

| Literature family | Shared idea | Product-A distinction to emphasize |
|---|---|---|
| SDM model tuning / ENMeval | spatial partitioning, metrics, complexity tuning, reproducibility | SDMR targets process-claim identification rather than best predictive configuration |
| SDM variable-importance simulation | known truth can reveal wrong variable importance | SDMR formalizes necessity/substitutability as certificate states and tests necessity through exclusion |
| ecologically informed predictor selection | biological meaning matters | SDMR does not rely on expert meaning alone; it tests which declared process information is indispensable under a frozen evidence design |
| ensemble/model uncertainty | retain multiple models and report variability | v2.3 shows retained-model agreement/spread can itself be anti-conservative for process necessity/boundary claims |
| Rashomon/model-class reliance | many good models imply explanation multiplicity | SDMR is process-level, occurrence-only, spatially sealed and falsification-first; importance ranges across good models are not treated as necessity certificates |
| partial identification | do not force point identification when data are insufficient | SDMR operationalizes unresolved ecological process states with prospectively calibrated abstention and known-truth validation |
| causal SDM interpretation | prediction does not equal causal mechanism | SDMR does not claim causal identification; it deliberately limits the estimand to defensible environmental-process information under the declared representation system |

## Novelty sentence for the manuscript

Approved working formulation:

> **Previous SDM research has shown that prediction, variable importance and ecological explanation can diverge, and statistical work has shown that many well-performing models can support different explanations. Product A contributes a prospectively falsified ecological-identification framework that asks a different question: which environmental-process claims remain indispensable after adequate alternative explanations are retained, excluded processes are challenged directly, unresolved evidence is allowed to remain unresolved, and the entire claim is protected from sealed spatial and taxon-level answer checks.**

## What would make the Ecology Letters case substantially stronger

Without changing Product-A evidence, the manuscript should show conceptually that this framework applies beyond a particular SDM algorithm or plant panel. The strongest route is not another favorable data set but a clearer general theorem-like argument in words/figures:

- any observational ecological model with substitutable environmental representations can have good predictive fit without unique process identification;
- intersection across selected good models is conditional on the selection rule and therefore cannot establish necessity unless alternatives have been exhaustively or prospectively challenged;
- a falsification-first set-valued output is the appropriate scientific object when ecological process truth is partially identified.

A future independent successor could then test full proxy-closure exclusion and external ecological truth, but those results must not be backfilled into the current Product-A paper.

## References to position explicitly

- Elith, J. & Leathwick, J.R. (2009). Species Distribution Models: Ecological Explanation and Prediction Across Space and Time. Annual Review of Ecology, Evolution, and Systematics 40:677–697.
- Smith, A.B. & Santos, M.J. (2020). Testing the ability of species distribution models to infer variable importance. Ecography 43:1801–1813.
- Harisena, N.V., Groen, T.A., Toxopeus, A.G. & Naimi, B. (2021). When is variable importance estimation in species distribution modelling affected by spatial correlation? Ecography 44:778–788.
- Kass, J.M. et al. (2021). ENMeval 2.0: Redesigned for customizable and reproducible modeling of species’ niches and distributions. Methods in Ecology and Evolution.
- Fisher, A., Rudin, C. & Dominici, F. (model class reliance work; use final bibliographic form in manuscript reference audit).
- Donnelly, J. et al. (Rashomon importance distribution; use final bibliographic form in manuscript reference audit).
- Partial-identification/model-ensemble literature should be cited as conceptual context, not as ecological evidence.
