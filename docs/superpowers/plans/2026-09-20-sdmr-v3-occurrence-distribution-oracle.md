# SDMR v3 Occurrence-Distribution Oracle Implementation Plan

**Goal:** Add a development-only occurrence-distribution oracle that sits between truth-surface identifiability and finite-sample learner recovery.

**Architecture:** The oracle uses the complete simulated cell-level occurrence and background probability distributions, not sampled occurrence/background rows. For each spatial fold it fits the same flexible deterministic classifier to exact weighted class mass, evaluates an exact equal-prior balanced log score on held-out cells, and compares the full predictor system with complete process-closure knockouts. The output uses the existing five-state SDMR state space and never changes Product-A, prospective thresholds, or fresh empirical data.

**Spec basis:** `docs/SDMR_V3_POSITIVE_EVIDENCE_AUDIT_V1_RESULT.md`

## Global constraints

- Development-only; seeds 23001–23008 are already burned evidence.
- Product-A remains `closed_not_reopened`.
- No fresh empirical data or prospective validation seeds are opened.
- Primary score is the exact equal-prior balanced occurrence/background log score.
- Complete simulated distributions are used; sampled occurrence/background rows are forbidden as oracle inputs.
- Process closure uses the frozen many-to-many registry.
- The oracle may return `replaceable`, `contributory`, `required`, `unresolved`, or `unavailable`.
- Existing margin `0.01`, adequacy floor `-0.75`, and SEM multiplier `1.0` are reused only as development diagnostics; they are not prospectively frozen.\n- Oracle numerical availability follows the authoritative design spec: the upper uncertainty bound of full-model Bayes-score regret must be at or below `0.01` nats.
- No finite-sample learner result is used to assign oracle state.

---

### Task 1: Exact observation-distribution probabilities

**Files**
- Create: `src/sdmr/process_id/known_truth/occurrence_oracle.py`
- Test: `tests/test_process_id_occurrence_oracle.py`

**Interface**
- `complete_observation_distributions(world) -> pd.DataFrame`
- Columns: `cell_id, occurrence_probability, background_probability, bayes_probability`

**Required behavior**
- occurrence mass is proportional to `true_suitability * sampling_effort`;
- background mass is proportional to `sampling_effort`;
- each class probability sums to exactly one up to numerical tolerance;
- `bayes_probability = p_occ / (p_occ + p_bg)`;
- sampled `world.occurrences` and `world.background` are not consulted.

**Tests**
- class masses sum to 1;
- two worlds with identical complete environment but different sampled rows produce identical oracle distributions;
- null constant suitability produces `bayes_probability == 0.5`.

---

### Task 2: Exact weighted balanced log score

**Files**
- Modify: `src/sdmr/process_id/known_truth/occurrence_oracle.py`
- Test: `tests/test_process_id_occurrence_oracle.py`

**Interfaces**
- `exact_balanced_log_score(p_occ, p_bg, prediction) -> float`
- `bayes_balanced_log_score(p_occ, p_bg) -> float`

**Definition**

```text
score(q) =
  0.5 * sum_i p_occ[i] * log(q[i])
+ 0.5 * sum_i p_bg[i]  * log(1-q[i])
```

**Tests**
- constant `q=0.5` equals `-log(2)`;
- Bayes prediction is never worse than the null prediction;
- invalid/non-normalized probability inputs fail closed.

---

### Task 3: Complete-distribution full vs process-knockout oracle

**Files**
- Modify: `src/sdmr/process_id/known_truth/occurrence_oracle.py`
- Test: `tests/test_process_id_occurrence_oracle.py`

**Interface**
- dataclass `OccurrenceDistributionOracleResult(fold_evidence, process_summary, bayes_summary, receipt)`
- `evaluate_occurrence_distribution_oracle(world, *, n_splits=3, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0) -> OccurrenceDistributionOracleResult`

**Fitting**
- duplicate complete environment cells conceptually into class 1 and class 0;
- use exact sample weights `0.5*p_occ` and `0.5*p_bg`;
- fit a deterministic `HistGradientBoostingClassifier` on training spatial groups;
- full and knockout routes use identical hyperparameters and folds;
- process knockout removes the complete frozen process closure;
- test-fold score renormalizes occurrence and background mass separately within that fold before applying the exact balanced score.

