# SDMR: all-five-state source climate rebase under NOAA 20261105 (v4)

**Stage:** source-only, no biological response or ecological mechanism claim. The historical FIA response, Product A/M5 and blocked Product B remain unchanged. PA/MI outcomes have not been opened.

## Why a new source step is needed

The [NOAA historical version bridge #44290985125](https://github.com/zuizui0223/sdmr/actions/runs/44290985125) succeeded and found **actual revisions** between the October 6 and November 5 NOAA releases in the 1991–2025 county-month source. Among the original 43,890 records, **RI changed 27 temperature and 5 precipitation cells, VA changed 296 and 2, WI changed 130 and 8**. The original v3 conclusion was correctly STOP: mixing old VA/WI climate values with newly acquired PA/MI exposure cannot verify transportability. That STOP remains archived and is not rewritten.

This distinct v4 rebase permits a single scientific remedy: rebuild the **same exact original 89,616 RI/VA/WI source-only prior-species × plot × interval records** under the **same NOAA 20261105 release** already used in 83,046 PA/MI source-only intervals. No tree outcome or new selection is opened.

## Rigid PLOT and climate identity

The original [first FIA source run #43696751589](https://github.com/zuizui0223/sdmr/actions/runs/43696751589), artifact 14155086669, has a source-only receipt SHA 0adcdeac7b974e91b83d986fca32ad0851000658f79fbe099407ce2fb37fa408. It pins three entire original FIA PLOT ZIP digests:

- RI: c19953851a4d804337959b772c1a9f4f1b7bb16d5686d49705b571a759684648
- VA: 18e791098390ce3543d48ebc53073da6df5901589edd55c22fe33e1cd14fc6fd
- WI: 0ec63fb21e03439a40771f28e5d535e0ae1d2a3ff2dc308b31ed2348936dac10

The [reconciled training source #43711159676](https://github.com/zuizui0223/sdmr/actions/runs/43711159676), artifact 14160283759, retains exactly **89,616** original species × PLOT-interval source records after excluding one county-unstable VA chain (14 rows). Its original source CSV SHA is 44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7. Neither the selection nor exclusion is recomputed after climate revisions.

Only those original three public FIA PLOT ZIP URLs may be retrieved, each **once**. Compare the entire newly downloaded ZIP SHA with its original first-open digest **before reading PLOT identity or dates**. If any ZIP differs or is unavailable, source rebase stops as noncomparable. It must never use a changed PLOT release to reconstruct original measurement windows. No TREE or COND is downloaded/read by this step.

The exact NOAA 20261105 temperature and precipitation raw ASCII inputs are reused from **run #44290985125**, raw artifact 14422420396, with SHA  ea6a159d3ad9a25b60cce6e3889d79898e17cf4e29b3d2c2282d19d7fb073a4d and 1f21b2435a29cc40369a4666a69b4f6d851643bad2811f7b8f1bab6521217b27. No new NOAA download or silent source-date substitution is authorized.

The complete five-state new NOAA county-month denominator is **75,390** April–September records for 1991–2025. For each old training record, reconstruct its **exact previous and current PLOT measurement date** using original PLOT CN, PREV_PLT_CN and the original plot-chain root; verify the original source county, species record, interval ID and end year. Recalculate 1991–2020 county baseline and all complete intervening Apr–Sep months (excluding boundary measurement months). Require the **same 89,616 source rows**; if any original observation becomes ineligible, STOP rather than select a favorable subset.

The PA/MI side is read unchanged from [v3 derived source-only artifact #14420899193](https://github.com/zuizui0223/sdmr/actions/runs/44290985125/artifacts/14420899193): **83,046** already SHA-frozen source-only rows under the November 5 NOAA release, CSV SHA b83298bfd792b25e71d62ade38486979d37b7618b8dece5da5f071921949de85. No PA or MI outcomes are accessed.

## Fixed source support; not fitted ecological inference

Training areas remain **VA and WI**. Each original species (all 13 retained) gets a 1°C temperature × 100mm growing-season precipitation × five-year period joint source cell; each cell must have at least two independent counties and five distinct plot chains in VA and WI *independently*, then intersect. The heldout PA and MI support for each species requires five counties, 25 plot chains, 20% plot support and at least two shared training cells. The pre-existing five-priority taxa are 129, 316, 802, 833 and 837; never choose species after seeing outcomes. The old RI source rows are preserved and rebased, but RI is not used to select training climate cells.

Passing means **climate comparisons might be empirically testable**. It does not mean a common growth response is correct, nor identify physiological stress, niche adaptation, mortality or competition. Geography is not randomization. A future biological test needs fixed PA←VA, MI←WI surrogate branch predictions or a disjoint local calibration/test scheme; PA/MI response coefficients cannot be estimated using VA/WI alone.

## Reproducibility boundary

The implementation and focused synthetic tests verify every old first-open SHA, original PLOT event/chain identity, complete source-denominator conservation, original NOAA v3 raw version, PA/MI derived climate source identity and zero biological-outcome reads. Outputs preserve the three exact PLOT ZIPs as separate short-lived source artifacts (not in Git), full species-by-region source-support status and new training derived source data. Source drift is a failure of source comparability, **not** a negative ecological finding. No further DataMart retry is authorized under this source contract.

Program: experiments/fia_PA_MI_NOAA_uniform_rebase_v4.py

Test: tests/test_fia_PA_MI_NOAA_uniform_rebase_v4.py

Science ceiling: identity-matched same-edition source support, not fitted tree response or demonstrated process.
