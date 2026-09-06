# Draft cover letter — Nature Ecology & Evolution

Dear Editors,

Please consider our Article, **“Predictive success does not identify ecological necessity in species distribution models,”** for publication in *Nature Ecology & Evolution*.

Species distribution modelling has long distinguished prediction from ecological explanation. Our study moves beyond that distinction by asking a concrete question: **can the generating environmental-process set be recovered when different defensible species-distribution models fit the same occurrence evidence?**

Using prospectively sealed occurrence evidence and unused controlled-truth cases, we find that it can. A consensus-first process certificate exactly recovered the complete hidden generating-process set in **55/60 cases (91.7%)**, compared with **50/60 (83.3%)** exact driver-process recovery for the AUC-selected fitted candidate. The two ecological selectors chose different fitted models in 22/60 cases, yet the stable process set still exactly matched hidden truth in **19/22 (86.4%)** of those model-disagreement cases. This is the paper’s principal positive result: ecological process information can remain recoverable when exact model identity is not.

The strongest mechanistic example occurs under observation confounding. The hidden ecological process set was `{temperature, water}` in all ten cases, while a separate recording-bias variable affected where records were observed. AUC selected an `observer_only` model in **5/10** cases, and those five models had driver-process precision, recall and F1 of **0.0**. Product A’s ecological selectors instead chose the ecological-plus-observation model in **10/10**, kept the observation variable out of the ecological process interpretation, and recovered `{temperature, water}` in **10/10**. Thus the method corrected a specific process-misattribution failure rather than merely demonstrating that prediction and explanation differ.

The result is not uniformly favorable, and we report that boundary explicitly. The stable process certificate recovered exact process truth in 7/10 omitted-driver cases whereas the AUC-selected role was exact in 10/10. More generally, only soil varied in process presence across the frozen generator suite: among ten true-soil cases, soil was stable in seven and contested in three; among fifty non-generating cases, soil was incorrectly stable in two, contested in seven and absent from both ecological selectors in forty-one. Temperature and water were invariant true processes, so the manuscript does not use their perfect retention to claim broad presence-versus-absence discrimination across many drivers.

A separate process-exclusion branch addresses necessity rather than stable process recovery. It eliminated false-required claims and retained all true processes, but its possible-process set remained broad and no process was positively required in the nine validation taxa. We therefore keep false-necessity control and positive process-set recovery as distinct achievements rather than combining them into one performance statistic.

Finally, we subjected the architecture to a prospectively frozen fresh empirical endpoint spanning 12 plant taxa, three spatial split seeds and three accessible-area assumptions. The preregistered test did **not** support strict ecological improvement over the AUC-selected comparator, and Product A was not promoted. We retain this result without rescue. Frozen artifacts show that ecological and AUC roles selected exactly the same candidate and predictor set in all **108/108** matched cells, so the empirical corpus supplied no realized selector contrast and no literal process-truth answer key.

We believe the study is broadly relevant because ecological interpretation frequently rests on selected models built from correlated environmental measurements, proxies and observation-biased records. The contribution is both methodological and empirical under controlled truth: it shows when process information can be recovered beyond model identity, demonstrates a concrete correction of observation-process misattribution, and exposes the cases in which the method remains conservative or wrong. The manuscript does not claim causal or fundamental-niche identification, universal superiority over AUC, or direct recovery of true processes in the fresh plant data.

All scientific endpoints, source artifacts and reporting transformations are frozen and auditable. The final unfavorable empirical endpoint was not rerun or retuned. Code, contracts and source-data tables are retained in the public repository, and the exact submission state will be archived with a permanent DOI before submission.

Thank you for considering our work.

Sincerely,

[Corresponding author]
