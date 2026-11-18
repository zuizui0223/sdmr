# SDMR external PA/MI: all-five-state climate rebase after full-ZIP drift (v5)

**Status:** distinct source-only v5, no biological outcomes, not causal inference, not FIA file-version equivalence. Original Product A/M5 and blocked Product B unchanged. Original practical regional climate improvement: 0/5. External Pennsylvania and Michigan have never had TREE.DIA or TREE.STATUSCD opened.

## What v4 proved and why v5 is separately justified

The [20261105 uniform NOAA rebase v4 first PLOT attempted run #44294243344](https://github.com/zuizui0223/sdmr/actions/runs/44294243344) stopped as required when RI's full **PLOT ZIP SHA changed** from original source \`c19953851a4d804337959b772c1a9f4f1b7bb16d5686d49705b571a759684648\` to new source \`b409bb55766011401ee581ca7ad97f7c7d3e5a3876db630c6a7027e5ea7fcde0\`. V4 never read a tree response or computed common support. The original v4 test-run [#44293158076](https://github.com/zuizui0223/sdmr/actions/runs/44293158076) failed before any PLOT acquisition due only to an incorrect synthetic-test exception regex; the corrected CI [#44293771674](https://github.com/zuizui0223/sdmr/actions/runs/44293771674) passed before first actual source fetch. Both failures and their receipts remain immutable.

The *full ZIP* mismatch can reflect changes to unrelated plot records or source packaging. It does **not** establish that the original **89,616 selected taxon × plot × interval** records changed, but v4 could not determine that because its intentionally strict whole-file gate stopped before reading the PLOT contents. It would be scientifically wrong either to call this "climate not transferable" or to silently reinterpret new PLOT bytes as the old source.

### New v5 inference boundary

A separate **event-identification** equivalence check replaces the full-ZIP equivalence claim with *explicit verification for every one of the original study units*, before calculating their new climate. Use immutable **original source-selected** identities and original NOAA 20261006 derived exposures as independent anchors:

- [Original reconciled source-only run #43711159676](https://github.com/zuizui0223/sdmr/actions/runs/43711159676), artifact 14160283759: exactly 89,616 original RI/VA/WI source-selected rows. The rowset and exclusions are fixed and may **never change** (source CSV SHA \`44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7\`).
- Old county Apr–Sep 1991–2025 source CSV has SHA \`623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8\`. The original temperature and precipitation anomalies are values **derived from that old source at the actual PLOT previous/current visit dates**, after subtracting the frozen 1991–2020 county baseline.
- RI **updated PLOT ZIP** from the actual v4 failed-first-open [artifact #14421539704](https://github.com/zuizui0223/sdmr/actions/runs/44294243344/artifacts/14421539704) (SHA of internal \`RI_PLOT.zip\`: \`b409bb55766011401ee581ca7ad97f7c7d3e5a3876db630c6a7027e5ea7fcde0\`). **Reuse it**; do not refetch RI again.
- Acquire VA and WI **PLOT ZIPs once each** into a new source lineage, recording the full actual new SHA and member. No TREE/COND is downloaded or read. No mixing any previously archived PLOT bytes under an unverified source label.
- For **every** 89,616 original taxon×plot×interval record, require identical \`state, species, county, interval PLOT CN, end-year, plot-chain root\`, a valid previous PLOT CN, and reconstructed **original** temperature anomaly within \`1×10⁻⁵°C\` and original precipitation anomaly within \`1×10⁻⁴ mm\` using exact interval months. These are near machine-rounding tolerances, not ecological-optimal calibration thresholds. **Any single** mismatch, missing previous/current PLOT or lost source interval STOPs the complete 13-species analysis. No choosing a favorable stable subset, alternative taxonomy, date shift, or rematching CNs after inspection.
- Only after proving complete original event-level consistency, compute the **same 89,616** source climate intervals from the independently frozen **NOAA 20261105** raw ASCII: temperature SHA \`ea6a159d3ad9a25b60cce6e3889d79898e17cf4e29b3d2c2282d19d7fb073a4d\`, precipitation SHA \`1f21b2435a29cc40369a4666a69b4f6d851643bad2811f7b8f1bab6521217b27\`. Original NOAA 20261006 values and v3 **historical-revision STOP** remain intact.
- Reuse without re-sourcing [83,046 PA/MI source-only taxon×plot×interval records](https://github.com/zuizui0223/sdmr/actions/runs/44290985125) acquired/derived under **that same 20261105** NOAA version (CSV SHA \`b83298bfd792b25e71d62ade38486979d37b7618b8dece5da5f071921949de85\`).

This validates the **source-selected event keys and climate exposure history**, not that the updated ZIP is literally the originally published file or that all of its non-selected PLOT records stayed constant. Recomputing the old anomalies independently guards against stale or silently altered measurement dates. No individual TREE persistence, response, management or FIA design weights are inferred.

## Source-only external support and thresholds (NOT the ecological endpoint)

Training climate-time cells: VA/WI only; original 1°C T × 100mm/6months P × 5-year end-period, each qualifying cell ≥2 distinct counties and ≥5 independent plot chains per state, and ≥2 shared training cells. External PA/MI each needs ≥5 counties, ≥25 plot chains, ≥20% unique plot chains in source-qualified training bins. Full **13×2** denominator retained, with fixed priority five codes \`129/316/802/833/837\`. RI original source retained but does not define VA/WI training climate bins.

A passing v5 means same-20261105 **environmental source overlap** can be assessed, not that biological response is stationary. A failing v5 is a **source comparability problem**, not a negative ecological model test. If support is available, the *next separate* study must first freeze VA/WI-trained model coefficients and PA←VA / MI←WI transfer to the external PA/MI holdout, and open actual PA/MI growth/status only after verifying full raw source SHA, all-prior-live denominator and tree-level/mortality interpretation.

## Execution

\`experiments/fia_PA_MI_NOAA_event_identity_v5.py\` implements the exact event-identity gate. \`tests/test_fia_PA_MI_NOAA_event_identity_v5.py\` uses synthetic corrupted dates, climate anomalies and plot-chain roots to require hard rejection. The new one-shot workflow downloads archived prior training/NOAA/PA-MI data and **reuses the v4 RI PLOT archive**, acquires only VA and WI original-state new PLOT ZIPs, writes source-only derived rows/report, and retains raw PLOT ZIPs temporarily in GitHub Actions artifact outside Git commits.

No raw FIA biological outcomes are opened, no external effects are fitted and no NEON credentials are required. The original 13 taxa/5 primary and all previous positive/negative results remain unchanged.


## Confirmed source-first-open v5 result (2026-11-18)

The independent source-only synthetic controls [run #44296038745](https://github.com/zuizui0223/sdmr/actions/runs/44296038745) passed; the unique lock-triggered [run #44296141877](https://github.com/zuizui0223/sdmr/actions/runs/44296141877) then **SUCCESSFULLY COMPLETED**. Its [derived source artifact #14423482128](https://github.com/zuizui0223/sdmr/actions/runs/44296141877/artifacts/14423482128) ZIP SHA-256 \`94fb77217fbfc0ff3a1e4f2ca2efabf3d8be85a032d53da3950b3a1d58d3eee5\`, full 13-taxon external support JSON SHA-256 \`c9c485be4a11e2c04ac12c58738feac02ba3cb4e33b9339a82a31dff5a8d6626\`, v5 receipt SHA-256 \`7802b1ed30486b23c13cee27c3141d99539d1ff4237cf1e4435661711c4eae67\` and 89,616-record training rebase CSV SHA-256 \`e3c872f5b0f4fce7e97bef5f172a631d0f09f28ced663d8bb6580a5ab894c11c\`. A separate original PLOT ZIP archive [#14423761461](https://github.com/zuizui0223/sdmr/actions/runs/44296141877/artifacts/14423761461) preserves new-source PLOT bytes outside Git.

**All original 89,616 taxon×plot×interval source rows** passed the original plot/chain/county/year check AND recovery of their archived previous 20261006 NOAA temperature and precipitation anomaly from the updated PLOT survey dates. Counts by original state: RI **1,471**, VA **38,128**, WI **50,017**. The new full-source ZIPs themselves were **not** byte-identical (new RI SHA \`b409bb55766011401ee581ca7ad97f7c7d3e5a3876db630c6a7027e5ea7fcde0\`, VA \`91a1c62cd3ca44fd2edf33a81325cef6e4754b7aa7b2dd7740514f22c76b50fd\`, WI \`05d84d314397683ee9bef4f36c4467916555ab3e0e6f4ef93a79f1330083aa36\`); the explicit and limited **selected-record event-identity comparability** is what was established.

On the **same NOAA 20261105 climate release**, source-only VA/WI-qualified joint 1°C × 100mm × five-year cells covered sufficient plots/counties in **both Pennsylvania and Michigan for all 13 frozen original taxa**, including all **5/5 previously selected primary species**. Their source-only unique-plot coverage is:

| Taxon | Qualified joint cells | PA source-plot coverage | MI source-plot coverage |
|---|---:|---:|---:|
| *Pinus strobus* (129) | 25 | 99.62% | 100% |
| *Acer rubrum* (316) | 28 | 99.89% | 99.96% |
| *Quercus alba* (802) | 27 | 100% | 100% |
| *Q. rubra* (833) | 28 | 99.93% | 100% |
| *Q. velutina* (837) | 21 | 99.67% | 99.13% |

Source eligibility is **not predictive accuracy, ecological process identity, survival, or a stable niche**. All new PA/MI diameter/status and demographic outcomes remain unopened. The next pre-outcome task is freezing VA/WI-trained coefficients on this source edition, including geographically defined PA←VA/MI←WI surrogate response transfer, without using holdout outcomes. The exact 13-taxon result and SHA lineage are summarized at \`results/fia_PA_MI_same_NOAA_source_support_checkpoint_v5.json\`. Previous v3 and v4 STOPs and earlier FIA results remain unchanged.
