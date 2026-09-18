# SDMR v3 Process Identification Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the new SDMR v3 process-identification core and prospective known-truth validation machinery without reopening Product-A.

**Architecture:** New code lives under `src/sdmr/process_id/` and consumes only generic frozen utilities from the existing repository. The core converts matched process-knockout evidence into abstention-aware states, generates W1–W8 known-truth worlds, evaluates truth-surface and occurrence evidence separately, and applies a strict KT-A–KT-F promotion gate. Fresh empirical code is explicitly deferred until this gate exists and passes under a separately frozen prospective contract.

**Tech Stack:** Python 3, pandas, NumPy, scikit-learn, pytest, existing SDMR utilities.

**Spec:** `docs/superpowers/specs/2026-09-18-sdmr-v3-process-identification-design.md`

## Global Constraints

- Product-A v2.8.4 remains closed: `empirical_confirmation_not_supported` and `not_promoted` are never recomputed or changed.
- Historical exposed seeds/denominators from v3.2/oracle/v4 are development-only and cannot be prospective validation evidence.
- Primary states are exactly `replaceable`, `contributory`, `required`, `unresolved`, and `unavailable`.
- `failure to establish non-inferiority != evidence of meaningful inferiority`.
- Process closure is many-to-many: every predictor registered to a process is removed in that process knockout; shared composites are removed in every linked process knockout.
- Observation-process information is never silently included in ecological process closure.
- The outer answer-check is not used by Phase 1 implementation or tests; fresh empirical work remains unopened.
- No historical Product-A promotion thresholds are imported into the new namespace.
- New public scientific API lives under `sdmr.process_id`, not a Product-A v2.x module.

---

### Task 1: Abstention-aware process state engine

**Files:**
- Create: `src/sdmr/process_id/__init__.py`
- Create: `src/sdmr/process_id/states.py`
- Test: `tests/test_process_id_states.py`

**Interfaces:**
- Produces: `PROCESS_STATES: tuple[str, ...]`
- Produces: `classify_process_state(evidence: pd.DataFrame, *, margin: float, adequacy_floor: float, sem_multiplier: float = 1.0) -> str`
- Evidence columns: `route`, `complete`, `full_adequate`, `knockout_adequate`, `delta_mean`, `delta_sem`
- Convention: `delta_mean > 0` means the process-free route has worse ecological loss than the matched full-information route.

- [ ] **Step 1: Write failing tests for all five scientific states**

```python
import pandas as pd
from sdmr.process_id.states import classify_process_state

def _rows(*rows):
    return pd.DataFrame(rows)

def test_replaceable_requires_positive_noninferiority_witness():
    evidence = _rows(
        dict(route="a", complete=True, full_adequate=True, knockout_adequate=True,
             delta_mean=0.005, delta_sem=0.002),
        dict(route="b", complete=False, full_adequate=True, knockout_adequate=False,
             delta_mean=float("nan"), delta_sem=float("nan")),
    )
    assert classify_process_state(evidence, margin=0.01, adequacy_floor=0.0) == "replaceable"

def test_indeterminate_viable_route_forces_unresolved():
    evidence = _rows(
        dict(route="a", complete=True, full_adequate=True, knockout_adequate=True,
             delta_mean=0.012, delta_sem=0.006),
        dict(route="b", complete=True, full_adequate=True, knockout_adequate=True,
             delta_mean=0.030, delta_sem=0.003),
    )
    assert classify_process_state(evidence, margin=0.01, adequacy_floor=0.0) == "unresolved"

def test_all_complete_positive_loss_with_adequate_survivor_is_contributory():
    evidence = _rows(
        dict(route="a", complete=True, full_adequate=True, knockout_adequate=True,
             delta_mean=0.030, delta_sem=0.003),
        dict(route="b", complete=True, full_adequate=True, knockout_adequate=False,
             delta_mean=0.040, delta_sem=0.004),
    )
    assert classify_process_state(evidence, margin=0.01, adequacy_floor=0.0) == "contributory"

def test_all_complete_positive_loss_and_no_adequate_route_is_required():
    evidence = _rows(
        dict(route="a", complete=True, full_adequate=True, knockout_adequate=False,
             delta_mean=0.030, delta_sem=0.003),
        dict(route="b", complete=True, full_adequate=True, knockout_adequate=False,
             delta_mean=0.040, delta_sem=0.004),
    )
    assert classify_process_state(evidence, margin=0.01, adequacy_floor=0.0) == "required"

def test_inadequate_full_reference_is_unavailable():
    evidence = _rows(
        dict(route="a", complete=True, full_adequate=False, knockout_adequate=False,
             delta_mean=0.05, delta_sem=0.001),
    )
    assert classify_process_state(evidence, margin=0.01, adequacy_floor=0.0) == "unavailable"
```

