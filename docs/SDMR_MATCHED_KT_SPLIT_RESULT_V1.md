# Matched known-truth split v1 — complete prospective result (2026-10-12)

**Disposition: scientifically complete, no empirical or original-M5 re-promotion.** This result was obtained on the first and only frozen target opening of seeds 91001–91003 and 8 declared worlds (24 world–seed cases), under the previously committed scientific contract `configs/sdmr_matched_kt_split_v1.json`. All 24 case jobs, preflight, and independent aggregate succeeded in [GitHub Actions run 38192262406](https://github.com/zuizui0223/sdmr/actions/runs/38192262406).

**Source artifacts:** [Aggregate artifact 11722575098](https://github.com/zuizui0223/sdmr/actions/runs/38192262406/artifacts/11722575098), ZIP SHA-256 `8680990085cf2fdfde35065c3c35b8fd8ace9220ae08f0c8c8ae620779a90cca`; 24 case ZIPs each contain a pre-oracle finite-state receipt and final case JSON, with SHA-256 records listed in the aggregate. Activation commit `dacae9e88ca216a0304c787f669e8f7250aae84f`, frozen source receipt `2d764a9d879cc42a32a461af507d6b02b6d99d12`. A separate post-outcome, no-fitting hash and crosswalk audit checked all 24 case receipts and **288/288 process×split states** against the aggregate.

## Estimand and denominator

The reference is the **occurrence-distribution information-state oracle (ODO)** calculated from simulated suitability, observation effort, and accessible-cell distribution. It is *not* independently known biological causal-process identity; generating-process membership is metadata only. The ODO reference is held fixed across the two validation split modes for each case.

- 24 world–seed cases = 3 seeds × 8 worlds
- 6 declared whole-process information closures per case
- 144 finite consensus cells **per split** (288 comparisons total), all retained; 2,016 finite fits over both splits
- Reference categories (144 distinct process targets): **12 contributory, 105 replaceable, 9 unresolved, 18 unavailable**
- Same sampled occurrences/backgrounds, two numerical learner recipes, thresholds, and complete process closure in the two split modes

The models are **train-fold standardized balanced L2 logistic** and frozen **shallow3 HGB**. The primary two-learner consensus accepts only an identical sharp state, while either learner unavailable makes the pair unavailable. Random-cell is interpolation; spatial GroupKFold is geographic extrapolation.

## Frozen primary results

| Fixed-denominator metric | Random-cell 3-fold | Spatial 3-fold |
|---|---:|---:|
| Jointly authorized cases | **18/24** (75.0%) | **15/24** (62.5%) |
| Stable-sharp consensus cells | **92/144** (63.9%) | **74/144** (51.4%) |
| Positive ODO information recovered | **3/12** (25%) | **0/12** (0%) |
| False positive among ODO replaceable | **0/105** | **0/105** |
| Overresolved ODO unresolved | **2/9** (22.2%) | **2/9** (22.2%) |
| Sharp assignments where ODO unavailable | **0/18** | **0/18** |
| Replaceable agreement | **87/105** | **72/105** |
| Consensus contributory calls | **5** | **2** |
| Consensus required calls | **0** | **0** |
| Consensus unresolved / unavailable | **16 / 36** | **16 / 54** |

The higher random-cell stable-sharp coverage is **not equivalent to positive-state truth recovery**. Eight of 24 paired cases had more sharp states under random-cell, 16 tied, and none had more under spatial; this is descriptive only, not a causal experiment on field ecology.

## Failure localization by independent learner

| Reference-positive recall (12 positive target cells) | Random-cell | Spatial |
|---|---:|---:|
| HGB **alone** | **7/12** | **8/12** |
| Standardized isotropic L2 **alone** | **3/12** | **1/12** |
| **Agreement-required** pair | **3/12** | **0/12** |

Even though HGB independently recovered eight of twelve positive targets under spatial CV, **none survived mandatory positive agreement with the linear learner**. Thus the cross-learner requirement produces a major sensitivity loss under the fixed learner pair. This result should not be summarized as “spatial folds eliminate all recoverable ecological information”; they eliminate it **in this two-learner consensus configuration**.

The twelve reference positives consist of:
- `unique_process` thermal, three seeds: pair **3/3 random, 0/3 spatial**; both learners fully authorized, but in spatial folds one or both is unresolved on thermal.
- `interaction` thermal and water, three seeds: pair **0/6 random and 0/6 spatial**. HGB is fully authorized on **3/3 cases in both split modes**, whereas standardized linear is authorized on **0/3 in both**. The pair necessarily abstains.
- `geographic_shift` thermal, three seeds: pair **0/3 both**; learner state disagreement or geographic authorization loss persists.

## Safety failure under observation bias

The two **spatial** consensus `contributory` calls were *both incorrect relative to ODO*: `observation_confounded` world thermal under seeds **91001** and **91002**. The same **two** world–seed cases were overresolved under random-cell, accounting for its 2/9 unresolved overresolutions too. Those are four split-cell manifestations of **two underlying cases**, not four independent world draws.

Both learners agreed on `contributory` for these cases although the ODO reference explicitly remains `unresolved` under observation confounding. **Learner consensus is therefore not sufficient to protect against a common observation-bias mechanism.** This does not establish false causal attribution in any real plant species; the study uses simulated world/effort assumptions.

The `omitted_driver` null world yielded zero jointly authorized cases in all three seeds under either split, and the aggregate recorded **0/18 sharp when the oracle reference is unavailable**. The lack of false favorable positives on 105 replaceable targets is reassuring **for this finite set**, but does **not** erase the 2/9 safety failures on unresolved states.

## Interpretation and limitations

1. **Two different problems coexist:** spatial validation can reduce predictive authorization and sharp coverage; strict agreement can independently erase valid positive signals that one learner recovers.
2. **Specificity trades against sensitivity:** no false positive among 105 ODO-replaceable cells, yet only 3/12 positives recovered random-cell and 0/12 spatial.
3. **Agreement is not a truth certificate:** independent learner agreement retained overresolved claims when the two learners shared observational bias.
4. The two split modes reuse identical simulated cases, and only three seeds per world were preregistered. Process cells within a case are dependent; do not construct simple independent-binomial confidence intervals or claim universal ecological performance.
5. ODO is an approximated **distribution-information estimand** (using an HGB regressor and oracle observation effort), **not actual physiological or causal process truth**. The fixed world generator and ODO design bound inference; the HGB oracle also shares model-family characteristics with the finite HGB learner.
6. This new benchmark is **not identical** to original M5 Stage-P: different learner pair, sampling levels, split comparison and reference definitions. No comparison to M5’s 71/80 positive recovery as if a shared denominator or target.
7. **Original fresh-v5 remains `failed_closed`** at 16/300; no original threshold, cohort or sealed result is changed. No prospective seed, learner or threshold was replaced after examining outcomes.

## Consequence for future work

Do not promote the current two-learner consensus as a validated method for sharp positive ecological attribution. A **new, separately frozen** experiment should compare capacity-matched nonlinear learners and explicitly model observation effort, with separate endpoints for (i) full-system authorization, (ii) positive ODO-state recovery, (iii) unsafe overresolution, and (iv) geographic transfer. It must retain no-outcome-adaptive design and independent holdout seeds. A tuned or alternative learner is not a retrospective reanalysis that can rescue this prospective outcome.

## Auditable source-backed crosswalk (added after outcome opening; no refits)

- `results/sdmr_matched_kt_split_v1_crosswalk_288.csv` — every paired world/seed/process/split label, both original learner states, oracle-reference state and authorization flags. A **post-outcome derivative**, never used to fit or alter the prospectively frozen decisions.
- `results/sdmr_matched_kt_split_v1_independent_audit.json` — source hashes, fixed denominators and independently recomputed confusion counts.
- `experiments/audit_matched_kt_split_v1_receipts.py` — Python **standard-library-only** verifier of all 24 downloaded case archives, each pre-oracle finite receipt and the aggregate's original SHA-256 provenance records. No model, predictor or seed selection is performed.

To rerun, download the 24 original case ZIP artifacts and aggregate ZIP from GitHub Action run 38192262406 into one folder, then execute `python experiments/audit_matched_kt_split_v1_receipts.py --artifacts DIR --aggregate AGGREGATE.zip --output DIR/report`. The audit ran successfully on all 24 originals and independently checked **288/288** split×process rows. The narrative result is written *after* the scientifically sealed 24-case outcomes, without changing any earlier settings.
