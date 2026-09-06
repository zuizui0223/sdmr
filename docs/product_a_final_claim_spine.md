# Product A final claim spine

Status: **authoritative manuscript logic for Product A reporting; scientific endpoints unchanged**

## One-sentence claim

**Under controlled truth, Product A recovered complete ecological generating-process sets more often than an AUC-selected winner and corrected observation-process misattribution, while necessity and unresolved evidence remained separate inferential questions.**

## What Product A started by asking

Product A began as a conventional SDM procedure-selection problem: choose one complete model-building procedure that transfers to sealed spatial blocks and unseen taxa. From the beginning, information barriers were protected: sealed blocks could not influence fitting or tuning, unseen taxa could not influence procedure selection, accessible-area assumptions were sensitivity conditions rather than optimized outcomes, and failure to promote a procedure was an admissible scientific result.

Known-truth development showed that the winner-selection estimand was too weak for ecological interpretation, then produced a concrete process-recovery result beyond that problem diagnosis.

## Result 1 — Prediction and stable response surfaces do not identify process truth

Controlled-truth tests showed that a procedure can recover withheld occurrence environments or produce stable response surfaces while attributing the pattern to the wrong generating environmental process.

`prediction adequacy / response stability != process identification`

Prediction remains an adequacy layer, not a proof of ecological necessity.

## Result 2 — Agreement among selected good models does not establish necessity

Replacing one winner with a set of ecologically adequate models did not solve the problem. Pareto pruning made the retained set sharper but could remove viable alternatives, lose truth or boundary coverage and create a false necessary-process core.

`agreement among performance-filtered models != ecological necessity`

The inferential error is to convert conditional agreement after model filtering into biological necessity.

## Branch A — Necessity is a falsification problem, but this branch did not positively discover a driver

The v2.4–v2.6 process-exclusion branch challenges a process by prospectively excluding the declared information associated with it and asking whether an adequate ecological explanation survives. Evidence insufficiency remains unresolved rather than becoming absence.

The complete calibrated v2.6 controlled-truth validation returned:

- possible-process recall = **1.000**;
- false-required processes = **0**;
- complete process and boundary certificates for all validation taxa;
- possible-process precision approximately **0.467**;
- `required_processes` empty in **9/9** validation taxa.

Interpretation: exclusion-based inference controlled false necessity, but it did **not** positively isolate a required ecological driver in these panels. This is a safety result.

## Branch B — Complete generating-process sets were recovered, including when models disagreed

The positive process-identification result comes from the separate v2.7.1–v2.7.2 consensus-first sequence. The v2.7.2 `stable_process_core` is the intersection of process sets supported by canonical niche recovery and perturbation-robust niche recovery. It is **not** the process-exclusion necessary-process set.

Across 60 unused known-truth cases from six niche families:

- stable process core exactly equalled the complete hidden generating-process set in **55/60 cases (91.7%)**;
- the AUC-selected candidate had exact driver-process recovery in **50/60 (83.3%)**;
- canonical ecological selector process sets were exact in **52/60**;
- robust ecological selector process sets were exact in **54/60**;
- the two ecological selectors chose different fitted candidates in **22/60** cases;
- within those model-disagreement cases, the stable process core still exactly matched hidden process truth in **19/22 (86.4%)**;
- pooled stable-core precision = **0.9889** and recall/F1 = **0.9833**;
- exact fitted-model consensus = **38/60** and process-set consensus = **50/60**;
- independent-process numerical differences = **0.0**.

This is the principal concrete result: the full hidden process set was recovered in most unused cases, including most cases in which exact model identity differed.

The 55/60 versus 50/60 AUC comparison is a reporting comparison of the already frozen known-truth outcomes, not a newly preregistered global superiority endpoint. The family pattern is heterogeneous: Product A is strongest under observation confounding but is more conservative than AUC in the omitted-driver family.

## Result 3 — Observation-process misattribution was corrected in a controlled test

The observation-confounded family is the clearest mechanism result.

Hidden ecological truth was `{temperature, water}` in all 10 cases, while `recording_bias` affected where records were observed.

AUC-selected models:

- `niche_plus_observer` in 5/10 → exact ecological process recovery;
- `observer_only` in **5/10** → driver-process precision, recall and F1 all **0.0**.

Product A ecological selectors:

- canonical selector chose `niche_plus_observer` in **10/10**;
- robust selector chose `niche_plus_observer` in **10/10**;
- observation-process information was not promoted as an ecological process;
- stable process core recovered `{temperature, water}` in **10/10**.

Thus record-prediction selection attributed half of these controlled cases entirely to observation, whereas the ecological/observation separation recovered the generating ecological process set in every case. This is a concrete failure corrected, not merely a warning about prediction versus explanation.

