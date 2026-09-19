# SDMR v3 process-identification development v1 — terminal result

Status: **development-only terminal result / not prospectively ready**

## Frozen execution

- workflow run: `35364827050`
- workflow head: `d518430facdcf2a63263a695aaf5b52222b1bb16`
- artifact: `sdmr-v3-process-id-development-v1`
- artifact id: `10556187737`
- artifact digest: `sha256:d2302354a1adf291186dc0263dc335db694c050bc7a38d5d70d8f1c83e94495d`
- config SHA-256: `c81c970c7641b64b1c665938e5d237bbdc84c9f5e089e8458a2f9f9790112a6a`
- seeds: **23001–23008**, now permanently burned for prospective performance claims
- worlds: all W1–W8
- process cells: **384**
- Product-A boundary: **closed_not_reopened**
- fresh empirical data opened: **false**

No KT threshold was frozen or changed after seeing this result.

## Overall development result

| metric | result |
|---|---:|
| positive recovery | **0.000** |
| false-positive rate | **0.000** |
| over-resolution rate | **0.000** |
| false unique-attribution rate | **0.000** |
| exact state agreement, excluding target-unavailable cells | **0.100** |
| target-unavailable cells | **54 / 384** |
| occurrence-side `unavailable` calls | **346 / 384 = 0.901** |

The zero false-positive, over-resolution and false-unique-attribution rates are not evidence of a successful conservative method because the occurrence layer abstained as `unavailable` on about 90% of all process cells.

Positive recovery was **0/30** positive target cells. Thermal positive recovery was 0 and water positive recovery was 0.

## World-level result

- `unique_process`: exact agreement **0.000**
- `redundant_representation`: **0.000**
- `shared_carrier`: **0.000**
- `null_correlated`: **0.000**
- `interaction`: **0.000**
- `observation_confounded`: **0.6875**
- `omitted_driver`: exact agreement undefined because all target states were unavailable as intended
- `geographic_shift`: **0.000**

Truth-surface oracle semantics were valid for **63/64 world × seed cases**. The single exception was interaction seed 23002, where all six oracle process states became unavailable under the frozen baseline R² floor. This is a development diagnostic and is not repaired in-place.

## State confusion

The authoritative confusion table is stored in `results/sdmr_v3_process_id_development_v1_state_confusion.csv`.

The dominant cells were:

- target `replaceable` → occurrence `unavailable`: **245**
- target `contributory` → occurrence `unavailable`: **28**
- target `required` → occurrence `unavailable`: **2**
- target `unresolved` → occurrence `unavailable`: **17**

Only the observation-confounded family regularly produced non-unavailable occurrence states.

## Load-bearing diagnosis

The v1 occurrence challenge states that its primary score is a **balanced, equal-prior presence/background log score**, but its logistic learner was fitted on the raw imbalanced sample counts: 180 occurrences versus 600 background records.

With no discrimination signal, an unweighted logistic intercept estimates the sample prevalence

[
180/(180+600) approx 0.231.
]

Evaluating that prediction with an equal-prior balanced log score gives approximately

[
0.5{log(0.231)+log(0.769)}approx -0.864,
]

which is already below the frozen v1 adequacy floor of (-0.75). Thus the fitting target and scoring target use different class priors. A route can be declared ecologically unavailable even before process information is meaningfully challenged.

This is an **estimand/implementation mismatch**, not evidence that the process identified-set concept failed and not a justification for tuning the (-0.75) floor against the observed outcomes.

## Decision

**Development v1 is not ready for prospective freezing.**

The next admissible development version must align fitting with the declared equal-prior density-ratio score, for example by fitting the logistic learner with balanced class weights or mathematically equivalent sample weights. That correction must be covered by a direct null-signal calibration test before rerunning the already-burned development seeds.

Any v2 development rerun may use only burned/development evidence. It cannot become prospective evidence, and the eventual prospective denominator must remain untouched.

The v1 result remains authoritative as the terminal record of this implementation version.
