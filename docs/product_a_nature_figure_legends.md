# Figure legends — Nature Ecology & Evolution Product A

Status: **submission-production draft; values sourced from frozen evidence**.

## Fig. 1 | Predictive adequacy, environmental recovery and process-information necessity are different inferential targets.

**a,** Conventional occurrence-only SDM selection evaluates candidate models using withheld observations or model-selection criteria and returns a winning model. **b,** Product A separates the model pool from a sealed answer-check before candidate construction; accessible-area/background assumptions are treated as sensitivity conditions and unseen taxa remain unavailable during procedure selection. **c,** Ecological interpretation is decomposed into predictive adequacy, recovery of the occupied environmental distribution and process-information claims. A process is not called necessary because it appears in a winning model; necessity is challenged against adequate alternatives under the declared process/representation registry. Separately, process stability can be evaluated across independently defined ecological selectors. Controlled-truth tests showed that a candidate could recover withheld occurrence environments or a stable environmental response surface while attributing the pattern to an incorrect generating process. `Necessary` refers to necessity under the declared evidence/representation system and is not a claim of a complete causal mechanism.

## Fig. 2 | Restricting inference to ecologically better models can create false necessity.

**a,** A complete prediction-adequate candidate set can contain multiple process explanations. **b,** Ecological Pareto filtering reduced the retained set and narrowed between-model response ranges in all three controlled-truth panels. **c,** This sharpening was anti-conservative: the retained set could lose generating-process or response-boundary coverage and create a false necessary-process core. Agreement within the selected model subset therefore did not establish biological necessity. **d,** The successor necessity framework replaced intersection-as-necessity with falsification-first process exclusion. A process claim is challenged by making its declared information unavailable and testing whether an adequate ecological certificate survives; insufficient calibration or evidence remains `unresolved/unavailable` rather than being converted into absence. Quantitative panel-level results are provided in Extended Data Figs. 3–4.

## Fig. 3 | Process information can be more stable than exact model identity under fresh controlled truth.

This figure reports the **consensus-first process-stability certificate**, not the process-exclusion necessity certificate. The stable process core is the intersection of process sets supported by the canonical ecological-recovery selector and the perturbation-robust ecological-recovery selector. **a,** Mean stable-process-core precision and recall for six preregistered niche-generating families (10 independently seeded cases per family; 60 cases total). Asymmetric, Gaussian, interaction and observation-confounded families each had mean precision and recall of 1.0. Omitted-driver cases retained precision 1.0 with recall 0.90; soft-threshold cases retained recall 1.0 with precision 0.933. Pooled precision was 0.9889 and pooled recall and F1 were 0.9833. **b,** Process-set consensus versus exact fitted-model consensus within each family. Across all cases, process-set consensus occurred in 50/60 whereas exact-model consensus occurred in 38/60. The largest gaps occurred for asymmetric (0.80 versus 0.40) and Gaussian (0.90 versus 0.50) niches. Observation-process correction activated in 10/10 observation-confounded cases and 0/50 other cases. Two independent computational processes produced exactly identical audited floating and discrete outputs; observed maximum absolute and relative differences were 0.0. These values support process-information stability across ecological selectors and must not be interpreted as the precision/recall of the exclusion-based necessity estimator. Values derive from frozen workflow run `32629842082`, artifact `9490817718`, with terminal decision artifact `9490827277`.

## Fig. 4 | Fresh empirical occurrence data collapse ecological and AUC selection to the same fitted model.

The prospectively frozen empirical endpoint contained 12 plant taxa in each of three split seeds and three accessible-area conditions (150, 300 and 500 km). **a,** Sealed presence-rank values for ecological and AUC roles across all 108 matched taxon × accessible-area × seed cells. **b,** Candidate identity and selected-predictor identity were both 108/108; every matched cell selected `all|logit_l2_C0.1_degree1_rs0`. Audited continuous Boyce, OR10, Schoener-D overlap, centroid distance, breadth error and quantile-profile error were likewise identical between roles. **c,** Formal preregistered endpoint: prediction guardrail passed; ecological nondomination occurred in 3/3 seed parts; strict ecological improvement occurred in 0/3; terminal decision `empirical_confirmation_not_supported`; separate promotion decision `not_promoted`. The 108 cells are reporting units for realized selector identity, not independent primary decision replicates; the frozen scientific denominator is three complete seed parts. Values derive from workflow run `33364164527` and terminal artifact `9750071472` plus its three finalized seed artifacts.

# Extended Data legends

## Extended Data Fig. 1 | Prospective information barriers in Product A.

Occurrence evidence is admitted and thinned before whole spatial blocks are assigned to model or sealed roles. Accessible-area/background data are generated from model-pool occurrences only. The complete focal panel is excluded from the target-group source to prevent sealed focal records from re-entering as background. Discovery taxa may select a procedure; unseen validation taxa do not participate. Sealed values are opened only after candidate/procedure freeze, and scientific confirmation is separated from method promotion.

