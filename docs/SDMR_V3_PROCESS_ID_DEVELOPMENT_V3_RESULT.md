# SDMR v3 process-identification development v3 — terminal result

Status: **development-only terminal result / shared-closure guardrail improved / quadratic learner not promoted / not prospectively ready**

## Frozen execution

- workflow run: `35411700699`
- workflow head: `665b00be9408677d1cddba68bb461e6ba84942f7`
- prior activation run `35368536242` stopped during validation before scientific execution and produced no development artifact
- recovery activation was explicitly recorded as pre-execution recovery
- artifact: `sdmr-v3-process-id-development-v3`
- artifact id: `10573728147`
- artifact digest: `sha256:628ca2df7e216d4c587c74395da874fb908536c320f01fa1cdc13b2f93da8a54`
- config SHA-256: `aab450b3fa5a6329b91e19739b780a2b1865fa5eb42422641f4c71def08aa228`
- seeds: **23001–23008**, reused only as already-burned development evidence
- worlds: all W1–W8
- process cells: **384**
- Product-A boundary: **closed_not_reopened**
- fresh empirical data opened: **false**
- prospective validation seeds opened: **none**

Development v3 changed two declared elements relative to v2:

1. identical process-information closures force `unresolved` for **all sharp states** (`replaceable|contributory|required`), not only positive states;
2. the occurrence learner changed from linear logistic to an equal-prior **quadratic logistic** route with pairwise interaction capacity.

Margins, SEM multiplier, adequacy floor, worlds, seeds, sample sizes, oracle settings, and class-prior correction remained unchanged.

## v2 → v3

| metric | v2 | v3 |
|---|---:|---:|
| exact state agreement | 0.8727 | **0.7606** |
| positive recovery | 0.0667 | **0.0000** |
| false-positive rate | 0.00364 | **0.0000** |
| over-resolution rate | 0.200 | **0.040** |
| false unique-attribution rate | 0.000 | **0.000** |

The shared-closure logical repair worked: v2 had five over-resolved unresolved cells, including four shared-carrier thermal/water calls. v3 had only **1/25** over-resolved unresolved cells, the previously observed null-correlated thermal case at seed 23002. No shared-carrier cell was sharply attributed.

However, the quadratic learner did **not** improve positive recovery.

## Positive-recovery result

There were again **30 target-positive cells**:

- unique-process thermal: 8
- interaction thermal: 7
- interaction water: 7
- geographic-shift thermal: 8

Occurrence-side outcomes were:

- `contributory|required`: **0**
- `replaceable`: **12**
- `unresolved`: **13**
- `unavailable`: **5**

Thus positive recovery was **0/30**.

By target family:

- unique-process thermal: 5 replaceable, 3 unresolved
- interaction thermal: 3 replaceable, 3 unresolved, 1 unavailable
- interaction water: 1 replaceable, 5 unresolved, 1 unavailable
- geographic-shift thermal: 3 replaceable, 2 unresolved, 3 unavailable

Thermal positive recovery remained 0 and water positive recovery remained 0.

This falsifies the development hypothesis that adding pairwise interaction capacity alone would repair the positive-identification gap.

## Safety and abstention

No target-replaceable cell was called `contributory|required`, giving a development false-positive rate of **0/275**.

The over-resolution rate fell to **1/25 = 0.04**. The sole over-resolved cell was:

- null-correlated, seed 23002, thermal: target `unresolved` → occurrence `replaceable`.

No forbidden shared-carrier or interaction world/seed group produced false unique attribution.

These are useful safety properties, but they do not compensate for zero positive recovery.

## Availability cost of the quadratic route

The occurrence side returned `unavailable` for **66/384** process cells. This did not occur in v2.

Occurrence-unavailable cells were concentrated in:

- geographic-shift: 18
- omitted-driver: 30
- interaction: 6
- null-correlated: 6
- shared-carrier: 6

Five target-positive cells became occurrence-unavailable.

This shows that extra representational capacity also introduced an adequacy/variance cost under the frozen sample size and absolute score floor.

## World-level agreement

- unique-process: **0.8125**
- redundant-representation: **0.8958**
- shared-carrier: **0.8333**
- null-correlated: **0.7917**
- interaction: **0.5714**
- observation-confounded: **0.9583**
- omitted-driver: target unavailable by design
- geographic-shift: **0.4375**

Truth-surface oracle semantics were valid for **63/64 world × seed cases**. Interaction seed 23002 remained oracle-unavailable under the frozen baseline R² floor, as in the earlier development denominator.

## Decision

**Development v3 is not ready for prospective freezing.**

The v3 result supports one part of the redesign and rejects another:

- **supported development change:** identical-closure abstention should cover every sharp process state;
- **not supported:** simply increasing the occurrence learner from linear to quadratic is sufficient to recover positive process information.

No KT threshold is frozen from v3, and no prospective or fresh empirical data are opened.

## Next admissible diagnostic

The next step is **diagnostic, not another learner substitution**.

Using only the already-burned development seeds, audit every target-positive cell under the linear and quadratic routes and retain:

- fold-level full-model balanced log score;
- fold-level process-knockout balanced log score;
- paired delta;
- mean delta and SEM;
- lower/upper interval relative to the unchanged 0.01 margin;
- full and knockout adequacy relative to the unchanged -0.75 floor;
- final state and reason.

This diagnostic must determine whether positive recovery fails because of:

1. no observable full-versus-knockout information gap;
2. a gap exists but interval uncertainty crosses the margin;
3. the full model itself fails the absolute adequacy floor;
4. the process closure removes information that is still recreated by registered proxies/shared carriers;
5. learner misspecification remains despite quadratic capacity.

Only after locating that boundary should another development method version be designed. The same burned outcomes may diagnose development, but can never become prospective performance evidence.
