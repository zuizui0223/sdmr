# HF453 v1 first original-publisher byte admission — locked source-only audit

**Stage: a separately frozen original-byte integrity test, not a biological outcome-opening protocol.** This has no overlap with the original M5 or 80-case Structural known-truth seed denominators, or with the consumed FIA/Structural ecological response sets.

## Source frozen before network

- Scientific purpose: verify that the *actual original provider file bytes* can be acquired and matched to an already published checksum without decoding any row, before proceeding to physical sampling opportunity and longitudinal risk-set checks.
- Publisher: Harvard Forest Annual Tree Health and Mortality Survey, **HF453 (v.1)**, EML **\`knb-lter-hfr.453.1\`**, DOI **10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193**, CC0.
- Exact single GET origin: **\`https://harvardforest.fas.harvard.edu/data/p45/hf453/hf453-01-tree-census-2021-2024.csv\`**, permitting only a known HTTPS redirect to \`harvardforest1.fas.harvard.edu\` at the same filename.
- Pre-recorded publisher preview checksum: MD5 **\`c6be7aa99e31ded2041a0aaea07c0205\`**. This is a *provider-published reference*, not a previously checked local SHA.
- Exactly one non-retrying network GET attempt; stream at most 48 MiB, compute byte SHA-256 and MD5, discard chunks without parsing CSV, keep only JSON receipt. In particular, no tree status, year, crown, health, death or growth values enter the analysis.
- Only \`configs/hf453_original_source_once_v1.lock\` creation on branch \`method/structural-context-closure-v1-20261118\` triggers the one-shot workflow. Changes to this document, unrelated code and ordinary PR updates **cannot** trigger a new source GET.

## Precommitted outcomes

1. \`original_byte_md5_matched_source_only\`: same entire retrieved original file bytes match recorded publisher MD5; store SHA-256 and byte size in a versioned receipt. This is **raw-file identity only** and does not authorize model fit or opening tree status responses.
2. \`publisher_md5_drift_stop\`: fully downloaded bytes did not match the publisher checksum; no silent acceptance of a revised dataset or alternate source.
3. \`original_source_unavailable_stop\`: HTTP or network/TLS access was unavailable; do not interpret as ecological absence or negative biological evidence.
4. \`original_source_integrity_stop\`: redirected URL out of allowlist, incorrect provider filename, exceeding the prespecified byte limit or malformed original source; stop.

The workflow asserts that its saved JSON **never** reports original response rows decoded, retained raw CSV, new biological model fits, empirical confirmation or Product-B unblocking. There is no fallback to a mutable EDI edition or a newer file, no automatic favorable rerun, and no change to the original M5/Structural/FIA decisions.

## Files

- \`scripts/hf453_original_byte_preflight_v1.py\`: original HTTPS stream-hash, exact MD5 expectation, redirect/size/refusal rules.
- \`tests/test_hf453_original_byte_preflight_v1.py\`: synthetic-only no-network fixtures, one-attempt/no-body, MD5-match/drift and HTTP STOP, contract/lock checks.
- \`.github/workflows/sdmr-hf453-original-byte-one-shot-v1.yml\`: lock-triggered first source-only execution; only JSON artifact retained.

## What remains after any byte-level PASS

**Original source version verification is necessary but not sufficient.** The author-public HF453 codebook reports annual field health/status censuses across one 35-ha forest (2021–2024), but those rows have **not** been audited here. For a separate *new* response protocol:

1. Reconstruct genuine \`StemTag × census occasion\` identity and source physical plot; do not invent across-forest independent sample counts.
2. Freeze at-risk living tree risk-events and an externally checkable census date/effort/opportunity ledger. Unrecruited/unobserved and missing are not observed zeros.
3. Keep \`DC/DS\` observed dead, \`DN\` (dead/not found) unresolved as to directly observed death. Verify status and actual outcome transitions before any binary partial-identification calculation.
4. Declare independent physical blocks and suitable pre-outcome covariates; report a **single-forest** within-site diagnostic only. This file alone cannot support cross-biome or plant-wide transfer.
5. Only after a separate prospective model/target freeze and legal scientific-source access may the tree-level response be opened for field testing. The full sampling observation audit can still fail even after publisher MD5 matches.

Source publication and methods: [Harvard Forest HF453](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF453); [Harvard Forest archived-data policy](https://harvardforest.fas.harvard.edu/data-archives/data-archive/).

**No main-branch promotion:** PR #286 stays Draft until independent biological and source-opportunity evidence exists.
