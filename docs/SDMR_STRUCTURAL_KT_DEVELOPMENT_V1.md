# SDMR × Structural: eight-world forest known-truth development benchmark v1

**Status: DEVELOPMENT ONLY.** This is an isolated synthetic follow-up to SDMR's frozen M5 process-information benchmark and the retrospective FIA/Structural ecology results. It does not modify M5 (71/80, 0/700), Product-A (non-promoted), Product-B (blocked), the failed real-v5 application, or Structural's original forest data.

## Target distinction

For each **physical site** `i` in source-independent **region** `r`, generate two visits `t=0,1`. Observed stand structure `B_it=U_i+V_it` mixes persistent site quality `U` and a changing local structural component `V`. Observed climate `C` partly correlates with `U`. Growth `Y` is produced with a known within-site coefficient `beta` and independent noise. All models get only their declared predictors, never latent `U`, truth labels or oracle selection probabilities. Region means of `U` shift slightly to prevent a trivial iid holdout.

Three distinct quantities are audited with the *same* physical sites and out-of-region folds:
1. `spatial_gain`: mean squared error of climate/reference minus climate/reference+`B_0` in the unseen region.
2. `temporal_gain`: heldout mean squared error of changes `Y_1−Y_0` predicted without versus with *same-interval* `B_1−B_0`. **This is within-site change association, not prospective future forecasting or causal intervention**.
3. `closure_gain`: heldout change in spatial error after excluding all structural carriers. For `shared_carrier` the reference contains `Z=B`; its *individual* addition of `B` should be near zero even when the **full B+Z carrier set** is informative.
4. Separate `beetle_gain` represents an **incompatible biological operator/endpoint**. It cannot be pooled or counted as tree-growth process confirmation.
5. `full_vs_null_gain`: full declared representation versus a training-only intercept; an omitted-driver world should not pass a meaningful absolute information check.

Each of eight regions is held out in turn. Default source denominator is **8 regions × 64 physical sites = 512 sites/world**, before explicitly reported outcome-dependent inclusion. A region, not its individual trees/visits, receives one unit of weight in the primary average. Models use train-only feature centering/scaling, intercept-unpenalized deterministic ridge (fixed coefficient penalty 0.01); the same fold is used for each paired contrast. Two-sided 8-block signed permutations are a conditional diagnostic and **do not establish causal Type-I control**.

## Fixed development worlds (not a results table)

| World | Generating contrast | Required methodological behavior |
| --- | --- | --- |
| `direct_structure` | `beta=+0.8` on visit-specific `V`, site effect also present | Spatial and change-related information may both be recoverable; not automatically causal in field data |
| `measured_site_proxy` | `beta=0`, reference explicitly observes `Z=U` | Adding `B` after adequate site information should have little extra value |
| `shared_carrier` | `beta=+0.8`, shared structural carrier `Z=B` also in reference | One-variable drop is redundant, whole-process carrier closure is informative |
| `observation_selection` | `beta=0`, outcome and `B` influence whether a site has *both* visits | Biased selected cohort is flagged as observation-unresolved, even if it predicts |
| `spatial_only` | `beta=0`, persistent unmeasured `U` predicts growth and correlates with `B` | Spatial signal may be positive despite no within-site association |
| `temporal_transfer` | `Y_1=baseline +0.8(V_1−V_0)+noise` | Detect eligible within-site change association; cross-region sign robustness examined |
| `operator_mismatch` | `beta_tree=0` but separate beetle endpoint depends on `B` | Endpoint-specific information cannot be transferred as forest-tree effect |
| `omitted_driver` | Growth primarily depends on missing site-persistent `W`, independent of climate and `B` | Full-system information adequacy must be evaluated before process claims |

The selected `observation_selection` cohort is NOT an unbiased conditional sample and may also show false *within-site* association. A real application requires external observation/attrition/effort justification; this method cannot discover an unobserved selection mechanism just by fitting more learners.

### Interpretive safeguards

- `spatial_gain > 0` means conditional predictive information, not a physiological mechanism or a causal intervention.
- `temporal_gain > 0` means same-interval within-site association. B and Y at visit 1 are contemporaneous and must not be marketed as a forecast using only earlier data.
- `closure_gain > 0` means the declared carrier set contains endpoint-relevant information. Whether that information represents the declared biological process requires additional measurement/identifiability controls.
- Missing observations/regions are `unavailable` or a contract STOP, not zero effects.
- Synthetic results are **always** tagged `development_known_truth_only` and `synthetic_diagnostic_only`. No promotion rule converts their p-values to field evidence.
- All development data are generated from exactly the same code and source **never** open real FIA, Structural, GBIF, NEON or new species-response values.

## Experiment and evidence partitions

Code: `src/sdmr/structural_known_truth_v1.py`, tests `tests/test_structural_known_truth_v1.py`.
Runner: `experiments/structural_known_truth_development_v1.py`.

**Burned development seeds only:** 1201, 1202, 1203, 8 worlds each = 24 scenarios. These may be inspected for engineering/sentinel failures and are permanently unavailable as new prospective evidence. The runner explicitly rejects any other seed. CI archives JSON metrics with a SHA-256, retaining original world/seed labels and source counts. No empirical effect can be inferred from this archive.

**Prospective status:** not initiated. A successor may open new seeds only after source, exact world parameters, model/holdout, process/observation adequacy gates, cross-learner comparators, denominator and success thresholds are frozen and code is smoke-tested on burned seeds. Do not tune a promotion threshold using these development outcomes and then call those same outcomes prospective. If a fresh prospective endpoint fails, archive it, do not change seed identities or relabel.

## Prior art and actual methodological research question

Blocked CV, multilevel decomposition, conditional importance and group variable removal are existing methods. SDMR seeks a **testable gain in error-bounded process-information inference**, not a novel brand of variable-importance score. The serious benchmark is whether all-carrier closure + reference adequacy + observation gating + space/time/operator separation produces a more favorable *positive recovery versus false/over-sharp attribution* tradeoff than a sufficiently strong predeclared conditional importance/refit comparator.

## Scientific next gate

After reading the burned-development artifact:
1. Identify and fix only provable implementation/estimand defects, recording each revision as development.
2. Freeze explicit reference/effort/selection criteria, independent learner comparators, denominator and error limits **before** any unused seeds.
3. Only then run an independent prospective synthetic gate and, separately, source-qualified independent forest response data. Leave original M5/Product-A results and Structural's preexisting manuscripts untouched.
