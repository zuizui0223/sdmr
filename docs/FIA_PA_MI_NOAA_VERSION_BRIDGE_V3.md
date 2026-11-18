# External PA/MI source-only climate version bridge v3 — NOAA 20261105 versus 20261006

**Study status 2026-11-18:** The fixed Pennsylvania and Michigan FIRST new source has succeeded, with **83,046 prior-visit taxon × PLOT chain × remeasurement interval rows** and all 13 original species passing an identity-and-calendar *availability* gate. No PA/MI DIA/STATUSCD or growth/survival data have been read. The first PA/MI climate acquisition correctly stopped because the pinned NOAA 20261006 URL under \`monthly/current/\` now returns HTTP 404. Its failed run [#44236792668](https://github.com/zuizui0223/sdmr/actions/runs/44236792668) is retained; the time-only successor [#44238110335](https://github.com/zuizui0223/sdmr/actions/runs/44238110335), artifact #14397884111, has archived both raw FIA ZIPs and derived source-only identities. **Do not attempt to re-run or rewrite either source accession.**

## Scientific rationale and rigid decision

The user's primary SDMR question is whether regional environmental-driver "turnover" reflects regionally different **available climate spaces applied to a common ecological response** or genuinely different region-dependent responses, not merely which variables predict tree outcomes. Test development used the earlier **VA/WI** FIA growth responses and the **NOAA 2026-10-06** derived 1991–2025 county-month record. PA and MI remain outcome-unopened.

The current official [NOAA nClimDiv county monthly index](https://www.ncei.noaa.gov/monitoring-content/data/us/climdiv/monthly/current/) publishes **2026-11-05** county \`climdiv-tmpccy\` and \`climdiv-pcpncy\` files, not the original \`20261006\` files. A changed raw-file SHA may reflect simply newer 2026 months, or revisions to *historical observations*; only the latter would invalidate the mixed old VA/WI versus new PA/MI 1991–2025 comparison. We must measure historical equality, **not presume either equality or difference**.

\`experiments/fia_PA_MI_NOAA_version_bridge_v3.py\` therefore acquires **one** copy of each exact new \`20261105\` file, preserves its original bytes, headers, dates, SHA, and parses all five state source climate records with NOAA **ordinal-state** codes mapped to FIA FIPS:
- RI: 37 → 44; VA: 44 → 51; WI: 47 → 55
- PA: 36 → 42; MI: 20 → 26

For the previously archived **exact old NOAA 43,890 county-month rows** (Git SHA-256 \`623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8\`, original 1991–2025 Apr–Sep), compare every original state, county, year, month, temperature °C and precipitation mm to the new 20261105 source after the original **6-digit rounded conversion**. Report missing rows, changed rows and maximum differences **per original state and variable**.

**Branch A — no historical changes (exact equality for all 43,890 old months):**
The original VA/WI source-only climate exposures are genuinely consistent with this new historical data release in their documented months. On the *same* 20261105 NOAA source, form PA and MI baselines (1991–2020, 180 Apr–Sep months per county); calculate interval anomalies from **all Apr–Sep months strictly between exact previous/current PLOT measurement dates**, never including either boundary measurement month and never filling missing months. Require each whole interval to have ≥6 complete growing-season months. For all **13 original taxa**, use exclusively VA/WI source-only cells to find T (1°C) × P (100mm/6months) × calendar 5-year joint bins with **≥2 counties + ≥5 independent plot chains** per training region. Holdout support in PA/MI needs **≥5 counties, ≥25 plot chains and ≥20% distinct plot chains within ≥2 shared joint training bins**. No PA/MI data may choose bins. This is *environment source overlap*, never a fitted growth response or proof of unchanged niche.

**Branch B — any historical source revision or missing original row:**
Refuse combined historical version claims. Archive the new PA/MI source-only climate anomalies and quantified differences to original NOAA, but do **NOT** generate a full common-support eligibility result mixing 20261006 VA/WI exposures with 20261105 PA/MI exposures. Mark the result \`historical_NOAA_revision_blocks_mixed_version_common_support\`, with species coverage and all environmental effects **unknown**, not zero. A future all-state release-consistent reprocessing of original VA/WI plot identities and climate requires a separately fixed source contract. No new outcomes are opened.

**Any source/ZIP/old-training-SHA failure:** hard source STOP. The original FIA study, PA/MI identity-only source result, 13-taxon denominator, 5 primary species, and Product A/M5/blocked Product B are never reinterpreted. The event is not a new ecological zero or a failure of transfer.

## Source identity and prevention of selection leakage

Frozen old VA/WI+RI training source: [run #43711159676](https://github.com/zuizui0223/sdmr/actions/runs/43711159676), artifact #14160283759, SHA \`44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7\` for reconciled 89,616-row source-only CSV.

Frozen PA/MI identity/time source: [run #44238110335](https://github.com/zuizui0223/sdmr/actions/runs/44238110335), artifact #14397884111, SHA \`70cf6e8db95c864d80e684ed7292606d6a8df64d71e8bd952ae1a1a2adc4d1c2\` for 83,046-row dated PLOT-chain × prior-visit taxon CSV. Identity source receipt SHA \`1392858a521f466e0b39892202883cec4a645f39dad6b5ab7e5d2afa534b5e3c\`. Nothing from either dataset's tree diameter, status or later growth is read.

New source first opening has its own **lock** and independent synthetic tests; neither \`20261105\` nor \`20261006\` data may be replaced by a current value while reusing an existing scientific result. Download raw NOAA files and retain SHA-fingerprinted originals *off Git in a separate short-retention artifact*. Derived PA/MI source climate CSV and the revision receipt remain reviewable separately. Source version is not tree individual independence.

## Next response-stage comparison (not run here)

Once and only once source climate compatibility is confirmed, freeze a **cross-region predictive evaluation** that learns the common environmental slopes in VA/WI alone and evaluates PA/MI with **no PA/MI parameter fitting**. The old stationary model contains state intercepts and WI-specific interactions. To avoid unidentified PA/MI intercepts, a predeclared **PA ← VA, MI ← WI mapping** can be used for region-specific surrogate transfer, compared against the common response with the SAME state-intercept transfer; a separate calibration-based local model requires disjoint PA/MI training vs test counties. Both are *predictions*, not direct causal niche mechanisms. True prior-tree live denominator, forest context, co-located status and survey weights still need to be inspected in a separately approved response opening.

Even if the new external model beats its competitor, **predictive RMSE alone cannot attribute driver limitation**: the primary scientific target is the explanation of apparent regional driver turnover by availability, observation processes or true response differences.

## Reproduce the nonbiological step

\`\`\`bash
python -m pytest -q tests/test_fia_PA_MI_NOAA_version_bridge_v3.py
python experiments/fia_PA_MI_NOAA_version_bridge_v3.py \
 --old-NOAA-csv results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv \
 --holdout-identity-v2 build/PA_MI_frozen_identity_v2 \
 --training-source-v2 build/frozen_train_src \
 --out build/fia_PA_MI_NOAA_bridge_v3
\`\`\`

The source first-open workflow downloads only the two new, explicitly versioned NOAA raw ASCII sources. No rereading FIADB tree status, diameter or outcomes, no NEON token, no taxon or state selection by results.
