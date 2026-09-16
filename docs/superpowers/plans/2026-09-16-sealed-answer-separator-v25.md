# Sealed Answer-Check Separator v25 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a genuinely new v24 separator that tests each v23-supported process on spatially sealed answer-check occurrences that were excluded from v21 support construction, then diagnose it on the already-consumed v21 denominator before any fresh prospective run.

**Architecture:** v25 keeps v23 support construction unchanged. Models and process-exclusion predictions are frozen from the model-pool evidence before answer-check outcomes are opened; separator evidence is then scored only on sealed occurrence blocks and a disjoint simulated reference sample. The separator emits `exclude`, `compatible`, `indeterminate`, or `unavailable`; v24 remains the only operator allowed to contract the supported set.

**Tech Stack:** Python 3.12, pandas, numpy, scikit-learn, existing `sdmr.model`, `sdmr.validation`, `sdmr.sealed_occurrence_contract`, `sdmr.density_ratio_process_challenge`, and v24 refinement code.

**Spec:** `docs/SEPARATING_EVIDENCE_REFINEMENT_V24_CONTRACT.md`

## Global Constraints

- The v21 support rule and thresholds are unchanged.
- Answer-check occurrence identities must never be available before a non-empty frozen prediction/selection receipt exists.
- Separator outcome evidence must be disjoint from the occurrence rows used to create v21 support.
- The density non-inferiority margin is inherited unchanged at `0.01` nats with one SEM.
- At least two sealed spatial blocks and at least ten complete sealed occurrences are required; otherwise separator state is `unavailable`.
- The separator may remove a v23 member only through v24; it may never add a process.
- Consumed seeds `17001–17010` are development-only and cannot produce a fresh performance claim.
- No fresh denominator is opened until the development rule, source, coverage gate, and prospective success criteria are frozen.

---

### Task 1: Freeze separator state semantics

**Files:**
- Create: `tests/test_sealed_answer_separator_v25.py`
- Create: `src/sdmr/sealed_answer_separator_v25.py`

**Interfaces:**
- Consumes: a fold-evidence DataFrame keyed by `family, seed, target_block, target_process, model_label, fold`.
- Produces: `classify_sealed_answer_separator(...) -> pd.DataFrame` with one row per context/process and `evidence_state` in the v24 vocabulary.

- [ ] **Step 1: Write the failing tests** for unanimous model-spec non-inferiority, clear inferiority, overlapping intervals, incomplete coverage, duplicate keys, and source/freeze guards.
- [ ] **Step 2: Run focused CI and verify RED** because `sdmr.sealed_answer_separator_v25` does not yet exist.
- [ ] **Step 3: Implement the minimal classifier**. For each model label, `delta = excluded_density_log_score - baseline_density_log_score`; compute mean, SEM, lower and upper bounds over sealed spatial blocks. A model is non-inferior when `lower >= -0.01`; clearly inferior when `upper < -0.01`. Emit `exclude` only when every required model label is complete and non-inferior; emit `compatible` when at least one complete model is clearly inferior; otherwise `indeterminate`. Coverage failures emit `unavailable`.
- [ ] **Step 4: Run focused CI and verify GREEN**.

### Task 2: Build sealed outer fold evidence without opening the answer key early

**Files:**
- Modify: `tests/test_sealed_answer_separator_v25.py`
- Modify: `src/sdmr/sealed_answer_separator_v25.py`

**Interfaces:**
- Produces: `build_sealed_answer_fold_evidence(...) -> pd.DataFrame`.
- Uses a frozen `OccurrenceAnswerCheckSplit`, fixed model specs, process registry, and a separator reference frame whose rows are disjoint from v21 background/occurrence inputs.

- [ ] **Step 1: Add failing leakage/coverage tests** proving empty receipt blocks opening, model-pool and answer-check IDs never overlap, and process closure removes all declared representations (e.g. `temperature` and `temp_proxy`).
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement minimal evidence generation**. Fit baseline and process-excluded models on model-pool evidence before opening answer-check rows. Reconstruct the frozen outer occurrence partition, score each sealed block against the disjoint reference frame with `balanced_density_ratio_log_score`, and retain explicit completeness and sample-count fields.
- [ ] **Step 4: Verify GREEN**.

### Task 3: Add a consumed-v21 development runner

**Files:**
- Create: `configs/sealed_answer_separator_v25_development.json`
- Create: `src/sdmr/sealed_answer_separator_v25_development.py`
- Create: `tests/test_sealed_answer_separator_v25_development.py`
- Create: `.github/workflows/sealed-answer-separator-v25-development.yml`
- Create: `docs/SEALED_ANSWER_SEPARATOR_V25_CONTRACT.md`

**Interfaces:**
- Consumes: authoritative v23 artifact `10431279663` / `context_sets.csv`, seeds `17001–17010`, and the existing simulation generator.
- Produces: truth-blind separator rows, v24-refined context sets, and a separate known-truth development score.

- [ ] **Step 1: Add failing contract tests** for exact consumed denominator, source artifact digest, inherited `0.01` margin, coverage floor, fixed model-spec roster, and `fresh_validation_authorized=false`.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement development runner**. Regenerate each consumed simulation, recreate the original sealed occurrence split, build a disjoint reference sample from unused simulation cells, freeze baseline/exclusion models, open sealed blocks only after a receipt exists, classify separator states, and pass them into v24 refinement.
- [ ] **Step 4: Run the consumed development workflow** and score truth only after truth-blind refinement artifacts are fixed.
- [ ] **Step 5: Record whether contraction is informative and safe** using mean contraction, false-member removal, true-member false deletion, and exact-set change. No threshold changes are allowed inside this endpoint.

### Task 4: Freeze or stop before fresh prospective validation

**Files:**
- Create only if Task 3 meets its predeclared development advancement screen: `docs/SEALED_ANSWER_SEPARATOR_V25_DEVELOPMENT_RESULT.md` and a separate prospective contract in a successor PR.

- [ ] **Step 1: If development safety fails, record the negative endpoint and stop**; do not spend fresh seeds.
- [ ] **Step 2: If it passes, freeze new unused seeds, success criteria, separator roster, and workflow before any fresh answer-check outcomes are opened.**
