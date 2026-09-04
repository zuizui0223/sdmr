# Verified reference boundary — Nature Ecology & Evolution Product A

Status: **literature-positioning aid; not a scientific endpoint**.

The Nature manuscript must not claim novelty for distinctions already established in SDM or model-interpretation literature.

## Core precedents

1. Elith, J. & Leathwick, J. R. *Annu. Rev. Ecol. Evol. Syst.* **40**, 677–697 (2009). doi:10.1146/annurev.ecolsys.110308.120159.  
   Inherited: explanation and prediction are distinct SDM roles.

2. Warren, D. L., Matzke, N. J. & Iglesias, T. L. *J. Biogeogr.* **47**, 167–180 (2020). doi:10.1111/jbi.13705.  
   Inherited: discrimination accuracy may not recover functional environmental response accuracy under virtual-species truth.

3. Kass, J. M. et al. *Methods Ecol. Evol.* **12**, 1602–1608 (2021). doi:10.1111/2041-210X.13628.  
   Inherited: spatial partitioning, tuning and reproducible SDM evaluation.

4. Dormann, C. F. et al. *Ecography* **36**, 27–46 (2013). doi:10.1111/j.1600-0587.2012.07348.x.  
   Inherited: collinearity complicates ecological predictor inference.

5. Roberts, D. R. et al. *Ecography* **40**, 913–929 (2017). doi:10.1111/ecog.02881.  
   Inherited: structured ecological data require structured validation.

6. Phillips, S. J. et al. *Ecol. Appl.* **19**, 181–197 (2009). doi:10.1890/07-2153.1; Fithian, W. et al. *Methods Ecol. Evol.* **6**, 424–438 (2015). doi:10.1111/2041-210X.12242.  
   Inherited: presence-only records/backgrounds have observation-process structure and sampling bias can be modelled.

7. Harisena, N. V. et al. *Ecography* **44**, 778–788 (2021). doi:10.1111/ecog.05534; Gábor, L. et al. *Ecography* **2023**, e06358 (2023). doi:10.1111/ecog.06358.  
   Inherited: predictive performance and ecological interpretation/variable importance can respond differently to spatial structure or occurrence error.

8. Fisher, A., Rudin, C. & Dominici, F. *J. Mach. Learn. Res.* **20**, 1–81 (2019); Donnelly, J. et al. *PNAS* **120**, e2216830120 (2023).  
   Inherited: many similarly performing models can support different importance/explanation claims.

## Product-A novelty after these precedents

Do not claim novelty for prediction≠explanation, CV/tuning, collinearity, Rashomon sets, variable-importance instability or sampling-bias correction themselves.

The defensible new sequence is:

1. **Ecological-recovery filtering can itself create false necessity.** v2.3 prospectively shows that a sharper ecologically selected subset can lose truth coverage and manufacture a false necessary-process core.
2. **Necessity is made a falsification target.** Explicit process-information exclusion asks whether an adequate ecological explanation survives without the declared process information; missing evidence remains unresolved.
3. **The exclusion branch is safe but can remain broad.** v2.6 had false-required=0 and possible-process recall=1.0, with possible-process precision ≈0.467 and wider calibrated intervals.
4. **Process stability is a separate estimand.** v2.7.2 `stable_process_core` is the intersection of process sets supported by canonical and perturbation-robust ecological selectors, not the exclusion-based necessary-process set. Under 60 unused known-truth cases it had P=0.9889 and R/F1=0.9833; process-set consensus was 50/60 versus exact-model consensus 38/60.
5. **Fresh data expose observational equivalence.** Ecological and AUC selection instantiated the same candidate and predictor set in 108/108 matched cells; formal empirical strict advantage remained not supported.
6. **Prospective state semantics matter.** Scientific non-support, unavailable evidence, technical failure and non-promotion are kept distinct without outcome-driven rescue.

## Introduction positioning

> Previous work established that predictive discrimination, functional response recovery and variable-importance inference need not coincide. We ask the stronger identification questions that remain: when is a process-information necessity claim falsified by adequate alternatives, and when is process information stable across defensible ecological selectors even if exact models differ?

## Discussion positioning

> Product A adds neither another prediction metric nor a generic Rashomon summary. It shows prospectively that ecological-recovery filtering can create false necessity, introduces exclusion-based necessity with protected unresolved states, and independently demonstrates that process information can be more stable than exact model identity under controlled truth.

## Non-negotiable wording boundary

Never attribute v2.7.2 P=0.9889/R=0.9833 to the exclusion-based necessity estimator. Those values quantify the consensus-first stable process core.