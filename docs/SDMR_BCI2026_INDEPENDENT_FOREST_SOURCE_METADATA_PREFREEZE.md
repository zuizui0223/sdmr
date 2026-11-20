# SDMR new independent forest: BCI 2026 Dryad original source-first gate

**2026-11-20. Frozen before any new BCI biological response or file bytes were retrieved.** This is a separate tropical forest source lineage for assessing observation-process validity and transport of *a method*, **not** a direct repetition of the Harvard canopy exposure effect or an independent test of HF453's original positive coefficient.

## Why Barro Colorado Island, and not immediate forest model fitting?

Official publisher: Wright, S. Joseph (2026), *Tree census data for 21 years and 58 hectares of secondary and old-growth forests at Barro Colorado Island, Panama*, Dryad DOI [10.5061/dryad.1g1jwsvc3](https://datadryad.org/dataset/doi:10.5061/dryad.1g1jwsvc3). Dryad records **Mar 17, 2026 (first release)** and **Aug 31, 2026 (revised release)**. The current corrected source has a *five-file* set: \`Key_sp6.txt\`, \`mainfile.txt\`, \`Plot_UTM_coordinates.txt\`, \`README.md\`, and \`stemfile.txt\`. Original metadata describes **six plots**, **58 hectares**, **34,367 census measurements**, **15,562 trees**, **222 species**, and three census labels **2004, 2014, 2025**. The earliest census was chiefly conducted in **2005** and the original \`date\` field must be used before computing any annualized rates. **These six plots are all on one island; not six independent forest biomes.**

This is **different from Harvard Forest** (temperate USA), with a different publisher, organism status coding, timing and sampling operator. That supports building a real external-source *method-availability test*, not automatically an externally validated biological model.

## Critical ecological/identification barriers, defined before opening BCI outcomes

1. **Exposure is post-outcome for a mortality test**: the dataset's five-point \`exposure\` light scale is measured only in **2025**, on alive trees with observed crowns. In particular, using 2025 light exposure as the 2014 baseline predictor for 2014→2025 mortality is **prohibited leakage/survivor selection**. No simulation or regression should silently impute earlier \`exposure\` from 2025.
2. **Original \`status\` is not an identical outcome ontology to Harvard**. BCI \`alive\` is observed alive; \`missing\` means previously alive but not found; \`future recruit\` indicates later entry into the minimum-diameter cohort, **not a recorded negative/absent tree**. BCI \`dead\` includes both directly found dead and some **presumed** dead from repeated failure to locate the tree. Without the source \`code\` and direct-observation provenance, BCI \`dead\` must not all be labeled observed-death equivalent to Harvard \`DC/DS\`.
3. **Stable original unit** is tree-level \`unique.id\` = \`plot-tag\`, not \`tag\` alone (tag numbers can repeat across plots). BCI's \`stemfile.txt\` represents multiple-stem dimensions but individual stem identities are **not necessarily stable across censuses**. Do not create independent biological individuals by splitting rows.
4. **Census time**: BCI labels \`2004\`, \`2014\`, \`2025\`, but actual dates differ within or between plots; unobserved intervals are not invariant 10-year hazards without audit of the original \`date\` field.
5. **Original quantitative variables**: \`dbh\` is in **millimeters**, sometimes absent for alive trees and ordinarily absent for not-alive or future recruits. Do not use missing DBH=0 or assume plot, size and species response are fully observed for all original records. The published sampling threshold was ~200 mm at initial tree censuses; a below-threshold future recruit is not a known survey zero.

The only honest prospective target for this particular new source is a **source-status and observation-opportunity method** (tree-level join/recruit/missing/presumed-dead classification, and perhaps future size/demography conditional on protocol availability). This does **not** directly identify a 2004 or 2014 canopy-exposure predictor. Even if independently validated source status is available, biological inference remains **blocked until a separate response-free target, baseline covariates, complete opportunity frame and geographic split are frozen**.

## Metadata-only first gate — frozen inputs

- DOI exactly \`10.5061/dryad.1g1jwsvc3\`.
- Choose **the 2026-08-31 revised provider version** from Dryad's own public version metadata by exact publication date. **Never** choose the API's newest/current version implicitly and never fall back silently to March 2026 if the revised edition is unavailable.
- Read only three published **metadata** endpoints: dataset DOI, DOI's version list, and the exact version's five-file manifest (Dryad REST API v2). Do not call the full-dataset download route, follow individual file links, decode README/raw dataset bytes or inspect status data.
- Require the exact five filenames, file IDs, versioned manifest URL, positive source-file sizes and publisher-provided digests where exposed. Missing version identity, incomplete metadata/pagination, inaccessible API or ambiguous same-day edition results in a typed **STOP/hold**. Keep raw original provider bytes, data use rights and biological results in separate states.
- Publisher metadata checksum is not the same as **our own complete downloaded byte SHA-256**; this first run does **not** validate original file bytes and **does not** authorize any ecological outcome to be opened.
- Run only with an exact, one-time source-metadata authorization lock; a normal PR push must not repeatedly contact the provider or create multiple implicit tests.
- Save JSON containing metadata versions, file names/IDs/size/digest and source-level eligibility; archive **no biological rows, original file bytes, individual IDs, source coordinates, exposures, mortality, models, effect signs, p-values or confidence intervals**.

Scientific contract: [\`configs/bci2026_independent_source_metadata_prefreeze_v1.json\`](../configs/bci2026_independent_source_metadata_prefreeze_v1.json). Exact source-free validation: [\`tests/test_bci2026_source_provider_metadata_v1.py\`](../tests/test_bci2026_source_provider_metadata_v1.py). Only [\`scripts/bci2026_source_provider_metadata_v1.py\`](../scripts/bci2026_source_provider_metadata_v1.py) is authorized to make this provider-metadata-only API read.

## Future source gate if original metadata PASS

In a **separately frozen successor**, use the exact selected Dryad **version ID and file ID** to retrieve the original **README / mainfile / stemfile** and compute original publisher-byte SHA-256 without interpreting the rows, with independently verified file sizes and digests. Only then may a further response-free original-header/survey-opportunity/individual/censoring audit be written. Any read of status values requires yet another **pre-response** frozen target and code, not a post-favorable-result model scan.

The pre-existing Harvard source outcomes, M5 71/80, Structural synthetic 30/30, Product-A \`not_promoted\`, and Product B \`blocked\` are **never reopened** by source metadata PASS. External ecological replication has **NOT been achieved** merely by identifying or downloading a tropical source.

## Alternative inspected, not automatically substituted

The Smithsonian Conservation Biology Institute (SCBI) temperate ForestGEO site has repeated 2008/2013/2018/2023 censuses and annual mortality records, with some 2018 crown positions. However, [the authoritative SCBI 2023 census README](https://github.com/SCBI-ForestGEO/2023census) points to a ForestGEO master portal for publication use, and the [SCBI mortality data-use agreement](https://github.com/SCBI-ForestGEO/SCBImortality) imposes **custom access/first-publication collaboration conditions on 2022+ mortality datasets**. Earlier crown records were a selected cored/dendroband cohort, not necessarily a complete original mortality opportunity frame. SCBI therefore cannot be silently treated as an unrestricted source for the same original CP→mortality experiment. Do not access those custom-agreement outcomes as a workaround.

## Publication ceiling

BCI's official Dryad listing provides public source **codebook knowledge**, not an empirical process result. The original greenhouse/forest scientific claim remains: SDMR's observational process attribution is still unvalidated across independent field source lines. Until independently tested, any alleged forest-wide causal superiority over ordinary SDM metrics (AUC, CBI, AICc, omission rate) is unsupported. PR for this new source remains Draft.
