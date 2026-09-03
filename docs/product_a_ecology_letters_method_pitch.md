# Ecology Letters Method proposal — Product A

Status: **journal pitch draft / frozen Product-A evidence only**.

## Proposed title

**From model selection to ecological identification in occurrence-only species distribution models**

Alternative:

**Prediction can succeed while niche processes remain unidentified: a falsification-first framework for species distribution models**

## One-sentence advance

Species distribution modelling usually selects the best-performing model or predictor set, whereas we show prospectively under known truth that prediction/stability, agreement among good models and ecological-process necessity are distinct inferential objects, and introduce a falsification-first set-valued procedure for identifying which process claims remain defensible without forcing observationally substitutable explanations into one winner.

## Why this is a general ecological Method rather than an SDM benchmark

Ecologists routinely use observational models both to predict patterns and to infer which environmental constraints matter. When correlated or substitutable environmental representations produce similar predictions, the best model need not uniquely identify the process claim. This problem extends beyond a particular taxon or algorithm: it concerns the logical step from predictive adequacy to ecological interpretation.

Our method changes the target of inference. Rather than asking which model wins, it asks which environmental-process claims survive direct falsification after adequate alternatives are retained. The output is explicitly set-valued: necessary, possible/substitutable, contested and unresolved claims remain distinct. Spatial and unseen-taxon answer checks are sealed before procedure selection, incomplete calibration yields an unavailable rather than negative result, observation bias is treated as potentially affecting both predictions and the held-out occurrence target, and deterministic execution is required when numerical drift can alter discrete variable selection.

## Prospective evidence sequence

The method arose through a preregistered/frozen falsification sequence rather than post-outcome model redesign.

1. **Prediction/stability did not imply process recovery.** In known-truth tests, a procedure could recover held-out occurrence environments or a stable response surface while attributing the niche to the wrong environmental process; ecological and AUC winner criteria also often converged.
2. **Sharpening good models could create false necessity.** Ecological Pareto filtering produced narrower certificates in all three known-truth panels but lost truth coverage and could create a false necessary-process core. Agreement among retained fitted models was therefore not accepted as biological necessity.
3. **Falsification-first exclusion protected truth.** After prospective calibration, complete process/boundary certificates had zero false-required processes and possible-process recall 1.0, initially at the cost of broad uncertainty.
4. **The final controlled-truth method was both sharp and reproducible.** On 60 unused known-truth cases across six niche families, stable-process-core precision was 0.9889 and recall/F1 were 0.9833. Two independent process replicates produced maximum absolute and relative differences of 0.0 across all compared scientific outputs. Observation-confounding correction activated in all declared confounded cases and in none of the other evaluated families.
5. **The fresh empirical endpoint bounds the claim.** A prospectively frozen 12-taxon × 3-seed × 3-accessible-area plant endpoint was fully evaluable. Prediction adequacy and process-status reproducibility passed, but strict ecological improvement relative to the AUC-selected role occurred in 0/3 parts and mean sealed presence-rank delta was 0.0. The method was therefore not empirically promoted and the endpoint was not retuned.

## What is new relative to adjacent work

Previous SDM literature has distinguished explanation from prediction and shown that variable-importance inference can fail under correlation, spatial structure or limited data. Statistical and machine-learning work has also established model multiplicity/Rashomon sets and variable-importance ranges across well-performing models.

Our contribution is not the claim that multiple good models exist. The new methodological object is an **ecological process certificate whose necessity claim is tested by prospective falsification rather than inferred from winner identity, variable importance or agreement within a selected good-model set**. The known-truth sequence directly shows why the stronger logic is needed: selecting only the ecologically better models can itself produce false necessity.

## Broad relevance

The identification problem applies whenever ecologists interpret environmental predictors from observational models with substitutable representations, including biogeography, climate-response modelling, habitat-suitability analysis, invasion ecology and conservation forecasting. The framework is algorithm-agnostic at the inferential level: prediction metrics remain adequacy checks, whereas the process certificate defines what ecological interpretation the data can support.

## Claim boundary

We do not claim causal identification, recovery of the fundamental niche, or universal empirical superiority over AUC. The fresh empirical endpoint explicitly did not support strict superiority. The demonstrated advance is a falsification-first framework that makes ecological-process identification measurable under controlled truth and prevents unavailable or observationally ambiguous evidence from being converted into false necessity.

## Proposed main display items

1. Model selection versus ecological identification and the sealed information barrier.
2. Prospective falsification: prediction/stability failure and false necessity after Pareto sharpening.
3. Falsification-first solution and controlled-truth performance (v2.6 → v2.7.2).
4. Fresh full-denominator empirical boundary and explicit non-promotion.

## Proposal decision rule

Send this proposal only after the four main figures and claim audit are complete. If the Method editor judges the contribution too SDM-specific or insufficiently general given the empirical non-promotion result, submit the same frozen manuscript directly to **Methods in Ecology and Evolution** without collecting additional favorable Product-A evidence.
