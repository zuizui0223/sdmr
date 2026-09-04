# Verified reference boundary — Nature Ecology & Evolution Product A

Status: **literature-positioning aid; not a scientific endpoint**.

The Nature manuscript must not claim novelty for distinctions already established in the SDM or model-interpretation literature. The paper's contribution begins where these precedents stop.

## Core precedents to cite in the main text

1. Elith, J. & Leathwick, J. R. Species distribution models: ecological explanation and prediction across space and time. *Annu. Rev. Ecol. Evol. Syst.* **40**, 677–697 (2009). doi:10.1146/annurev.ecolsys.110308.120159.

   **Inherited point:** explanation and prediction are different roles of SDMs; predictor/model choices and uncertainty matter for ecological interpretation.

2. Warren, D. L., Matzke, N. J. & Iglesias, T. L. Evaluating presence-only species distribution models with discrimination accuracy is uninformative for many applications. *J. Biogeogr.* **47**, 167–180 (2020). doi:10.1111/jbi.13705.

   **Inherited point:** discrimination accuracy can be weakly related or actively misleading for functional accuracy under virtual-species truth. This is the strongest direct prior art to the statement `prediction ≠ ecological response recovery`.

3. Kass, J. M. et al. ENMeval 2.0: redesigned for customizable and reproducible modeling of species’ niches and distributions. *Methods Ecol. Evol.* **12**, 1602–1608 (2021). doi:10.1111/2041-210X.13628.

   **Inherited point:** spatial partitioning, tuning, multiple performance metrics, metadata and reproducible SDM evaluation are established methodology.

4. Dormann, C. F. et al. Collinearity: a review of methods to deal with it and a simulation study evaluating their performance. *Ecography* **36**, 27–46 (2013). doi:10.1111/j.1600-0587.2012.07348.x.

   **Inherited point:** correlated ecological predictors can destabilize parameter inference and identification of relevant predictors; collinearity is not solved by naïve model selection.

5. Roberts, D. R. et al. Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography* **40**, 913–929 (2017). doi:10.1111/ecog.02881.

   **Inherited point:** structured ecological data require structured validation; naïve CV can underestimate error and overfit non-causal predictors.

6. Phillips, S. J. et al. Sample selection bias and presence-only distribution models: implications for background and pseudo-absence data. *Ecol. Appl.* **19**, 181–197 (2009). doi:10.1890/07-2153.1.

   **Inherited point:** presence-only records and background sampling are observation processes; target-group-style background is an established response to sampling bias.

7. Fithian, W. et al. Bias correction in species distribution models: pooling survey and collection data for multiple species. *Methods Ecol. Evol.* **6**, 424–438 (2015). doi:10.1111/2041-210X.12242.

   **Inherited point:** presence-only sampling bias can be modelled explicitly and shared across species; target-group background has known strengths and limitations.

8. Harisena, N. V., Groen, T. A., Toxopeus, A. G. & Naimi, B. When is variable importance estimation in species distribution modelling affected by spatial correlation? *Ecography* **44**, 778–788 (2021). doi:10.1111/ecog.05534.

   **Inherited point:** spatial autocorrelation and response form can bias variable-importance inference even with controlled truth.

9. Gábor, L. et al. Species distribution models affected by positional uncertainty in species occurrences can still be ecologically interpretable. *Ecography* **2023**, e06358 (2023). doi:10.1111/ecog.06358.

   **Inherited point:** predictive performance and ecological interpretability can respond differently to occurrence error; good/bad prediction does not map one-to-one to inferential quality.

## General model-class / Rashomon precedents

10. Fisher, A., Rudin, C. & Dominici, F. All models are wrong, but many are useful: learning a variable's importance by studying an entire class of prediction models simultaneously. *J. Mach. Learn. Res.* **20**, 1–81 (2019).

11. Donnelly, J. et al. The Rashomon importance distribution: getting RID of unstable, single model-based variable importance. *Proc. Natl Acad. Sci. USA* **120**, e2216830120 (2023).

   **Inherited point:** variable importance should be considered across many well-performing models rather than from a single selected model.

## Product-A novelty that remains after these precedents

Do **not** claim novelty for:

- prediction versus explanation as a conceptual distinction;
- spatial holdout or cross-validation;
- SDM hyperparameter tuning;
- the fact that AUC/discrimination may fail to track ecological response recovery;
- collinearity causing unstable variable importance;
- retaining a set/Rashomon class of good models;
- sampling-bias correction in presence-only data.

The manuscript's strongest defensible novelty is the following sequence:

1. **Ecological-recovery selection is itself insufficient for necessity.** Product A prospectively shows that pruning to models with better ecological recovery can narrow uncertainty yet create a false necessary-process core. This goes beyond showing that predictive discrimination is the wrong objective.

2. **Process-information necessity is turned into a falsification target.** A process is not necessary because it is important or shared across good models; necessity is challenged by removing declared process information and asking whether an adequate ecological certificate survives.

3. **Unresolved/unavailable is a protected inferential state.** Missing calibration or structural support is not converted to absence or scientific non-support.

4. **The process-level target is evaluated under hidden generating truth.** After prospective calibration and deterministic execution, the stable process core reaches precision 0.9889 and recall 0.9833 across six declared niche families.

5. **Model identity and process identity are empirically separated under the same known truth.** Exact-model consensus is 38/60 while process-set consensus is 50/60.

6. **The fresh empirical endpoint supplies a distinct observational-equivalence result.** Different ecological and AUC selection objectives collapse to the same selected candidate in 108/108 matched cells; this is not evidence for AUC as ecological truth, but evidence that observational data may fail to instantiate the contrast required for a winner comparison.

7. **Prospective governance is part of the scientific argument.** Non-support, unavailable states, technical failure and non-promotion are kept distinct, and the final unfavorable empirical endpoint is retained without retuning.

## One-sentence positioning for the Introduction

> Previous work has shown that predictive discrimination can fail to recover ecological response functions and that variable importance may vary across correlated or equally predictive models; we ask the stronger identification question of when an environmental process can be defended as necessary, and test necessity by prospective falsification against adequate alternatives rather than by the identity or agreement of selected models.

## One-sentence positioning for the Discussion

> Product A does not replace established SDM evaluation or Rashomon-style uncertainty summaries; it adds a process-level falsification criterion showing that even ecologically well-recovered model subsets can create false necessity unless adequate alternative explanations are explicitly allowed to survive.