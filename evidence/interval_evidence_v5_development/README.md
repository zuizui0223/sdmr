# v5 interval-evidence development: frozen readout

**Development only. Product A remains closed. No prospective performance claim.**

This records completed PR #202 development evidence. It does not change the
learner, runner, workflow, scientific contract, seeds, thresholds, model grid,
process closure, shared-carrier settings or observation correction. It does not
open answer-check data or start another simulation. The audit is retrospective
bookkeeping, not a newly predeclared scientific pass/fail rule.

## Provenance and completed CI

Source repository: `zuizui0223/sdmr`, PR #202.
Source head: `f3b95c7aa5ea0f559b54dc797ec46fda141582c8`.
Tests run: `34037107404`; all five required jobs completed successfully:
`core-py3.10`, `core-py3.11`, `core-py3.12`, `core-py3.13`,
`geo-rasterio-py3.12`.
Development run: `34037107229`, attempt 1; gate, all six families and aggregate
completed successfully. Aggregate completed `2026-09-06T13:55:44Z`
(`2026-09-06 22:55:44 JST`).
Aggregate artifact: `9990648093`. The original ZIP is preserved here byte for
byte, so the readout does not depend on GitHub Actions artifact retention.

- [Source PR](https://github.com/zuizui0223/sdmr/pull/202)
- [Required tests](https://github.com/zuizui0223/sdmr/actions/runs/34037107404)
- [Development run](https://github.com/zuizui0223/sdmr/actions/runs/34037107229)

`shard_audit.json` records the original six artifact IDs and SHA256 digests.
All six downloaded ZIP digests matched GitHub metadata. Their process and case
tables, concatenated and sorted, matched the aggregate exactly as parsed tables.
This was an audit of existing artifacts, not another fit or run attempt.

## Unchanged contract

Burned denominator: seeds 13001–13010 x six frozen families = 60 cases.
Five process cells per case = 300 cells; true 130, false 170.
Rank margin 0.02; density margin 0.01 nats; both relative SEM multipliers 1.0.
All baseline science is pinned by the source head and these config blob SHAs:

| Config | Git blob SHA |
|---|---|
| v5 development | `097280fbee343f79b858b7162d05e04ef0ac0bec` |
| v4 development | `8ecccbf3733b163ee38bf38cead28b24f5a3e88e` |
| base science successor v2 | `e37c6e672646d097479afc8f4875288c35403d70` |

The candidate model grid has six entries. The inherited v3 baseline-adequacy
filter determines which labels supply process-exclusion routes. Expected route
counts are therefore 3 in 15 cases, 5 in 1 case and 6 in 44 cases, consistently
across each case's five processes. This is **not** a changed model grid or missing
family/case. The audit must not silently replace this inherited rule by demanding
six process baselines in every case.

## Recomputed results

| Generating truth | Contributory | Replaceable | Unresolved | Required | Total |
|---|---:|---:|---:|---:|---:|
| True process | 49 | 38 | 43 | 0 | 130 |
| False process | 0 | 157 | 13 | 0 | 170 |
| Total | 49 | 195 | 56 | 0 | 300 |

True-process challenge recall: **49/130 = 37.6923%**.
False-process challenge rate: **0/170 = 0% observed**.
Unique-attribution counts/rates coincide in this run (49/130 and 0/170).
False required: 0/170; total required: 0. No contested-shared attribution.
Zero observed false challenges is not a population guarantee.

| Family | Contributory | Replaceable | Unresolved | Required | True challenge | False challenge |
|---|---:|---:|---:|---:|---:|---:|
| gaussian | 4 | 32 | 14 | 0 | 4/20 | 0/30 |
| asymmetric | 9 | 35 | 6 | 0 | 9/20 | 0/30 |
| soft_threshold | 10 | 33 | 7 | 0 | 10/20 | 0/30 |
| interaction | 9 | 35 | 6 | 0 | 9/20 | 0/30 |
| omitted_driver | 6 | 32 | 12 | 0 | 6/30 | 0/20 |
| observation_confounded | 11 | 28 | 11 | 0 | 11/20 | 0/30 |

All 56 raw v4-to-v5 changes are contributory -> unresolved: 43 true and 13
false process cells. The other 244 raw process statuses are unchanged.
The `v4_status` column is **pre-attribution**. It does not establish a paired
comparison against historical v4 shared-carrier/unique-attribution results.

All 300 cells report zero incomplete routes. The 56 unresolved cells have
viable indeterminate relative-evidence routes, not reported implementation
failures. The original route summaries/intervals are not included in the ZIP,
so the audit checks their exported counters, not the underlying interval values.

The 81 undetected true cells separate into 43 unresolved and 38 replaceable.
Thus non-detection must not be described uniformly as uncertainty or absence:
replaceable means a surviving noninferior exclusion route under this contract,
not that the generating ecological process is absent. Likewise contributory is
not required, and neither statement alone establishes a real-world mechanism.

## Offline reproduction

From the repository root, with Python 3.10 or newer:

```bash
python scripts/audit_interval_evidence_v5_readout.py --output /tmp/v5-readout.json
python -m pytest -q tests/test_interval_evidence_v5_readout_audit.py
```

The stdlib-only audit verifies the pinned archive digest, exact unique 60-case
and 300-cell denominators, strict boolean flags, receipt format, occurrence
partition counts, prediction-label membership, known-truth labels, process
status consistency with exported route counters, attribution flags, and every
overall/family metric. It also exports the truth-by-status table and raw v4-to-v5
transition counts. `readout_audit.json` is the deterministic output.

The 36 regression tests include missing/duplicate cases and cells, wrong truth,
invalid booleans, sealed/proxy boundary flag violations, altered receipts/model
labels, inconsistent route counters, metric changes, and modified archive bytes.
They inspect the frozen artifact only; they never fit a model or draw new seeds.

## Limits and terminal boundary

This is artifact consistency, not independent refitting, receipt recomputation
or proof of no leakage. The source runner uses the sealed model-pool split;
the audit checks its exported flags and partition counts. Occurrence-ID manifests,
raw interval endpoints and fitted models are not present in this bundle.

Development readout is complete. No new seeds are selected, no prospective run
is authorized, and Product A is not reopened. A future prospective evaluation
would need a separately authorized frozen contract and unused seeds; this
readout neither supplies nor dispatches them. No threshold retuning or rescue
run follows from these development outcomes.
