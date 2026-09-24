# SDMR v4 full-system gate calibration implementation plan

**Goal:** Calibrate and independently confirm the finite full-system information authorization rule after the prospective v3 KT-E failure.

## Task 1 — full-model information evaluator

Create:
- `src/sdmr/process_id/known_truth/full_system_calibration.py`
- `tests/test_process_id_full_system_calibration.py`

Interfaces:
- `FullSystemInformationEvaluation`
- `evaluate_full_system_information(world, *, split_mode="random_cell", learner="hgb", hgb_profile="shallow3", n_splits=3, adequacy_floor=-0.75) -> FullSystemInformationEvaluation`
- `evaluate_information_candidates(summary, multipliers) -> pd.DataFrame`

The evaluator must fit only the complete predictor system. It may reuse finite split and probability helpers from `evidence.py`.

Output per world/seed:
- fold full scores;
- mean full score;
- gain over -log(2);
- SEM gain;
- lower gain for every frozen candidate multiplier.

## Task 2 — deterministic calibration panel

Create:
- `configs/sdmr_v4_full_system_gate_calibration_v1.json`
- runner/workflow sharded by world × seed block.

Frozen:
- seeds 41001–41100;
- 8 worlds;
- 8x sample;
- shallow3;
- random_cell;
- candidate grid [1.0,1.645,1.96,2.326,2.576,3.09].

No process knockouts.

## Task 3 — candidate selector

Create:
- `select_full_system_gate_candidate(summary, config)`

Selection:
- W7 <= 0.01;
- each W1/W2/W3/W4/W5/W8 >= 0.95;
- W6 report-only;
- choose smallest qualifying multiplier;
- fail closed if none.

Persist selected multiplier plus all candidate rates.

## Task 4 — independent confirmation

Only after a calibration candidate is terminally selected, freeze:
- seeds 42001–42050;
- selected multiplier unchanged.

Confirmation:
- W7 = 0/50 authorized;
- each informative control >=48/50;
- W6 report-only.

No reselection.

## Task 5 — future prospective reservation

Record 43001–43020 as reserved/unopened. Do not create an activation marker until v4 integration testing is complete.
