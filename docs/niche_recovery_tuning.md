# Ecological niche-recovery tuning

## Core distinction

SDMR Product-A v2 is **not** a new model-evaluation metric.

AUC/presence-rank, Boyce/CBI, OR10 and AICc answer conventional model-evaluation or model-selection questions. Product-A v2 asks a different question:

> Which model-building **procedure** recovers an ecologically interpretable realized/accessible environmental niche from genuinely unused occurrence evidence, and which parts of that ecological conclusion survive plausible observation, M/background and domain perturbations?

The prediction surface is an intermediate object. The scientific target is niche structure: environmental process support, response shape, centre/optimum, breadth, limits/tails and the uncertainty of those conclusions.

## Layer 1 — conventional model criteria

### AUC / presence-rank

`presence_rank` is the presence-background ROC-AUC-equivalent ranking statistic, with half credit for ties. It measures discrimination/ranking, not niche geometry.

### Boyce / continuous Boyce

Boyce/CBI measures whether observed presences become relatively more frequent as predicted suitability increases. It is a useful presence-only prediction diagnostic, but it does not establish that response shape, optimum, breadth or limits are biologically correct.

### OR10

`sdmr.model_criteria.or10` is threshold-dependent omission at the 10% training-presence omission threshold. It is useful for transfer/overfit diagnostics and guardrails. Known-truth experiments show that optimizing OR10 alone is not a niche-recovery objective.

### AICc

`sdmr.model_criteria.corrected_aic` provides the mathematical AICc correction when a valid likelihood, defensible parameter/effective-df count and sample size are supplied. SDMR does **not** manufacture AICc for the current class-balanced penalized presence-background logistic core by simply counting coefficients.

AICc therefore remains a conventional comparator or late parsimony criterion only where its inputs are justified.

## Layer 2 — prediction adequacy is an admission condition, not the objective

Product-A v2 does not require a candidate to be near the best AUC. That would quietly turn the method back into AUC optimization.

The current absolute adequacy rule requires independent within-domain evidence above chance:

- mean AUC-equivalent presence-rank >= 0.51; and
- mean AUC minus 1 SEM >= 0.50.

The hard gate is applied to predeclared **sampling/background (M) perturbations**. Domain-transfer AUC is not allowed by itself to declare an ecological niche wrong. Known-truth `interaction / seed 7` provided the decisive counterexample: the biologically better niche model had source-to-shifted record AUC < 0.5, so an all-perturbation AUC gate produced a false ecological abstention.

Domain transfer therefore remains mandatory ecological-robustness evidence, but transfer-record discrimination is not the niche objective.

## Layer 3 — observation process is separated from ecological suitability

Occurrence records mix ecological suitability with observation/accessibility/detectability processes. Product-A v2 separates those roles explicitly.

### Model-side marginalization

A candidate may include predeclared observation predictors in the record model. `score_ecological_suitability` then marginalizes those nuisance predictors over a fixed model-pool observation reference while holding ecological predictors at the target row.

Thus:

- full scores answer: how well does the model predict **records**?;
- marginalized ecological scores answer: what ecological suitability surface remains after the declared observation process is integrated out?

### Heldout-target correction

The withheld occurrence distribution can itself be observation-biased. A candidate-independent nuisance-only classifier is fitted on training focal records versus training target-group background. Its inverse density-ratio weights can transport heldout occurrences toward the target-group observation reference.

Correction is not activated just because a nuisance column exists. A global replicated gate requires the nuisance-only signal to satisfy the same weak absolute AUC evidence rule in every predeclared sampling/M/domain perturbation. If replication fails, weights revert exactly to one.

### Ecological model admissibility

If a nuisance process is globally validated, ecological inference admits only record models that explicitly declare that nuisance in `observation_predictors`. A model that ignores a validated observation process may still be reported as a conventional AUC comparator, but its ecological coefficients are not treated as deconfounded niche evidence.

Fresh known-truth confirmation reproduced this specificity: replicated correction activated in 10/10 observation-confounded cases and 0/50 cases from the other five structural niche families.

## Layer 4 — ecological recovery profile

Product-A v2 keeps ecological dimensions separate rather than building another arbitrary weighted super-score.

The empirical recovery profile includes:

- `niche_overlap_schoener_d_pc12` — higher is better;
- `centroid_distance` — lower is better;
- `breadth_log_sd_error` — lower is better;
- `quantile_profile_error` — lower is better;
- `sealed_pc12_envelope_coverage90` — descriptive boundary coverage, not optimized alone.

Known-truth post-selection audits additionally include direct hidden-target measures such as suitability-surface rank/error, response-curve error, optimum error, lower/upper limit error and environmental-process precision/recall/F1.

Hidden truth is never available to fitting or selection.

## Candidate universe and audit space are different objects

Real CHELSA data exposed an important design constraint: the full candidate predictor universe cannot automatically be used as the common complete-case audit basis.

The current strict empirical path therefore separates:

1. **candidate predictor universe** — all 43 predeclared CHELSA predictors remain available to candidate procedures;
2. **ecological audit space** — selected independently from model-pool availability plus predeclared manifest `process` labels only.

For each ecological process, the audit-space selector chooses the highest-coverage model-pool representative, requires high marginal coverage, and greedily preserves a minimum joint complete-case fraction. Sealed occurrence rows are not an input to this decision.

