# Sealed Answer Superiority v26 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and prospectively validate a source-disjoint v26 separator that removes a v23-supported process only when its full-closure knockout is predictively superior across every frozen model specification.

**Architecture:** Reuse the v25 sealed-answer evidence generation and leakage ordering, replace only the evidence classifier with the prospectively frozen 1.96-SEM superiority rule, and regenerate fresh v21 support plus v23 sets on unused seeds 20001–20020. Freeze the truth-blind refined sets before known-truth scoring; never retrofit v26 thresholds from fresh outcomes.

**Tech Stack:** Python 3.12, pandas, numpy, scikit-learn, pytest, GitHub Actions.

**Spec:** `docs/SEALED_ANSWER_SUPERIORITY_V26_CONTRACT.md`

## Global Constraints

- Fresh seeds are exactly integers 20001–20020 inclusive.
- Families are exactly gaussian, asymmetric, soft_threshold, interaction, omitted_driver, observation_confounded.
- v21 support thresholds and v23 `build_context_sets` logic remain unchanged.
- v22 pairwise rankings are not inputs.
- `exclude` requires every frozen model spec to satisfy `mean_delta - 1.96 * SEM > 0`.
- The zero superiority boundary and 1.96 multiplier cannot change after fresh outcomes are opened.
- Coverage requires at least 10 answer-check occurrences, at least 2 sealed blocks, and a complete required model roster.
- Source disjointness and prediction-freeze-before-answer-open are fail-closed invariants.
- Fresh terminal scoring requires zero true-member removals and at least one false-member removal.

---

### Task 1: Superiority classifier

**Files:**
- Create: `src/sdmr/sealed_answer_superiority_v26.py`
- Create: `tests/test_sealed_answer_superiority_v26.py`

**Interfaces:**
- Consumes: fold-level v25-compatible evidence columns (`family`, `seed`, `target_block`, `target_process`, `model_label`, `fold`, baseline/excluded completeness and density scores, coverage counts, source-disjoint/freeze flags).
- Produces: `classify_sealed_answer_superiority(...) -> pd.DataFrame` with one row per context/process and `evidence_state` in `{exclude, compatible, indeterminate, unavailable}`.

- [ ] **Step 1: Write failing classifier tests**

```python
import pandas as pd
import pytest

from sdmr.sealed_answer_superiority_v26 import classify_sealed_answer_superiority


def _rows(deltas_by_model, *, n_answer=6):
    rows = []
    for model, deltas in deltas_by_model.items():
        for fold, delta in enumerate(deltas):
            rows.append({
                "family": "gaussian",
                "seed": 20001,
                "target_block": -1,
                "target_process": "noise",
                "model_label": model,
                "fold": fold,
                "baseline_complete": True,
                "excluded_complete": True,
                "baseline_density_log_score": -0.60,
                "excluded_density_log_score": -0.60 + float(delta),
                "n_answer_occurrences": n_answer,
                "n_separator_background": 40,
                "sealed_answer_source_disjoint": True,
                "prediction_frozen_before_answer_open": True,
            })
    return pd.DataFrame(rows)


def test_all_models_must_have_positive_196_sem_lower_bound():
    out = classify_sealed_answer_superiority(
        _rows({"m1": [0.04, 0.06], "m2": [0.05, 0.07]}),
        required_model_labels=("m1", "m2"),
    )
    assert out.iloc[0].evidence_state == "exclude"


def test_one_uncertain_model_prevents_exclusion():
    out = classify_sealed_answer_superiority(
        _rows({"m1": [0.04, 0.06], "m2": [-0.01, 0.03]}),
        required_model_labels=("m1", "m2"),
    )
    assert out.iloc[0].evidence_state == "indeterminate"


def test_nonpositive_upper_bound_is_compatible():
    out = classify_sealed_answer_superiority(
        _rows({"m1": [-0.04, -0.02], "m2": [0.04, 0.06]}),
        required_model_labels=("m1", "m2"),
    )
    assert out.iloc[0].evidence_state == "compatible"


def test_missing_roster_or_coverage_is_unavailable():
    out = classify_sealed_answer_superiority(
        _rows({"m1": [0.04, 0.06]}),
        required_model_labels=("m1", "m2"),
    )
    assert out.iloc[0].evidence_state == "unavailable"


def test_reused_or_unfrozen_outcome_fails_closed():
    reused = _rows({"m1": [0.04, 0.06], "m2": [0.05, 0.07]})
    reused.loc[0, "sealed_answer_source_disjoint"] = False
    with pytest.raises(ValueError, match="source-disjoint"):
        classify_sealed_answer_superiority(reused, required_model_labels=("m1", "m2"))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest -q tests/test_sealed_answer_superiority_v26.py`

