# Product A final claim spine

Status: **authoritative manuscript logic for Product A reporting; scientific endpoints unchanged**

## One-sentence claim

**Under controlled truth, process-level ecological information can be recovered even when exact species-distribution models disagree, while necessity and unresolved evidence require separate tests rather than being inferred from a winner.**

## What Product A started by asking

Product A began as a conventional SDM procedure-selection problem: choose one complete model-building procedure that transfers to sealed spatial blocks and unseen taxa. From the beginning, information barriers were protected: sealed blocks could not influence fitting or tuning, unseen taxa could not influence procedure selection, accessible-area assumptions were sensitivity conditions rather than optimized outcomes, and failure to promote a procedure was an admissible scientific result.

The development sequence then showed that the original winner-selection estimand was too weak for ecological interpretation.

## Result 1 — Prediction and stable response surfaces do not identify process truth

Controlled-truth tests showed that a procedure can recover withheld occurrence environments or produce stable response surfaces while attributing the pattern to the wrong generating environmental process. Therefore:

`prediction adequacy / response stability != process identification`

Prediction remains an adequacy layer, not a proof of ecological necessity.

## Result 2 — Agreement among selected good models does not establish necessity

Replacing one winner with a set of ecologically adequate models did not solve the problem. Pareto pruning made the retained set sharper but could remove viable alternatives, lose truth or boundary coverage and create a false necessary-process core. Therefore:

`agreement among performance-filtered models != ecological necessity`

The main lesson is not that one predictive metric is wrong; the inferential error is to convert conditional agreement after model filtering into biological necessity.

## Branch A — Necessity is a falsification problem, but this branch did not positively discover a driver

The necessity branch is the v2.4–v2.6 process-exclusion sequence.

A process-level necessity claim is challenged by prospectively excluding the declared information associated with that process and asking whether an adequate ecological explanation still survives. Outcomes distinguish `required_by_frozen_evidence_contract`, `refuted_as_necessary` and `unresolved`; evidence insufficiency is not converted into absence.

The complete calibrated controlled-truth validation at v2.6 returned:

- possible-process recall = **1.000**;
- false-required processes = **0**;
- complete process and boundary certificates for all validation taxa;
- possible-process precision approximately **0.467**;
- `required_processes` empty in **9/9** validation taxa.

Interpretation: exclusion-based inference controlled false necessity and retained true processes, but it did **not** positively isolate a required ecological driver in these panels. This is a necessity-safety result.

## Branch B — Complete generating-process sets were recovered despite model disagreement

The positive process-identification result comes from the separate v2.7.1–v2.7.2 consensus-first sequence.

The v2.7.2 `stable_process_core` is the intersection of process sets supported by two independently defined ecological selectors: canonical niche recovery and perturbation-robust niche recovery. It is **not** the process-exclusion necessary-process set.

Across 60 unused known-truth cases from six niche families:

- stable process core exactly equalled the complete hidden generating-process set in **55/60 cases (91.7%)**;
- canonical selector process sets were exact in **52/60**;
- robust selector process sets were exact in **54/60**;
- the two selectors chose different fitted candidates in **22/60** cases;
- within those model-disagreement cases, the stable process core still exactly matched hidden process truth in **19/22 (86.4%)**;
- pooled stable-core precision = **0.9889** and recall/F1 = **0.9833**;
- exact fitted-model consensus = **38/60**;
- process-set consensus = **50/60**;
- independent-process numerical differences = **0.0**.

This answers a concrete question: **what was identified?** In most unused controlled-truth cases, the complete generating process set itself was recovered, even when the fitted model identities differed.

### The selective identification test was soil

The frozen process registry contained `temperature`, `water` and `soil`.

Temperature and water were generating in **all 60 cases** and stable in all 60. They therefore demonstrate retention of invariant true processes, not presence-versus-absence discrimination.

Soil truth varied and supplied the real selective test:

- soil truly generating: 10 cases → stable **7**, contested **3**, absent from both selectors **0**;
- soil non-generating: 50 cases → incorrectly stable **2**, contested **7**, absent from both selectors **41**.

Thus all 10 true-soil cases remained visible in the set-valued certificate; seven were stable and three were explicitly uncertain rather than silently lost. Only two of 50 non-generating soil cases were incorrectly promoted to stable.

All five exact process-set errors were soil errors:

