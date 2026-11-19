# SDMR × Structural: five archived forest source-only admission audits v1

**Evidence stage: source/meta-only, no new ecological response.** This is an executable method-development check on published and previously archived metadata receipts. It is **not** a new field-source opening, a reanalysis, a causal diagnosis, a rejection of previous ecological findings, or a change to frozen M5/Product-A/Product-B.

## The inferential issue the 80-case synthetic PASS does not solve

The previous prospective **synthetic** benchmark passed 30/30 reference-positive and 0/50 false-favorable process-information candidates. However, in the observation-confounded world, the simulation provides a privileged ground-truth eligibility flag. Real field datasets do **not** normally label selection and detection bias as 'verified safe' by themselves. Therefore, a new method version needs to audit **original sampling opportunity and missingness before ecological process information is classified**. A positive heldout model gain cannot substitute for this audit.

The `src/sdmr/forest_source_gate_v1.py` module refuses to equate:
- original surveyed **zero** (with demonstrated positive effort) versus an unvisited or unsequenced site;
- **survivor-only** stem increments with population-level tree growth/mortality;
- taxa detected among captured individuals with the full regional arthropod population;
- one physical stand with multiple trees, traps, methods, dates, taxa or forest-guild labels with multiple independent geographic replicates;
- source manuscript terms that are taxonomic format-sensitivity matches with author-verified names;
- archive-derived analysis ZIP receipts with raw original publisher file hashes.

It accepts only exact source metadata fields, with an explicit source receipt, original/analysis-artifact receipt role, observation and zero frame, effort and attrition state, taxon ontology, physical grouping, nested geography, time alignment, process-carrier coverage, and whether the response was already exposed. Unknown, insufficient, and zero eligible observations remain distinct.

## Real-source metadata re-audit (five lineages, NOT five independent tests of one effect)