Expected: collection failure because `sdmr.sealed_answer_superiority_v26` does not yet exist.

- [ ] **Step 3: Implement the minimal classifier**

Implement strict boolean parsing, duplicate-key rejection, source/freeze fail-closed guards, coverage/roster checks, per-model mean/SEM, `lower = mean - 1.96*SEM`, `upper = mean + 1.96*SEM`, and the four frozen evidence states. Do not add tunable scientific thresholds.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `pytest -q tests/test_sealed_answer_superiority_v26.py`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/sdmr/sealed_answer_superiority_v26.py tests/test_sealed_answer_superiority_v26.py
git commit -m "Add frozen v26 superiority classifier"
```

### Task 2: Fresh support and set-construction pipeline

**Files:**
- Create: `configs/sealed_answer_superiority_v26_prospective.json`
- Create: `src/sdmr/sealed_answer_superiority_v26_prospective.py`
- Create: `tests/test_sealed_answer_superiority_v26_prospective.py`

**Interfaces:**
- Consumes: v21 simulation/support machinery, `set_valued_attribution_v23.build_context_sets`, v25 sealed evidence generator, v24 refinement operator, v26 classifier.
- Produces: truth-blind per-family artifacts containing fresh `context_decisions.csv`, `context_sets.csv`, separator fold evidence, separator states, and refined context sets.

- [ ] **Step 1: Write failing contract/pipeline tests**

Tests must assert:

```python
assert tuple(cfg["fresh_seed_denominator"]) == tuple(range(20001, 20021))
assert cfg["sem_multiplier"] == 1.96
assert cfg["superiority_boundary"] == 0.0
assert cfg["post_outcome_rule_changes_allowed"] is False
assert cfg["seed_replacement_allowed"] is False
```

Also test that the truth-blind constructor rejects any attempt to pass a fresh context set not built by `build_context_sets`, and that terminal truth labels are absent from the preterminal receipt.

- [ ] **Step 2: Run prospective tests and verify RED**

Run: `pytest -q tests/test_sealed_answer_superiority_v26_prospective.py`

Expected: missing prospective module/config failure.

- [ ] **Step 3: Implement frozen config loader and fresh support builder**

Reuse v21 internal functions with the v26 seed denominator rather than editing v21. Build fresh support rows with the same process roster and thresholds, then call:

```python
context_sets = build_context_sets(context_decisions)
```

No truth columns may be read before terminal scoring.

- [ ] **Step 4: Implement sealed superiority evidence generation**

For each fresh family/seed and each member present in the fresh v23 supported set, reuse the v25 full-closure model/exclusion evidence generator. Classify with `classify_sealed_answer_superiority` and feed only qualified `exclude` states to v24 refinement.

- [ ] **Step 5: Verify focused fresh-pipeline tests GREEN**

Run: `pytest -q tests/test_sealed_answer_superiority_v26.py tests/test_sealed_answer_superiority_v26_prospective.py tests/test_separating_evidence_refinement_v24.py tests/test_set_valued_attribution_v23.py`

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add configs/sealed_answer_superiority_v26_prospective.json src/sdmr/sealed_answer_superiority_v26_prospective.py tests/test_sealed_answer_superiority_v26_prospective.py
git commit -m "Add prospective v26 fresh pipeline"
```

### Task 3: Truth-blind freeze and deterministic rerun gate

**Files:**
- Modify: `src/sdmr/sealed_answer_superiority_v26_prospective.py`
- Modify: `tests/test_sealed_answer_superiority_v26_prospective.py`

