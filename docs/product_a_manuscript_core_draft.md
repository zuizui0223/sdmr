# From model selection to ecological identification in occurrence-only species distribution models

Status: **core manuscript draft / scientific endpoint unchanged**.

This draft reorganizes only evidence that is already frozen in the repository. It does not authorize additional Product-A experiments, reinterpret the consumed v2.8.4 endpoint, or unblock Product B.

## Abstract

Species distribution models (SDMs) are commonly tuned by choosing the model or predictor set that optimizes discrimination, calibration, omission, parsimony, or transfer performance. These criteria are useful for model evaluation, but ecological interpretation asks a stronger question: which environmental information is actually defensible as part of a species' realized environmental niche? We developed Product A of SDMR as a prospectively sealed occurrence-only framework for this identification problem. Whole spatial blocks were assigned to model-pool or sealed answer-check roles before fitting, accessible-area/background assumptions were treated as sensitivity conditions rather than score-optimized candidates, and unseen taxa were withheld from procedure selection. We then used known-truth simulations to prospectively falsify increasingly strong ecological interpretations. Prediction transfer and stable response surfaces did not guarantee recovery of the generating environmental process. Sharpening an adequate model set by ecological Pareto filtering produced narrower certificates but could lose truth coverage and create false necessary-process claims. Replacing winner-based inference with falsification-first process exclusion and explicit abstention protected generating processes: with adequate calibration, all known-truth validation certificates were complete, false-required processes were zero, and possible-process recall was 1.0, although the resulting admissible sets were initially broad. A deterministic successor subsequently evaluated 60 unused known-truth cases from six niche families in two independent processes and exactly reproduced all compared outputs; stable-process-core precision was 0.9889 and recall/F1 were 0.9833. Observation-process correction activated in all confounded cases and in none of the other simulated niche families. Finally, a prospectively frozen fresh empirical endpoint completed the full 12-taxon × 3-seed × 3-accessible-area denominator. Prediction adequacy and process-status reproducibility passed, but strict ecological improvement over the AUC-selected role occurred in 0/3 preregistered parts and the mean sealed presence-rank delta was 0.0. Product A was therefore not promoted. These results support an identification framework rather than a universally superior empirical selector: ecological SDM tuning should distinguish prediction adequacy, process necessity, substitutable alternatives, unresolved evidence, observation bias, and computational reproducibility instead of forcing all uncertainty into one winning predictor set.

## Introduction

Species distribution modelling often turns a biologically difficult problem into a tractable selection problem. Candidate predictors, feature structures, regularization levels, background definitions and model families are compared, an evaluation criterion is optimized, and the resulting model is interpreted as the best representation of the species–environment relationship. AUC and presence-background rank statistics, Boyce/CBI, omission rates such as OR10, information criteria such as AICc, and spatial cross-validation all provide useful information about fitted models. They do not, however, answer exactly the same question as ecological niche interpretation.

The distinction becomes important when multiple environmental representations are observationally substitutable. Correlated climatic variables, derived exposure metrics, topographic proxies and composite summaries can generate similar fitted predictions while implying different ecological interpretations. A model may therefore predict unused occurrences well without uniquely identifying which environmental information constrains the realized niche. Conversely, an ecologically appropriate response surface can perform poorly as a record-discrimination model when the observation or accessible-area distribution changes. Treating these outcomes as a single scalar optimization problem risks conflating model adequacy with ecological identification.

A second difficulty is that occurrence-only evidence contains two interacting processes. The first is the ecological process that structures where a species can occur. The second is the observation process that structures which occurrences enter the record. Correcting only the prediction surface for sampling or detectability covariates is not necessarily sufficient because the withheld occurrence environments used as an answer-check target may themselves be observation-biased. The target of validation therefore also requires an explicit information model.

