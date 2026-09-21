# SDMR v3 occurrence-distribution oracle audit v2 — terminal diagnostic

Status: **development-only terminal result / numerical-oracle correction successful / finite learner now dominant bottleneck / no prospective freeze**

## Frozen execution

- workflow run: `35495871747`
- workflow head: `7b617af22aebf105e11f92761e51354537880853`
- artifact: `sdmr-v3-occurrence-distribution-oracle-audit-v2`
- artifact id: `10601311224`
- artifact digest: `sha256:bc67412ccf10e40cd5039f204410bf31f96773de4d0f808268e2773e9192488c`
- config SHA-256: `09431a2a84c3f13d77becfeee74224b99f10a69f9f3b868e3bf8615948fd1148`
- seeds: **23001–23008**, reused only as already-burned development evidence
- worlds: all W1–W8
- process cells: **384**
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

Development v2 changed exactly one numerical-oracle element relative to v1: occurrence-distribution oracle cross-fitting changed from spatial GroupKFold to deterministic random KFold. The complete observation distributions, HGB numerical function class, biological margin 0.01, occurrence adequacy floor -0.75, SEM multiplier 1.0, Bayes-regret tolerance 0.01, worlds, sample profile and burned seeds were unchanged.

## v1 → v2 numerical-oracle repair

| quantity | v1 | v2 |
|---|---:|---:|
| ODO unavailable process cells | 221 / 384 | **48 / 384** |
| numerically inadequate process cells | 222 / 384 | **48 / 384** |
| truth-positive cells | 38 | 38 |
| truth-positive also ODO-positive | 7 / 38 | **30 / 38** |
| truth-positive → ODO-positive fraction | 0.184 | **0.789** |

The remaining 48 ODO-unavailable cells are exactly the six processes × eight seeds of `omitted_driver`, where the hidden driver is absent from the declared predictor system. This is the intended unavailable case.

Thus the seed-locked numerical failures seen under spatial cross-fitting were artifacts of mixing population identifiability with spatial extrapolation, not genuine occurrence-distribution non-identifiability.

## Occurrence-distribution states after correction

Across 384 process cells:

- `contributory`: **32**
- `replaceable`: **280**
- `unresolved`: **24**
- `unavailable`: **48**

The positive ODO cells are structurally clean:

- unique_process thermal: **8/8 contributory**
- interaction thermal: **8/8 contributory**
- interaction water: **8/8 contributory**
- geographic_shift thermal: **8/8 contributory**

Shared-carrier thermal/water remain `unresolved` for all eight seeds because their process closures are identical.

Observation-confounded thermal remains `unresolved` for all eight seeds because ecology and observation effort are not separable under the declared observation architecture.

The 38 truth-surface-positive cells decompose as:

- **30** also ODO-positive;
- **8** ODO-unresolved, all eight being the intended W6 observation-confounded thermal cells.

Therefore, after numerical correction, no truth-surface-positive cell is lost to ordinary occurrence-distribution replaceability.

Two interaction seed-23002 cells are ODO-positive while the truth-surface oracle was unavailable for that world-seed because the older truth-surface numerical oracle failed its own adequacy check. They are retained as occurrence-distribution-positive development cells rather than being silently discarded.

## Finite learner result conditional on ODO-positive cells

There are **32 ODO-positive cells**.

### Linear finite learner

- recovered positive: **2 / 32 = 0.0625**
- unresolved: **12 / 32**
- replaceable: **18 / 32**

The two recovered cells are geographic-shift thermal.

### Quadratic finite learner

- recovered positive: **0 / 32**
- unresolved: **15 / 32**
- replaceable: **12 / 32**
- unavailable: **5 / 32**

Thus aligning the learner denominator to occurrence-distribution identifiability does **not** rescue finite-sample recovery. The dominant remaining bottleneck is now downstream of the population oracle.

## Safety

Among ODO-replaceable cells:

- linear false-positive rate: **0.00357**
- quadratic false-positive rate: **0.00000**

Among ODO-unresolved cells, finite over-resolution was **0** for both learners.

The single linear positive call outside the ODO-positive set occurred in a target-replaceable cell and remains a development false positive.

## Scientific interpretation

The revised hierarchy is now empirically supported within the simulator:

```text
truth-surface process information
        ↓
occurrence-distribution process information
        ↓
finite-sample process recovery
```

The first transition contracts only where the observation architecture itself blocks attribution: W6 observation confounding.

The large remaining loss occurs at the second transition: finite sampled occurrences/backgrounds do not reliably establish the ODO-positive score gaps under the current learner/evidence design.

Therefore future finite-learner recovery must be evaluated against **ODO-positive cells**, not raw truth-surface-positive cells.

However, the current finite learner is not ready for prospective validation because recovery remains 2/32 for linear and 0/32 for quadratic.

## Decision

**ODO v2 is adequate as the development target for occurrence-only process identification, but the finite-sample SDMR procedure is not prospectively ready.**

Do not tune the 0.01 margin or -0.75 floor against these results.

The next diagnostic must separate:

1. finite learner function-class mismatch;
2. finite-sample information/power;
3. interval-estimation conservatism.

A factorial development audit should vary learner capacity and sample size while leaving ODO states, margin, adequacy floor, process closure, and burned worlds fixed.

Only ODO-positive cells are the positive-recovery denominator in that diagnostic.

No current v2 result is prospective evidence.
