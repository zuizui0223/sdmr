# Nature Portfolio reporting summary — Product A draft answers

Status: **submission-production aid; copy into the journal's current reporting-summary form at submission**.

## Field

Ecological, evolutionary & environmental sciences.

## Study design

### Research sample / study units

The manuscript contains two evidence lanes with different units and claims.

**Controlled-truth lane:** 60 independently seeded simulation cases, formed by six preregistered niche-generating families × 10 previously unused seeds (`3101`–`3110`). Stable-process-core recovery is evaluated against hidden generating truth. Family-level summaries use n=10 cases per family; pooled summaries use n=60 cases.

**Fresh empirical lane:** 12 prospectively frozen plant taxa evaluated under three split seeds (`2026082201`, `2026082202`, `2026082203`) and three accessible-area/background sensitivity conditions (150, 300 and 500 km). The preregistered primary scientific denominator is three complete seed parts; each part requires all 12 taxa × all three M conditions. The 108 taxon × M × seed matched cells are reporting units for realized ecological-versus-AUC selector identity and are not treated as 108 independent primary decision replicates.

### Sample-size determination

No post-outcome power calculation or adaptive sample-size change was used. Sample sizes and decision denominators were prospectively frozen.

For deterministic known-truth confirmation, the pre-outcome contract fixed six niche families, 10 unused seeds per family and 60 total cases. Scientific non-regression thresholds were frozen before seeds 3101–3110 were opened.

For fresh empirical confirmation, all 12 taxa were required in each of three split-seed parts and all three M specifications were required. The primary denominator was fixed at three parts. No taxon, seed, M condition or denominator was added/dropped after sealed outcome inspection.

### Data exclusions

Taxa were not excluded for unfavorable outcomes. Empirical admission required prospectively defined occurrence/background sufficiency. The original contract required at least 80 admitted occurrences and 50 unique 0.05° cells per species. A taxon could be excluded only by predeclared objective data-sufficiency/background gates, with exclusion retained in the evidence ledger.

Structural or technical unavailability was distinguished from scientific non-support. An earlier presealed feasibility lane stopped before environmental-value reads when frozen spatial-assignment support could not be satisfied; these cases were not reclassified as ecological failures and were not used to alter the final denominator.

### Replication

Known-truth v2.7.2 used two independent computational process replicates of the same 60 prospectively frozen cases to test estimator/process identity. All audited floating and discrete outputs were exactly reproduced, with observed maximum differences 0.0.

The empirical scientific decision was replicated across three prospectively frozen split-seed parts. Each part contained the complete 12-taxon × 3-M design.

### Randomization

Random seeds were explicitly frozen. The deterministic known-truth successor used seeds 3101–3110 for simulation, model `random_state=0`, and selection-process NumPy seed 0. The empirical endpoint used split seeds 2026082201–2026082203, model `random_state=0`, and selection-process NumPy seed 0. Random states/thresholds were not changed after outcomes were inspected.

### Blinding / information masking

The study did not use human-experiment blinding. Instead, scientific information barriers played the analogous role of preventing target leakage:

- whole spatial blocks were assigned to model versus sealed roles before tuning;
- sealed rows could not influence predictor/universe choice, regularization, response complexity, stopping, M/background construction, candidate choice or thresholds;
- unseen validation taxa did not participate in discovery procedure selection;
- known-truth hidden generating labels were not used during model/procedure selection;
- validation truth could not create missing discovery calibration support;
- sealed empirical outcomes could not tune candidates, thresholds, seeds, fraction, M or denominator.

## Statistics

### Exact n reporting

Main/figure legends report:

- controlled truth: six families, n=10 cases each, n=60 total;
- observation correction: 10 observation-confounded and 50 other cases;
- empirical primary denominator: n=3 seed parts;
- empirical composition: 12 taxa × 3 M conditions in every part;
- selector-identity audit: 108 matched taxon × M × seed cells.

### Statistical tests

The principal results are contract-based recovery/decision metrics rather than null-hypothesis significance tests. Known-truth outcomes are precision, recall, F1, coverage and consensus proportions evaluated against literal hidden generating truth under preregistered thresholds. Empirical confirmation uses frozen guardrail/nondomination/strict-improvement criteria across the three-part denominator. No post hoc P-value threshold or multiple-testing search was used to promote Product A.

### Error bars / uncertainty

Where plotted, family-level values summarize the 10 independently seeded known-truth cases per family. The current main Figure 3 emphasizes exact family means and case counts; if uncertainty intervals are added for visualization they must be explicitly described as reporting summaries and must not create new scientific thresholds.

Set-valued process/boundary outputs are not confidence intervals unless explicitly stated. Product-A certificates retain possible/substitutable and unresolved states; between-model spread is not interpreted as a complete confidence interval.

## Software and algorithms

- package: `sdmr` version `0.3.0.dev0`;
- language: Python >=3.10;
- main libraries: NumPy, pandas, scikit-learn;
- optional: rasterio, pyarrow, duckdb;
- model solver in deterministic successor: scikit-learn `liblinear`;
- model random state: 0 in v2.7.2 and final empirical successor;
- selection NumPy seed: 0;
- code license: MIT.

A software-submission checklist should accompany the paper because newly developed code is central to the claims.

## Data collection / sources

Empirical occurrence evidence was tied to the GBIF monthly snapshot dated 2026-08-01, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`. Environmental predictor sources/identities are frozen in the repository manifest and exact workflow receipts. Target-group background comes from Plantae records in the same occurrence snapshot and is treated as an observation/reference frame, not biological absence.

## Ethics

No human participants, human data, vertebrate experiments or newly collected live-animal/plant experimental material are involved in Product A. The empirical lane analyses biodiversity occurrence/environmental records.

## Data/Code availability

Use the final text in `docs/product_a_nature_data_code_availability.md`. Before submission, replace branch-only references with a permanent archive DOI for the exact submission code/source-data state.

## Outcome-neutral safeguards to emphasize

- non-promotion was permitted prospectively;
- thresholds were not relaxed after adverse/unavailable outcomes;
- unavailable, technical STOP, scientific non-support and non-promotion are separate states;
- v2.7.1 nondeterminism was retained as a failed predecessor and not repaired by tolerance widening;
- v2.8.4 `empirical_confirmation_not_supported` and `not_promoted` remain authoritative;
- no v2.9 or favorable-panel search is authorized.