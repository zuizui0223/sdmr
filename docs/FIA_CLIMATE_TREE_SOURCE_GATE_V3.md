# FIA county climate × TREE/COND source readiness v3

**State:** a new, source-only cohort. The archived first-open FIA growth, density, physiography and previous plot-only NOAA results are **unchanged**. This is not a causal environmental effect analysis, not a confirmatory biological programme, and does not promote SDMR Product A/B or M5.

## Current scientific problem

FIA live-to-live stem increment was measurable for 13 fixed tree species in RI, VA and WI, and a strong within-species inverse association with stand basal area was recorded. Mesic/xeric site classes had non-uniform, often region-reversed patterns. However, neither a contemporaneous temperature/precipitation variable nor a source-coherent link between the FIA PLOT, COND and TREE archives had been tested. The independent NOAA `20261006` source has 43,890 April–September county-month rows for 209 counties and remains read-only. The new PLOT successor v2 has 64,206 climate-complete repeat-plot chains out of 83,065 (not tree growth observations).

## Pre-response source census

- Fixed states: RI, VA, WI; fixed species: FIA `68,129,261,316,318,371,531,541,743,762,802,833,837`. No species chosen by inspecting climatic associations.
- Each downloaded **PLOT ZIP must byte-match its already archived successor SHA-256**. No new PLOT version can silently replace it. If 3/3 fail, report 0/3 and stop rather than treating missing data as zero.
- Download the **COND and TREE** from the same current DataMart source family. Preserve their full ZIP SHA-256 and original row denominators as a separately labelled *new* version. Do **not** read any TREE `DIA`, `STATUSCD` or increment values in this gate.
- Establish each TREE `PREV_TRE_CN → CN` within the same species, and require its current and previous PLOT identities to match the previously validated plot-chain climate interval. Require forested, natural-origin conditions with recorded `STDAGE` and `BALIVE` at both censuses; these conditions are source eligibility, not a selection effect estimate.
- No source exclusions disappear from the ledger. Every fixed state, every fixed species, failures to retrieve a ZIP, and unchanged/revised metadata SHA are retained. The diagnostic flags at least 30 source-eligible linked trees, 8 plot revisits, and 3 counties **without inspecting a tree's growth or mortality**. These are exploratory power/source gates, not significance tests.
- County-level climatology is deliberately coarse, in part to reduce dependence on fuzzed and swapped public FIA plot coordinates. This is not precise plot-level temperature, soil-water, or drought exposure. Intervening April–September months must all be present, including neither boundary measurement month; no extrapolation or missing-month imputation.

## Prospective development estimand (only after source frozen)

A *separate*, explicitly exploratory observational study may use the same source-pinned ZIP SHA values to evaluate, within fixed taxon and state, calendar-measurement-interval-normalized `log(DIA_current/DIA_prior)/years`. A candidate climate×density model should contain county-level interval temperature and precipitation (centered within county), source stand basal area as a density term, their interactions, initial tree diameter, natural-stand age and temporal/cohort controls. Growth must be conditional on verified prior-live/current-live measurements, with removal/death/nonobservation counted separately (not zero-growth). The inferential unit cannot be treated as independent trees across repeated PLOTs; residual dependence, repeated trees, FIA expansion factors, within-county exposure confounding and survival selection must be audited. A formal hypothesis test or claims about local adaptation need independent, previously unseen plots and physiological/demographic anchors.

This source gate **alone cannot** verify whether climatic drivers switch, or whether crowding is causal. It only decides whether climate-exposed FIA tree identities and source conditions are available to justify opening an outcome analysis.

## Reproduce

```bash
python -m pytest -q tests/test_fia_climate_tree_source_gate_v3.py
python experiments/fia_climate_tree_source_gate_v3.py \
  --plot-source results/fia_noaa_county_climate_v1/plot_successor_v2_result.json \
  --noaa-csv results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv \
  --noaa-receipt results/fia_noaa_county_climate_v1/source_receipt.json \
  --output artifacts/fia_climate_tree_source_gate_v3.json
```

The v3 source-only CI attaches its complete JSON receipt even if a state fails. The historical first-open outcomes are never overwritten or implicitly promoted by this workflow.
