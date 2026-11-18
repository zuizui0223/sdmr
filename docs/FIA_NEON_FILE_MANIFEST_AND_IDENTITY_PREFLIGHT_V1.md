# NEON 2026 independent forest-cohort prerequisite: file manifest & tagged-individual source identity

**Status (2026-11-17): source-only, blocked before outcome access.** The previously consumed FIA survivor-growth source and all 5-species positive and negative results remain fixed. Distinct provider **does not** establish biological independence or causal competition until actual stable tree IDs, plot sampling and management/environmental context are matched. PR #284 remains draft; Product A, M5 unchanged, Product B blocked.

## Official release-specific corrections

Official [NEON DP1.10098.001 RELEASE-2026 product documentation](https://data.neonscience.org/data-products/DP1.10098.001/RELEASE-2026) and the [NEON vegetation structure user guide, revision F.1 (2026-01-06)](https://data.neonscience.org/documents/10179/2237401/NEON_vegStructure_userGuide_vF.1/ad2a7494-4312-f987-d035-d164c938ed6b?version=1.0) establish:

- \`vst_perplotperyear\`: \`eventID × plotID\` is the plot sampling record and reports **growth-form-specific total sampled area**. Source eligibility must not be based on individual presence while ignoring \`samplingImpractical\`, nested subplots or sampling area.
- \`vst_mappingandtagging\`: \`individualID\` links stable taxonomic identity and mapping records. In **RELEASE-2026**, \`eventID\`, \`subplotID\` and \`nestedSubplotID\` were removed from the static table. Duplicate corrected mapping records must use the most recently created \`date\` per individual and source version; **do not join this table on eventID**.
- \`vst_apparentindividual\`: \`eventID × individualID × tempStemID\` is an **event-level** key. For multi-stem individuals, \`tempStemID\` is **not a longitudinal bole ID**. \`TEMP\` individuals are not tagged reidentifiable trees across events. Tag IDs can be duplicated among plots; use NEON's persistent \`individualID\`, site, plot and validated event instead.
- Taxa of concern may be fuzzed in published NEON identifiers. The FIA \`SPCD\` codes 129/316/802/833/837 cannot be equated with NEON \`taxonID\` without independent source-versioned taxonomy checks.

The [NEON API authentication guidance](https://data.neonscience.org/data-api/authentication/) specifies the \`X-API-Token\` header for file endpoint requests; the [data endpoint contract](https://data.neonscience.org/data-api/endpoints/data/) states that \`/data/{product}/{site}/{year-month}\` returns **file metadata**, including downloadable URLs that may expire. We must not commit token values, time-limited signed URLs or raw tree records to Git.

## One-shot optional-credential file MANIFEST pilot

The previous first-open public \`RELEASE-2026\` catalog [run 44034394812](https://github.com/zuizui0223/sdmr/actions/runs/44034394812), artifact 14306711443 ZIP SHA-256 \`178009f2f30a4d64a27b71549524e275780873febde747deb697503bde123238\`, documents 42 sites and 37 sites with a four-year release span, **not** 37 remeasured-tree populations.

Before opening actual NEON plant records, fix a **minimal, nonbiological metadata-pilot** of four release site-months at two well-documented forest sites:
- HARV: 2014-08 and 2024-08
- SCBI: 2014-08 and 2024-09

These are **not** a representative or randomly selected population sample, and were selected after source availability and previous FIA outcomes. Their only purpose is verifying that the API provides files for \`vst_perplotperyear\`, \`vst_mappingandtagging\`, and \`vst_apparentindividual\` in the target release. A later independent study cannot limit itself to favorable two sites without a separately fixed site/region sampling design.

\`experiments/fia_neon_manifest_probe_v1.py\` requires the EXACT original public catalog JSON SHA-256 \`0ba89ff5835ea54071e7a8f12f05b5ca928cec05a1dd424660727de4f94d9bcf\` and source receipt SHA-256 \`29699a799b5fc09411b952548f371b7f27545d4b0f73d479590576f63937021f\`. If the repo secret \`NEON_API_TOKEN\` is absent, it makes **zero** authenticated calls and writes \`no_NEON_API_TOKEN_secret_configured_no_network_data_request\`, not a zero-tree count. If a token is present, it requests exactly the four fixed **JSON manifest endpoints** with \`X-API-Token\`, records only file name, size and table-presence counters, and omits token, signed URLs and raw measurements entirely. Invalid/401/403/missing tables are STOP, never an eligibility pass. No automatic repeat of a changed source is permitted.

The pipeline does not attempt a CSV file download **even if the secret is configured**. A 4/4 result would mean *four file manifests available*, not any same-tree remeasurement, taxon overlap or biological effect.

## Implemented identity-only contract for a later authorized raw source acquisition

\`experiments/fia_neon_identity_contract_v1.py\` takes **normalized, projected identity fields only** from three tables in synthetic/unit tests, with exact allowlists rejecting status, diameter, coordinates and growth fields.

- \`perplotperyear\`: \`site, plotID, eventID, surveyYear, samplingImpractical, totalSampledAreaTrees\`; requires a unique plot×event with positive tree sampling area and \`samplingImpractical == ok\`.
- \`mappingandtagging\`: \`site, plotID, individualID, date, taxonID\` **without eventID**; choose latest correction, exclude \`TEMP\`, reject conflicting corrections, and keep taxonomic IDs **unverified**.
- \`apparentindividual\`: \`site, plotID, eventID, individualID, tempStemID\`; validate event uniqueness, exclude \`TEMP\`, same ID in multiple plots, multi-stem \`tempStemID\` nonstability and missing plot effort. A candidate requires the same **stable tagged individualID in the same plot** to be observed in at least two valid events separated by ≥4 calendar years. This is a structural **candidate**, not verified biological survival, comparable measurement height or growth response.

Before this parser processes any real NEON tables, a **separate adapter and source receipt** must prove that the raw 2026 schema supplies all normalized fields correctly, that the observed \`surveyYear\` is derived from the appropriate event date, and that sampling area reflects each measured growth form. The present source-identity parser **has never been run against NEON individual data**, and cannot report counts from synthetic fixtures as observed counts.

To progress to an independent biological test, confirm actual source-only remeasurement, presence of fixed taxa, plot effort and event equivalence, save source versioned raw tables securely (outside Git, without credentials), freeze minimum census/unit support and then **independently** open tree growth/status. A tagged individual present at two dates is not evidence that its growth is comparable or that unobserved tags are dead.

## Run / reproducibility

Offline synthetic tests (no token, no network):

\`\`\`bash
python -m pytest -q \
  tests/test_fia_neon_manifest_probe_v1.py \
  tests/test_fia_neon_identity_contract_v1.py
\`\`\`

The lock-triggered Actions pilot downloads **only** the prior public 2026 catalog artifact and reads \`NEON_API_TOKEN\` from GitHub Secrets. It records token-absent and manifest errors as bounded source-only status receipts and never exposes a credential. It neither automatically retries nor uses actual tree measurements. **Scientific promotion prohibited throughout.**


## First official preflight outcome: authorization STOP, not biological zero (2026-11-17)

The newly added offline synthetic source-contract workflow initially had an invalid YAML name because its title contained an unquoted colon; it failed to start, with zero jobs. That was fixed at commit \`47b623f\`, and [source-only contract CI #44075557509](https://github.com/zuizui0223/sdmr/actions/runs/44075557509) **passed**. This correction changed no scientific logic, data or models.

The **only** [manifest pilot run #44075687516](https://github.com/zuizui0223/sdmr/actions/runs/44075687516) then completed its workflow successfully **by failing closed**: the source catalog was SHA-verified, but the GitHub Actions runner had **no configured secret named \`NEON_API_TOKEN\`**. It issued **0 authenticated requests**, never accessed the NEON \`/data\` endpoint, and did not download any vegetation table. The [first-attempt artifact #14325400964](https://github.com/zuizui0223/sdmr/actions/runs/44075687516/artifacts/14325400964) has ZIP SHA-256 \`3813347d3e9eee815a79062d53cb9127d4b6203ac3d0ee77cfcb3618d78f7852\`; its sanitized \`neon_2026_file_manifest_source_gate.json\` SHA-256 is \`c51023e853210e2312e5276c1f66cff3b58f6126cfbe4b308fc9fa85502192ef\`.

**Status is \`no_NEON_API_TOKEN_secret_configured_no_network_data_request\`**, not \`data unavailable\`, and certainly not \`zero repeated individual trees\`. The pilot site-months remain exactly HARV 2014-08/2024-08 and SCBI 2014-08/2024-09; all four requested file-manifest sets are still **unknown**, not false. The parallel synthetic normalized individual-ID tests use **fixture data only** and do not replace actual NEON files.

A small [checkpoint](../results/fia_NEON_2026_manifest_pilot_first_attempt_checkpoint_v1.json) preserves the first-run STOP and SHA provenance. The prior independent NEON public catalog result, FIA growth results and Product A/M5, blocked Product B and zero biological confirmations are unchanged.

**Next required external dependency:** the authorized user creates a personal NEON API token via the official NEON portal, then sets \`NEON_API_TOKEN\` in **GitHub repository → Settings → Secrets and variables → Actions**. Do not paste it into chat, GitHub source, a PR or an artifact. Once the secret exists, a **distinct versioned successor** may request the same four pinned **file metadata manifests** and audit their presence without opening growth/status records. Do not silently rerun or reinterpret the initial failed-closed source-check outcome.