- omitted-driver: three true-soil cases downgraded to contested;
- soft-threshold: two false-soil cases retained as stable.

This is the current failure envelope and must be reported alongside the positive result.

## Worked positive example

`asymmetric`, seed `3103`:

- canonical fitted candidate: `climate_soil_quadratic`;
- canonical processes: `{soil, temperature, water}`;
- robust fitted candidate: `tw_quadratic`;
- robust processes: `{temperature, water}`;
- stable process core: `{temperature, water}`;
- contested: `{soil}`;
- hidden generating truth: `{temperature, water}`.

The models disagree; the process certificate does not. It removes selector-specific soil from the stable claim and returns the complete generating process set correctly.

## Result 3 — Unresolved evidence is a scientific state

Across the development sequence, `not_supported`, `unavailable`, `unresolved` and technical failure were kept distinct. Calibration insufficiency, structurally infeasible spatial partitions and runtime failure before sealed ecological evidence were not reinterpreted as ecological negatives.

The framework therefore preserves at least these distinct evidential roles:

- required under the frozen evidence contract;
- refuted as necessary;
- possible / substitutable;
- contested;
- unresolved / unavailable.

## Result 4 — Fresh occurrence data exposed observational equivalence

The final fresh empirical endpoint tested a narrower claim: whether ecological selection instantiated an independently better empirical solution than an AUC-selected comparator behind the same prospective barriers.

The formal endpoint was:

- prediction adequacy passed;
- ecological nondomination passed in 3/3 parts;
- strict ecological improvement occurred in **0/3** parts;
- `empirical_confirmation_not_supported`;
- separate Product-A decision = `not_promoted`.

Full-denominator artifact audit showed that ecological and AUC roles selected the same candidate and the same predictor set in **108/108** matched taxon x accessible-area x seed cells. All 108 selected `all|logit_l2_C0.1_degree1_rs0`.

Interpretation: the empirical endpoint did not show that AUC identifies ecological truth. It showed that two distinct selection objectives were observationally equivalent at the realized selected-model level, so winner comparison contained no process-identification contrast to evaluate.

## Final synthesis

The development sequence supports a shift from model selection to ecological identification:

`fit models -> pick winner -> interpret selected variables`

becomes

`fit defensible alternatives -> recover stable process set -> challenge necessity separately -> retain contested / unresolved claims`

The central contribution is therefore not merely a warning that model selection can mislead. The concrete controlled-truth result is:

> **the complete hidden generating-process set was recovered in 55/60 unused cases and in 19/22 cases where the fitted models themselves disagreed.**

The framework then distinguishes four questions:

1. **predictive adequacy** — can the model recover withheld observations?
2. **process-set recovery** — which process information is shared across defensible ecological selectors and matches generating truth under controlled validation?
3. **process necessity** — does an adequate explanation survive exclusion of declared process information?
4. **identification failure** — which claims remain contested or unresolved when evidence is insufficient or selectors collapse empirically?

## What the paper does not claim

- It does not claim causal, physiological or fundamental-niche necessity.
- It does not claim that AUC is universally optimal.
- It does not claim that v2.7.2 P=0.9889 / R=0.9833 is falsification-first necessity-estimator performance.
- It does not claim broad selective validation across many independently varying process identities: in the frozen v2.7.2 suite, soil was the only process whose truth presence varied.
- It does not claim that the fresh empirical endpoint validated true generating processes.
- It does not claim a complete real-world proxy/composite closure; such a test would require a new prospective contract.
- It does not reopen Product A or unblock Product B.

## Nature Ecology & Evolution framing

The broad ecological claim is no longer only a problem statement. It is:

**Ecological process information can be recovered at a level more stable than exact fitted-model identity, but process necessity and unresolved evidence require separate inference.**

The evidence is concrete: 55/60 exact generating-process-set recovery overall, 19/22 exact recovery when fitted models disagree, and a fully traceable soil-specific failure envelope. The fresh empirical lane then establishes the external-validity boundary rather than manufacturing a positive biological conclusion.

## Manuscript closure rule

For submission reporting, this file is the authoritative scientific logic. Older development notes may retain historical terminology, but they must not be used to replace exact process-set recovery with a pooled-score-only story, merge the v2.6 exclusion-based necessity estimand with the v2.7.2 consensus-first process-recovery estimand, or reinterpret the frozen v2.8.4 non-support/non-promotion endpoint.
