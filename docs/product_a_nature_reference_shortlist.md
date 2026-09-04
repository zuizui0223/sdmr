# Product A — verified Nature-track reference shortlist

Status: **submission-production literature aid; no change to Product-A scientific endpoints**.

The Nature manuscript must not claim that the distinction between predictive accuracy and ecological interpretation is itself new. The novelty begins one step later: Product A prospectively shows that even sharpening to ecologically better recovered models can create false process necessity, and replaces agreement-based necessity with falsification against adequate alternatives.

## Core inherited literature

1. **Elith, J. & Leathwick, J. R. (2009).** Species Distribution Models: Ecological Explanation and Prediction Across Space and Time. *Annual Review of Ecology, Evolution, and Systematics* **40**, 677–697. DOI: `10.1146/annurev.ecolsys.110308.120159`.
   - Use: establishes the long-standing dual role of SDMs in prediction and ecological explanation and the need to connect model practice to ecological theory.

2. **Warren, D. L., Matzke, N. J. & Iglesias, T. L. (2020).** Evaluating presence-only species distribution models with discrimination accuracy is uninformative for many applications. *Journal of Biogeography* **47**, 167–180. DOI: `10.1111/jbi.13705`.
   - Use: directly precedes Product A in showing with simulation that discrimination accuracy can be weakly related to functional accuracy. Do not present `prediction ≠ functional recovery` as a Product-A novelty.

3. **Smith, A. B. & Santos, M. J. (2020).** Testing the ability of species distribution models to infer variable importance. *Ecography* **43**, 1801–1813. DOI: `10.1111/ecog.05317`.
   - Use: establishes that high predictive accuracy does not guarantee robust inference of variable importance under known truth. Product A must distinguish process-level falsification from standard importance estimation.

4. **Dormann, C. F. et al. (2013).** Collinearity: a review of methods to deal with it and a simulation study evaluating their performance. *Ecography* **36**, 27–46. DOI: `10.1111/j.1600-0587.2012.07348.x`.
   - Use: establishes the long-recognized effect of correlated predictors and why variable selection among substitutable environmental representations is difficult.

5. **Kass, J. M. et al. (2021).** ENMeval 2.0: Redesigned for customizable and reproducible modeling of species' niches and distributions. *Methods in Ecology and Evolution*. DOI: `10.1111/2041-210X.13628`.
   - Use: establishes modern reproducible tuning, partitioning, and evaluation practice. Product A is not novel merely because it performs spatial CV, tuning, or multiple evaluation metrics.

6. **Fisher, A., Rudin, C. & Dominici, F. (2019).** All Models are Wrong, but Many are Useful: Learning a Variable's Importance by Studying an Entire Class of Prediction Models Simultaneously. *Journal of Machine Learning Research* **20**(177), 1–81.
   - Use: establishes the general idea of studying a set/Rashomon class of well-performing models rather than only one winner. Product A's set-valued output should therefore be framed around the falsification semantics and known-truth anti-conservative counterexample, not the existence of model sets alone.

## Product-A novelty boundary after this literature

The manuscript should claim the following sequence, not any inherited ingredient alone:

1. protected known-truth evidence shows that a prediction/functional-recovery target is still insufficient for **process necessity**;
2. ecological Pareto sharpening provides a prospective counterexample where a narrower, apparently better model set creates a **false necessary-process core**;
3. necessity is therefore redefined operationally as a falsification problem: whether adequate ecological explanations remain when declared process information is excluded;
4. insufficient evidence remains `unresolved/unavailable` instead of being converted into absence;
5. under unused known truth this falsification-first set-valued estimator becomes both safe and sharp (P `0.9889`, R `0.9833`) and more stable at the process level than at the exact-model level (`50/60` vs `38/60` consensus);
6. a fresh full-denominator empirical endpoint shows an orthogonal identification limit: distinct selection objectives can collapse to the same candidate (`108/108`), so a winner comparison may contain no realized ecological contrast at all.

## Wording boundary

Safe Nature-level formulation:

> Earlier work established that predictive discrimination, fitted functional accuracy and variable-importance inference need not coincide. Product A addresses the stronger identification problem that remains after those distinctions: when multiple adequate representations survive, which process-necessity claims can be defended against alternatives rather than inferred from a winner or from agreement within a selected model subset?

Do not write that Product A first discovered the prediction/explanation distinction, collinearity, model uncertainty, Rashomon sets, spatial cross-validation, or variable-importance instability.
