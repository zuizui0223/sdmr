# Nature Portfolio reporting summary — Product A draft answers

Status: **submission-production aid synchronized to controlled-truth replication and the completed frozen real positive-control audit**.

## Field

Ecological, evolutionary & environmental sciences.

## Study design

### Research samples and inferential units

The manuscript contains four distinct evidence layers that are not pooled.

**Factorial discovery/falsification.** Temperature, water and soil varied across all seven non-empty process combinations. Seeds `4201`–`4205` produced 35 cases. This lane falsified the predecessor stable-process intersection and was then used only to calibrate process-specific counterfactual thresholds.

**Fresh controlled-truth validation.** Unused seeds `4301`–`4305` across the same seven process sets produced 35 validation cases. The primary gate required the complete denominator, exact process-set recovery >=0.80, and sensitivity and specificity >=0.80 for temperature, water and soil separately.

**Unchanged controlled-truth replication.** After validation, estimator and thresholds were frozen unchanged. Seeds `4401`–`4410` produced 70 independent replication cases. Each process was true in 40 cases and false in 30.

**Empirical evidence.** Two prospectively frozen real-data tests are reported separately. The earlier v2.8.4 plant endpoint used 12 taxa, three split seeds and three accessible-area conditions (150, 300 and 500 km), yielding 108 matched taxon × M × seed reporting cells. A later positive-control test used eight literature-backed taxa in two four-taxon lanes, each evaluated at 150, 300 and 500 km, yielding 24 taxon × M cells. The positive controls provide one-sided evidence that a target process should be recoverable; they are not complete generating-process truth and contain no negative labels.

### Sample-size determination

No post-outcome power calculation or adaptive favorable sample-size change was used.

The factorial discovery denominator was prospectively fixed at seven process combinations × five seeds = 35. Fresh validation used a disjoint five-seed set = 35. Replication used ten new unused seeds × seven process sets = 70, declared before outcome.

The v2.8.4 empirical endpoint required all 12 taxa and all three M conditions within each of three split-seed parts. The later real positive-control contract fixed four plant and four nonplant taxa before outcome. Each taxon required all three M scores for recovery; unavailable M values remained in the taxon/lane denominator.

### Data exclusions and missingness

No controlled-truth process combination or seed was excluded after unfavorable outcome.

No real positive-control taxon was removed after outcome. All 24 taxon × M pipelines completed technically, but only 21/24 contained at least one prediction-adequate candidate. Missing prediction-adequate comparisons remained missing under the frozen all-three-M rule rather than being converted to an available-case result. Only 17/24 expected-process cells had two-sided adequate comparisons.

### Replication

The principal process-identification replication is a genuinely unused controlled-truth replication: discovery `4201`–`4205`, validation `4301`–`4305`, then unchanged replication `4401`–`4410` (`n=70`).

The three v2.8.4 split seeds are repeated frozen empirical partitions, not independent biological populations. Repeated execution of a consumed real-control workflow is not treated as biological replication. The eight positive controls form one frozen validation panel split into plant and nonplant lanes; their combined 3/8 recovery is descriptive only and is not a pooled replacement endpoint.

### Randomization

Simulation seeds and candidate random states were fixed in contracts. Thresholds calibrated from discovery were not changed after seeds `4301+` were opened. Empirical split seeds and accessible-area conditions were prospectively fixed.

### Blinding / information masking

This study did not involve human-experiment blinding. Scientific information barriers were used instead:

- hidden generating-process truth was unavailable to candidate fitting/selection;
- discovery truth could calibrate thresholds only before fresh validation;
- validation and replication seeds were disjoint from discovery and from each other;
- whole spatial blocks were separated within occurrence-model evaluation;
- v2.8.4 sealed outcomes could not tune the consumed endpoint;
- real positive-control labels and recovery rules were frozen before the final audit and were not relaxed after non-support.

## Statistics

### Exact n reporting

Main text and legends report:

- predecessor factorial falsification: `n=35`;
- fresh counterfactual validation: `n=35`;
- unchanged replication: `n=70`;
- per-process replication denominators: 40 present / 30 absent for each of T/W/S;
- ecological-model disagreement in replication: `n=30`;
- v2.6 exclusion-based necessity validation: nine taxa;
- v2.8.4 primary denominator: three complete seed parts; 108 matched reporting cells;
- real positive controls: eight taxa in two lanes; 24 taxon × M pipelines; 21/24 with an adequate candidate; 17/24 two-sided expected-process comparisons.

