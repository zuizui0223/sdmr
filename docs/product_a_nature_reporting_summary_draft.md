# Nature Portfolio reporting summary — Product A draft answers

Status: **submission-production aid; copy into the journal's current reporting-summary form at submission**.

## Field

Ecological, evolutionary & environmental sciences.

## Study design

### Research samples and inferential units

The manuscript contains controlled-truth and fresh empirical evidence, and the controlled-truth evidence itself contains two distinct process-level estimands.

**Exclusion-based necessity evidence:** the v2.4–v2.6 branch tests whether an adequate explanation survives after declared information for a process is removed. The complete v2.6 validation contains three panels and nine validation taxa. Its headline quantities are false-required process counts, possible-process recall/precision, boundary coverage and interval width. Under the frozen v2.6 criterion, false-required processes were zero and possible-process recall was 1.0 in every panel, while possible-process precision was 0.467.

**Consensus-first process-stability evidence:** v2.7.2 contains 60 independently seeded simulation cases, formed by six preregistered niche-generating families × 10 previously unused seeds (`3101`–`3110`). Its `stable_process_core` is the intersection of process sets supported by canonical and perturbation-robust ecological selectors. Hidden generating truth is used only after that certificate exists. Stable-core precision/recall/F1 and process-set versus exact-model consensus are evaluated on these 60 cases. These quantities are not measurements of the exclusion-based necessity set.

**Fresh empirical evidence:** 12 prospectively frozen plant taxa were evaluated under three split seeds (`2026082201`, `2026082202`, `2026082203`) and three accessible-area/background sensitivity conditions (150, 300 and 500 km). The preregistered primary scientific denominator is three complete seed parts; each part requires all 12 taxa × all three M conditions. The 108 taxon × M × seed matched cells are reporting units for realized ecological-versus-AUC selector identity and are not 108 independent primary decision replicates.

### Sample-size determination

No post-outcome power calculation or adaptive sample-size change was used. Sample sizes and decision denominators were prospectively frozen.

For v2.6, calibration-support requirements and the validation panels/taxa were frozen before validation truth was opened. For deterministic v2.7.2 confirmation, the pre-outcome contract fixed six niche families, 10 unused seeds per family and 60 total cases, with non-regression thresholds frozen before seeds 3101–3110 were opened. For fresh empirical confirmation, all 12 taxa and all three M specifications were required in each of three split-seed parts. No taxon, seed, M condition or denominator was added or dropped after sealed outcome inspection.

### Data exclusions

Taxa were not excluded for unfavorable outcomes. Empirical admission required prospectively defined occurrence/background sufficiency; the original contract required at least 80 admitted occurrences and 50 unique 0.05° cells per species. A taxon could be excluded only by predeclared objective data-sufficiency/background gates, with the exclusion retained in the evidence ledger.

Structural or technical unavailability was distinguished from scientific non-support. Presealed feasibility failures before environmental-value reads were not reclassified as ecological failures and did not alter the final denominator.

### Replication

v2.7.2 used two independent computational process replicates of the same 60 prospectively frozen cases to test estimator/process identity. All audited floating and discrete outputs were exactly reproduced, with observed maximum absolute and relative differences 0.0.

The empirical scientific decision was replicated across three prospectively frozen split-seed parts, each containing the complete 12-taxon × 3-M design.

### Randomization

Random seeds were explicitly frozen. The deterministic known-truth successor used seeds 3101–3110 for simulation, model `random_state=0`, and selection-process NumPy seed 0. The empirical endpoint used split seeds 2026082201–2026082203, model `random_state=0`, and selection-process NumPy seed 0. Random states and scientific thresholds were not changed after outcomes were inspected.

### Blinding / information masking

The study did not use human-experiment blinding. Scientific information barriers prevented target leakage:

- whole spatial blocks were assigned to model versus sealed roles before tuning;
- sealed rows could not influence predictor/universe choice, regularization, response complexity, stopping, M/background construction, candidate choice or thresholds;
- unseen validation taxa did not participate in discovery procedure selection;
- hidden generating labels were not used during model/procedure selection;
- validation truth could not create missing discovery calibration support;
- sealed empirical outcomes could not tune candidates, thresholds, seeds, fraction, M or denominator.

## Statistics

### Exact n reporting

Main text and legends report:

- exclusion-based v2.6 validation: three panels, nine validation taxa;
- consensus-first v2.7.2 controlled truth: six families, n=10 cases each, n=60 total;
- observation correction: 10 observation-confounded and 50 other cases;
- empirical primary denominator: n=3 seed parts;
- empirical composition: 12 taxa × 3 M conditions in every part;
- selector-identity audit: 108 matched taxon × M × seed cells.

### Statistical tests and metrics

The principal results are contract-based recovery/decision metrics rather than null-hypothesis significance tests.

For exclusion-based necessity, outcomes include false-required counts, possible-process recall/precision, boundary coverage and interval width. For consensus-first process stability, stable-core precision, recall and F1 are calculated against literal hidden generating truth after certificate construction, and process-set/exact-model consensus are case-level binary outcomes. The two metric families refer to different estimands and are not compared as successive precision estimates of one procedure.

Empirical confirmation uses frozen prediction-guardrail, nondomination and strict-improvement criteria across the three-part denominator. No post hoc P-value threshold or multiple-testing search was used to promote Product A.

### Error bars / uncertainty

Where plotted, v2.7.2 family-level values summarize 10 independently seeded cases per family. Any added visualization interval must be described as a reporting summary and cannot create a new scientific threshold.

Set-valued exclusion/process-boundary outputs are not confidence intervals unless explicitly stated. Broad possible-process sets and `unresolved` states are retained as inferential outcomes; between-model spread is not treated as a complete confidence interval.

## Software and algorithms

- package: `sdmr` version `0.3.0.dev0`;
- language: Python >=3.10;
- main libraries: NumPy, pandas, scikit-learn;
- optional: rasterio, pyarrow, duckdb;
- deterministic successor solver: scikit-learn `liblinear`;
- model random state: 0 in v2.7.2 and final empirical successor;
- selection NumPy seed: 0;
- license: MIT.

Newly developed software is central to the claims; a software-submission checklist accompanies the manuscript package.

## Data collection / sources

Empirical occurrence evidence was tied to the GBIF monthly snapshot dated 2026-08-01, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`. Environmental predictor identities are frozen in the repository manifest and workflow receipts. Target-group background comes from Plantae records in the same occurrence snapshot and is treated as an observation/reference frame, not biological absence.

## Ethics

No human participants, human data, vertebrate experiments or newly collected live-animal/plant experimental material are involved. The empirical lane analyses biodiversity occurrence/environmental records.

## Data/Code availability

Use `docs/product_a_nature_data_code_availability.md`. Before submission, replace branch-only references with a permanent archive DOI for the exact submission code/source-data state.

## Outcome-neutral safeguards

- non-promotion was permitted prospectively;
- thresholds were not relaxed after adverse or unavailable outcomes;
- unavailable, technical STOP, scientific non-support and non-promotion remain separate states;
- v2.7.1 nondeterminism was retained as a failed predecessor and not repaired by tolerance widening;
- v2.6 broad exclusion uncertainty was retained rather than post-hoc sharpened;
- v2.7.2 stable-core P/R is not relabelled as necessity performance;
- v2.8.4 `empirical_confirmation_not_supported` and `not_promoted` remain authoritative;
- no v2.9 or favorable-panel search is authorized.