# Outcome-blind FIA PLOT × NOAA climate eligibility result (successor v2)

**First completed source run:** [GitHub Actions 40075320067](https://github.com/zuizui0223/sdmr/actions/runs/40075320067), artifact `12552881767` (`fia-noaa-county-plot-successor-v2`). The complete original structured result is archived unchanged at `results/fia_noaa_county_climate_v1/plot_successor_v2_result.json`; do not alter the source stop or the original tree-growth archives.

## Previously failed PLOT source and recovered *new* version

The original source-only join [run 40074802488](https://github.com/zuizui0223/sdmr/actions/runs/40074802488) was **0/3**, because the bytes of all three current FIA DataMart PLOT ZIPs differed from a prior independent source freeze; it correctly returned `source_unavailable_or_changed`. The exact original failure receipt is `results/fia_noaa_county_climate_v1/original_plot_source_stop.json` (SHA-256 verified). A separately designated *new PLOT version* retains those changed ZIP hashes as its explicit eligibility identity; a second GET on the successor run reproduced each same hash and the **three-of-three source check passed**. The unmodified NOAA 20261006 county climate was validated against the SHA-256 of its independent receipt and 43,890-row CSV (209 counties; 1991–2025 Apr–Sep).

## Real source gate result

| Source state | All linked PLOT revisits | Links with complete paired measurement-month-to-measurement-month growing-season NOAA exposure | Source-check verdict |
|---|---:|---:|---|
| Rhode Island | 759 | 754 | PASS (new PLOT version) |
| Virginia | 34,861 | 20,781 | PASS (new PLOT version) |
| Wisconsin | 47,445 | 42,671 | PASS (new PLOT version) |
| **Fixed denominator** | **83,065** | **64,206 (77.3%)** | **3/3 source-complete** |

The climate contains observed, county-specific **temperature and precipitation** averaged/summed over April–September months **strictly between** the two plot measurement months. Minimum six intervening valid growing-season months. The result counts **PLOT revisit chains**, *not* independent trees, live trees, climate–growth pairs, state-specific physiological stress, biomass, productivity, survival, or climate effect sizes.

Source exclusions (source labels are not mutually inclusive with earlier metadata validity status) are retained without zero-imputation. RI 5 incomplete exposure windows; VA 13,941 incomplete windows, 137 invalid PLOT county/date and 2 county changes; WI 4,761 absent previous PLOT IDs in this source, 12 invalid county/date, and 1 changed county. Much of the nonoverlap can reflect NOAA's 1991–2025 date boundaries; this requires a separate period audit, not assumed ecological absence. Eligible monthly windows are not necessarily equal-duration intervals across states.

## Interpretability and next source gate

This is a **source-linkage feasibility result** only. A source-consistent new TREE and COND cohort with fully versioned ZIPs, current/previous tree and plot identity, measured dates, condition records, focal species and nonresponse inclusion rules must be acquired **before** applying any growth or density measurements. Public FIA coordinates are spatially perturbed; county FIPS is coarser but still includes administrative and within-county exposure heterogeneity. A joint temperature/precipitation × basal-area density model must test common support and account for same-plot correlation, size, stand age, calendar/interval length, censoring and managed/removed individuals. There is **no climate × competition ecological effect estimate at this stage**.

Closed Product A/M5, blocked Product B, previously opened measured-response files remain unchanged.
