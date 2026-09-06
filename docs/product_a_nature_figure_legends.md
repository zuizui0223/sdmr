# Figure legends — Nature Ecology & Evolution Product A

Status: **submission-production draft; values sourced from frozen evidence**.

## Fig. 1 | Predictive adequacy and ecological process identification are different inferential targets.

**a,** Conventional occurrence-only SDM selection evaluates candidate models using withheld observations or model-selection criteria and returns a winning model. **b,** Product A separates model-pool evidence from sealed answer-check evidence before candidate construction; accessible-area/background assumptions are treated as sensitivity conditions rather than optimized outcomes. **c,** Ecological interpretation is decomposed into predictive adequacy, environmental niche recovery, process membership and the stronger claim of process necessity. Controlled-truth tests showed that prediction or stable response surfaces can coexist with incorrect process attribution. `Necessary` remains contract-relative and is not a claim of a complete causal mechanism.

## Fig. 2 | Restricting inference to ecologically better models can create false necessity.

**a,** A complete prediction-adequate candidate set can contain multiple process explanations. **b,** Ecological Pareto filtering reduced the retained set and narrowed between-model response ranges in all three controlled-truth panels. **c,** This sharpening was anti-conservative: the retained set could lose generating-process or response-boundary coverage and create a false necessary-process core. **d,** A falsification-first necessity certificate therefore challenged process claims by making their declared information unavailable and retaining `unresolved/unavailable` when evidence was insufficient. Quantitative panel-level results are provided in Extended Data.

## Fig. 3 | Counterfactual ecological-recovery loss identifies independently varying environmental processes.

Process membership was estimated from the ecological recovery lost when all declared representations of one process were excluded from the prediction-adequate candidate class. Thresholds were calibrated only on the 35-case `4201`–`4205` discovery lane and frozen before fresh truth was opened. **a,** Complete generating-process-set recovery in fresh validation (`4301`–`4305`, 35 cases) and an unchanged independent replication (`4401`–`4410`, 70 cases). Counterfactual recovery was 30/35 (85.7%) in fresh validation and 65/70 (92.9%) in replication, compared in the same cases with AUC-selected winners (25/35 and 56/70) and the falsified predecessor stable-core rule (23/35 and 49/70). **b,** Process-specific classification in the 70-case replication. Temperature: TP=40, FN=0, TN=28, FP=2, sensitivity 1.000 and specificity 0.933. Water: TP=40, FN=0, TN=28, FP=2, sensitivity 1.000 and specificity 0.933. Soil: TP=39, FN=1, TN=30, FP=0, sensitivity 0.975 and specificity 1.000. **c,** Exact recovery by true process combination in the independent replication. Counterfactual recovery was 8/10 for `{T}`, 8/10 for `{W}`, 10/10 for `{S}`, 10/10 for each two-process set and 9/10 for `{T,W,S}`. Canonical and perturbation-robust ecological selectors chose different fitted models in 30/70 replication cases, yet the complete counterfactual process set remained exact in 27/30 (90.0%). The unchanged replication used thresholds temperature 0.2653964368, water 0.0671670999 and soil 0.3342415841. Authoritative replication: workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

## Fig. 4 | Fresh empirical occurrence data collapse ecological and AUC selection to the same fitted model.

The prospectively frozen empirical endpoint contained 12 plant taxa in each of three split seeds and three accessible-area conditions (150, 300 and 500 km). **a,** Sealed presence-rank values for ecological and AUC roles across all 108 matched taxon × accessible-area × seed cells. **b,** Candidate identity and selected-predictor identity were both 108/108; every matched cell selected `all|logit_l2_C0.1_degree1_rs0`. Audited continuous Boyce, OR10, Schoener-D overlap, centroid distance, breadth error and quantile-profile error were likewise identical between roles. **c,** Formal preregistered endpoint: prediction guardrail passed; ecological nondomination occurred in 3/3 seed parts; strict ecological improvement occurred in 0/3; terminal decision `empirical_confirmation_not_supported`; separate promotion decision `not_promoted`. The frozen scientific denominator is three complete seed parts. Values derive from workflow `33364164527` and terminal artifact `9750071472` plus its three finalized seed artifacts.