A third difficulty is inferential rather than predictive. If several adequate fitted models support the same environmental process, their agreement may appear to strengthen a necessity claim. Yet agreement within a selected model subset is not proof that alternatives outside that subset are incompatible with the data. Likewise, the spread among retained fitted models is not automatically a complete uncertainty interval. Ecological necessity is a falsification problem: the relevant question is not simply whether a process appears in the best models, but whether an adequate ecological explanation remains available when the declared information carried by that process is unavailable.

We developed SDMR Product A to investigate these problems prospectively rather than by post-outcome reinterpretation. The project began with a conventional aim—identify one reproducible full model-building procedure that transfers to sealed spatial blocks and unseen taxa—but retained strict information barriers and predeclared promotion criteria from the outset. We then used known-truth generators to test whether increasingly ecological selection rules actually recovered generating processes and response boundaries. Each failed interpretation was retained as evidence and used to motivate a narrower prospective successor rather than being repaired after outcome inspection.

This sequence led to five questions. First, does successful prediction transfer or response-surface stability imply correct ecological-process recovery? Second, can agreement among a sharpened set of ecologically good models be interpreted as biological necessity? Third, can falsification-first process exclusion preserve generating processes while allowing unresolved outcomes when calibration is incomplete? Fourth, can a conservative set-valued procedure become both sharp and exactly reproducible? Fifth, does the resulting ecological procedure show independent advantage over a conventional AUC-selected role in fresh empirical plant occurrence data? We report the answers as a methodological falsification sequence rather than as a contest among software versions.

## Methods

### Prospective information barrier

Product A separates occurrence evidence before any tuning decision. Within each admitted taxon, deterministically thinned occurrence records are assigned by whole spatial blocks to a model pool or a sealed answer-check pool. Sealed blocks cannot influence predictor or universe selection, regularization, response complexity, stopping rules, accessible-area/background construction, or procedure choice. A second taxon-level barrier separates discovery taxa, which may select a procedure, from unseen validation taxa, which evaluate only a frozen procedure.

Accessible-area/background definitions are treated as predeclared sensitivity conditions. The main empirical program evaluates 150, 300 and 500 km occurrence-buffer specifications rather than choosing the buffer that produces the highest score. Target-group background supports the observation/reference frame but is not treated as biological absence or as the ecological answer key.

### Candidate procedures and conventional comparators

The candidate space includes environmental predictor universes, all-variable and VIF baselines, predictive forward selection, ecological recovery selection, regularization, and response complexity. Conventional evaluation criteria include AUC-equivalent presence-background rank performance, Boyce/CBI, OR10 where applicable, AICc where a valid likelihood and parameter count are available, and local nested spatial cross-validation. These criteria are retained as model-evaluation or model-selection comparators; none is defined as the ecological truth target.

### Ecological recovery targets

Ecological recovery is evaluated in a common environmental audit space fitted using model-pool information only. The development program tracks environmental centroid, breadth and quantile-profile recovery; environmental niche overlap; response-curve structure, optima and lower/upper limits where literal generating truth is known; and recovery of generating ecological processes. Prediction and ecological metrics are not collapsed into an arbitrary weighted super-score.

### Known-truth falsification

Controlled generators supply literal process and response-boundary truth unavailable in real GBIF occurrence data. The development sequence varies niche family, predictor substitutability, observation confounding, accessible-area assumptions and model-form alternatives. New validation seeds are kept unused until the relevant candidate set, calibration rule and decision criterion are frozen.

### Set-valued and falsification-first certificates

After single-winner interpretations proved insufficient, Product A retained sets of adequate ecological explanations. Process claims distinguish necessary, possible/substitutable, contested and unsupported or unresolved states rather than converting all candidate uncertainty to one predictor set. Necessity is evaluated through exclusion logic: a process cannot be called required merely because retained fitted models contain it; the relevant test is whether a valid ecological certificate remains available when the corresponding declared information is excluded under a prospectively frozen design.

Boundary claims are calibrated using discovery-only known-truth evidence. If the predeclared calibration support for a required response key is insufficient, the result is unavailable rather than negative. Validation truth cannot be used to create a missing calibration radius or to relax a minimum support threshold.

