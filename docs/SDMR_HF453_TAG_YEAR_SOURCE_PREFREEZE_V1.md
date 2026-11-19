# HF453 next-step source-only StemTag × census-year identity audit — prespecified v1

**Before original identity rows opened**, 2026-11-19. This is a distinct source-only stage from first publisher-byte hashing. It is not a second opening of a biological effect, not an outcome check, and not a new ecological confirmation.

## Frozen preceding evidence

- One earlier publisher raw-byte stream matched the archived original **5,524,386 bytes**, SHA-256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, published MD5 \`c6be7aa99e31ded2041a0aaea07c0205\`. First-run artifact and exact digests: [\`evidence/hf453_publisher_original_bytes_first_open_v1.json\`](../evidence/hf453_publisher_original_bytes_first_open_v1.json).
- Publisher source: Harvard Forest HF453 v1, EML \`knb-lter-hfr.453.1\`, DOI \`10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193\`. **Do not accept another edition or unverified host/URL.**
- Only one exact new URL GET from publisher, no automatic network retry or fallback. The file must match **all three** previously frozen byte size, SHA-256 and MD5 **before** any CSV row is decoded. A provider update returns a full-source STOP.

## Strict exposure barrier

After matching full original file bytes, inspect **only header positions and values for \`StemTag\` and \`year\`**; deliberately never index/read \`status\`, \`CP\`, health/crown, species, growth, death, mortality or any other biological outcome/predictor value. Source bytes are temporarily stored during the read, then deleted at job exit, never archived or committed.

Predeclared admissible census labels: **2021, 2022, 2023, 2024**. Require original header fields exactly \`StemTag\` and \`year\`, no duplicate header names, no blank/trim-altered tag or unregistered year, and no repeated identical \`StemTag × year\` identity. An unknown/duplicate identity yields **STOP**, not an opportunity to select or deduplicate favorable records.

### Outputs fixed before the first identity request

- Total original rows scanned (excluding original CSV header); original \`StemTag×year\` rows, distinct literal tree tags, duplicate identities, invalid source tags/years.
- Full four-year \`StemTag\` header/occasion record counts, number of tags with ≥2 years, tags with all four years, three adjacent-year exact tag intersections.
- Separate source status \`tag_year_source_identity_indexed_only\` when no invalid identities, duplicate rows, or year-frame gaps are observed; otherwise one of the predefined strict STOP states.
- A candidate same-tag overlap is only **potential record linkage**, not verified stem survival, proof of complete annual survey opportunity or independent forest replication. Absence in next year's table is **not** recorded death, and a row present in two years need not be an alive-at-risk event without inspecting original status.
- The receipt always declares \`status_CP_health_taxon_columns_not_used=true\`, \`new_tree_response_opened=false\`, \`new_biological_models_fit=0\`, \`new_biological_inference_authorized=false\`, and \`Product_B_unblocked=false\`.

## Frozen state machine

Source SHA/version mismatch → \`original_frozen_source_byte_mismatch_stop\` before any identity scan.

HTTP, TLS or network access failure → \`original_source_fetch_unavailable_stop\`.

Parser/encoding/internal source integrity issue → \`original_source_identity_read_stop\`.

Exact repeated \`StemTag×year\` → \`duplicate_original_tag_year_stop\`.

Missing expected original columns or out-of-frame tags/years → \`identity_source_fields_invalid_stop\` (for wrong header a parser STOP).

Any census year with zero candidate source rows → \`identity_year_frame_incomplete_stop\`.

Only otherwise → \`tag_year_source_identity_indexed_only\` (ID metadata available; **NOT** measured opportunities or full process carriers).

## Execution design

- \`scripts/hf453_tag_year_identity_source_only_v1.py\`: exact SHA-before-read and fixed two-column parser.
- \`tests/test_hf453_tag_year_identity_source_only_v1.py\`: network-free synthetic source drift, duplicate, invalid year, status/CP-mutation invariance and missing-frame tests.
- \`.github/workflows/sdmr-hf453-tag-year-source-one-shot-v1.yml\`: triggered only once by first creation of \`configs/hf453_tag_year_original_once_v1.lock\` on the designated branch. JSON only; no raw CSV artifact.

## What this cannot resolve

An actual survey/effort ledger, true measured negative responses, status codes \`A/AU/DC/DS/DN\`, prior CP strata, same-tree death risks, site-level independence and missingness-corrected effects remain **unexamined**. These require a distinct prospective response-admission stage built on [the existing HF453 risk-set prefreeze](SDMR_HF453_RISKSET_PREFREEZE_V1.md). No physiological, competition, cross-biome or Product-B claim may be promoted from this metadata scan.