**Interfaces:**
- Consumes: completed fresh family shards from Task 2.
- Produces: immutable `truth_blind_refinement_receipt.json`, deterministic hashes, and a rerun comparison receipt.

- [ ] **Step 1: Write failing determinism tests**

Assert that two independently constructed truth-blind outputs with identical frozen inputs have identical context-set, separator-state, and refinement digests. Assert any discrete mismatch blocks terminal scoring.

- [ ] **Step 2: Verify RED**

Run: `pytest -q tests/test_sealed_answer_superiority_v26_prospective.py -k determinism`

Expected: determinism gate API is missing.

- [ ] **Step 3: Implement canonical hashing and rerun comparison**

Canonicalize row order and field formatting before SHA-256. Require exact identity for discrete states and hashes before truth open.

- [ ] **Step 4: Verify GREEN**

Run the focused determinism tests twice.

- [ ] **Step 5: Commit**

```bash
git add src/sdmr/sealed_answer_superiority_v26_prospective.py tests/test_sealed_answer_superiority_v26_prospective.py
git commit -m "Gate v26 terminal on deterministic truth-blind outputs"
```

### Task 4: Terminal known-truth scorer

**Files:**
- Modify: `src/sdmr/sealed_answer_superiority_v26_prospective.py`
- Modify: `tests/test_sealed_answer_superiority_v26_prospective.py`

**Interfaces:**
- Consumes: frozen deterministic refinement receipt plus fresh context/refinement rows.
- Produces: `prospective_decision.json` and member/context audit tables.

- [ ] **Step 1: Write failing terminal tests**

Test that terminal scoring refuses to run without a valid frozen truth-blind receipt and determinism pass. Test the exact gate:

```python
passed = (
    removed_true_members == 0
    and contexts_with_any_true_deletion == 0
    and removed_false_members >= 1
    and all_removals_qualified
)
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q tests/test_sealed_answer_superiority_v26_prospective.py -k terminal`

Expected: terminal scoring function missing.

- [ ] **Step 3: Implement terminal scorer**

Open `generating_process_true` only after receipt/determinism validation. Preserve failed/null rows in denominator. Emit counts/rates plus explicit authorization booleans.

- [ ] **Step 4: Verify GREEN**

Run all v26/v24/v23 focused tests.

- [ ] **Step 5: Commit**

```bash
git add src/sdmr/sealed_answer_superiority_v26_prospective.py tests/test_sealed_answer_superiority_v26_prospective.py
git commit -m "Add sealed v26 prospective terminal scorer"
```

### Task 5: GitHub Actions prospective endpoint

**Files:**
- Create: `.github/workflows/sealed-answer-superiority-v26-prospective.yml`

**Interfaces:**
- Consumes: frozen v26 code/config.
- Produces: independent truth-blind replicate artifacts and one terminal prospective decision artifact.

- [ ] **Step 1: Add focused CI before scientific execution**

Workflow first runs the v26/v24/v23 tests. Scientific jobs depend on that gate.

- [ ] **Step 2: Run two truth-blind replicates**

Each replicate executes all six families over the frozen 20001–20020 denominator without truth scoring and uploads immutable artifacts.

- [ ] **Step 3: Compare replicate digests**

Block terminal evaluation on any discrete/hash mismatch.

- [ ] **Step 4: Run terminal truth scoring exactly once**

Only after truth-blind outputs are frozen and deterministic, execute the terminal scorer and upload `prospective_decision.json` plus audit tables.

- [ ] **Step 5: Verify workflow completion and artifacts**

Confirm all jobs complete, no seed/family disappears, and terminal output reports the exact frozen denominator.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/sealed-answer-superiority-v26-prospective.yml
git commit -m "Run prospective v26 superiority endpoint"
```

## Self-review

- Spec coverage: classifier, source-disjointness, fresh denominator, unchanged v21/v23/v24 chain, determinism, truth-blind freeze, terminal gate, and hard stops all have explicit tasks.
- Placeholder scan: no implementation step relies on TBD/TODO placeholders.
- Type consistency: all tasks use `pd.DataFrame` context/fold tables and the same four evidence-state vocabulary; `build_context_sets` remains the sole v23 constructor.