### Observation-process separation

Product A distinguishes ecological suitability from occurrence-record observation. Declared observation nuisance variables can be marginalized from predictions, and a candidate-independent nuisance model can transport the held-out occurrence target toward a common target-group observation reference when nuisance-only evidence is independently supported. This addresses the possibility that both predictions and the withheld occurrence distribution are observation-biased.

### Deterministic scientific execution

The procedure treats computational identity as part of scientific reproducibility when optimization can alter discrete selected predictors. After an independent-process parity failure in the predecessor implementation, the deterministic successor fixed the model random state and selection-process NumPy seed prospectively. Independent process replicates were then required to reproduce both floating and discrete scientific outputs under the frozen comparison contract.

### Fresh empirical endpoint

The final empirical endpoint used a fresh, prospectively frozen plant panel and source lane, a single calibrated sealed fraction of 0.25, split seeds 2026082201, 2026082202 and 2026082203, and 150/300/500 km accessible-area sensitivity. Every preregistered part required all 12 taxa and all three M specifications. Structural and technical unavailability were distinguished from scientific non-support before sealed ecological outcomes were interpreted.

The primary empirical rule required prediction adequacy and ecological support across the full denominator. Ecological nondomination alone was insufficient; strict independent ecological improvement relative to the AUC-selected role was required according to the frozen contract. Process-status reproducibility was a conditional component and could not override failure of the primary ecological-support rule.

## Results

### Prediction transfer and stable response surfaces did not identify ecological process truth

The original Product-A architecture successfully established a leakage-resistant model-pool/sealed design and an unseen-taxon barrier, but its scientific output was still one complete winning procedure. Known-truth development then tested whether increasingly ecological winner criteria solved the interpretation problem.

They did not. In the first known-truth differentiation tests, canonical ecological recovery and canonical AUC often selected the same procedure, and the ecological selector did not establish robust differentiation across the full panel. A subsequent surface-stability line reached the deeper negative result: a procedure could recover held-out occurrence environments or generate a stable response surface while still attributing the niche to the wrong environmental processes. Thus prediction transfer, ecological surface similarity and process attribution were empirically separable targets under known truth.

This result changed the estimand. Product A no longer treated a single winning model or procedure as sufficient evidence for ecological necessity. Prediction remained a minimum adequacy layer, but the main ecological question became which environmental information remained defensible across adequate alternative explanations.

### Sharpening retained models could create false ecological necessity

The next development step replaced the single winner with a set-valued ecological certificate. Complete adequate candidate sets were filtered by ecological-recovery performance to obtain a sharper Pareto certificate, from which necessary processes were initially defined by intersection across retained fitted process sets and boundary uncertainty by the retained between-model spread.

This sharpening operation failed prospectively. Across all three known-truth validation panels, the ecological Pareto certificate was sharper than the complete-adequate certificate, but it did not preserve truth coverage. It could exclude a generating process or boundary and create a false necessary-process core. The result was therefore `identified_set_not_supported` despite the apparently attractive reduction in interval width.

The failure identified two anti-conservative interpretations. First, agreement among retained fitted models is conditional on the retention rule and cannot by itself establish biological necessity. Second, the min–max spread among retained fitted models is not automatically a complete uncertainty interval. A sharper model subset can be more certain and more wrong at the same time.

### Falsification-first process exclusion protected truth but required explicit abstention

Product A next changed from agreement-based necessity to falsification-first exclusion. The process question became whether an adequate ecological certificate remained available when the relevant information was removed under a frozen known-truth design. Boundary uncertainty was calibrated separately using discovery evidence rather than inferred from the spread of retained validation fits.

The first exclusion-certificate validation produced a mixed but informative result. All nine validation taxa had complete process certificates. False-required processes were zero and possible-process recall was 1.0 in every panel. The complete process-plus-boundary product nevertheless failed its frozen availability contract because each panel required 21 response keys but only 18 complete discovery-calibrated intervals were available; the missing keys were the omitted-driver soil lower limit, optimum and upper limit. The endpoint was therefore `exclusion_certificate_unavailable`, not ecological non-support.

