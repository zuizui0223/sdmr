# SDMR v3 prospective known-truth v3 — terminal result

Status: **prospective terminal FAIL / KT-E only / fresh empirical validation remains closed**

## Frozen prospective execution

- workflow run: `35998363272`
- workflow head: `bbb4960e51c9e92bea5178997a5cb13ba67cd3cd`
- terminal artifact: `sdmr-v3-prospective-kt-v3`
- artifact id: `10808210084`
- artifact digest: `sha256:b1af8f272a9ae9981e0658f303819c59621cdaeea435149e79b4820f5c3cb066`
- prospective seed denominator: **33001–33020**
- first and only opening of those seeds: this execution
- fresh empirical data opened: **false**
- Product-A: **closed_not_reopened**

The scientific contract, sample size, learner, process margin, full-system gate, and KT-A–KT-F thresholds were frozen before these outcomes were opened.

## Frozen gate result

| gate | result |
|---|---|
| KT-A target / provenance integrity | **PASS** |
| KT-B Stage-P positive recovery >= 0.80 | **PASS** |
| KT-C false-positive rate <= 0.01 | **PASS** |
| KT-D unresolved/refusal integrity | **PASS** |
| KT-E whole-system unavailability | **FAIL** |
| KT-F spatial transfer safety | **PASS** |

Strict conjunction:

```text
KT-A & KT-B & KT-C & KT-D & KT-E & KT-F
= FALSE
```

Therefore prospective v3 is **not promoted**.

## Prospective metrics

Declared ODO denominator:

- positive: **80**
- replaceable: **700**
- unresolved: **60**
- unavailable: **120**
- structural refusal: **60**

Observed endpoints:

- Stage-P positive recovery: **70/80 = 0.875**
- false-positive rate among ODO-replaceable: **0/700 = 0**
- over-resolution among ODO-unresolved: **0/60 = 0**
- structural-refusal violation: **0/60 = 0**
- unavailable favorable-positive rate: **0/120 = 0**
- unavailable sharp-state rate: **6/120 = 0.05**
- non-W7 full-system information adequacy: **139/140 = 0.992857**
- W7 omitted-driver full-system information adequacy: **1/20 = 0.05**
- Stage-P-positive → spatial-replaceable contradiction: **1/70 = 0.014286**
- spatial structural-refusal violation: **0**

All frozen thresholds were met except KT-E, which required both W7 adequacy and unavailable sharp-state rate to equal zero.

## Exact KT-E failure

The entire KT-E failure is one prospective ecological seed:

`seed 33009 / omitted_driver`

For that world:

```text
mean full-system gain over null = 0.001449
SEM                            = 0.000655
lower gain = mean - 1*SEM      = 0.000794 > 0
full balanced log score        = -0.691698
null score                     = -log(2) ≈ -0.693147
```

The frozen full-system information gate therefore declared the system informative.

All six process closures then produced `replaceable`:

- thermal
- water
- seasonality
- radiation_energy
- soil_substrate
- productivity

Thus the 120 ODO-unavailable cells decomposed as:

- `unavailable → unavailable`: **114**
- `unavailable → replaceable`: **6**
- `unavailable → contributory|required`: **0**

This is a **false availability / sharp-negative** error, not a favorable false-positive process claim.

## Other prospective performance

Positive recovery by world:

- unique_process: **20/20 = 1.00**
- interaction: **38/40 = 0.95**
- geographic_shift: **12/20 = 0.60**

Positive recovery by process:

- thermal: **50/60 = 0.8333**
- water: **20/20 = 1.00**

The single Stage-T contradiction was:

`seed 33016 / geographic_shift / thermal`

Stage P called `contributory`; the spatial transfer endpoint called `replaceable`.

This produced the prospective spatial contradiction rate **1/70 = 0.0143**, below the frozen 0.05 threshold.

## Root-cause diagnosis

The Stage-P full-system gate used:

```text
mean full score >= -0.75
AND
mean gain over -log(2) - 1*SEM > 0
```

The second term is an uncertainty-aware zero-information test, but **1×SEM is not a calibrated Type-I error criterion**.

Under a true no-information W7 system, finite sampled records can occasionally produce a positive cross-fitted gain. Seed 33009 is exactly such an event.

The prospective outcome therefore identifies a distinct failure mode:

> process-specific positive/negative evidence can be safe while the upstream finite-data authorization to ask the process question still has nonzero false-availability probability.

This is not repaired within v3.

## Non-retroactivity

Prospective v3 remains failed.

The following are prohibited:

- changing KT-E and rescoring v3;
- replacing seed 33009;
- dropping W7;
- increasing sample size and calling the same denominator prospective;
- changing the information-gate multiplier and reinterpreting v3 as a pass.

Seeds 33001–33020 are permanently burned and may only be used for postmortem/development.

## Next admissible programme

Create **SDMR v4 development** whose only target is calibration of the full-system information authorization layer.

Do not alter:

- process-state definitions;
- ODO v2;
- shallow3 probability-quality selection logic;
- process margin 0.01;
- Stage-P/Stage-T separation.

The next development question is:

> What predeclared full-system informativeness rule controls false availability under W7 while retaining adequate authorization in genuinely informative worlds?

That rule must be calibrated on development-only seeds and then evaluated on a completely unused prospective denominator.

Fresh empirical plant validation remains closed.
