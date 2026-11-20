# BCI revised 2026 independent tropical source — metadata PASS, original download HTTP401 STOP

**2026-11-20. Source-provenance evidence only. Zero BCI organism responses opened, zero tree/census data parsed, zero ecological models fit.** This new forest lineage is **not an independent biological replication of Harvard CP→recorded-death**.

## Reproducible first two original-source gates

### 1. Exact publisher edition and all five metadata SHA256s identified

First [official Dryad metadata-only one-shot run #44758571119](https://github.com/zuizui0223/sdmr/actions/runs/44758571119) **technically SUCCESS**. The DOI was exact \`10.5061/dryad.1g1jwsvc3\`, revised publisher date **2026-08-31**, **Dryad versionNumber 5**, immutable within the provider API **version ID 460507**, and CC0 1.0 license. The five expected original files \`Key_sp6.txt\`, \`mainfile.txt\`, \`Plot_UTM_coordinates.txt\`, \`README.md\` and \`stemfile.txt\` all came with published **SHA256 (digestType sha-256)** and exact byte sizes, summarized in [the first immutable source metadata checkpoint](../evidence/bci2026_first_dryad_published_metadata_v1.json). Archive #14640041728 ZIP SHA256 \`2a8826dd61418ff8f6e81d6ce51be70f204b08792fb5321d1f641521cea83e52\`, inner metadata JSON SHA256 \`d19ec833ea2e2c8194d22d37847e1c564b83a2cefc5c335bd922572f618be158\`.

The v1 adapter returned \`provider_original_file_manifest_missing_checksums_hold\`, but this label is **overbroad**: it recorded all five published SHA256s and lengths. The original **numeric file IDs were missing from its output** because it read top-level \`id\`, while Dryad presents file IDs under \`_links.self\` and \`_links.stash:download\`. That repair was separately frozen in [the second source-only prefreeze](SDMR_BCI2026_ORIGINAL_V5_BYTES_SHA_PREFREEZE.md); the first report remains immutable.

### 2. Full original publisher file byte attempt — HTTP401 stop

Second one-shot [BCI Dryad v5 full-byte SHA-only run #44759824350](https://github.com/zuizui0223/sdmr/actions/runs/44759824350) technically **SUCCESS as an executed STOP/receipt**, with artifact **#14639284302**, ZIP SHA256 \`f5660adc6d8652e4a8532a110554fe9e00ce7f748693320cc2f1f32adba86d0a\`. Original result JSON SHA256 \`4bf42b6471bb924556eef1676811b4256cda53b6714f54a3a03db0137ec3dc30\`; preflight JSON SHA256 \`763da363eacd0a0273224308461473e2c640e07ddffafdc92f334c0c69b0bf39\`.

- Original versioned file ID extracted successfully from provider manifest: \`Key_sp6.txt\` → **file ID 4933611**.
- First original file download from Dryad version **460507** returned **HTTP 401**. No file bytes were available to compare with publisher SHA.
- Predeclared source result: \`original_file_http_access_unavailable_STOP\`. **0 of 5 original files byte-verified**, 0 original tree rows/text, 0 mortality outcomes, 0 models and 0 independent biological tests. One original byte request was attempted, then stopped; no fallback to earlier version or alternate copy.
- [Permanent original HTTP401 checkpoint](../evidence/bci2026_first_original_file_401_access_stop_v1.json). The published metadata SHA digests remain useful *reference hashes only*, not a signature that we independently verified file contents.

A green CI job **does not indicate source admission**. It indicates the locked provider API, exact source edition and scientific safety guards correctly preserved an explicit **access STOP**.

## Methodological result developed without biological data

[Pure BCI source ontology operator](../src/sdmr/bci2026_observation_operator_v1.py) and [synthetic tests](../tests/test_bci2026_observation_operator_v1.py) enforce the codebook before any future authorized original response opening:

- Original tree identity is \`(plot, tag)\` (not tag alone), with literal source plots only. Stemfile rows cannot be presumed stable cross-census.
- \`missing\` means not found, and is **unknown**, not a known zero nor directly observed dead. \`future recruit\` means not previously eligible; it is **not** a surveyed absence.
- \`dead\` includes at least some inferred deaths and cannot be upgraded to verified directly observed death based only on the provided \`status\` string. Strict direct-death binary outcome remains **unknown**, while \`alive\` can be a source-coded negative subject to external opportunity audit.
- The nominal first census year 2004 includes visits in 2005; rates cannot be annualized by subtracting nominal census years without original dates and exposure records.
- \`exposure\` was measured only in 2025, among recorded alive trees; it is **invalid as a 2014 baseline predictor** for 2014→2025 mortality. The operator refuses such retrospective exposure leakage.
- These are **source-free logical invariants**, not empirical BCI mortality estimates or proof of source sampling completeness. An externally verified detection/effort and physical-unit frame remains necessary for a new biological conclusion.

## Independent field source candidate comparison — do not invent a replacement

The BCI DOI is indeed a different tropical source from Harvard, but its actual original file download is **not available under the uncredentialed provider endpoint used here**. We will not fabricate a new outcome by fitting to publisher metadata, choosing a different Dryad release, or using the 2025 survivor-only exposure as a baseline driver.

SCBI (Virginia, temperate) has another ForestGEO census source family, including public 2018 data and 2023 recensus records. However its [authoritative usage rules](https://forestgeo.si.edu/explore-data/scbi-termsconditionsrequest-forms) require a data request for publication with an approved data version, and later annual mortality has [separate custom data-use conditions](https://github.com/SCBI-ForestGEO/SCBImortality). The 2018 crown-position sample is also restricted to particular dendroband/core sampling cohorts, not necessarily a complete forest-wide risk set. Those source opportunities are worth a *separate rights/effort audit* but do not authorize substituting SCBI raw outcomes under the existing BCI protocol.

Other ForestGEO publicly distributed *example* subsets from Luquillo can teach status-code distinctions but are **not full original independent sampling frames**; treating curated 1000-row extracts as biome-level replication would repeat the very inference error SDMR aims to detect.

## Current scientific decision

- **PASS:** BCI dataset identity, exact official revised v5 source version, provider SHA-256 and five-file original metadata.
- **BLOCKED:** actual original file byte identity, full opportunity/absence and direct-vs-inferred-death audit, any new tropical biological response, and any claim of independent real-world process-validation.
- **COMPLETED METHOD-ONLY:** BCI observation ontology/testable refusal logic with no raw original data.
- **UNCHANGED:** original M5 71/80, Structural synthetic 30/30 and 0/50, Harvard Forest within-site field-status association and its score disagreement, Product A \`not_promoted\`, Product B \`blocked\`.

The next concrete opportunity for a **new tropical field outcome** requires authorized access to the exact BCI v5 original file bytes matching the five published SHA256 digests, followed by a *new* source-response-free eligibility freeze and an untouched response protocol. No background work or retries are promised.