A subsequent calibration stage preserved the predeclared requirement for at least two complete calibration taxa per predictor-by-response key. Soil boundary keys remained below that threshold, and fresh validation was not opened. No threshold was relaxed after the support deficit was observed.

After calibration redundancy was supplied prospectively, the next fresh known-truth validation passed. All three panels were available; all nine validation taxa had complete process and boundary certificates; false-required processes were zero; and minimum possible-process recall was 1.0 in every panel. Boundary coverage improved relative to the complete-adequate certificate. The price of this safety was wider uncertainty: possible-process precision remained approximately 0.467 and calibrated response intervals were broader than the complete-adequate intervals.

Together, these results show that abstention and conservative set width are substantive outputs. When the data or calibration design do not identify a narrower ecological claim, the valid result is unresolved rather than absent. Premature sharpening had already been shown to lose truth.

### Deterministic set-valued inference became both safe and sharp on fresh known truth

The next limitation emerged from execution rather than ecological logic. An independent M-shard parity check reproduced the evidence structure but changed one of 96 discrete selected-predictor outputs. The reference fold selected `ngd5,bio2,bio16,bio6,ngd10,scd,rsds`, whereas the independent-shard reconstruction selected the same set without `rsds`. The frozen fitting helper used scikit-learn liblinear without an explicit random state. Small process-dependent numerical differences were therefore able to cross a discrete variable-selection boundary.

The deterministic successor fixed estimator and selection-process random-state identity prospectively and was evaluated on 60 unused known-truth cases spanning six niche families and seeds 3101–3110 in two independent process replicates. Reproducibility was exact. Candidate fold metrics contained 7,140 rows and 173,880 compared floating cells; ecological inference certificates, observation summaries, selector choices and truth tables were also compared. The observed maximum absolute and relative difference was 0.0 in every table.

Scientific recovery was retained and sharpened. The robust ecological selector produced a resolved selection in 60/60 cases. Mean stable-process-core precision was 0.9889, recall was 0.9833 and F1 was 0.9833. Observation-confounded correction activated in 1.000 of the confounded family and 0.000 of all other niche families. These results passed all predeclared non-regression checks.

Thus the broad uncertainty observed in the earlier safe certificate was not an inevitable property of set-valued inference. Under fresh controlled truth, process-level identification could be simultaneously conservative in logic, sharp in recovery, and exactly reproducible in execution.

### Fresh empirical evidence did not support strict ecological improvement over AUC

The empirical lane added outcome-blind availability checks before sealed ecological interpretation. One fresh presealed feasibility experiment showed that spatial validation geometry itself could invalidate parts of a proposed denominator: two seed/fraction combinations at sealed fraction 0.30 failed the frozen evidence-balanced spatial-assignment support rule after 32 attempts. No environmental values, candidate scores or sealed ecological outcomes had been read. This was treated as structural unavailability rather than ecological evidence.

Fresh cohort eligibility and raw-source acquisition were subsequently rebuilt prospectively. A later scientific execution reached presealed model-pool computation but encountered a frozen runtime boundary before sealed ecological evidence. That endpoint was classified as technical provenance, not a favorable, null or adverse ecological result.

The final v2.8.4 successor preserved the scientific semantics and changed execution/runtime structure only. It completed the full preregistered denominator. Each of three seed parts contained all 12 taxa and all three 150/300/500 km M specifications, with all required sealed metrics finite. The prediction guardrail passed. The ecological procedure was nondominated relative to the AUC-selected role in 3/3 parts, and process-status reproducibility passed with minimum modal fraction 1.0.

However, strict ecological improvement occurred in 0/3 parts. Within every part, the ecological and AUC roles had the same sealed metric summary, and the mean presence-rank delta versus AUC was 0.0. The preregistered primary ecological-support rule therefore failed. The terminal decision was `empirical_confirmation_not_supported`, followed by a separate `not_promoted` decision. No taxon, seed, M, sealed fraction, threshold, candidate library, predictor universe, denominator, source or provider was changed to seek a favorable result.

