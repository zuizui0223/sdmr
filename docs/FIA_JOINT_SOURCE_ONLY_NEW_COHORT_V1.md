# FIA × NOAA joint exposure: one-shot source-only new-cohort acquisition

**Status (2026-11-15):** An isolated prospective-data *design/collection* lane for PR #284. It is not a repair, replay, or reinterpretation of the frozen v4 survivor-growth outcome, M5 or Product A. It cannot unblock Product B. The lock-triggered workflow is source-only and does not fit a demographic or biological model.

## Why a new data source is necessary

The original v4 archive contains only per-state marginal minima/maxima of temperature and precipitation for 13 tree species. Hence *all 13* remain unestimable for empirical **joint** environmental overlap. The earlier synthetic counterexample proves that separate univariate range overlap does not imply bivariate overlap. The old ZIP receipts, selection and outcomes remain unchanged and may not be revived by accepting the later DataMart ZIP bytes as the same study.

## Source-only construction

`experiments/fia_joint_source_only_v1.py` reads the committed **NOAA 2026-10-06 county × month** climate CSV (43,890 rows, 209 counties, Apr–Sep 1991–2025), verifies its archival SHA-256, and obtains one fresh FIA PLOT and TREE ZIP per state (RI/VA/WI) **once per named source cohort**. Every acquired ZIP SHA, byte count, schema and source failure is recorded. A complete source gate requires all **3/3 states**. No previous recorded FIA v4 source ZIP is overwritten.

FIA PLOT `CN, PREV_PLT_CN, STATECD, COUNTYCD, MEASYEAR, MEASMON` establishes remeasurement intervals and actual measurement end year. A persistent plot-chain identity follows predecessor links. Source-only FIA TREE processing indexes **only** `PLT_CN` and `SPCD` from the **PREVIOUS PLOT** for the 13 predeclared taxa. In particular, the code does not read, parse, retain or fit `TREE.STATUSCD`, `TREE.DIA` or other growth / survival outcome columns, and does not use **current PLOT species presence** to select eligible species. This last rule prevents conditioning on a taxon's continued presence in the later visit, an implicit persistence/survival filter.

The resulting CSV has precisely:
`species_code,state,county_fips,plot_chain_id,interval_id,interval_end_year,temperature_anomaly_c,precipitation_anomaly_mm`.

One row is one *prior-visit observed species × plot chain × eligible remeasurement interval*, not one tree or one independent mortality/growth result. Time-varying exposures come from complete intervening Apr–Sep county months, excluding the boundary measurement months (as in the existing no-outcome PLOT gate). Anomalies use the 1991–2020 NOAA county baseline. A species recorded only at the later visit cannot be used to define prior opportunity. Unrecorded species are **not verified absences**.

**Science/evidence limitation:** this is a descriptive sampling-opportunity subset. Because it conditions on completed PLOT remeasurements, it does not fully solve detection/selection, attrition, or forest-design weighting. It includes source-observed taxa irrespective of forest COND suitability or growth, so passing this gate would **not** imply adequate downstream natural-forest demographic data. County climate is not measured plot microclimate or plant water stress.

## Two-stage auditable output

- `source_receipt.json` or `source_stop.json`: source identity and all three region denominators, never a partial-success imputation. SHA hashes are necessary identity receipts but do not preserve the raw mutable upstream FIA ZIP bytes.
- `fia_new_cohort_joint_source_only.csv`: emitted **only if 3/3 source archives validate**, with a SHA-256 pinned in the receipt.
- `source_support_gate_v1_1.json`: `fia_joint_support_gate_v1.py` counts qualifying joint T-P climate cells *within the same predeclared five-year end-measurement period*, requiring distinct counties and plot chains; it distinguishes time-ignored and time-matched support, and refuses an unsupported denominator. Its positive status means **descriptive input support only**.

The coarse 1°C × 100-mm grid, five-year strata, five counties and 25 plots/region, two counties and five plots/bin, two shared bins, and 20% unique-plot coverage are **design-development choices after the original v4 outcome**. Even if new source-only data pass, this is *not* a prospective or confirmatory demographic effect test. A separate externally justified, independently source-frozen biological evaluation is required.

## Execution and reproducibility

Offline tests (no downloads or outcome access):
```bash
python -m pytest -q tests/test_fia_joint_source_only_v1.py tests/test_fia_joint_support_gate_v1.py
```

The dedicated [source-only one-shot workflow](../.github/workflows/fia-joint-source-one-shot-v1.yml) is activated by an explicit, uniquely named `configs/fia_joint_source_acquire_once_v1.lock` addition on this research branch, rather than by every pull request update. It intentionally has **no scheduled retry or routine PR trigger**. Source acquisition uses current public FIA DataMart bytes as a **new cohort**, not as a replay of the mutable historical result. On a missing changed source the workflow archives a complete STOP and does not produce biological conclusions. Never edit the lock file to improve an adverse source eligibility result.

Before any later growth/survival model, an independently dated protocol must freeze sampling frame, source identities (and make raw-data reproducibility feasible), a spatially independent plot/county holdout, an environmental joint-support definition, cluster-weighted uncertainty, source attrition rules, and a minimally worthwhile prediction difference. Any resulting climate association still does not independently establish physiology or local adaptation.
