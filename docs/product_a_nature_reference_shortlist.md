# Product A — verified Nature-track reference shortlist

Status: **submission-production literature aid; no change to Product-A scientific endpoints**.

The Nature manuscript must not claim that the distinction between predictive accuracy and ecological interpretation is itself new. The novelty begins one step later: Product A prospectively shows that even sharpening to ecologically better recovered models can create false process necessity, operationalizes necessity by process-information exclusion, and separately evaluates whether process information is stable across ecological selectors.

## Core inherited literature

1. **Elith, J. & Leathwick, J. R. (2009).** Species Distribution Models: Ecological Explanation and Prediction Across Space and Time. *Annual Review of Ecology, Evolution, and Systematics* **40**, 677–697. DOI: `10.1146/annurev.ecolsys.110308.120159`.
   - Inherited: prediction and ecological explanation are distinct SDM roles.

2. **Warren, D. L., Matzke, N. J. & Iglesias, T. L. (2020).** Evaluating presence-only species distribution models with discrimination accuracy is uninformative for many applications. *Journal of Biogeography* **47**, 167–180. DOI: `10.1111/jbi.13705`.
   - Inherited: discrimination accuracy can be weakly related to functional response accuracy under virtual-species truth.

3. **Smith, A. B. & Santos, M. J. (2020).** Testing the ability of species distribution models to infer variable importance. *Ecography* **43**, 1801–1813. DOI: `10.1111/ecog.05317`.
   - Inherited: predictive performance does not guarantee robust inference of variable importance under known truth.

4. **Dormann, C. F. et al. (2013).** Collinearity: a review of methods to deal with it and a simulation study evaluating their performance. *Ecography* **36**, 27–46. DOI: `10.1111/j.1600-0587.2012.07348.x`.
   - Inherited: correlated predictors complicate ecological interpretation and variable selection.

5. **Kass, J. M. et al. (2021).** ENMeval 2.0: Redesigned for customizable and reproducible modeling of species' niches and distributions. *Methods in Ecology and Evolution*. DOI: `10.1111/2041-210X.13628`.
   - Inherited: spatial partitioning, tuning and reproducible evaluation are established methodology.

6. **Fisher, A., Rudin, C. & Dominici, F. (2019).** All Models are Wrong, but Many are Useful: Learning a Variable's Importance by Studying an Entire Class of Prediction Models Simultaneously. *Journal of Machine Learning Research* **20**(177), 1–81.
   - Inherited: sets/classes of similarly performing models can be more informative than one winner.

## Product-A novelty boundary after this literature

The manuscript should claim the following sequence, not any inherited ingredient alone:

1. prediction/functional-recovery success remains insufficient for **process necessity**;
2. ecological Pareto sharpening provides a prospective counterexample in which a narrower, apparently better model set creates a **false necessary-process core**;
3. **necessity branch:** process necessity is therefore made a falsification problem—whether adequate ecological explanations survive when declared process information is excluded;
4. insufficient evidence remains `unresolved/unavailable` rather than being converted into absence; with adequate calibration, v2.6 had zero false-required processes and possible-process recall 1.0, but the safe possible-process set remained broad (precision ≈0.467);
5. **stability branch:** a different consensus-first certificate asks whether canonical and perturbation-robust ecological selectors support the same process information. Its stable process core—not the exclusion necessity set—had P `0.9889`, R `0.9833`, with process-set consensus `50/60` versus exact-model consensus `38/60` under unused known truth;
6. a fresh full-denominator empirical endpoint shows an orthogonal identification limit: distinct selection objectives can collapse to the same candidate (`108/108`), so a winner comparison may contain no realized ecological contrast.

## Wording boundary

Safe Nature-level formulation:

> Earlier work established that predictive discrimination, fitted functional accuracy and variable-importance inference need not coincide. Product A addresses the stronger identification problem that remains after those distinctions: when multiple adequate representations survive, which process-necessity claims can be falsified by excluding their declared information, and which process information remains stable across defensible ecological selectors even when exact models differ?

Do not write that Product A first discovered prediction/explanation differences, collinearity, model uncertainty, Rashomon sets, spatial cross-validation or variable-importance instability. Do not write that the v2.7.2 P/R values measure the exclusion-based necessity estimator.