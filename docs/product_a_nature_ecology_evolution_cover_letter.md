# Draft cover letter — Nature Ecology & Evolution

Dear Editors,

Please consider our Article, **“Counterfactual niche recovery identifies environmental processes beyond model selection,”** for publication in *Nature Ecology & Evolution*.

Species distribution modelling has long distinguished prediction from ecological explanation. We address the next operational question: when correlated environmental representations support multiple adequate SDMs, can environmental-process membership be tested directly rather than inferred from the identity of a winning model?

We developed a process-specific counterfactual estimator. Among models that pass a prospective prediction-adequacy gate, it asks how much best attainable held-out ecological niche recovery is lost when **every declared representation of one process is excluded**, repeated across frozen sampling/background perturbations. The score contains no hidden process truth and does not require a unique winning fitted model.

We first allowed the preceding Product-A estimator to fail. Temperature, water and soil were varied independently across all seven non-empty process combinations. The predecessor stable-process intersection recovered only **22/35 (62.9%)** complete process sets, versus **25/35 (71.4%)** for the AUC-selected winner. We retained that non-support and used those discovery cases only to freeze one counterfactual threshold per process before opening new truth.

On unused seeds `4301`–`4305`, the frozen counterfactual estimator recovered **30/35 (85.7%)** complete process sets and passed every preregistered process gate. Without changing method or thresholds, an independently frozen replication on seeds `4401`–`4410` (`n=70`) recovered **65/70 (92.9%)**, versus **56/70 (80.0%)** for AUC-selected winners and **49/70 (70.0%)** for the predecessor. Temperature sensitivity/specificity were **1.000/0.933**, water **1.000/0.933**, and soil **0.975/1.000**. Ecological fitted models disagreed in 30/70 cases, yet process membership remained exactly correct in **27/30 (90.0%)**.

The mechanism is interpretable: process evidence is not “this variable was selected,” but the ecological recovery that becomes unattainable when the complete declared information channel for that process is forbidden. A separate exclusion-based necessity certificate remained deliberately broader and asserted no required process in its nine validation taxa, so process membership is not conflated with physiological or causal necessity.

We also subjected the framework to prospectively frozen real-data tests, and these **did not validate general empirical process identification**. The earlier v2.8.4 plant endpoint produced the same ecological and AUC candidate/predictor set in **108/108** matched cells and remained `empirical_confirmation_not_supported` / `not_promoted`. We then tested eight independent literature-backed positive controls in two frozen four-taxon lanes. Plants recovered **2/4** controls and nonplants **1/4**; temperature was recovered in 3/4 controls but water in **0/4**, so both lanes failed their original >=3/4 plus process-group gates.

This empirical non-support is not hidden or post hoc rescued. All **24/24** taxon × accessible-area pipelines completed technically, but only **21/24** contained a prediction-adequate candidate and only **17/24** expected-process cells had two-sided adequate comparisons. The labels are positive-only and therefore cannot estimate specificity, and the implemented process scores used model-pool inner spatial cross-validation rather than an invoked outer-sealed transfer evaluation. We accordingly claim controlled-truth process-membership identification and an empirical identification boundary—not direct proof of generating processes in GBIF data.

We believe the combination is ecologically useful precisely because the positive and negative results constrain each other. The study provides a falsifiable process-level estimand, demonstrates prospective failure of a weaker estimator, validates and independently replicates the successor under complete process ON/OFF truth, and then shows where the present occurrence-data implementation fails to earn the same claim in real systems.

All contracts, thresholds, seeds, candidate libraries, scientific decisions, result audits and immutable workflow artifacts are retained in the public repository. The exact submission state and source-data tables will be archived with a permanent DOI before submission.

Thank you for considering our work.

Sincerely,

[Corresponding author]
