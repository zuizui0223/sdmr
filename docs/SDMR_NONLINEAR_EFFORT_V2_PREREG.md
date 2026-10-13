# SDMR v2 prospective diagnostic: nonlinear cross-learner agreement and known observation effort

**Scientific status:** preregistered developmental benchmark *before any new seed opening*. This is a separate study; the former M5 and the frozen negative fresh-v5 result are immutable. The previously verified 24-case experiment (PR #279) is exploratory motivation, not fresh v2 confirmation.

## Question and hypotheses

1. **Representation/learning capacity:** In interactions and geographic shifts, does pairing shallow3 HGB with a distinct nonlinear learner (Random Forest) retain ODO-positive process information more effectively than pairing HGB with a standardized linear logistic model? Prediction ability and process classification are separate steps.
2. **Shared observational confounding:** Do false-sharp calls persist when two model families agree in the observationally confounded case? Consensus is not an independent truth certificate.
3. **Privileged effort upper bound (secondary):** If the simulator's *true cell-specific sampling effort* were directly available as an extra nuisance covariate, would process-state availability and false-sharp behavior change? This is NOT a field-ready correction or an equivalent predictor universe to the effort-blind ODO target.

**No performance/advancement criterion is retrofitted to these outcomes.** All positive and adverse results will be reported; there is no seed substitution or threshold rescue.

## Locked before opening new seeds

See `configs/sdmr_nonlinear_effort_v2_contract.json`. **New unused seeds**: `92001, 92002, 92003` (code search in the main repository before the new design returned no existing occurrence). **Six fixed worlds**: unique_process, interaction, observation_confounded, omitted_driver, null_correlated, geographic_shift. This totals 18 independent world×seed cases, **108** process-reference cells in each split/policy and **4,536** finite learner/knockout fold fits.

All worlds use the unchanged `simulate_process_world` with 1,600 cells, 180 occurrences and 600 backgrounds. Two 3-fold split modes: random-cell (group unique sampled cell IDs) and spatial GroupKFold (same original spatial groups). Each model sees identical ecological features and occurrence/background labels for its world/seed and split. No true suitability or oracle process state is passed to the learner.

Three fixed learners:

- **standardized isotropic L2**: existing matched-v1 train-fold scaler, balanced C=1 linear logistic, newton-cholesky max100/tol1e-10. Any convergence warning or 100-iteration limit must abstain.
- **HGB shallow3**: existing frozen balanced, 100 rounds, three leaves, min leaf 40, LR 0.05, L2 1.0, seed 0.
- **Random Forest leaf7**: `RandomForestClassifier`, 256 trees, maximum 7 leaves, min leaf 20, max_features 1.0, bootstrap true, balanced_subsample, seed 0, single thread. **Not capacity-equivalent** to HGB; the algorithm and ensemble structures differ. No tuning or selection based on current outcomes.

Primary pair: **HGB+Random Forest**, relative to the unchanged HGB+L2 baseline. Both accept a process state only when they return the exact same sharp class (replaceable/contributory/required), abstain if disagreement, and mark unavailable if either full system is unavailable. The complete registered process information carrier closure is removed on every knockout, without dropping additional features or tuning alternatives. Fixed authorization gate: balanced held-out log-score >= −0.75, gain over −log2 >= .01, p<=.001 with 999 within-fold held-out label permutations, seed 0. Process margin .01; mean ±1 SEM across three folds; identical-closure abstention.

Two declared effort regimes:

- **Unavailable (primary):** the biological ecological predictor matrix alone, no effort feature.
- **Known effort upper bound (secondary):** additionally supply `log(sampling_effort)` using only simulator's effort column, train/test values restricted by the same folds; retain this nuisance feature in every knockout. Real GBIF cannot generally provide this ground-truth effort. The ODO reference remains the frozen ecological-feature information state, so this is a *different representation universe* and may NOT be interpreted as a matched ODO accuracy improvement.

## Oracle and information barrier

The ODO (`evaluate_occurrence_oracle_states`) is the **same, unchanged occurrence-distribution information-state approximation** with 250 boosting steps and random-cell splits. It is based on the simulated suitability/effort distribution and includes a structural abstention on observation-confounded thermal. This target is *not* biological causal truth, and its HGB approximation may favor the finite HGB family.

**Order:** all finite model fits, original OOF predictions, certificates, states, and primary/secondary pair states are first serialized in `finite_before_oracle.json`, hashed SHA256 and retained. Only then does the process calculate ODO labels and save `case.json`. The oracle never decides model choice or threshold.

Raw full-system OOF probabilities are retained this time, allowing independent recalculation of all permutation p-values. Numerical oracle state/evidence tables are also retained for non-refitting arithmetic inspection; this is not an independent oracle refit.

## Fixed outputs and denominators

Report per split, effort regime, and pair for all 18 cases and all 108 process cells: (i) joint full-system authorization; (ii) ODO-positive recovery among all ODO-positive reference cells; (iii) favorable false positives on replaceable ODO references; (iv) sharp overresolution on ODO-unresolved references; (v) sharp on ODO-unavailable references; (vi) total sharp/unresolved/unavailable coverage, with per-world breakdown. Do not silently exclude missing, structurally unresolved or nonconvergent cases. All eight policies use the **same 108 oracle reference cells**; zero-denominator rates are reported null.

Safety, accuracy and abstention must appear as separate measures. Compare random-cell and spatial *within the same case*; do not treat nearby random-cell interpolation as geographical transfer. Count the observationally confounded 3 seeds once each, not independently for both split appearances. Conditional on model authorization is descriptive only and never replaces the 108-cell denominator.

## Run sequence

1. Commit source and contract; **smoke only on consumed/burned seed 91001**, in `interaction` and `observation_confounded`. Require the effort-unavailable HGB+L2 output to reproduce the unchanged v1 reference states and authorization. Do not open 92001–92003 in smoke.
2. Freeze all final source hashes and exact source-head SHA in a separate receipt after smoke passes; create one explicit activation-only commit.
3. Exactly one prospective execution over **all 18** world×seed cases. Require all original case artifacts and pre-oracle receipts. No rerunning selected failed cells or replacing seeds.
4. Aggregate by independent no-refit audit of SHA receipts, all 4,536 route-fold fit records, all 864 pair-state cells and full-system permutation statistics recalculated from saved OOF probabilities. A partial/failed aggregate blocks conclusions. All-fail outcomes remain valid negative evidence and do not trigger threshold changes.

Original PR #279, the 71/80 M5 simulator result, and the failed-closed real-v5 16/300 remain untouched. This study cannot alone identify a universal plant-niche process or validate SDMR for field occurrence data.
