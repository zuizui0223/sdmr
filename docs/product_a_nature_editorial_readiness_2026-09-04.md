# Nature Ecology & Evolution editorial-readiness gate — 2026-09-04

Status: **submission-production assessment; no new Product-A science**.

## Current recommendation

**Proceed toward a first-shot Nature Ecology & Evolution Article submission.**

This is a high-risk editorial challenge, not the highest-probability acceptance route. The evidence is now strong enough that the journal fit should be decided by editors rather than pre-emptively downgraded to a specialist methods journal. The manuscript must remain framed as a general ecological inference result, not an SDM software benchmark.

## Gate 1 — Is the central advance broader than one algorithm or taxon panel?

**PASS, with wording constraint.**

The central claim is not that SDMR predicts better. It is that predictive/functional model selection and process-information necessity are different inferential objects when multiple environmental representations remain adequate. The controlled-truth false-necessity result and falsification-first replacement do not depend conceptually on one MaxEnt-style algorithm.

Constraint: do not claim that all observational ecological models share the exact empirical failure observed in the 12 plant taxa. Generality is conceptual and controlled-truth-supported; empirical scope remains bounded.

## Gate 2 — Is there a result beyond the already known `prediction ≠ explanation` literature?

**PASS.**

Direct prior art already establishes that discrimination accuracy may not recover functional environmental responses. Product A goes further in two steps:

1. selection on **ecological-recovery** criteria can still create a false necessary-process core;
2. process-information necessity is then made a falsification target by excluding declared process information and retaining unresolved states when evidence is insufficient.

This is now explicitly separated from Warren et al. (2020), ENMeval, collinearity studies and Rashomon/model-class variable-importance work in `docs/product_a_nature_reference_boundary.md`.

## Gate 3 — Is the positive result strong enough?

**PASS for controlled truth.**

Frozen v2.7.2 evidence:

- 60 unused cases;
- six preregistered niche families;
- stable-core precision 0.9889;
- recall/F1 0.9833;
- four of six families with mean precision and recall 1.0;
- exact-model consensus 38/60 versus process-set consensus 50/60;
- observation correction 10/10 in confounded cases, 0/50 elsewhere;
- exact independent-process equality for all audited discrete/floating outputs, observed max difference 0.0.

This supports `identification is possible under controlled truth`; it does not support direct empirical truth recovery.

## Gate 4 — Does the empirical lane add information rather than merely fail?

**PASS after frozen-artifact audit, but it remains the main editorial vulnerability.**

Formal endpoint:

- complete 3/3 denominator;
- prediction guardrail passed;
- ecological nondomination 3/3;
- strict ecological improvement 0/3;
- `empirical_confirmation_not_supported`;
- separate `not_promoted`.

Reporting-only full-denominator audit:

- ecological candidate = AUC candidate in 108/108 matched taxon × M × seed cells;
- selected predictors identical in 108/108;
- one candidate identity across every cell: `all|logit_l2_C0.1_degree1_rs0`.

Therefore the empirical result is not a hidden unfavorable comparison between different fitted models. It demonstrates an observational-equivalence limit: the two selection objectives did not instantiate different models on this corpus.

Editorial vulnerability: there is still no empirical case in this paper where the proposed identification framework changes a biological conclusion relative to a conventional selector.

## Gate 5 — Are claim boundaries sufficiently strict for Nature-level scrutiny?

**PASS after current revision.**

The manuscript now distinguishes:

- process-information necessity under a declared representation/evidence system from causal mechanism;
- controlled-truth process recovery from empirical process truth;
- formal empirical superiority `tested and not supported` from the uninstantiated empirical disagreement contrast;
- process exclusion under the declared registry from a future complete proxy-closure test;
- taxon × M × seed reporting rows from the three-part primary empirical denominator.

## Gate 6 — Is the manuscript in the journal's Article format?

**PARTIAL → production only.**

Current status:

- abstract = 183 words, below the 200-word limit;
- Nature-style Article draft exists;
- Introduction is unheaded in the revised draft;
- Results use topical subheadings;
- Discussion has no topical subheadings;
- four main figures planned, below the six-display-item limit;
- Online Methods drafted;
- Extended Data plan contains 10 items;
- cover letter drafted;
- verified literature boundary drafted;
- Data/Code Availability drafted;
- `CITATION.cff` added.

Remaining: verify final main-text word count after references/figure citations are integrated and keep it ≤3,500 words.

## Gate 7 — Can an editor understand the manuscript in 30 seconds?

**PASS if the submission package uses the current title/abstract/Fig. 1.**

Title:

**Predictive success does not identify ecological necessity in species distribution models**

30-second argument:

1. previous work shows prediction may not recover ecological response functions;
2. we show even ecologically better recovered model subsets can create false necessity;
3. necessity must therefore be tested by falsification against adequate alternatives;
4. that target is recovered with ~0.99 precision / ~0.98 recall under fresh controlled truth;
5. fresh plant data reveal a different identification limit because ecological and AUC objectives collapse to the same model in 108/108 cells.

## Gate 8 — What would trigger a Nature Communications transfer?

Transfer without new Product-A data if the Nature Ecology & Evolution rejection is primarily:

- insufficient broad ecological interest;
- too methodological/specialized;
- absence of a changed empirical biological conclusion;
- preference for a specialist readership despite sound evidence.

Do **not** generate a favorable new taxon panel to answer those editorial objections. The correct fallback ladder remains Nature Communications → Methods in Ecology and Evolution.

## Submission-production tasks still open

### Required before first-shot submission

1. Render and visually QA four main figures from frozen source data.
2. Produce source-data CSVs for main and Extended Data figures.
3. Complete the final numbered reference list and insert citations into the manuscript.
4. Run exact word-count/format QA against the final Article file.
5. Archive the exact submission branch/code/source-data state with a permanent DOI.
6. Complete Nature Portfolio reporting summary and software submission checklist.
7. Add final author affiliations, contributions, competing interests, acknowledgements and corresponding-author details.

### Not required / prohibited

- no v2.9;
- no new Product-A scientific test;
- no search for taxa that force ecological/AUC selector divergence;
- no threshold or candidate-library change;
- no retroactive proxy-closure empirical analysis;
- no Product-B result inserted into this manuscript.

## Editorial decision

**Nature Ecology & Evolution: challenge submission justified once the seven production tasks above are complete.**

The most likely desk-rejection argument is not technical weakness but insufficient empirical biological consequence. The strongest defense is not to overclaim; it is to show that the prospective sequence changes the inferential standard itself: predictive adequacy and ecological recovery are not proofs of process necessity, and even empirical comparison can become unidentified when alternative objectives select the same model.