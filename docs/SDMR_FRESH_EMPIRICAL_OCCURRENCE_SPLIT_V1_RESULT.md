# SDMR fresh empirical occurrence split v1 — terminal result

Status: **50/50 source gate PASS / coordinate-only outer split frozen / environmental values unopened**

- workflow run: `36222283703`
- workflow head: `f9b23730b453afa7255f655606f86491428709b4`
- artifact id: `10899781608`
- artifact digest: `sha256:fdea13477e7918cae826397ba5154874894ce7955e81d435f1b566c630036e6a`

All 50 frozen taxa passed the predeclared source gate without replacement. Across the panel there are **186,645 raw GBIF occurrences**, **58,323 thinned 0.05-degree occurrence cells**, **43,201 model-pool occurrences**, and **15,122 sealed answer-check occurrences**. The weakest taxon still had 512 raw records and 130 thinned cells, above the frozen 80/50 gate.

The outer split used only occurrence identity and coordinates. The model-pool artifact retains coordinates for M construction; the sealed ledger retains IDs, spatial blocks and roles but not coordinates. Environmental values, answer-check features, model fitting, and accessible-area construction all remained unopened/unperformed.

Next gate: build the frozen 300-km target-group accessible area and deterministic background using **model-pool coordinates only**.