### Primary controlled-truth outcomes

Fresh validation: exact recovery **30/35 = 0.857**; temperature sensitivity/specificity **1.000/0.933**; water **1.000/0.800**; soil **1.000/0.933**.

Independent replication: exact recovery **65/70 = 0.929**; temperature **1.000/0.933**; water **1.000/0.933**; soil **0.975/1.000**. Process truth was exact in **27/30** cases where ecological fitted models disagreed.

The same 70 cases are descriptively compared with AUC-selected winner process sets (**56/70 exact**) and the predecessor stable core (**49/70 exact**). Paired counts are 51 both exact, 14 counterfactual-only, 5 AUC-only and 0 both wrong. No universal-superiority endpoint was added post hoc.

### Real positive-control outcome

The frozen taxon rule required all three M scores, mean expected-process score >0 and at least two positive M scores. Each four-taxon lane required >=3/4 recovered taxa and at least one recovery in both temperature and water groups.

Observed:

- plant lane: **2/4**, temperature 2/2, water 0/2;
- nonplant lane: **1/4**, temperature 1/2, water 0/2;
- both lane decisions: **NOT SUPPORTED**;
- temperature overall: 3/4;
- water overall: 0/4.

The positive-only design cannot estimate specificity, a false-positive rate or complete process-identification accuracy. Combined 3/8 is not a replacement primary endpoint.

### Counterfactual score

For each process and frozen perturbation, prediction-adequate candidates are separated into process-containing and process-excluded classes after prospective alias mapping. The controlled-truth score is the normalized difference in best held-out Schoener-D niche overlap between those classes, averaged across perturbations. Frozen thresholds were calibrated only on discovery truth:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

The empirical positive-control implementation used model-pool inner spatial-CV process scores. Outer rows were separated/materialized, but no outer-sealed process-transfer evaluation was invoked for this endpoint.

### Statistical tests and uncertainty

Primary scientific decisions use prospectively frozen absolute recovery gates rather than post hoc P-value thresholds. Descriptive proportions or Wilson intervals do not replace those gates. The positive-control audit does not infer specificity from positive-only labels.

## Software and algorithms

- package: `sdmr` version `0.3.0.dev0`;
- Python >=3.10;
- main libraries: NumPy, pandas, scikit-learn;
- optional geospatial dependencies: rasterio, pyarrow, duckdb;
- counterfactual scorer: `src/sdmr/counterfactual_process_recovery.py`;
- fresh validation: `src/sdmr/counterfactual_process_validation.py`;
- replication: `src/sdmr/counterfactual_process_replication.py`;
- real-control audit: `scripts/audit_real_positive_control_results.py`;
- licence: MIT.

The audit reproduces 96 stored candidate summaries from 284 fold rows, all 48 process × M scores, eight taxon outcomes and both lane decisions without refitting models or changing rules.

## Data collection / sources

Empirical occurrence evidence was tied to the GBIF monthly snapshot dated 1 August 2026, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`. Environmental predictor identities are frozen in repository manifests. Target-group background is an observation/reference frame, not biological absence.

## Ethics

No human participants, human data, vertebrate experiments or newly collected live-animal/plant experimental material are involved. The empirical lanes analyse biodiversity occurrence and environmental records.

## Data/Code availability

Use `docs/product_a_nature_data_code_availability.md`. Before submission, replace branch-only references with a permanent archive DOI for the exact submission state.

## Outcome-neutral safeguards

- predecessor **22/35** non-support remains visible;
- discovery cases are not counted as validation;
- validation/replication seed sets are disjoint and thresholds were frozen before validation;
- no controlled-truth seed/process/candidate/perturbation was dropped after outcome;
- v2.6 necessity and counterfactual membership remain separate estimands;
- v2.8.4 remains `empirical_confirmation_not_supported` / `not_promoted`;
- real positive controls remain plant **2/4**, nonplant **1/4**, water **0/4** under the original all-three-M rule;
- positive-only controls are not used to claim specificity;
- inner-CV positive-control evidence is not described as outer spatial-transfer validation;
- consumed real-control labels cannot become fresh validation after a successor is tuned.