- [ ] **Step 2: Run the focused test and confirm import failure**

Run: `pytest -q tests/test_process_id_states.py`

Expected: FAIL because `sdmr.process_id.states` does not exist.

- [ ] **Step 3: Implement strict interval logic**

```python
PROCESS_STATES = ("replaceable", "contributory", "required", "unresolved", "unavailable")

def classify_process_state(evidence, *, margin, adequacy_floor, sem_multiplier=1.0):
    # Validate schema, unique non-empty route ids, finite non-negative SEM for complete rows.
    # If any complete matched full reference is not adequate -> unavailable.
    # A complete adequate knockout route with upper = mean + k*SEM <= margin -> replaceable.
    # If any required route is incomplete and no replaceable witness exists -> unresolved.
    # For all complete routes, lower = mean - k*SEM.
    # Any lower <= margin < upper -> unresolved.
    # After excluding replaceable/indeterminate cases, every route must have lower > margin.
    # If any knockout route is adequate -> contributory; otherwise -> required.
```

The `adequacy_floor` argument is validated and retained in the public contract even though evidence already carries the precomputed `knockout_adequate`/`full_adequate` booleans.

- [ ] **Step 4: Add fail-closed tests**

Test missing columns, duplicate route names, negative SEM, empty evidence, non-boolean flags, and non-finite complete deltas.

Run: `pytest -q tests/test_process_id_states.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `Add abstention-aware SDMR process states`

---

### Task 2: Plant process taxonomy and frozen registry

**Files:**
- Create: `src/sdmr/process_id/taxonomy.py`
- Create: `src/sdmr/process_id/registry.py`
- Modify: `src/sdmr/process_id/__init__.py`
- Test: `tests/test_process_id_registry.py`

**Interfaces:**
- Consumes existing `sdmr.process_information_closure.normalize_process_information_registry`
- Produces: `DEFAULT_PLANT_PROCESSES`
- Produces dataclass: `FrozenProcessRegistry(table, processes, predictors, digest)`
- Produces: `freeze_process_registry(registry, *, predictor_universe, process_universe=DEFAULT_PLANT_PROCESSES) -> FrozenProcessRegistry`

- [ ] **Step 1: Write failing tests**

Tests must assert:
1. default process order is exactly `thermal, water, seasonality, radiation_energy, soil_substrate, productivity`;
2. a predictor may map to multiple processes when its role is `composite`;
3. an undeclared process fails closed;
4. an uncovered ecological predictor fails closed;
5. digest is deterministic under input-row permutation.

Example shared carrier:

```python
registry = pd.DataFrame([
    {"predictor": "temp", "process": "thermal", "role": "direct"},
    {"predictor": "pet", "process": "thermal", "role": "composite"},
    {"predictor": "precip", "process": "water", "role": "direct"},
    {"predictor": "pet", "process": "water", "role": "composite"},
    {"predictor": "bio15", "process": "seasonality", "role": "direct"},
    {"predictor": "rsds", "process": "radiation_energy", "role": "direct"},
    {"predictor": "soil_n", "process": "soil_substrate", "role": "direct"},
    {"predictor": "ndvi", "process": "productivity", "role": "direct"},
])
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `pytest -q tests/test_process_id_registry.py`

- [ ] **Step 3: Implement taxonomy and deterministic registry freeze**

Digest input is canonical CSV of normalized `predictor,process,role` rows plus ordered process/predictor universes, hashed with SHA-256.

- [ ] **Step 4: Run focused tests**

