# HF253 × HF453: pre-outcome historical stem identity crosswalk, source-only v1

**Freeze on 2026-11-19, after the HF453 first observed-status outcome.** This is an explicitly **post-outcome exploratory source-linkage stage**, not a new independent biological test and not a way to change the preregistered 2021→2022 CP comparison. Its purpose is only to determine whether the older 2019 ForestGEO original records could provide pre-outcome species, diameter and plot context in a *future exploratory confounding audit*.

## Original sources and known physical grain

1. HF453: original Harvard Forest 2021–24 health/status file, version \`knb-lter-hfr.453.1\`, DOI \`10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193\`, exact whole-file SHA256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, MD5 \`c6be7aa99e31ded2041a0aaea07c0205\`. The frozen 2021 source cohort has **30,808 unique \`StemTag\`**, not necessarily 30,808 live observations. For this crosswalk, **only \`StemTag\` and \`year\` are read**; previously consumed \`status\`, \`CP\`, health, death or other biological Y is not reopened.
2. HF253: official Harvard Forest CTFS-ForestGEO Mapped Forest Plot **v6** (2023 publication; EML \`knb-lter-hfr.253.6\`), DOI \`10.6073/pasta/818789a882a318c1d7f3fc43a2289e12\`; original named **\`hf253-06-stems-2019.csv\`** at \`https://harvardforest.fas.harvard.edu/data/p25/hf253/hf253-06-stems-2019.csv\`. The official [author data dictionary](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF253) distinguishes \`tag\` (tree label), \`stem.tag\` (stem label, if present), \`tree.id\` and \`stem.id\` (different physical observational grains). Only these four fields may be indexed in this stage. All species, DBH, spatial position and 2019 alive/dead codes are **forbidden** to the matching operation.
3. The 2019 HF253 census did **not fully sample the central swamp**. Therefore, no exact crosswalk to that earlier provider record should be interpreted as proof that unmatched HF453 trees were absent, dead or unmeasured in 2021.
4. The HF253 original 2019 file has **not yet** been byte-hashed under this protocol. Unlike the prior HF453 original file, an exact publisher preview MD5 was **not independently verified before first fetch**; the first HTTPS acquisition can create a new immutable SHA-256 receipt and declares **publisher-asserted file/version identity without independently checked provider checksum**. Do not report a publisher MD5 match if none was supplied.

## Single predeclared read and both identity routes

- Strict direct HTTPS published URL, permitted same-file redirect only between known Harvard Forest hosts, one original GET, no automatic alternate versions, max 256 MiB.
- Verify the **known HF453 full source SHA-256, publisher MD5 and size before any old source processing**. Refuse an unexpected HF453 edition.
- HF253 \`tag\` and \`stem.tag\` are **two simultaneous source alternatives**, not competing outcome-predictive model choices. Compute both exact literal, case-sensitive and leading-zero-preserving intersections with the original 30,808 HF453 2021 tags. Do not normalize to maximize join success or choose a favorable branch using the already-opened HF453 mortality effect.
- Duplicate original \`tag\` rows can legitimately be multiple stems of one tree; count ambiguity only if one literal tag maps to multiple different \`tree.id\` values. Likewise, \`stem.tag\` ambiguity is based on distinct \`stem.id\` mappings. Missing original \`NA\` is not an individual identity.
- The outputs are the full HF253 **original record and candidate-key denominators**, exact matches via each candidate column, both / tree-only / stem-only / neither, and ambiguity counts. Only aggregate JSON and new first SHA/MD5 bytes are retained, **never original source rows, tag strings, taxon, DBH or outcome measurements**.
- An exact candidate tag match proves **string correspondence only**; it does not yet prove a stable physical tree/stem identity or whether a pre-2019 diameter/species value is an adequate proxy for 2021. Original author crosswalk and per-grain agreement remain separate gates.
- Any provider GET, header, source hash, malformed CSV or source-version failure must produce a STOP, not a presumed negative ecological result or a new model option.

## Downstream interpretation boundary

The earlier first HF453 field result remains what it was: **one source-specific CP-associated difference**, with a sharp missing-next-status interval excluding zero, but without causal confirmation. The next project would be a **post-outcome exploratory confounding check** using 2019 original species/size/site context if the source identity crosswalk is unambiguous and complete enough for its declared subgroup. The single physical forest cannot become multiple independent biomes by splitting into quadrats or species.

This linkage **cannot** change original Product-A \`not_promoted\`, blocked Product B, original M5 71/80, Structural 30/30, or the already-opened HF453 result. Keep PR #286 Draft.

## Reproducible files

- [Source-only preregistration](../configs/hf253_hf453_source_identity_prefreeze_v1.json).
- [First original source/linkage script](../scripts/hf253_hf453_original_tag_crosswalk_v1.py).
- [No-source synthetic tests](../tests/test_hf253_hf453_original_tag_crosswalk_v1.py).
- Lock-triggered, one-shot source-only workflow to be added, then activated **only after its tests and source contract are fixed**.
