# SDMR v6 full-pipeline integration v1 — terminal result

Status: **development integration FAIL / INT-E only / authorization gate itself behaved correctly / prospective seeds remain unopened**

## Frozen execution

- workflow run: `36122603465`
- workflow head: `e13d2e6f76c8e038c7215395e92c9eda9db3d45a`
- terminal artifact: `sdmr-v6-full-pipeline-integration-v1`
- artifact id: `10857564844`
- artifact digest: `sha256:bb07b4a5d4e65ca48f180dc54fc2ee564c8c952bdfd46f84b0fb2fd9ccf1dd9d`
- integration seeds: **73001–73020**
- prospective seeds 74001–74020 opened: **false**
- fresh empirical data opened: **false**

## Frozen conjunction

- INT-A: PASS
- INT-B: PASS
- INT-C: PASS
- INT-D: PASS
- INT-E: **FAIL**
- INT-F: PASS

Overall: **FAIL**.

## Process-state performance

- Stage-P positive recovery: **0.8875 = 71/80**
- false-positive rate among ODO-replaceable: **0/700**
- over-resolution among ODO-unresolved: **0/60**
- structural-refusal violation: **0/60**
- unavailable favorable-positive rate: **0/120**
- unavailable sharp-state rate: **0/120**
- Stage-P-positive → spatial-replaceable contradiction: **0.02817**
- spatial structural-refusal violation: **0**

Thus the full process-state and transfer layers satisfied their frozen safety/recovery requirements.

## Full-system authorization by world

| world | authorized |
|---|---:|
| unique_process | **20/20** |
| redundant_representation | **20/20** |
| shared_carrier | **20/20** |
| null_correlated | **20/20** |
| interaction | **20/20** |
| geographic_shift | **20/20** |
| observation_confounded | **1/20** — report-only |
| omitted_driver | **0/20** |

The v6 magnitude-permutation authorization layer therefore behaved exactly as intended on its predeclared informative controls and W7 null control.

## Exact INT-E failure

The frozen v1 integration contract defined:

```text
minimum_non_w7_authorization_rate >= 0.95
```

The implementation computed this across **all non-W7 worlds**, including W6 `observation_confounded`.

But W6 had been explicitly declared **report-only** during both v6 validation and confirmation because its focal thermal process is structurally nonseparable from observation effort.

Observed non-W7 authorization:

```text
six informative controls: 120/120
W6 report-only:            1/20
--------------------------------
pooled non-W7:            121/140 = 0.8642857
```

Therefore INT-E failed even though:

- every predeclared informative control authorized 100%;
- W7 authorized 0%;
- unavailable process states never sharpened.

## Interpretation

This is a **contract-scope/estimand mismatch**, not a failure of the v6 magnitude-permutation gate.

Validation and confirmation had consistently defined:

- W1/W2/W3/W4/W5/W8 = informative controls;
- W6 = report-only;
- W7 = null control.

Integration v1 accidentally replaced that structure with a pooled `non-W7` denominator.

The integration contract must not be rescored post hoc.

## Non-retroactivity

Integration v1 remains failed.

Prohibited:

- excluding W6 and retroactively calling v1 a pass;
- changing the 0.95 threshold and rescoring;
- opening prospective seeds 74001–74020 under the failed v1 integration contract.

Seeds 73001–73020 are burned.

## Next admissible design

Create **SDMR v6 full-pipeline integration v2** with fresh development seeds and explicit authorization scope:

- informative controls = W1/W2/W3/W4/W5/W8;
- W6 = report-only;
- W7 = null control;
- each informative control must authorize >=95%;
- W7 must authorize 0%;
- all other INT-B/C/D/F criteria unchanged.

No learner, sample size, permutation setting, magnitude threshold, ODO rule, process margin, or state definition changes.

Fresh integration seeds:
`75001–75020`.

The already-reserved prospective denominator `74001–74020` remains unopened and may be retained for a new prospective contract because its outcomes have never been accessed.