Run: `pytest -q tests/test_process_id_registry.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `Freeze SDMR v3 plant process registry`

---

### Task 3: W1–W8 known-truth worlds

**Files:**
- Create: `src/sdmr/process_id/known_truth/__init__.py`
- Create: `src/sdmr/process_id/known_truth/worlds.py`
- Test: `tests/test_process_id_known_truth_worlds.py`

**Interfaces:**
- Produces: `KNOWN_TRUTH_WORLDS = ("unique_process", "redundant_representation", "shared_carrier", "null_correlated", "interaction", "observation_confounded", "omitted_driver", "geographic_shift")`
- Produces dataclass `KnownTruthWorld` with:
  - `name: str`
  - `environment: pd.DataFrame`
  - `true_suitability: np.ndarray`
  - `occurrences: pd.DataFrame`
  - `background: pd.DataFrame`
  - `process_registry: pd.DataFrame`
  - `predictor_universe: tuple[str, ...]`
  - `process_universe: tuple[str, ...]`
  - `spatial_groups: np.ndarray`
  - `generating_processes: tuple[str, ...]`
  - `observation_unresolved_processes: tuple[str, ...]`
  - `model_pool_mask: np.ndarray`
- Produces: `simulate_process_world(name, *, seed, n_cells=4000, n_occurrences=400, n_background=1600) -> KnownTruthWorld`

- [ ] **Step 1: Write structural tests before simulator code**

Tests must assert:
- deterministic output for equal seed;
- W1 thermal is generating and has a nonredundant thermal signal;
- W2 thermal is generating while a non-thermal process predictor is deliberately redundant with the thermal truth signal;
- W3 has identical effective closure for thermal and water through a shared composite carrier;
- W4 seasonality is nongenerating but strongly correlated with thermal;
- W5 generating processes are thermal + water and suitability contains a joint interaction;
- W6 declares thermal in `observation_unresolved_processes`;
- W7 contains a hidden driver absent from `predictor_universe`;
- W8 has a proxy relation that changes between `model_pool_mask=True` and the held-out region.

- [ ] **Step 2: Run focused test and confirm failure**

Run: `pytest -q tests/test_process_id_known_truth_worlds.py`

- [ ] **Step 3: Implement one shared landscape generator and eight explicit truth functions**

All worlds use the same canonical predictor names:
`temperature, water, seasonality, radiation, soil, productivity, pet_shared, elevation_proxy`.

Registry mapping:
- temperature -> thermal/direct
- pet_shared -> thermal/composite and water/composite
- water -> water/direct
- seasonality -> seasonality/direct
- radiation -> radiation_energy/direct
- soil -> soil_substrate/direct
- productivity -> productivity/direct
- elevation_proxy -> radiation_energy/proxy

For W2, water is engineered to reconstruct the thermal truth sufficiently even after thermal closure.
For W3, truth is driven by `pet_shared` and exclusive temperature/water signals are attenuated so unique attribution is structurally ambiguous.
For W7, `hidden_driver` affects truth but is not part of the predictor universe or registry.
For W8, the correlation sign between `elevation_proxy` and temperature changes in the held-out half-space.

Occurrence sampling probability is proportional to `true_suitability * effort`; background samples from effort. W6 effort uses the same thermal gradient that drives suitability and marks thermal as structurally unresolved.

- [ ] **Step 4: Run structural world tests**

Run: `pytest -q tests/test_process_id_known_truth_worlds.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `Add SDMR v3 known-truth process worlds`

---

### Task 4: Oracle-state adapter and shared-carrier abstention

**Files:**
- Create: `src/sdmr/process_id/known_truth/oracle.py`
- Modify only if necessary: `src/sdmr/oracle_process_identifiability.py` (compatibility bugfixes only; no threshold changes)
- Test: `tests/test_process_id_oracle.py`

**Interfaces:**
- Consumes existing `oracle_process_identifiability(...)`
- Produces: `evaluate_oracle_states(world: KnownTruthWorld, *, n_splits=5, margin=0.02, sem_multiplier=1.0, baseline_r2_floor=0.80, required_r2_ceiling=0.0) -> pd.DataFrame`
- Output columns: `process, state, oracle_raw_state, closure_predictors, reason`

- [ ] **Step 1: Write mapping tests**

Map old oracle constants as:
- `oracle_replaceable_under_predictor_system -> replaceable`
- `oracle_contributory_under_predictor_system -> contributory`
- `oracle_required_under_predictor_system -> required`
- `oracle_contested_under_predictor_system -> unresolved`
- `oracle_unavailable -> unavailable`

