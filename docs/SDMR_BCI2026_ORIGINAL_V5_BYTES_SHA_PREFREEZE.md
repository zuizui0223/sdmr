# BCI Dryad 2026 revised v5: original five-file byte SHA-256 prefreeze

**Scientific stage: independent tropical forest original-file provenance only, no biological response opening.** Fixed on 2026-11-20 after the separate provider metadata first-run, but before any BCI \`mainfile\` or \`stemfile\` bytes were fetched in this successor.

## Earlier metadata result, not overwritten

Authoritative first [BCI source-metadata Actions #44758571119](https://github.com/zuizui0223/sdmr/actions/runs/44758571119), archive ZIP SHA-256 \`2a8826dd61418ff8f6e81d6ce51be70f204b08792fb5321d1f641521cea83e52\`, first original JSON SHA-256 \`d19ec833ea2e2c8194d22d37847e1c564b83a2cefc5c335bd922572f618be158\`, established public Dryad **DOI 10.5061/dryad.1g1jwsvc3**, exact revised date **2026-08-31**, **provider versionNumber=5 and version ID=460507**, \`CC0-1.0\` license, and five original file names with **publisher-provided SHA-256 digests and byte lengths**. [Immutable metadata checkpoint](../evidence/bci2026_first_dryad_published_metadata_v1.json).

The first program's file-ID field was \`null\` for all five entries. This is a **metadata adapter omission**: it expected a top-level numeric \`id\` while Dryad instead places the file ID under its \`_links.self\` / \`_links.stash:download\` relation. The first \`provider_original_file_manifest_missing_checksums_hold\` label was therefore overly broad: **the SHA-256 digests and sizes do exist**, but the version-pinned file IDs remained missing. This program does NOT retroactively change the first result; this newly frozen, explicitly second-stage source-only workflow repairs the link extraction and performs actual bytes-to-publisher-digest comparison.

## Frozen five-file input and exact SHA256

| Exact original v5 name | Provider byte size | Provider SHA-256 |
| --- | ---: | --- |
| \`Key_sp6.txt\` | 15,795 | \`4e7e3c1c5a93443b50d2d0f287e4887892f7b8f7d64faa7031aa105f1307b4e4\` |
| \`Plot_UTM_coordinates.txt\` | 463 | \`fdb5617b3ca49a46cdd8be5ef7879d6ae332a36c377d5038f55cab5421cf6b7c\` |
| \`README.md\` | 16,958 | \`df27e18c1b23003c8b694cffde8b20303820cab583c03d46a0d9abaeb7b48b15\` |
| \`mainfile.txt\` | 4,444,083 | \`e0e37862f6763316d7cbdab16ecc9cc60370955afd251211732c550e8778528c\` |
| \`stemfile.txt\` | 537,486 | \`e527f8bfab145bf1e343b522c45131ac250eaf5774126aa24c1dde52809ddf40\` |

These are **metadata-provided checksums**, not yet verified complete downloaded files when this plan was frozen. Do not infer these are authenticated biological field data or that the provider checksum makes source sampling opportunities complete.

## Strict second source gate

- Only one fixed file-manifest metadata GET: \`https://datadryad.org/api/v2/versions/460507/files\`, not a \`latest\` or dataset-level download URL.
- Require **exact matching 5 original filenames**, full bytes and provider SHA256 digests, exact \`sha-256\` type, and per-file \`_links.self\` + \`_links.stash:version\` + \`_links.stash:download\` relationships to the **same version 460507**. Resolve file IDs from these versioned links only.
- Perform a single original HTTPS stream GET per **exact versioned file ID**. Allow redirects only to HTTPS Dryad or known Amazon S3 infrastructure; never choose another source, replace any file, or auto-retry an alternative URL or version.
- For each exact file, calculate **complete-file SHA256** and verify the byte length equals the above publisher metadata; cap each stream at the recorded original length and all files at 8 MiB total. Immediately discard bytes, no decoding, header parsing, row splitting, numerical ecology, raw CSV archive or source copy in the GitHub repository.
- If one file is unavailable, status is an explicit **source access STOP**. If a byte hash or length differs, **source drift STOP**. The code must not silently continue and advertise 5/5 on a partial match.
- Archive **only** source name, immutable numeric file ID, exact byte counts, published and observed SHA256, trusted final provider host or typed STOP. No original tree data or full source payloads in output.
- Even if all five bytes match, **BCI observation/sampling opportunity and biological testing remain BLOCKED** pending a separate original frame/attrition/census semantics gate and then response-opening protocol. In particular, **2025 exposure cannot enter models of earlier survival**.

Source-only implementation: [\`scripts/bci2026_v5_original_bytes_sha_only_v1.py\`](../scripts/bci2026_v5_original_bytes_sha_only_v1.py). No-network synthetic original checksum fixtures: [\`tests/test_bci2026_v5_original_bytes_sha_only_v1.py\`](../tests/test_bci2026_v5_original_bytes_sha_only_v1.py). First publisher SHA and version receipt: [\`evidence/bci2026_first_dryad_published_metadata_v1.json\`](../evidence/bci2026_first_dryad_published_metadata_v1.json).

**Scientific inference ceiling remains unchanged:** one tropical island landscape does not create six biome replicates; observed \`dead\` may include inferred deaths; original M5 and Structural synthetic benchmark results are frozen; Product-A v2.8.4 not promoted, Product B blocked. No biological effect from BCI is estimated at this stage.
