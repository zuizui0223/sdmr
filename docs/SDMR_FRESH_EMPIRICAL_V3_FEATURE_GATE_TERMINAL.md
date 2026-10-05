# SDMR fresh empirical v3 — feature-gate terminal result

## Terminal decision

The fresh empirical v3 programme stopped **before model fitting and before any answer-check environmental value was opened**.

Authoritative execution:
- workflow run: `37128999833`
- artifact: `11278021879`
- artifact digest: `sha256:db80f36ca78a1af090b02bd1342e9750707fc542519ff7ea460bc2823b5d0a67`
- final50 manifest SHA-256: `4b49f457bcf8b74969e39144789c8e20a3b9739558475290f0a7abf77d7f9359`

Result:
- declared taxa: **50**
- taxa passing the frozen 46-predictor complete-case gate: **48/50**
- required: **50/50**
- terminal status: `v3_feature_gate_terminal_unavailable`

Failed taxa:
- *Luzula arcuata*: model-pool complete rows **179/535**, retention **0.334579**; background complete rows **4032/5000**
- *Micranthes foliolosa*: model-pool complete rows **153/456**, retention **0.335526**; background complete rows **4043/5000**

Frozen gate:
- model-pool retention >= 0.80;
- model-pool complete rows >= 50;
- background complete rows >= 4000;
- all 50 declared taxa required;
- no replacement, predictor deletion, threshold relaxation or new value-dependent decoding.

The two failed taxa satisfied the absolute minimum model-row and background-row counts, but failed the prospectively frozen model-pool retention criterion.

## Information boundary

At terminal closure:
- environmental values read: **yes**, model-pool/background only;
- answer-check access: **no**;
- model fitting: **no**;
- process states: **not generated**;
- prediction metrics: **not generated**;
- EMP-A through EMP-F: **not opened**;
- taxon replacement: **no**;
- predictor deletion: **no**;
- threshold relaxation: **no**.

Therefore this is an **availability/feature-completeness terminal**, not evidence for or against empirical process-information performance.

## Relation to M5

The prospective known-truth M5 result remains unchanged:
- positive recovery 71/80 = 0.8875;
- false positives 0/700;
- unresolved over-resolution 0/60;
- structural-refusal violations 0/60;
- KT-A through KT-F all PASS.

Fresh empirical v3 was an independent external-validation lane and cannot reclassify that result.

## Post-terminal diagnostic

A diagnostic-only audit is authorized to decompose missingness for the two failed taxa.

That audit is forbidden from:
- opening answer-check data;
- fitting models;
- replacing taxa;
- deleting predictors;
- relaxing thresholds;
- adding new decoding rules.

Its result may explain the availability failure but cannot rescue or reopen v3.

## Development stop

No model-pool process fitting or sealed scoring is authorized under v3.

A future empirical programme, if any, must be a separately frozen successor whose cohort eligibility is defined before focal environmental values or answer-check outcomes are opened. The v3 denominator is consumed and remains terminal.