- [ ] **Step 2: Write shared-carrier postprocessing test**

When two processes have identical closure predictor sets and both raw oracle states are positive (`contributory|required`), both final states become `unresolved` with reason `identical_shared_carrier_closure`.

This is an attribution boundary, not a change to the underlying truth-surface reconstruction result.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `pytest -q tests/test_process_id_oracle.py`

- [ ] **Step 4: Implement adapter**

Call the existing oracle with the world's declared predictors/processes/groups. Preserve raw states and selection receipt. Do not import Product-A promotion code.

- [ ] **Step 5: Add W7 unavailable test and W1/W4 sanity tests**

W7 full-system oracle must be allowed to return `unavailable`; W1 thermal should not be `replaceable`; W4 seasonality should be `replaceable` under deterministic test parameters.

- [ ] **Step 6: Run tests**

Run: `pytest -q tests/test_process_id_oracle.py`

Expected: PASS.

- [ ] **Step 7: Commit**

Commit message: `Adapt truth-surface oracle to SDMR v3 states`

---

### Task 5: Occurrence-only process challenge with observation-design refusal

**Files:**
- Create: `src/sdmr/process_id/evidence.py`
- Test: `tests/test_process_id_evidence.py`

**Interfaces:**
- Produces dataclass: `OccurrenceProcessEvaluation(evidence: pd.DataFrame, states: pd.DataFrame)`
- Produces: `evaluate_occurrence_processes(world, *, n_splits=5, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0, C=1.0) -> OccurrenceProcessEvaluation`
- Primary score: balanced presence/background mean log score from a logistic model; absolute probability is not claimed.
- Matched full and process-closure knockout fits use the same fold, learner hyperparameters, and background rows.

- [ ] **Step 1: Write tests for evidence bookkeeping**

Tests assert:
- one full/knockout paired delta per process × fold;
- no observation-only columns appear in ecological process closure;
- route completeness is explicit;
- process closure uses the frozen registry;
- same learner/fold is used for full and knockout.

- [ ] **Step 2: Write W6 refusal test**

For any process listed in `world.observation_unresolved_processes`, final state is `unresolved` with reason `observation_process_not_separable` regardless of a numerically favorable fitted delta.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `pytest -q tests/test_process_id_evidence.py`

- [ ] **Step 4: Implement balanced logistic score**

For each spatial fold:
1. concatenate training occurrences as label 1 and training background as label 0;
2. fit `sklearn.linear_model.LogisticRegression(C=C, penalty="l2", solver="lbfgs", max_iter=1000, random_state=0)`;
3. compute mean Bernoulli log score on matched held-out occurrence/background rows;
4. convert score difference to loss delta `full_log_score - knockout_log_score`, so positive values mean the knockout is worse;
5. summarize mean/SEM across folds per learner route;
6. set `knockout_adequate` from the frozen absolute log-score floor;
7. call `classify_process_state`.

- [ ] **Step 5: Run tests**

Run: `pytest -q tests/test_process_id_evidence.py`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `Add occurrence-only SDMR process challenge`

---

### Task 6: Known-truth benchmark metrics and KT-A–KT-F promotion gate

**Files:**
- Create: `src/sdmr/process_id/known_truth/benchmark.py`
- Create: `src/sdmr/process_id/known_truth/promotion.py`
- Test: `tests/test_process_id_known_truth_gate.py`

**Interfaces:**
- Produces: `compare_oracle_and_occurrence(oracle_states, occurrence_states) -> pd.DataFrame`
- Produces dataclass: `KnownTruthGateDecision(passed: bool, gates: dict[str, bool], metrics: dict[str, float], reasons: tuple[str, ...])`
- Produces: `evaluate_known_truth_gate(comparison, world_summary, *, min_positive_recovery, max_false_positive, max_overresolution, max_false_unique_attribution, min_sealed_transfer) -> KnownTruthGateDecision`

- [ ] **Step 1: Write comparison-metric tests**