## Result 4 — Selective process identification was tested most directly for soil

The frozen ecological process truth contained `temperature`, `water` and `soil`.

Temperature and water were generating in **all 60 cases** and stable in all 60. They demonstrate retention of invariant truths, not presence-versus-absence discrimination.

Soil truth varied:

- soil truly generating: 10 cases → stable **7**, contested **3**, absent from both ecological selectors **0**;
- soil non-generating: 50 cases → incorrectly stable **2**, contested **7**, absent from both selectors **41**.

For strict stable/not-stable soil classification, precision was **7/9 = 77.8%**, recall **7/10 = 70.0%**, and specificity **48/50 = 96.0%**. The set-valued result is more informative: none of the true-soil cases vanished completely; the three missed from the stable core remained contested.

All five exact stable-process-set errors were soil errors:

- omitted-driver: three true-soil cases downgraded to contested;
- soft-threshold: two false-soil cases retained as stable.

This is the current controlled-truth failure envelope. The paper must not imply that many independently varying process identities were already classified at pooled ~0.99 accuracy.

## Worked positive example — model disagreement but correct process recovery

`asymmetric`, seed `3103`:

- canonical fitted candidate: `climate_soil_quadratic`;
- canonical processes: `{soil, temperature, water}`;
- robust fitted candidate: `tw_quadratic`;
- robust processes: `{temperature, water}`;
- stable process core: `{temperature, water}`;
- contested: `{soil}`;
- hidden generating truth: `{temperature, water}`.

The models disagree. The process certificate isolates selector-specific soil as contested and returns the complete generating process set correctly.

## Result 5 — Fresh occurrence data exposed observational equivalence

The final fresh empirical endpoint tested whether ecological selection instantiated an independently better empirical solution than an AUC-selected comparator behind the same prospective barriers.

The formal endpoint was:

- prediction adequacy passed;
- ecological nondomination passed in 3/3 parts;
- strict ecological improvement occurred in **0/3** parts;
- `empirical_confirmation_not_supported`;
- separate Product-A decision = `not_promoted`.

Full-denominator artifact audit showed that ecological and AUC roles selected the same candidate and predictor set in **108/108** matched taxon × accessible-area × seed cells. All 108 selected `all|logit_l2_C0.1_degree1_rs0`.

This does not show that AUC identifies ecological truth. It shows that the fresh plant endpoint provided no realized model contrast on which to test process-level empirical advantage.

## Final synthesis

The concrete contribution is no longer only a warning that model selection can mislead:

> **Under unused controlled truth, Product A recovered the complete generating-process set in 55/60 cases versus 50/60 for the AUC-selected candidate, retained exact process truth in 19/22 cases despite fitted-model disagreement, and corrected an observation-only AUC misattribution in 5/10 confounded cases.**

The method therefore separates four questions:

1. **predictive adequacy** — can a model recover withheld observations?
2. **process-set recovery** — which ecological process information survives across defensible ecological selectors?
3. **process necessity** — does an adequate explanation survive exclusion of declared process information?
4. **identification failure** — which claims remain contested or unresolved when evidence is insufficient or empirical selectors collapse?

## What the paper does not claim

- It does not claim causal, physiological or fundamental-niche necessity.
- It does not claim a preregistered universal superiority of Product A over AUC from the 55/60 versus 50/60 reporting comparison.
- It does not claim that AUC is universally optimal.
- It does not claim that v2.7.2 P=0.9889 / R=0.9833 is falsification-first necessity-estimator performance.
- It does not claim broad selective validation across many independently varying process identities: soil was the only process whose truth presence varied in the frozen v2.7.2 suite.
- It does not claim that the fresh empirical endpoint validated true generating processes.
- It does not claim a complete real-world proxy/composite closure.
- It does not reopen Product A or unblock Product B.

## Nature Ecology & Evolution framing

The Nature-level claim should lead with the positive controlled-truth result:

**Ecological process information can be recovered beyond exact model identity, and separating ecological from observation processes can prevent a predictive winner from erasing the true environmental drivers.**

Necessity, contested alternatives and empirical non-identification then define the boundary of that result rather than replacing it with a generic problem statement.

## Manuscript closure rule

This file is the authoritative scientific logic for submission reporting. Older development notes must not replace exact process-set recovery with a pooled-score-only story, merge the v2.6 exclusion estimand with the v2.7.2 process-recovery estimand, treat the descriptive known-truth AUC comparison as a new preregistered superiority endpoint, or reinterpret the frozen v2.8.4 non-support/non-promotion endpoint.