**State classification**
- summarize paired `full_score - knockout_score` across folds;
- `full_adequate` is the numerical-oracle condition defined in the design spec: upper full-model Bayes-score regret `<= 0.01` nats;
- `knockout_adequate = mean_knockout_score >= adequacy_floor`;
- call existing `classify_process_state`;
- apply identical-closure abstention after state assignment.

**Additional diagnostics**
- exact Bayes score and null score per fold;
- full-model recovery fraction of Bayes gain:
  `(full_score + log(2)) / (bayes_score + log(2))`, when Bayes gain is positive.

**Tests**
- W1 thermal is not unavailable under standard development profile;
- W4 seasonality remains replaceable;
- W3 thermal/water remain unresolved because of identical closure;
- W7 must be `unavailable` when the full declared predictor system cannot approximate the exact Bayes score within the frozen `0.01`-nat oracle tolerance.

---

### Task 4: Three-level identifiability crosswalk

**Files**
- Create: `src/sdmr/process_id/known_truth/identifiability_crosswalk.py`
- Test: `tests/test_process_id_identifiability_crosswalk.py`

**Interface**
- `build_identifiability_crosswalk(truth_states, occurrence_oracle_states, finite_states) -> pd.DataFrame`

**Columns**
- `world, seed, process`
- `truth_surface_state`
- `occurrence_distribution_state`
- `finite_sample_state`
- `distribution_positive`
- `finite_positive`
- `finite_false_negative_given_distribution_positive`
- `truth_positive_but_distribution_not_positive`

**Tests**
- truth-positive/distribution-replaceable is not counted as finite learner false negative;
- distribution-positive/finite-unresolved is counted as finite learner non-recovery;
- duplicate/misaligned keys fail closed.

---

### Task 5: Burned-seed occurrence-oracle audit runner

**Files**
- Create: `scripts/run_sdmr_v3_occurrence_distribution_oracle_audit.py`
- Create: `configs/sdmr_v3_occurrence_distribution_oracle_audit_v1.json`
- Create: `.github/workflows/sdmr-v3-occurrence-distribution-oracle-audit.yml`
- Test: `tests/test_process_id_occurrence_oracle_audit_contract.py`

**Frozen development profile**
- seeds: 23001–23008;
- worlds: `unique_process, interaction, geographic_shift`;
- n_cells: 1600;
- n_splits: 3;
- margin: 0.01;
- adequacy floor: -0.75;
- SEM multiplier: 1.0;\n- maximum upper full-model Bayes-score regret for oracle availability: 0.01 nats;
- no sampled-row counts are inputs to the oracle;
- prospective status: `not_frozen`;
- fresh empirical open: false.

**Outputs**
- `occurrence_oracle_states.csv`
- `occurrence_oracle_fold_evidence.csv`
- `identifiability_crosswalk.csv`
- `metrics.json`
- `manifest.json`

**Primary development metrics**
- number of truth-surface-positive cells;
- number and fraction also occurrence-distribution-positive;
- finite-sample recovery conditional on occurrence-distribution-positive;
- truth-positive but occurrence-distribution-nonpositive count;
- breakdown by W1/W5/W8 and thermal/water.

No PASS/FAIL promotion decision is made in this audit.

---

### Task 6: Terminal diagnostic record

**Files after execution**
- Create: `docs/SDMR_V3_OCCURRENCE_DISTRIBUTION_ORACLE_AUDIT_V1_RESULT.md`
- Create: `results/sdmr_v3_occurrence_distribution_oracle_audit_v1_metrics.json`

**Decision rule**
- If most truth-positive failures become occurrence-distribution-replaceable/unresolved, redefine future learner-recovery denominator to occurrence-distribution-positive cells.
- If occurrence-distribution-positive cells remain common but finite recovery stays poor, the learner/evidence procedure remains the bottleneck.
- If the oracle itself is frequently unavailable despite positive Bayes gain, improve oracle function class before any prospective freeze.
- Do not tune margin/floor using this audit and then treat the same cells as prospective evidence.