Metrics:
- positive recovery: oracle `contributory|required` recovered as `contributory|required`;
- false-positive rate: oracle `replaceable` called `contributory|required`;
- over-resolution rate: oracle `unresolved` called any sharp state;
- false unique-attribution rate: shared-carrier/interaction world marked uniquely supported when oracle forbids it;
- sealed-transfer rate supplied by precomputed independent held-out world records;
- unavailable cells are excluded from directional numerators but retained in denominator bookkeeping.

- [ ] **Step 2: Write strict conjunction tests**

```python
decision = evaluate_known_truth_gate(... thresholds that all pass ...)
assert decision.passed
assert all(decision.gates.values())

decision = evaluate_known_truth_gate(... one metric just outside threshold ...)
assert not decision.passed
assert decision.gates["KT-C"] is False
```

KT-A checks oracle/world validity flags, KT-B positive recovery, KT-C false-positive safety, KT-D abstention calibration, KT-E false unique attribution, KT-F sealed transfer.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `pytest -q tests/test_process_id_known_truth_gate.py`

- [ ] **Step 4: Implement fail-closed gate**

Reject:
- missing required worlds;
- duplicate `world,seed,process` comparison cells;
- missing gate metrics;
- NaN directional metrics when the required denominator should exist;
- any attempt to compensate one failed gate with another passed gate.

- [ ] **Step 5: Run focused tests**

Run: `pytest -q tests/test_process_id_known_truth_gate.py`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `Add prospective SDMR known-truth promotion gate`

---

### Task 7: Package exports, frozen Phase-1 contract, and CI

**Files:**
- Modify: `src/sdmr/process_id/__init__.py`
- Create: `configs/sdmr_v3_process_id_phase1_contract.json`
- Create: `docs/SDMR_V3_PROCESS_ID_PHASE1.md`
- Create: `.github/workflows/sdmr-v3-process-id.yml`
- Test: `tests/test_process_id_phase1_contract.py`

**Interfaces:**
- Public exports: process states, default taxonomy, registry freeze, world simulator, oracle evaluation, occurrence evaluation, known-truth gate.
- Contract status starts `development_only`; no prospective seeds or thresholds are labeled validated until a later freeze commit.

- [ ] **Step 1: Write contract tests**

Tests assert:
- Product-A is explicitly `closed_not_reopened`;
- burned seed range includes historical `13001–13010`;
- W1–W8 names are exact;
- fresh empirical opening is `false`;
- contract points to the design spec;
- no prospective performance status is set to PASS.

- [ ] **Step 2: Add CI workflow**

Workflow triggers on pushes/pull requests touching:
- `src/sdmr/process_id/**`
- `tests/test_process_id_*.py`
- `configs/sdmr_v3_process_id_phase1_contract.json`

Command:

```bash
python -m pip install -e .
pytest -q   tests/test_process_id_states.py   tests/test_process_id_registry.py   tests/test_process_id_known_truth_worlds.py   tests/test_process_id_oracle.py   tests/test_process_id_evidence.py   tests/test_process_id_known_truth_gate.py   tests/test_process_id_phase1_contract.py
```

- [ ] **Step 3: Add concise developer document**

Document the scientific data flow, state meanings, W1–W8, and explicit statement that fresh empirical data remain unopened.

- [ ] **Step 4: Run focused Phase-1 suite**

Run the CI command locally where possible.

Expected: all Phase-1 tests PASS.

- [ ] **Step 5: Run compatibility tests for reused modules**

Run:

```bash
pytest -q   tests/test_process_information_closure.py   tests/test_sealed_occurrence_contract.py   tests/test_oracle_process_identifiability_development_contract.py
```

Expected: PASS; Product-A scientific files/results unchanged.

- [ ] **Step 6: Commit**

Commit message: `Freeze SDMR v3 Phase-1 development boundary`

---

## Phase-1 Completion Criteria

Phase 1 is complete only when:

1. all seven new focused test files pass;
2. compatibility tests for reused generic modules pass;
3. Product-A closure files are unchanged;
4. the branch contains no fresh empirical cohort identities or answer-check outcomes;
5. CI reports green for the exact branch head;
6. no KT threshold is described as prospectively validated merely because development tests pass.

The next plan may freeze prospective seeds/thresholds and execute the KT-A–KT-F experiment. A separate fresh-empirical implementation plan is permitted only after that prospective known-truth gate passes.