This prevents two opposite failures:

- letting a candidate define the environmental space in which it is judged; and
- letting dozens of partially missing rasters collapse the sealed audit sample to zero.

In the strict two-taxon real-data smoke, this changed the audit from a 43-variable complete-case intersection to approximately 12 process-representative axes while leaving the 43-variable candidate universe intact.

## Procedure-level tuning, not fixed predictor-set competition

The scientific object is the **tuning procedure**, not one lucky fixed raster subset.

`niche_recovery_procedure` implements nested spatial evaluation of procedures such as:

- all variables;
- iterative VIF;
- predictive forward selection;
- ecological/niche forward selection;
- model complexity/regularization profiles.

Each outer spatial fold reruns the procedure using only that fold's training data. A selected procedure is then rerun on the complete model pool to determine the final predictor set before outer sealed evidence is opened.

This prevents a predictor subset discovered using one partition from being treated as if it were the method itself.

## Ecological selection rule

Within a candidate set that passes prediction adequacy, ecological selection is:

1. aggregate each ecological recovery dimension over training-only spatial folds;
2. remove Pareto-dominated candidates;
3. rank the Pareto front separately on each ecological dimension;
4. minimize the worst ecological rank;
5. break ties by mean ecological rank and then lower complexity.

No AUC/CBI/OR10/ecological weighted sum is used.

## Perturbation robustness

A second ecological selector asks whether the conclusion survives predeclared perturbations in:

- sampling effort;
- accessible-area/background M;
- environmental transfer domain.

The method ranks candidates within each perturbation before cross-perturbation aggregation, avoiding scale artifacts where an "easy" M dominates raw metric values.

Several stronger-looking robustness gates were falsified and retained as ablations rather than tuned until successful:

- worst single heldout fold;
- generic refit-surface stability;
- per-perturbation observation correction;
- all-perturbation hard AUC adequacy.

These failures are part of the method's evidence, not results to hide.

## Abstention is a valid result

Real-data procedure tuning can legitimately return no ecological winner.

Product-A v2 records distinct states for:

- canonical ecological selector unavailable;
- no perturbation-robust candidate satisfying the hard within-domain adequacy contract;
- selected procedure unable to instantiate when rerun on the full model pool.

The pipeline does **not** inspect sealed evidence and then substitute a fallback procedure. Outer sealed rows are opened only for procedures that were selected and successfully refit without using them.

## Known-truth evidence

The structural benchmark currently spans six niche families:

- Gaussian;
- asymmetric;
- soft threshold;
- interaction;
- omitted driver;
- observation-confounded.

The frozen fresh confirmation uses unused seeds 11–20 (60 cases). The robust ecological selector selected in 60/60 cases and differed from canonical AUC in 27/60.

Across those 27 disagreements, robust ecology improved, on average, the main direct niche-structure targets relative to AUC: environmental overlap, centroid error, breadth error, quantile/tail error, hidden-surface rank, optimum error and environmental-process F1. AUC remained better on some surface-magnitude/response-curve summaries, so the result is **not** that one robust scalar winner is universally best.

The supported methodological conclusion is narrower and stronger:

> record-prediction quality and ecological niche recovery are genuinely different targets.

## Interpretation product: consensus before winner worship

Because canonical ecological recovery and perturbation robustness can disagree, Product-A does not force them into one super-score.

`EcologicalInferenceCertificate` reports:

- `model_consensus`;
- `process_consensus_model_uncertainty`;
- `partial_process_consensus`;
- `process_contested`;
- abstention states.

The strong ecological claim is the **stable process core** shared by canonical and robust ecological inference. Selector-specific processes remain contested/sensitivity evidence.

On fresh known-truth cases, this stable process core achieved approximately precision 0.978, recall 0.967 and F1 0.970 against the hidden process truth.

The interpretation layer also returns response profiles including marginal optima, environmental 5–95% limits, breadth and binned response curves. Canonical and robust profiles are retained separately or as selector ranges rather than averaged into a pseudo-certain response.

## Real-data claim boundary

With GBIF occurrence-only data, the empirical target is a **realized/accessibility-conditioned environmental niche signal** supported by unused records. Product-A v2 does not claim direct recovery of the fundamental physiological niche, demographic fitness, dispersal history or biotic interactions without independent evidence.

The strict prepared-data path enforces:

- whole outer occurrence blocks frozen before M/background construction;
- M built from model-pool occurrence information only;
- target-group background separated from focal sealed positives;
- tuning on model-pool rows only;
- final opening of outer sealed presence/reference rows after procedure selection/refit.

The public `sdmr-prepared-v2` strict frozen-data smoke passes this information barrier and records both successful sealed validation and explicit abstentions.

## Link to Product B

Legacy Product-B driver summaries based on predictor selection frequency, drop-one loss and unseen-taxon predictive transfer remain useful predictive baselines.

The v2 ecological-synthesis lane instead aggregates Product-A certificates across real taxa at the **ecological process** level, keeping separate counts for:

- stable-core support;
- contested support;
- explicit non-support;
- unresolved/abstaining taxa.

No universal-driver threshold is inferred from known-truth seeds or chosen after seeing the empirical result. Raw raster names, predeclared ecological processes and correlation/equivalence diagnostics remain distinct layers.
