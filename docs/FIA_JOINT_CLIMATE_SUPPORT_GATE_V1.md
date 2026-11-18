# Joint temperature–precipitation support gate: archive boundary and source-only design (2026-11-15)

**Status:** offline diagnostic and future source-only design scaffold, revised v1.1 for time-matched unique-plot coverage on the exploratory PR #284 branch. No SDMR Product-A, Product-B or M5 endpoint is reopened. This does **not** claim evidence for climatic constraint switching or niche evolution.

## Completed first-open v4 re-audit (not a new biological test)

[The original one-run Actions source and response](https://github.com/zuizui0223/sdmr/actions/runs/40543320267) is fixed at artifact 12751849450, ZIP SHA-256 `66fe0e81815f99b0112b991f1ee6f766f968889fc858989e4a2f878993cfcaa3`. Extracted first-run receipts have independently checked SHA-256 strings hard-coded in `experiments/fia_joint_support_gate_v1.py`. The exact complete derived audit has SHA-256 `5b9711f23dad5c847bdbfd395599f8e45caa932347a790d9b667f4539d1e0bc6`. A compact terminal result and per-species marginal intervals are versioned under `results/` in this PR.

The original v4 result has per-species and per-state **minimum/maximum** of `tanom3` and `panom200`, not all matched bivariate observations. For **13/13** fixed species, each variable's individual marginal intervals overlap across RI, VA and WI. For **13/13**, actual joint climate support is **unknown / not evaluable**. The number of measured joint-overlap positive cases is **not zero biological overlaps**: it is **zero measurements**, with **13 unknown**.

The stored climate ranges and RI sample sizes are conditional on opening the original live–live growth cohort. Consequently they may only be used for this **retrospective estimability audit**, never for future outcome-blind source eligibility.

The first-open archive includes no exact per-species `(T,P,county,plot,measurement interval)` tuples. No Gaussian assumption, rectangle cross-product, nearest-neighbour approximation or independent sample inflation may be used to turn separate min/max values into empirical joint support.

## Source-only input for a distinct, independent future study

`experiments/fia_joint_support_gate_v1.py` provides an offline, fail-closed interface. A source-only CSV must contain exactly:

`species_code,state,county_fips,plot_chain_id,interval_id,interval_end_year,temperature_anomaly_c,precipitation_anomaly_mm`

One row is **one taxon × plot-chain × remeasurement interval**, not one tree. `interval_end_year` is the four-digit FIA PLOT measured end year (1991–2026), not `TREE.INVYR` and not the midpoint of the NOAA climate window; periods with unknown end year must be excluded with a recorded source-only denominator. Plot chains whose county identity changes are rejected rather than silently reconciled. Deduplicate before loading and retain the complete declared denominator, including unavailable taxa. County FIPS must match RI `44`, VA `51`, WI `55`. The temperature and precipitation anomalies must be derived on the same full intervening April–September months between *measured* PLOT dates, relative to the already defined 1991–2020 NOAA baseline. Never impute unmeasured months, and never equate county anomalies to actual tree water stress.

The CSV must be SHA-256-verified against a separate receipt with `status: source_only_pre_response`, `no_status_diameter_growth_read: true`, `species_identity_only_not_survivor_selected: true`, `climate_source: NOAA_20261006_county_interval_anomalies`, and exact `sha256`. The receipt is a **provenance declaration requiring independent human audit**, not cryptographic proof of which FIA columns were originally opened. Do **not** build eligibility from previously selected live→live survivors or from later outcomes. A new mutable FIA download is a **new cohort** and cannot stand in for the old frozen v4 ZIPs.

### How the structural gate works

- Place every paired anomaly in a fixed 2D grid, anchored at `0°C, 0 mm`, with *illustrative* widths `1°C × 100 mm`. Use signed floor bins (including negative anomalies), never marginal interval cross-products. Assign each source interval by **measured end year** to a fixed 5-year cohort starting in 1990; these are comparison strata, not inferred historical climatic optima.
- Only count a grid cell when it contains enough **distinct counties and plots** per region. Treat a plot observed in different intervals as **one** independent plot: the **primary coverage fraction is the fraction of unique (county, plot-chain) units** in time-aligned shared cells. Plot–interval coverage remains a secondary diagnostic but cannot pass the gate.
- Report both the environmental-only intersection and the **temperature × precipitation × 5-year cohort** intersection across all declared regions. **Only the time-aligned intersection can pass**. This rejects falsely shared opportunities when one region was sampled decades later. Preserve each species and region even when missing, with exact denominator, coverage fractions and reasons for non-eligibility.
- This **coarse observational shared-bin** condition is a necessary design check, **not** exact equality of climates, independent physiological fitness, niche conservation, or demographic transfer. A bin can hide different within-bin environments.
- The example config's 5 counties/region, 25 plots/region, 2 counties and 5 plots/bin/period, 2 time-aligned shared bins, ≥20% *unique-plot* coverage is **a development configuration chosen after the legacy v4 response was opened**. It is **not** a preregistered test or rescue of v4. For a new independent cohort, externally justify and freeze all cutoffs and bin-origin/width sensitivities *before* opening any new growth or survival response.

## How to run

Archived v4 (actual result; must remain unavailable):

```bash
python experiments/fia_joint_support_gate_v1.py \
  --config configs/fia_joint_climate_support_gate_v1.json \
  --archive-v4 path/to/verified_first_artifact_12751849450.zip \
  --output build/fia_joint_support_legacy_boundary.json
```

Future **source-only** record table, after auditing receipt identity (does not open any growth):

```bash
python experiments/fia_joint_support_gate_v1.py \
  --config configs/fia_joint_climate_support_gate_v1.json \
  --samples source_only_new_cohort.csv \
  --source-receipt source_only_new_cohort_receipt.json \
  --output build/fia_joint_support_new_cohort.json
```

Offline controlled tests:

```bash
python -m pytest -q tests/test_fia_joint_support_gate_v1.py
```

Tests include **identical marginal ranges but disjoint two-dimensional occupied sets**, geographically matched climate cells sampled in **different decades**, repeated intervals at **the same plots** that would inflate interval-weighted coverage, plot chains moving counties, invalid calendar years, absence/duplicate/outcome-field rejection, signed bins, complete-denominator preservation and receipt SHA mismatch.

## Next empirical gate and inference ceiling

There is **no present route to calculate the real-v4 joint common-support estimate** from the archived aggregates. A newly source-frozen, outcome-blind taxon–plot–interval file from an independently versioned cohort is required. If data remain unavailable, terminate `not_evaluable`; never reduce thresholds or move taxa into the denominator after seeing performance. Passing this **source-only gate** authorizes only *consideration* of a separate preregistered spatially independent comparison of stationary versus region-varying growth responses. That later test additionally requires plot/county-block uncertainty, enough within-bin spatial units, survivor/death/missingness handling, FIA design context and an independently specified minimally worthwhile change in held-out performance.

Do not infer local adaptation or physiological limiting factors from any purely correlative model even if regional interactions later improve prediction.

## Implementation revision and frozen-result invariance (2026-11-15)

The v1.1 source-only gate strengthens the *prospective eligibility interface* without changing the post-outcome v4 observations or the frozen M5/Product A endpoints. Its output distinguishes the number of T-P bins shared **ignoring sampling time** from the number shared in the **same 5-year end-measurement cohort**. Region coverage is now primarily unique spatial plot chains (composite county + plot identity), not repeated intervals. Requiring a time cohort and an immutable source-only receipt is a design safeguard, not an empirical finding about niches. There is no new source-only FIA table available in this repository; the historic v4 joint-support result remains `not_evaluable` for all 13 taxa.

These five-year cohorts and the thresholds remain *development choices informed by earlier outcomes*, not a preregistered independent species comparison. An independently timed and sampled study must justify the cohort width and conduct sensitivity analyses at other widths before proposing a biological process attribution. Exact climate equality within a grid and identical demography cannot be inferred from this gate.