## Discussion

### Ecological SDM tuning is an identification problem

The central result of Product A is not a new scalar score or a universally superior model selector. The prospective development sequence instead identifies what an ecologically interpretable tuning procedure must prove. Prediction adequacy, response-surface stability, agreement among good models, and process necessity are different inferential objects. Under observational substitutability, a high-performing or stable model can remain ecologically ambiguous, while aggressive model-set sharpening can create false certainty.

This distinction suggests a reframing of occurrence-only SDM tuning. Conventional model selection asks which candidate maximizes or minimizes a criterion. Ecological identification asks which environmental information is incompatible with the evidence when removed, which alternatives remain substitutable, which processes are contested across admissible procedures, and which claims remain unresolved. The latter question is naturally set-valued.

The known-truth results support this reframing directly. A falsification-first procedure recovered complete generating-process coverage with no false-required processes once calibration was adequate, and the deterministic successor subsequently achieved approximately 0.99 precision and 0.98 recall for stable process cores across fresh known-truth cases. These values do not establish equivalent performance in empirical GBIF data, but they demonstrate that retaining set-valued uncertainty does not preclude sharp ecological recovery when the evidence is informative.

### Prediction criteria remain necessary but are not proofs of ecological necessity

The results should not be interpreted as an argument against AUC, Boyce/CBI, OR10, AICc or spatial cross-validation. These criteria quantify useful properties of fitted models. Product A itself retains prediction adequacy as a guardrail. The limitation is inferential: a model-evaluation statistic answers a question about predictive or likelihood behaviour, not automatically about which environmental process is biologically necessary.

The final empirical result reinforces rather than weakens this distinction. Under the frozen plant corpus, the ecological and AUC roles were empirically indistinguishable on the preregistered sealed summaries and the ecological procedure did not achieve strict improvement. The correct conclusion is therefore not that AUC recovers ecological process truth universally, but that the fresh occurrence evidence did not demonstrate an independent advantage for the more elaborate ecological procedure under this contract.

### Agreement, set width and abstention require explicit semantics

The v2.3 failure is especially important because it illustrates how apparently sensible uncertainty reduction can become anti-conservative. Conditioning on an ecologically favourable subset of adequate fitted models narrowed the reported certificate while excluding truth. This is a general warning against interpreting consensus within a selected model set as evidence that unselected ecological alternatives are impossible.

The later exclusion framework adopts the opposite default. A process remains possible unless the evidence can falsify explanations that omit it under the declared design. A wide possible-process set therefore means the evidence has not identified a narrower statement. Likewise, an unavailable certificate is not equivalent to a negative process result. In v2.4 and v2.5, the missing object was calibration support, not ecological evidence against soil. Treating such cases as `not_supported` would manufacture information that was never observed.

### Observation bias can affect the answer-check target itself

Occurrence-only validation is often discussed as if the held-out occurrence sample were an unbiased ecological reference once it has been withheld from fitting. Product A's observation-process development makes a stronger distinction. The held-out occurrence environments can themselves inherit collector access, detectability, spatial effort or other observation bias. Marginalizing nuisance predictors from the fitted prediction surface therefore addresses only one side of the problem.

The candidate-independent target correction implemented here should be interpreted cautiously. It is activated only when nuisance-only evidence is independently supported, and its controlled-truth performance does not prove complete correction in empirical biodiversity data. Nevertheless, the conceptual point is broader: answer-check evidence has an observation model too. Validation designs that ignore this may reward candidates for reproducing sampling structure rather than ecological occupancy structure.

### Computational determinism can be scientifically material

The v2.7.1 parity failure shows that reproducibility is not separable from ecological inference when the scientific output contains discrete variable-selection decisions. The changed fold differed by one selected predictor despite fixed data, folds, candidate library and scientific rules. Once a floating-point or solver difference can change membership in the reported predictor set, process identity and random-state specification become part of the scientific procedure.