# Extended Data legends

## Extended Data Fig. 1 | Prospective information barriers in Product A.

Occurrence evidence is admitted and thinned before whole spatial blocks are assigned to model or sealed roles. Accessible-area/background data are generated from model-pool occurrences only. Discovery evidence may develop a procedure; later validation truth remains unopened until procedure and thresholds are frozen. Sealed empirical values are opened only after candidate/procedure freeze.

## Extended Data Fig. 2 | Candidate and evaluation architecture.

Product A retains AUC-equivalent rank discrimination, Boyce/CBI, OR10, AICc where valid and spatial cross-validation as model diagnostics/comparators. Ecological recovery measures environmental centroid, breadth, quantile profiles and Schoener-D overlap without a weighted prediction–ecology super-score.

## Extended Data Fig. 3 | Ecological Pareto sharpening loses truth coverage.

Known-truth evaluation of the first set-valued certificate. Ecological Pareto pruning sharpened retained response ranges but failed the frozen truth-coverage criterion and could assert a false necessary process. This result motivated process-level falsification rather than threshold relaxation.

## Extended Data Fig. 4 | Safe exclusion certificates can remain broad.

After prospective calibration redundancy, v2.6 produced complete process and boundary certificates with false-required=0 and possible-process recall 1.0, but possible-process precision approximately 0.467 and `required_processes` empty in all nine validation taxa. The result is false-necessity control rather than positive driver discovery.

## Extended Data Fig. 5 | Factorial process truth falsifies the predecessor stable-core rule.

All seven non-empty combinations of temperature, water and soil were prospectively generated for seeds `4201`–`4205` (35 cases). The preceding stable process intersection recovered only 22/35 complete process sets, versus 25/35 for AUC-selected winners. Temperature specificity was 0.667, water sensitivity 0.70 and soil specificity 0.867. This non-support was retained and used as discovery evidence for the successor rather than repaired by dropping process combinations.

## Extended Data Fig. 6 | Discovery-only counterfactual-score separation and threshold freeze.

For each process, counterfactual score compares the best held-out Schoener-D overlap achievable by prediction-adequate process-containing candidates with the best overlap achievable when every declared representation is excluded. Discovery maximum false versus minimum true scores were 0.2522 versus 0.2786 for temperature, 0.0525 versus 0.0818 for water and 0.2068 versus 0.4617 for soil. Midpoint thresholds were frozen before seeds `4301+` were opened.

## Extended Data Fig. 7 | Fresh counterfactual validation passes every process gate.

On unused seeds `4301`–`4305` across all seven process combinations (`n=35`), complete counterfactual process-set recovery was 30/35, versus 25/35 for AUC and 23/35 for the predecessor. Temperature sensitivity/specificity were 1.000/0.933, water 1.000/0.800 and soil 1.000/0.933. All preregistered ≥0.80 gates passed.

## Extended Data Fig. 8 | Independent replication preserves the frozen counterfactual estimator.

No method or threshold was changed after fresh validation. New seeds `4401`–`4410` produced 70 cases. Counterfactual exact process-set recovery was 65/70, AUC 56/70 and predecessor 49/70. Paired exact outcomes were 51 both exact, 14 counterfactual only, 5 AUC only and 0 both wrong. The five counterfactual errors were two false-water calls in temperature-only niches, two false-temperature calls in water-only niches and one missed-soil call in a three-process niche.

## Extended Data Fig. 9 | Sealed empirical metrics are identical between ecological and AUC roles.

Matched differences between ecological and AUC roles across 108 cells for presence rank, continuous Boyce, OR10, Schoener-D environmental overlap, centroid distance, breadth error and quantile-profile error are all zero because both roles instantiate the same candidate and selected-predictor set in every matched cell.

## Extended Data Fig. 10 | Scientific outcome states and immutable evidence provenance.

Product A keeps prospective discovery, supported/not-supported validation, unavailable evidence, technical STOP and empirical non-promotion distinct. The figure links the factorial falsification, counterfactual fresh validation, unchanged 70-case replication and frozen v2.8.4 empirical non-support to their immutable contracts and workflow artifacts.
