# Draft cover letter — Nature Ecology & Evolution

Dear Editors,

Please consider our Article, **“Counterfactual niche recovery identifies environmental processes beyond model selection,”** for publication in *Nature Ecology & Evolution*.

Species distribution modelling has long distinguished prediction from ecological explanation. Our study addresses the next operational problem: **when correlated environmental representations support multiple adequate SDMs, can we identify which environmental processes actually generate the niche rather than simply interpret the winning model?**

We develop a process-specific counterfactual estimator. For each declared environmental process, we first retain only models that satisfy a prospective prediction-adequacy gate. We then compare the best held-out environmental-niche overlap attainable by models carrying that process with the best overlap attainable when **every declared representation of the process is excluded**, repeating the comparison across frozen sampling and background perturbations. The resulting counterfactual recovery loss contains no hidden process truth and does not require a unique winning model.

We deliberately subjected the preceding Product-A estimator to a stronger factorial falsification before promoting this method. Temperature, water and soil were independently varied across all seven non-empty process combinations. The predecessor stable-process intersection recovered only **22/35 (62.9%)** complete process sets, versus **25/35 (71.4%)** for the AUC-selected winner. We retained this non-support and used these discovery cases only to freeze one counterfactual threshold per process before opening new truth.

On unused seeds `4301`–`4305`, the frozen counterfactual estimator passed every preregistered gate, recovering **30/35 (85.7%)** complete process sets. We then made no method or threshold changes and prospectively froze a second independent replication on seeds `4401`–`4410` (`n=70`). The unchanged estimator recovered **65/70 (92.9%)** complete generating-process sets, compared with **56/70 (80.0%)** for AUC-selected winners and **49/70 (70.0%)** for the predecessor stable-core rule. Temperature sensitivity/specificity were **1.000/0.933**, water **1.000/0.933**, and soil **0.975/1.000**. Canonical and perturbation-robust ecological selectors chose different fitted models in 30/70 cases, yet counterfactual process membership remained exactly correct in **27/30 (90.0%)**. Paired with AUC, 51 cases were exact under both procedures, 14 only under the counterfactual estimator, 5 only under AUC and none under neither.

The mechanism is interpretable. Process evidence is not “this variable was selected”; it is the ecological recovery that becomes unattainable once the complete declared representation of that process is forbidden. In the independent replication, every one of the seven temperature–water–soil process combinations was represented ten times; exact recovery was 8/10 for temperature alone, 8/10 for water alone, 10/10 for soil alone and for all three two-process combinations, and 9/10 when all three processes generated the niche. The five errors were localized to four extra cross-process calls in single-process niches and one missed soil process in the three-process niche.

A complementary controlled-truth result shows why this distinction matters for occurrence data. Under explicit observation confounding, AUC selected an observation-only model in 5/10 cases and recovered no ecological driver there, whereas Product A separated observation from ecological information and recovered the true temperature–water process set in 10/10.

We keep stronger claims separate. An exclusion-based necessity certificate controlled false-required claims but remained broad and did not positively identify a required process in its nine validation taxa. The new counterfactual estimator identifies **process membership under a declared representation registry**; it is not a claim of physiological causation or fundamental-niche necessity.

Finally, the prospectively frozen fresh plant endpoint remains unfavorable and unchanged. Across 12 taxa, three spatial split seeds and three accessible-area assumptions, strict ecological improvement over the AUC role occurred in 0/3 primary parts and Product A was not promoted. Full-denominator audit showed identical ecological and AUC-selected models in **108/108** matched cells, and empirical occurrence data provide no literal generating-process answer key. We therefore present the controlled-truth identification result and its empirical boundary without rescue.

We believe this advances ecological inference beyond the familiar warning that prediction and explanation differ. It provides a reproducible, falsifiable estimator of environmental-process membership, demonstrates prospective failure of a weaker estimator, and then validates and independently replicates the successor under complete process ON/OFF truth.

All contracts, thresholds, seeds, candidate libraries, scientific decisions and immutable workflow artifacts are retained in the public repository. The exact submission state and source-data tables will be archived with a permanent DOI before submission.

Thank you for considering our work.

Sincerely,

[Corresponding author]