| Archived source lineage | Verified source opportunity | Unresolved for a **new** SDMR process-identification protocol |
| --- | --- | --- |
| **Finland beetle host guild** (Structural PR #469) | 142 original physical sites, nine spatial cells, original year/host-guild matched response already opened | One occupied spatial cell has **one** site; true sampled-zero/capture effort and complete carrier-level process representation are not demonstrated; historical ecological positive remains untouched |
| **Carpathian Weiss170 trophic beetles** (Structural PR #469) | 116 original physical plots, 18 stands; original no-benefit exploratory result **ΔHellinger² = −0.00106793** | 18 stands nested in **unverified nine mountain ranges**; original species→guild mapping is a 170/309 post-source-header format sensitivity, not author-verified; no complete zero/effort process |
| **England NFI canopy/Malaise eDNA** (Structural PR #469) | 83 original plot-years; 77 with both methods sequenced and overlapping; 316/316 sequenced sample headers linked | Pre-frozen region×year randomization has singleton strata and stopped before biological OTU rows; physical site independence/ontology/effort unresolved |
| **FIA VA/WI survivor growth** (SDMR PR #284) | Source-frozen 170,994 live→live diameter-growth rows for five fixed species; spatial BA improvement positive in 5/5, temporal BA positive point estimate in 2/5 | Survivor conditioning (unknown selection for mortality/harvest); raw individual/county geographic group crosswalk cannot be inferred from 714 species×scored-county records; full process carriers not measured |
| **NEON 2014–2018 historical field forest VST linkage** (Structural PR #469) | 730 paired beetle/plant forest plot-years, 227 VST matching original same plot-year candidates | **0** plot-years satisfy strict valid VST opportunity with positive surveyed tree area; 0 is an available-source/eligibility STOP, NOT a biological absence or zero trait effect |

Evidence anchors:
- [Finnish original host-guild spatial result](https://github.com/zuizui0223/Structural/blob/analysis/forest-macro-plot-environment/docs/FOREST_BEETLE_FINLAND_142SITE_DEADWOOD_HOSTGUILD_SPATIAL_HOLDOUT_ACTUAL_RESULT_20261115.md)
- [Carpathian original exploratory non-support](https://github.com/zuizui0223/Structural/blob/analysis/forest-macro-plot-environment/docs/FOREST_MACRO_CARPATHIAN116_WEISS170_GUILD_DEADWOOD_LOSO_ONEPASS_ACTUAL_RESULT_20261118.md)
- [England NFI response-unopened endpoint STOP](https://github.com/zuizui0223/Structural/blob/analysis/forest-macro-plot-environment/docs/FOREST_NFI_ENGLAND_2026_OTU_EXACT_JOIN_AND_REGIONYEAR_GATE_ACTUAL_RESULT_20261119.md)
- [FIA survivor/cohort structural sensitivity](https://github.com/zuizui0223/sdmr/blob/research/geographic-driver-turnover-macro-v0-20261019/docs/FIA_WITHIN_COUNTY_BA_PLOT_EQUAL_SENSITIVITY_V1.md)
- [Historical NEON VST attrition and zero eligible trees](https://github.com/zuizui0223/Structural/blob/analysis/forest-macro-plot-environment/docs/FOREST_MACRO_NEON_HISTORICAL_2014_2018_VST_ORIGINAL_QA_ATTRITION_RESULT_20261114.md)

The source catalog stores the existing original or analysis artifact SHA-256 and records what kind of receipt that digest represents. It does **not** retrieve original files anew or independently prove the source metadata fields. Source provenance and source-identity claims are inherited from those already executed public audits, with this dependence made explicit.

## Admission contract

`configs/forest_source_gate_archived_sources_v1.json` carries five **response-free** source profiles. `experiments/forest_source_gate_audit_v1.py` produces their independently evaluated metadata decisions. A source cannot be promoted merely because data were publishable or a pipeline completed:

1. Validate original file/receipt identity, unit and group validity and the exact eligible denominator; refuse unknown, zero or non-independent support.
2. Require estimable independent geographic/time blocks. The **new method test** requires ≥6 verified blocks and ≥2 eligible physical units per block, different from historical exploratory tests; this new rule does **not retroactively invalidate prior papers**.
3. Require response/taxon/trait ontology, temporal alignment and measured sampling frame. An unconditional biological response requires *sampled zeros with effort*, not only detected taxa; conditional detection/survivor targets are accurately labeled but cannot act as evidence for full sampling-corrected ecological process identity.
4. Require observation/attrition and process carrier completeness; partial/unknown is unresolved even if prediction improved. Candidate/process closure needs a declared complete carrier registry; one single BA or VD10 predictor does not suffice.
5. Historical exposed outcomes stay historical. Even a source satisfying all metadata gates only receives `metadata_ready_for_separate_protocol_freeze`, **never automatic response-opening authorization**.

The gate output contains each missingness reason and explicitly asserts:
`response_opening_authorized=false`, `biological_effect_estimated=false`, `source_only=true` for **every source**, including a fully qualified synthetic source fixture. The receipt refuses any extra biological outcome/loss fields.

## Physical-site and original sampling-opportunity adapter (synthetic-tested)

The companion `src/sdmr/forest_sampling_opportunity_v1.py` validates **original method metadata**, distinct from ecological responses. Each source `surveyed` event must have positive recorded effort and an ISO date. `not_surveyed` and `unknown` are separate statuses; no response row, count, detected species or sampled-zero label may enter the metadata schema.

Each physical site has one fixed outer holdout block. Multiple trap/source rows do not create multiple independent sites. The adapter requires an explicit source-defined **expected block list**: a wholly unsurveyed block remains in the denominator and causes nonestimability rather than disappearing before heldout evaluation. Any duplicated source record ID, site reassignment across blocks, unexpected biological outcome column or fabricated zero triggers refusal.

Its only possible successful status is `survey_opportunity_ready_for_separate_observation_audit`. Even this permits **no biological response opening**, proves no measured zeros, and says nothing about missing individuals, sampling-selection ignorability or process causality. Full observation-state verification occurs in a *different*, prospectively frozen stage after source methods and outcomes have been separated.

Synthetic regression tests check 8 blocks×3 physical sites under 8 versus 1 trap replicates, missing blocks, zero effort, unknown status, unstable physical IDs and order-independent source SHA ledgers. **These are software contract tests, not additional field-research observations.**

## Scientific next stage

An independently sourced biological programme must start with actual original physical site/stand/individual identities, dates and measurement-state logs, *including not-seen or not-alive observation opportunities*, then freeze a source-version-locked endpoint, process-carrier registry, reference, validation hierarchy and pre-outcome comparators. A new field dataset with only detected species or surviving trees must either target **explicitly conditional** composition/growth or remain unresolved for broader population-process claims.

**No opportunistic 'rescue' of the already negative Carpathian endpoint or response-unopened England NFI singleton design.** A genuinely new study/response design with separate populations is required for empirical generalization. Existing Finnish positive and Carpathian negative cannot be statistically pooled because the trophic guild ontologies and references differ.

If a new source qualifies, it can next produce a frozen response-blind unit/group ledger and only then enter process-closure model comparison. If it does not, the scientifically correct result is a source/estimability hold, not another threshold search.
