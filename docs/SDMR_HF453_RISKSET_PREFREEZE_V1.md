# HF453 v1: prospective within-forest status and risk-set prefreeze (no response opening)

**Date:** 2026-11-19. **Status:** prospective design-only, **NOT** an executed biological analysis, source-row audit, or cross-biome replication. First original publisher byte identity has passed, but **0 tree-level observation records have been inspected**. This is a fresh HF453 within-forest diagnostic and is NOT an extension of the consumed FIA VA/WI outcome or the synthetic 80-case experiment.

## Frozen source and exact current evidence

- Dataset: Harvard Forest HF453, v1 / EML \`knb-lter-hfr.453.1\`, DOI \`10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193\`.
- Original source: \`hf453-01-tree-census-2021-2024.csv\`; published MD5 \`c6be7aa99e31ded2041a0aaea07c0205\`.
- Source-only [first-open GitHub Actions run #44475206249](https://github.com/zuizui0223/sdmr/actions/runs/44475206249), artifact **#14506116223**, exact artifact ZIP SHA-256 \`b7934bb8bbe351f90fb95de871b8c959061d4256f8bdfd7e4624206592755a96\`.
- Original publisher stream **5,524,386 bytes**, SHA-256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, **MD5 matched**; original tree file bytes were streamed for hash only and discarded. Source first-open commit \`a14cc8362a971aff66e7d49c003eb37de108d190\`.
- Immutable machine checkpoint: [\`evidence/hf453_publisher_original_bytes_first_open_v1.json\`](../evidence/hf453_publisher_original_bytes_first_open_v1.json).
- **No raw response rows, individual counts, taxon distributions, transitions, mortality events, covariates or model scores examined.** These remain unknown, not zero. No new GET/retry for this first-source version.

## Prespecified descriptive endpoint only

- One *original* physical ForestGEO forest, annual July published census labels \`2021, 2022, 2023, 2024\`; no independent forest-level replication.
- Candidate risk-event \`(StemTag, t→t+1)\`, t=2021,2022,2023, where \`StemTag\` is a stable **original tree tag** and its t status was \`A\` or \`AU\`. A tagged tree may contribute multiple risk-events, so those are **not independent individuals**. No claim of calendar-exact survival hazard without original day/effort records.
- No retrospective conditioning on later survival or on an outcome at t+1 when defining eligibility. Records first entering after t are **future recruits / unavailable prior risk**, never 0-outcome at t.
- Primary observed endpoint **Y=1** only if t+1 is \`DC\` (dead/down) or \`DS\` (dead/standing), both originally visually identified statuses; **Y=0** only if t+1 is \`A\` or \`AU\` (seen alive).
- \`DN\` is author-coded dead/not found, **not directly certified observed death**: classify as \`Y=unknown\`, not as known 1. An entirely absent t+1 record is also \`Y=unknown\`, not observed zero. Duplicate \`StemTag×year\`, unverified repeated-stem identity, incompatible census time or unaccounted field effort yields source/identity hold rather than forced classifications.
- Already dead/unfound at time t is not an alive-at-risk event; report its **exclusion count**, never quietly include in the at-risk denominator.

## Frozen structural contrast and missingness-robust output

- Candidate prior-occasion **canopy position \`CP\`** is a structural-context proxy: \`1 or 2\` = understory/shaded, \`3,4,5\` = more exposed canopy. Use original **t**, never future \`t+1\` CP. No tuning of the split on observed death.
- Source status with unregistered/unknown prior \`CP\` is carried as a **separate unknown-context ledger**, not allocated to an attractive result. Reject cross-group inference if either predeclared group lacks an independently validated opportunity denominator. Exact group counts are **unknown** until separately authorized biological source access.
- For each group, report \`p = known observed dead\`, \`z = known observed alive\`, \`m = outcome unknown (including DN and missing reobservations)\`, \`N=p+z+m\`. Denominators must retain each predeclared at-risk event. If a complete source opportunity/recorded-negative frame cannot be proved, refuse numerical bounds.
- Apply preregistered [sharp partial-identification calculator](SDMR_OBSERVATION_PARTIAL_IDENTIFICATION_V1.md) to the **associational** canopy-status contrast: \`[p1/N1-(p0+m0)/N0, (p1+m1)/N1-p0/N0]\`. Report \`positive\` or \`negative\` **only when the entire interval excludes zero**. Otherwise \`unresolved\`. These finite-population bounds **do not** constitute causal mortality, climate limitation or tree competition evidence.
- No independent geographic transport/biome claim even if a sign can be identified. Tree-clustered and source block–aware sampling uncertainty requires a separately frozen analysis and measured plot-level identities; an identification interval is **not** a confidence interval.

## Mandatory source gate before any ecological response test

1. Preserve original file/metadata version; separately validate original \`StemTag\` uniqueness within this protocol, raw survey dates, actual effort and all expected census opportunities **without calculating status outcomes or selection-conditioned effects**.
2. Independently verify observed-zero status, \`DN\` handling, unobserved t+1 and genuine risk-set denominator. No invented death, absence or alive state.
3. Freeze study-specific model, sample-selection and evaluation before opening outcome comparisons. Decide whether an original spatial/plot hierarchy is actually recoverable from the linked HF253 source. If not, this remains a single-forest descriptive bounded contrast.
4. Record the full denominator and unresolved/excluded categories; if source suitability fails, **STOP rather than replace the cohort, threshold, endpoint or missingness definition to improve an estimate**.

Existing [\`forest_longitudinal_status_v1.py\`](../src/sdmr/forest_longitudinal_status_v1.py) already distinguishes HF453 \`DN\` from visual \`DC/DS\` and refuses unregistered status codes. The current original-file match does not bypass these scientific gates.

## No ecological reclassification

Original Product A remains \`not_promoted\`, Product B remains \`blocked\`, original M5 71/80 and Structural synthetic 30/30 remain independent fixed denominators, and original FIA stand-structure spatial 5/5 versus temporal 2/5 remains *retrospective predictive information* under its original survivor-selected cohort. HF453 is not yet a biological replication of any one of them.
