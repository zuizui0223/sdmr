# Nature Extended Data and source-data plan — Product A

Status: **reporting/production plan only; scientific endpoints unchanged**.

Nature Ecology & Evolution permits up to 10 Extended Data items for Articles. The main text should carry only the four inferential figures. Everything needed to audit prospective design, calibration, computational identity and endpoint provenance moves here.

## Main display items

### Figure 1 — Prediction is not identification

Purpose: establish the inferential distinction, not software history.

Panels:

- conceptual separation of predictive adequacy, functional/environmental recovery and process-information necessity;
- protected information flow: model pool → frozen candidate/procedure → sealed answer-check;
- compact controlled-truth counterexample from the early single-winner/stability line showing that acceptable predictive/environmental recovery can coexist with incorrect generating-process attribution.

No version-number timeline in the figure body. Version provenance belongs in the legend/Extended Data.

### Figure 2 — Ecological sharpening can create false necessity

Purpose: show the methodological discovery.

Panels:

- complete adequate candidate set;
- ecological Pareto pruning;
- narrower retained spread but lost truth coverage / false necessary core;
- falsification-first replacement: exclude declared process information, retain `required`, `refuted_as_necessary` and `unresolved` states.

The visual claim is `agreement among retained good models ≠ biological necessity`.

### Figure 3 — Falsification-first identification is safe and sharp under controlled truth

Source: frozen v2.7.2 artifact `9490817718` plus terminal decision `9490827277`.

Panels:

A. stable-core precision and recall for six niche families;
B. process-set consensus versus exact-model consensus by family;
C. compact annotation: independent-process numeric/discrete max difference = 0.0;
D. observation correction specificity: 10/10 activation in observation-confounded, 0/50 elsewhere.

Source-data assertions are implemented in `scripts/build_nature_product_a_figures.py`.

### Figure 4 — Fresh empirical occurrence data reveal selector collapse

Source: frozen v2.8.4 finalized seed artifacts and terminal artifact `9750071472`.

Panels:

A. ecological versus AUC sealed presence-rank identity for all 108 matched cells;
B. candidate identity = 108/108; selected-predictor identity = 108/108;
C. common candidate `all|logit_l2_C0.1_degree1_rs0`;
D. formal endpoint summary: prediction guardrail pass; nondominated 3/3; strict improvement 0/3; `empirical_confirmation_not_supported`; `not_promoted`.

The legend must explicitly state that 108 taxon × M × seed cells are reporting units for realized selector identity and do not replace the preregistered three-part scientific denominator.

## Extended Data

### Extended Data Fig. 1 — Full prospective information barrier

Show:

- GBIF/source freeze;
- deterministic thinning/admission;
- spatial-block model/sealed assignment;
- M/background from model-pool occurrences only;
- complete focal-panel exclusion from target-group source;
- discovery/unseen-taxon barrier;
- sealed opening only after candidate/procedure freeze;
- separate promotion gate.

This figure establishes that the later falsification sequence was possible without post-outcome rescue.

### Extended Data Fig. 2 — Candidate space and ecological audit dimensions

Summarize:

- 43-predictor active environmental manifest;
- `bioclim19`, `chelsa_bioclim`, `active_all` universes;
- all/VIF/predictive and ecological-recovery strategies;
- regularization/response complexity;
- M = 150/300/500 km as sensitivity;
- prediction metrics versus ecological recovery targets.

Make clear that AUC, Boyce/CBI, OR10 and AICc are comparators/diagnostics rather than the ecological answer key.

### Extended Data Fig. 3 — v2.3 anti-conservative certificate result

Show each controlled-truth panel:

- complete-adequate coverage;
- Pareto certificate sharpness;
- false necessary-process count;
- lost process/boundary coverage.

This is the quantitative support for Figure 2.

### Extended Data Fig. 4 — Calibration and abstention sequence

Show v2.4 → v2.5 → v2.6:

