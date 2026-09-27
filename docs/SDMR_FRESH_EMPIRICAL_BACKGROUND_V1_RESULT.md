# SDMR fresh empirical background v1 — terminal result

Status: **model-pool-only M/background PASS / primary 300-km background complete / environmental values unopened**

The frozen global non-focal Tracheophyta target footprint contains **1,060,909** occupied 0.05-degree cells. It was constructed from the DOI-backed 2026-08-01 GBIF snapshot under the same 2010-2025 occurrence and coordinate QC as the focal panel, with all 50 frozen focal taxa excluded before footprint aggregation.

Accessible areas were then constructed using **only the 43,201 model-pool occurrence coordinates** from the sealed occurrence-stage artifact. Answer-check coordinates and answer-check environmental features were not read.

For the primary **300 km** M:
- 50/50 taxa have **5,000 deterministic background cells**;
- the smallest candidate accessible area still contains **5,606** target-group cells (Aidia micrantha);
- total primary background rows = **250,000**;
- no taxon used an undersized all-available fallback.

Sensitivity M values remain frozen at 150 and 500 km. At 150 km, one taxon has fewer than 5,000 candidate cells (Aidia micrantha, 2,973), which is permitted by the predeclared sensitivity rule. At 500 km, every taxon has at least 9,698 candidate cells.

Execution provenance:
- chunk source run: `36239328323` — preflight + 32/32 GBIF shard jobs passed; its aggregate failed only because DuckDB was absent from that runner;
- aggregate-only recovery run: `36240044258` — PASS without rescanning GBIF;
- terminal artifact: `10905064972`;
- artifact digest: `sha256:d907566fcdef3586692ab854dc441f9e762fd0f50392daa199675ce139be916f`.

Information boundary remains intact: environmental values unread; answer-check coordinates unread during M construction; answer-check features unread; model fitting not started.

Next gate: extract the frozen 46 environmental predictors for model-pool occurrences and frozen background points only. The sealed answer-check remains closed.
