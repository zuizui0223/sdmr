# HF453 original tag-year identity — first decoding STOP, frozen v2 successor

**Evidence stage:** response-free physical-identity metadata only. The already-opened v1 attempt is **consumed and immutable**. This is a strictly narrower *technical* successor, not a new biological result, not a change to observational targets or a second independent forest.

## Why v1 cannot be promoted

- First publisher-original byte identity: Actions [#44475206249](https://github.com/zuizui0223/sdmr/actions/runs/44475206249) identified original HF453 v1 **5,524,386 bytes**, published MD5 `c6be7aa99e31ded2041a0aaea07c0205` matched, full SHA256 `0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74`.
- First tag-year attempt: Actions [#44476932274](https://github.com/zuizui0223/sdmr/actions/runs/44476932274), commit `c0557e2cc36ddc469e3fcce2a368b8bdb0663c45`, artifact #14507101277 (ZIP SHA-256 `c9be3fac7c8952f172424afe3a0ae1940bf7c3bf727a59a4b067015fb4ab5712`).
- Workflow technical conclusion **SUCCESS**, but science/status **`original_source_identity_read_stop`** due to **`UnicodeDecodeError`** while decoding the original CSV with `utf-8-sig`. Thus **no tag/year count was established**, no duplicate decision, and no biological response was examined. A green workflow does not override this embedded STOP.
- Complete immutable outcome: [`evidence/hf453_first_tag_year_source_read_stop_v1.json`](../evidence/hf453_first_tag_year_source_read_stop_v1.json).

## Exact authorized technical delta — frozen before successor source request

The unchanged original SHA-256, MD5, byte size, URL, source edition, four census years `2021–2024`, exact `StemTag`/ `year` header, original group denominator, duplicate/invalid ID refusal and all biological no-opening constraints are **identical to v1**.

The only necessary technical change is to decode the original CSV via reversible **Latin-1 (one byte ↔ one code point)** instead of `utf-8-sig`. Only the two documented source identity fields `StemTag` and `year` can enter the calculations, and both must be **ASCII**. Standard CSV tokenization transiently handles whole rows to respect quoting and delimiters; other source columns are **not indexed, interpreted, retained, scored or exported**. This clarification is important: "no other column ever passed through the CSV tokenizer" would be incorrect.

The first Unicode failure does **not** establish which original biological text column contains a non-UTF8 byte. The reversible decoder avoids inventing a different source edition or dropping such rows, and source SHA is verified **before** source identity decoding.

Both original codebook and authoritative Harvard metadata list `StemTag`, `year`, and 2021–2024 census years, but the original row counts/duplicates remain unknown until the new scan. [Harvard HF453 data dictionary](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF453).

## Frozen v2 execution contract

- `scripts/hf453_tag_year_identity_source_only_v2.py`: sha256 + MD5 + size check **before** exact two-field indexing; reject non-ASCII identities, duplicates and year-frame gaps.
- `tests/test_hf453_tag_year_identity_source_only_v2.py`: simulated Latin1 non-UTF8 note, strict ASCII-tag rejection, UTF8 BOM compatibility, prior v1 STOP pin, original source-hash refusal, duplicates and no dependence on biological columns.
- `.github/workflows/sdmr-hf453-tag-year-source-one-shot-v2.yml`: branch-specific one-shot, triggered **only** by first creation of `configs/hf453_tag_year_original_once_v2.lock`. No network retries, fallback source editions or original CSV artifact. Exact UTF8 v1 source and terminal receipts stay untouched.
- Allowed endpoint is `tag_year_source_identity_indexed_only` or a declared source/identity STOP; **not** a mortality/survival result. Even a positive identity count does not establish that matching tags are alive, that an unrecorded tag is dead, or that sampling effort is complete.
- No physiology, causal competition, demographic outcome, multi-biome generalization, M5 reinterpretation or Product-B unblocking is permitted.

## Gate after v2

Only if the identity stage gives an original-source-verifiable success can a **separately frozen observation opportunity** stage begin. It must use independent original field protocols to audit actual effort/expected opportunities and prove a real at-risk denominator before reading any status rows. If the source refuses, preserve STOP as a method-availability finding and diagnose the source assumptions rather than cycling through thresholds or different data to manufacture a positive result.