- v2.4 process certificates complete but boundary product 18/21 response keys;
- v2.5 minimum calibration support retained and validation unopened;
- v2.6 complete process/boundary certificates, false-required = 0, possible-process recall = 1.0;
- panel boundary coverage 0.762, 0.762, 0.857 versus 0.381, 0.333, 0.381 complete-adequate;
- possible-process precision 0.467 and width ratios approximately 3.05, 1.44, 1.35.

This figure demonstrates that `unavailable` is a protected state rather than a euphemism for negative performance.

### Extended Data Fig. 5 — Computational nondeterminism as a scientific failure

Show the v2.7.1 one-row discrete difference:

- reference predictors: `ngd5,bio2,bio16,bio6,ngd10,scd,rsds`;
- independent process: `ngd5,bio2,bio16,bio6,ngd10,scd`;
- frozen `liblinear` solver with historical `random_state=None`;
- sealed environmental values not read;
- successor fixed model and selection RNG to 0 before new known truth.

This supports treating computational identity as part of the estimator when selection is discrete.

### Extended Data Fig. 6 — v2.7.2 exact determinism tables

Report output families, rows/floating cells and observed max differences:

- candidate fold metrics: 7,140 rows / 173,880 floating cells / 0.0;
- ecological inference certificates: 60 / 360 / 0.0;
- observation signal summary: 420 / 2,100 / 0.0;
- selector choices: 180 / 540 / 0.0;
- selector truth summary: 3 / 42 / 0.0;
- truth evaluation: 180 / 5,220 / 0.0.

### Extended Data Fig. 7 — Structural availability before ecological evidence

Use the v2.7.3 coordinate-only presealed feasibility result:

- 6 seed/fraction conditions;
- 4 available;
- two 0.30-fraction conditions unavailable because no evidence-balanced spatial assignment met frozen support constraints after 32 attempts;
- environmental values, candidate scores and sealed ecological outcomes not read.

This distinguishes structural availability from ecological performance.

### Extended Data Fig. 8 — Fresh empirical full-denominator composition

For each of three seeds show:

- 12 taxa;
- M = 150/300/500 km;
- 36 taxon × M cells;
- two reported selection roles per cell;
- complete sealed metric availability.

Total matched selector-identity cells = 108.

### Extended Data Fig. 9 — Empirical metric identity

For all 108 matched ecological/AUC pairs, demonstrate identity for:

- presence rank;
- continuous Boyce;
- OR10;
- Schoener-D overlap;
- centroid distance;
- breadth error;
- quantile-profile error.

This should be a compact difference-from-zero panel rather than seven redundant scatterplots.

### Extended Data Fig. 10 — Evidence-state taxonomy and immutable provenance

Four distinct outcome classes:

1. `supported` / `not supported` — scientific decision under complete evidence;
2. `unavailable` — requested estimand cannot be formed under frozen evidence requirements;
3. `technical STOP` — execution failed before scientific evidence was opened/completed;
4. `not promoted` — separate governance decision after a scientific endpoint.

Alongside these, list exact terminal run/artifact IDs and digests for v2.6, v2.7.2 and v2.8.4.

## Source Data files

The submission package should include or generate:

- `Source Data Fig. 3`: six-family recovery and consensus table derived from `ecological_inference_certificates.csv`;
- `Source Data Fig. 4`: 108 matched empirical selector rows with candidate identity and sealed presence rank;
- Extended Data source tables for v2.3, v2.6 and v2.7.2 determinism;
- machine-readable v2.8.4 terminal evidence table already present in the repository.

No source-data file may contain a post hoc threshold, newly selected taxon subset or replacement denominator.

## Legends: mandatory wording boundaries

- `process` means a declared ecological process group under the frozen registry, not a fully established causal mechanism;
- `necessary` means necessary under the declared evidence/representation contract;
- known-truth families are simulation structures, not empirical ecosystem categories;
- v2.8.4 taxon × M × seed cells are not independent scientific replicates for the primary promotion decision;
- empirical selector identity does not demonstrate that AUC is an ecological truth criterion;
- Product B universal-driver claims remain outside this manuscript.