The deterministic successor resolved this specific failure and reproduced all compared outputs exactly across independent processes. Exact equality is not always required for every ecological algorithm, but a method that reports discrete selected variables should define a tolerance or deterministic rule capable of preventing unacknowledged process-dependent scientific outcomes.

### The empirical non-promotion result defines the external-validity boundary

Product A provides strong controlled-truth evidence but no claim of general empirical superiority. The v2.8.4 endpoint is therefore essential to the manuscript. It prevents known-truth success from being presented as if it automatically transfers to real plant occurrence data. The full denominator was available, prediction safety passed, process statuses were reproducible, and the ecological role was not worse under the nondomination criterion; nevertheless, it was not strictly better than the AUC role in any preregistered part.

This result has two implications. First, the added ecological identification machinery should not be justified by an empirical performance claim that the current evidence does not support. Second, the absence of empirical separation does not retroactively invalidate the known-truth demonstration that winner selection, retained-model agreement and nondeterministic execution can create incorrect ecological claims. The contribution is therefore the identification architecture and a prospectively measured boundary on its external advantage.

### From raster selection to process and representation hierarchy

The development sequence also clarifies the next conceptual bottleneck. A raw environmental raster is not equivalent to an ecological process. Direct environmental fields, derived exposures, topographic or spatial proxies and composite summaries may carry overlapping process information. A selected raster should therefore be interpreted as a representation, not automatically as a causal driver.

The current Chapter-1 hierarchy distinguishes geophysical template, direct environmental field, integrated biological exposure and composite summary representation, with explicit predictor roles such as spatial geometry, substrate, direct environment, derived exposure, proxy and composite summary. A future hierarchy-aware experiment would need to test process-information indispensability under a predeclared representation or proxy closure: if a temperature-labelled raster is removed while elevation, growing-degree metrics or composite climatic summaries still carry temperature information, the process itself has not been excluded.

That extension is a future design implication, not a reinterpretation of the current endpoint. It requires a new prospective contract and independent evidence. Product B remains blocked under the present Product-A decision.

### Limitations

The known-truth simulations expose literal generating processes but necessarily simplify ecological reality. The fresh empirical endpoint evaluates recovery of the environmental distribution of unused occurrences, not the fundamental niche, demographic fitness, dispersal limitation, historical range dynamics or biotic interactions. Presence-only background/reference environments are not biological absences. The target-group observation frame is a sampling reference, not a biological answer key.

The final empirical panel is also a finite frozen corpus. `empirical_confirmation_not_supported` means that strict ecological improvement was not demonstrated under this 12-taxon, three-seed, three-M contract. It does not imply that AUC is universally optimal or that ecological-process-aware methods cannot be useful in other systems. Conversely, the strong known-truth process-core recovery should not be generalized to empirical causal-driver identification without independent evidence.

Finally, the process registry and representation hierarchy remain incomplete solutions to environmental substitutability. Product A established why process-level and representation-level claims must be separated; it did not complete a universal proxy-closure test for real plants.

## Conclusion

Occurrence-only SDM tuning should not automatically compress ecological interpretation into a single winning predictor set. Across a prospectively frozen falsification sequence, successful prediction transfer and stable response surfaces failed to guarantee process recovery; agreement among sharpened fitted-model sets could create false necessity; falsification-first set-valued certificates protected generating processes by preserving unresolved alternatives; and deterministic execution proved necessary when numerical process differences altered discrete selected predictors. Under fresh controlled truth, the deterministic framework recovered stable process cores with high precision and recall. Under the final frozen empirical plant endpoint, however, it did not show strict ecological improvement over the AUC-selected role and was not promoted.

The resulting contribution is therefore neither a new universal performance metric nor a claim of empirical superiority. It is an ecological identification framework that separates what the occurrence evidence predicts from what it can defensibly identify, and that preserves support, non-support, substitutability, unavailability and technical failure as different scientific states.