## Extended Data Fig. 2 | Candidate and evaluation architecture.

Product A separates conventional model evaluation from ecological recovery. The frozen environmental manifest contained 43 active predictors and three nested environmental universes. Accessible-area specifications of 150, 300 and 500 km were evaluated as sensitivity conditions rather than optimized by score. AUC-equivalent rank discrimination, Boyce/CBI, OR10, AICc where valid and spatial cross-validation were retained as model diagnostics/comparators. Ecological recovery used a model-pool-defined audit space and measured environmental centroid, breadth, quantile profiles, overlap and known-truth response/process recovery without a weighted prediction–ecology super-score.

## Extended Data Fig. 3 | Ecological Pareto sharpening loses truth coverage.

Known-truth evaluation of the first set-valued certificate. The ecological Pareto certificate was sharper than the complete-adequate certificate in all three validation panels but failed the frozen truth-coverage criterion and could assert a false necessary process. This result motivated the falsification-first replacement rather than a looser post hoc threshold.

## Extended Data Fig. 4 | Calibration availability, abstention and the safe broad exclusion certificate.

The first falsification-first validation produced complete process certificates for all nine validation taxa, false-required processes of zero and possible-process recall 1.0, but only 18 of 21 required discovery-calibrated boundary intervals per panel; the endpoint was therefore unavailable. A subsequent calibration stage retained the frozen minimum-support rule and did not open fresh validation when soil boundary calibration remained insufficient. After prospective calibration redundancy, all process and boundary certificates were complete. Boundary coverage increased from 0.381, 0.333 and 0.381 to 0.762, 0.762 and 0.857 across panels D1–D3, with possible-process recall 1.0 and precision 0.467. Wider intervals were retained as the cost of truth coverage. This exclusion-based result concerns false-necessity control and must be reported separately from the v2.7.2 consensus-first stable-core precision/recall.

## Extended Data Fig. 5 | Independent process execution can change a discrete selected predictor.

In the predecessor parity audit, one of 96 fold rows selected `ngd5,bio2,bio16,bio6,ngd10,scd,rsds` in the reference process but `ngd5,bio2,bio16,bio6,ngd10,scd` after independent process/shard reconstruction. The frozen fitter used scikit-learn `liblinear` without explicit `random_state`. Sealed environmental values were not opened. The failed implementation was not rescued by widening tolerance or ignoring the discrete difference; the successor froze estimator and selection random states prospectively before new known-truth evidence.

## Extended Data Fig. 6 | Exact deterministic parity in the successor implementation.

Two independent processes were compared across candidate fold metrics (7,140 rows, 173,880 floating cells), ecological inference certificates (60 rows, 360 cells), observation summaries (420 rows, 2,100 cells), selector choices (180 rows, 540 cells), selector truth summaries (3 rows, 42 cells) and truth evaluation (180 rows, 5,220 cells). Observed maximum absolute and relative differences were 0.0 for every table and all discrete comparisons were identical. The ecological inference certificates here are consensus-first process-stability certificates.

## Extended Data Fig. 7 | Structural validation availability can fail before ecological evidence is read.

A coordinate-only presealed feasibility design evaluated six seed × sealed-fraction conditions. Four were structurally available. Two conditions at sealed fraction 0.30 failed because no evidence-balanced spatial assignment satisfied the frozen row-support constraints after 32 attempts. Environmental values, candidate models, candidate scores and sealed ecological outcomes had not been opened, so the result was classified as structural unavailability rather than ecological evidence.

## Extended Data Fig. 8 | Composition of the final fresh empirical denominator.

Each of three preregistered seed parts contained all 12 taxa and all three 150/300/500 km accessible-area specifications, yielding 36 taxon × M cells per part and 108 matched cells overall. All required sealed metrics were finite. The primary decision remained the three-part frozen denominator.

## Extended Data Fig. 9 | Sealed empirical metrics are identical between ecological and AUC roles.

Matched differences between ecological and AUC roles across 108 cells for presence rank, continuous Boyce, OR10, Schoener-D environmental overlap, centroid distance, breadth error and quantile-profile error. All audited differences are zero because both roles instantiate the same candidate and selected-predictor set in every matched cell.

## Extended Data Fig. 10 | Scientific outcome states and immutable evidence provenance.

Product A keeps four states distinct: scientific `supported/not supported` decisions formed under complete evidence; `unavailable` when the requested estimand cannot be constructed under frozen evidence requirements; technical STOP before a valid scientific endpoint; and the separate `not_promoted` governance decision. The figure links these states to the principal frozen v2.6, v2.7.2 and v2.8.4 workflow/artifact identities and digests.