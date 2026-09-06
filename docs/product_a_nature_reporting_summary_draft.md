# Nature Portfolio reporting summary — Product A draft answers

Status: **submission-production aid; copy into the journal's current reporting-summary form at submission**.

## Field

Ecological, evolutionary & environmental sciences.

## Study design

### Research samples and inferential units

The manuscript contains controlled-truth method development, controlled-truth fresh validation/replication and a separately frozen empirical plant endpoint.

**Factorial discovery/falsification:** temperature, water and soil were varied over all seven non-empty process combinations. Seeds `4201`–`4205` produced 35 process-set cases. This lane falsified the predecessor stable-process intersection and was then used only to calibrate process-specific counterfactual thresholds.

**Fresh counterfactual validation:** unused seeds `4301`–`4305` across the same seven process sets produced 35 independent validation cases. The primary gate required the full denominator, exact complete process-set recovery ≥0.80, and sensitivity and specificity ≥0.80 separately for temperature, water and soil.

**Independent replication:** after validation, the counterfactual estimator and all thresholds were frozen unchanged. Seeds `4401`–`4410` across the seven process sets produced 70 independent replication cases. Each process was true in 40 cases and false in 30. The same absolute support gates were applied.

**Exclusion-based necessity evidence:** the earlier v2.4–v2.6 branch is a separate estimand. Its complete validation contains three panels and nine validation taxa. It evaluates false-required counts, possible-process recall/precision and process-boundary coverage rather than counterfactual process-membership accuracy.

**Fresh empirical evidence:** 12 prospectively frozen plant taxa were evaluated under three split seeds (`2026082201`, `2026082202`, `2026082203`) and three accessible-area/background conditions (150, 300 and 500 km). The primary empirical denominator is three complete seed parts. The 108 taxon × M × seed matched cells are reporting units for realized ecological-versus-AUC selector identity, not independent primary decision replicates.

### Sample-size determination

No post-outcome power calculation or adaptive sample-size change was used.

The factorial discovery denominator was prospectively fixed at seven process combinations × five seeds = 35 cases. The fresh validation used a disjoint five-seed set with the same seven combinations = 35 cases. After validation succeeded, the replication contract fixed ten new unused seeds × seven combinations = 70 cases before replication outcomes were opened.

No seed, process set, candidate, perturbation or threshold was dropped after validation or replication outcomes. The empirical endpoint separately required all 12 taxa and all three M specifications in each of three split-seed parts.

### Data exclusions

No controlled-truth process combination or seed was excluded for an unfavorable outcome. Robust-selector unavailability, where present, remained part of the predecessor reporting rather than causing case removal from the counterfactual denominator.

Empirical taxa were not excluded for unfavorable outcomes. Empirical admission depended only on prospectively defined occurrence/background sufficiency. Structural or technical unavailability was distinguished from scientific non-support.

### Replication

The principal process-identification replication is a genuinely unused controlled-truth replication: the counterfactual rule calibrated on `4201`–`4205`, validated on `4301`–`4305`, and was then applied **unchanged** to `4401`–`4410` (`n=70`). `method_changed_after_4301_4305_validation=false` is recorded in the replication decision.

The empirical scientific decision was separately replicated across three prospectively frozen split-seed parts.

### Randomization

Simulation seeds were explicitly frozen in contracts before the corresponding validation/replication outcomes. Candidate model random states were fixed. Thresholds calibrated from the discovery lane were not changed after seeds `4301+` were opened.

### Blinding / information masking

The study did not use human-experiment blinding. Scientific information barriers prevented target leakage:

- hidden generating process labels were not inputs to model fitting or candidate selection;
- discovery truth could calibrate counterfactual thresholds only before fresh validation;
- validation seeds `4301`–`4305` were disjoint from discovery seeds;
- replication seeds `4401`–`4410` were disjoint from discovery and validation;
- thresholds, process sets, candidate library and perturbations were frozen before validation and remained unchanged for replication;
- whole spatial blocks were separated within occurrence-model evaluation;
- sealed empirical outcomes could not tune the consumed v2.8.4 endpoint.

## Statistics

### Exact n reporting

Main text and legends report:

- factorial predecessor falsification: `n=35`;
- fresh counterfactual validation: `n=35`;
- independent unchanged counterfactual replication: `n=70`;
- per-process replication truth denominators: 40 process-present and 30 process-absent cases for each of temperature, water and soil;
- replication ecological-model disagreement cases: `n=30`;
- exclusion-based v2.6 validation: three panels, nine validation taxa;
- empirical primary denominator: `n=3` seed parts;
- empirical selector-identity audit: 108 matched taxon × M × seed cells.

### Primary outcomes

The counterfactual process-membership primary outcomes are:

1. exact equality between the complete predicted process set and hidden generating-process set;
2. sensitivity and specificity separately for temperature, water and soil;
3. complete denominator.

Fresh validation results: exact recovery **30/35 = 0.857**; temperature sensitivity/specificity **1.000/0.933**; water **1.000/0.800**; soil **1.000/0.933**.

Independent replication results: exact recovery **65/70 = 0.929**; temperature **1.000/0.933**; water **1.000/0.933**; soil **0.975/1.000**. Process truth was exact in **27/30** cases where the canonical and robust ecological fitted models disagreed.

The same 70 cases are descriptively compared with AUC-selected winner process sets (**56/70 exact**) and the predecessor stable core (**49/70 exact**). The paired counterfactual-versus-AUC exact counts are 51 both exact, 14 counterfactual-only exact, 5 AUC-only exact and 0 both wrong. No new post-outcome universal-superiority threshold was introduced for this paired comparison.

### Counterfactual score

For each process and each of five predeclared sampling/background perturbations, prediction-adequate candidates are separated into process-containing and process-excluded classes after frozen process-alias mapping. The score is the normalized difference between the maximum held-out Schoener-D niche overlap attainable in these two classes. Case score is the arithmetic mean across perturbations.

Frozen process thresholds were calibrated only on discovery truth and fixed before validation:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

### Statistical tests and uncertainty

The principal scientific decisions use prospectively frozen absolute recovery gates rather than null-hypothesis P-value thresholds. Descriptive proportions and optional Wilson intervals may be reported, but these do not replace the frozen gates.

For exclusion-based necessity, outcomes remain false-required counts, possible-process recall/precision and boundary coverage. These are not merged with counterfactual process-membership accuracy.

Empirical confirmation retains its frozen prediction-guardrail, nondomination and strict-improvement criteria across the three-part denominator. No post hoc P-value threshold was used to promote Product A.

## Software and algorithms

- package: `sdmr` version `0.3.0.dev0`;
- language: Python ≥3.10;
- main libraries: NumPy, pandas, scikit-learn;
- optional geospatial dependencies: rasterio, pyarrow, duckdb;
- counterfactual scorer: `src/sdmr/counterfactual_process_recovery.py`;
- fresh validation: `src/sdmr/counterfactual_process_validation.py`;
- independent replication: `src/sdmr/counterfactual_process_replication.py`;
- license: MIT.

Newly developed software is central to the claims; a software-submission checklist accompanies the manuscript package.

## Data collection / sources

Empirical occurrence evidence was tied to the GBIF monthly snapshot dated 2026-08-01, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`. Environmental predictor identities are frozen in the repository manifest and workflow receipts. Target-group background is treated as an observation/reference frame, not biological absence.

## Ethics

No human participants, human data, vertebrate experiments or newly collected live-animal/plant experimental material are involved. The empirical lane analyses biodiversity occurrence/environmental records.

## Data/Code availability

Use `docs/product_a_nature_data_code_availability.md`. Before submission, replace branch-only references with a permanent archive DOI for the exact submission code/source-data state.

## Outcome-neutral safeguards

- the factorial predecessor result **22/35** remains an explicit scientific non-support;
- discovery cases are not counted as validation cases;
- validation and replication use disjoint unused seed sets;
- counterfactual thresholds were frozen before fresh validation and not changed afterward;
- no seed, process-set, candidate or perturbation was dropped after outcome;
- the unchanged 70-case replication is reported independently from the 35-case validation;
- exclusion-based necessity and counterfactual process membership remain distinct estimands;
- v2.8.4 `empirical_confirmation_not_supported` and `not_promoted` remain authoritative;
- new controlled-truth success does not convert the empirical endpoint into process-truth confirmation.
