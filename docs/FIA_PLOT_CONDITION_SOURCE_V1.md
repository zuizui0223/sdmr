# FIA plot/condition exposure gate v1 — new source lineage, not historical re-promotion

## Scientific objective

The frozen archived 13-species × 3-state survivor diameter pattern uses `TREE.INVYR` differences for interval normalization and ignores plot age and forest stand structure. `INVYR` is a *panel inventory year*, not necessarily the actual year the tree was measured. A follow-up needs the independently dated PLOT measurement years/months and CONDITION stand-age/natural/artificial-origin information **before** interpreting a geographical growth gradient as a temperature–water mechanism.

## New-source contract

- Fixed states **RI, VA, WI**, identical to the archived demographic pilot. This is a **separate source lineage**, NOT a replacement of its frozen TREE ZIPs or 308,181 growth pairs.
- Read-only USDA FIA DataMart `/CSV/{STATE}_PLOT.zip` and `/CSV/{STATE}_COND.zip`, separate complete ZIP SHA-256, byte count, exact CSV member and field schema for every state/table. All missing or invalid entries are reported explicitly. No ZIP bytes are committed or claimed to be immutable if the remote changes again.
- PLOT: CN, PREV_PLT_CN, INVYR, MEASYEAR, MEASMON, PLOT_STATUS_CD. Report the fraction with actual measurement year, paired plot records, and scheduled-vs-measured-year discrepancies.
- COND: PLT_CN, CONDID, COND_STATUS_CD, STDAGE, STDORGCD, CONDPROP_UNADJ, FORTYPCD, STDSZCD, DSTRBCD1. Count linked forest conditions with valid age, natural/artificial origin and disturbance fields. Do not use forest condition records as randomly sampled trees.
- **No TREE measurements, survival, growth, observed species states or ZIP source replacement are read in this source gate.** Data from `TREE` must be joined later on source-compatible `PLT_CN`, within a separately pinned source-cohort contract with exact SHA receipts.
- If the three fixed source states do not all finish, the output is an **availability HOLD**, not a claim about absent growth or absent species. Do not choose a different state for a favorable result.

## Interpretation and decision

The first test asks how often `INVYR` and `MEASYEAR` are unequal and whether forest-stand metadata are present. Large differences would demonstrate **measurement-interval and forest-age composition as plausible confounding**, not prove they cause the already-observed growth ranking.

A biologically informative next experiment must use a **single compatible snapshot** of TREE, PLOT and COND, actual measurement intervals, repeated plot/condition identities, size/age/forest management and environmental exposure; compare stationary versus region-specific growth curves on held-out plots. Precisely located climate exposures need an explicit uncertainty treatment for FIA fuzzed public coordinates. Plot weights and survivor selection are distinct issues. Growth and mortality must not be pooled into one endpoint.

## Run

```bash
python -m pytest -q tests/test_fia_plot_condition_source_gate_v1.py
python experiments/fia_plot_condition_source_gate_v1.py --output artifacts/fia_plot_condition_source_v1.json
```

Historical Product A and M5 are closed, and blocked Product B remains blocked. This independent source audit does not reopen or change any of them.
