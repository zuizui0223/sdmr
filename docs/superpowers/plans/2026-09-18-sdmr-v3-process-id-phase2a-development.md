# SDMR v3 Process Identification Phase 2a Development Benchmark Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Run a completely development-only W1–W8 panel that diagnoses the new SDMR v3 identified-set method before any prospective validation seeds or thresholds are frozen.

**Architecture:** A new development runner composes the already-implemented W1–W8 simulator, truth-surface oracle, occurrence-only process challenge, and oracle/occurrence comparison. It adds explicit occurrence-level target overrides for observation-confounded worlds and reports recovery, false-positive, over-resolution, false-unique-attribution, and state-confusion summaries. All development seeds are burned immediately and may never become prospective evidence.

**Tech Stack:** Python 3.12, pandas, NumPy, scikit-learn, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-18-sdmr-v3-process-identification-design.md`

## Global Constraints

- Product-A remains closed and untouched.
- Phase 2a is `development_only`; no output is a prospective performance result.
- Development seeds are fixed at `23001–23008` before execution and are permanently burned.
- All eight W1–W8 worlds run for every seed; no failed/adverse world may be dropped or replaced.
- Prospective validation seeds remain empty during Phase 2a.
- No KT-A–KT-F threshold may be selected or labeled frozen until after the full Phase-2a result is recorded.
- W6 occurrence-level target is `unresolved` for declared observation-confounded processes even when the truth-surface oracle supports the ecological process.
- W3 identical shared-carrier closures must remain unresolved at the occurrence-attribution layer.
- Development outcomes may motivate a new method version, but any outcome-driven change requires rerunning only burned development seeds and a later untouched prospective denominator.

---

### Task 1: Development panel compositor

**Files:**
- Create: `src/sdmr/process_id/known_truth/development.py`
- Test: `tests/test_process_id_development.py`

**Interfaces:**
- `expected_occurrence_targets(world, oracle_states) -> pd.DataFrame`
- `run_development_panel(seeds, *, worlds=KNOWN_TRUTH_WORLDS, n_cells=1600, n_occurrences=180, n_background=600, n_splits=3) -> DevelopmentPanelResult`
- `DevelopmentPanelResult(comparison, world_summary, metrics)`

**Required behavior:**
- Adds `world` and `seed` keys to all process cells.
- Starts target state from final oracle state.
- Overrides processes in `world.observation_unresolved_processes` to target `unresolved`.
- Marks `unique_attribution_forbidden=True` for W3 thermal/water and W5 thermal/water.
- W7 is oracle-valid only when the declared full system returns unavailable rather than manufacturing process rankings.
- Never uses raw generating-process membership as the occurrence-level target.
- Returns exact full denominator, including unavailable cells.

**Tests:** deterministic same seed; W6 target override; W3 attribution boundary; complete W1–W8 × seed denominator.

---

### Task 2: Development metrics

**Files:**
- Modify: `src/sdmr/process_id/known_truth/development.py`
- Test: `tests/test_process_id_development.py`

**Metrics:**
- positive recovery among target `contributory|required`
- false positive among target `replaceable`
- over-resolution among target `unresolved`
- exact state agreement excluding target `unavailable`
- unavailable-cell count
- false unique attribution by forbidden world/seed group
- state confusion counts `target_state × occurrence_state`
- process-wise positive recovery and false-positive rates
- world-wise exact agreement

No metric is converted into PASS/FAIL in Phase 2a.

---

### Task 3: Development CLI and frozen burned-seed contract

**Files:**
- Create: `scripts/run_sdmr_v3_process_id_development.py`
- Create: `configs/sdmr_v3_process_id_development_v1.json`
- Test: `tests/test_process_id_development_contract.py`

**Contract values:**
- status: `development_only`
- seeds: exactly 23001–23008
- worlds: all W1–W8
- n_cells: 1600
- n_occurrences: 180
- n_background: 600
- n_splits: 3
- oracle margin: 0.02
- oracle SEM multiplier: 1.0
- oracle baseline R² floor: 0.70
- oracle required R² ceiling: 0.0
- occurrence margin: 0.01
- occurrence SEM multiplier: 1.0
- occurrence adequacy floor: -0.75
- logistic C: 1.0
- prospective status: `not_frozen`
- fresh empirical open: false

CLI outputs:
- `comparison.csv`
- `world_summary.csv`
- `metrics.json`
- `state_confusion.csv`
- `manifest.json`

Manifest fingerprints the exact config and outputs.

---

### Task 4: One-shot development workflow

**Files:**
- Create: `.github/workflows/sdmr-v3-process-id-development.yml`
- Modify: `docs/SDMR_V3_PROCESS_ID_PHASE1.md` only to link the development lane; do not change Phase-1 status.

Workflow:
- manual dispatch only
- exact branch guard: `design/sdmr-v3-process-identification`
- install `.[test]`
- run development contract tests
- run CLI against the committed config
- upload all outputs as `sdmr-v3-process-id-development-v1`
- no automatic prospective continuation

---

### Task 5: Record terminal development result

**Files after workflow completion:**
- Create: `docs/SDMR_V3_PROCESS_ID_DEVELOPMENT_V1_RESULT.md`
- Create: `results/sdmr_v3_process_id_development_v1_metrics.json`
- Create: `results/sdmr_v3_process_id_development_v1_state_confusion.csv`

The result document must:
- report all primary development metrics without hiding adverse worlds/processes;
- explicitly label seeds 23001–23008 burned;
- distinguish logical/design failures from ordinary weak recovery;
- state whether the method architecture is ready to freeze prospectively or requires a new development version;
- prohibit threshold tuning followed by reuse of the same development result as prospective evidence.

If method changes are required, Phase 2a ends with a new development-version design. If no load-bearing issue is found, a separate Phase 2b plan freezes unused prospective seeds and KT thresholds before execution.
