# HF253 × HF453 original parent-tree grain source-only first audit — frozen 2026-11-19

**Pre-open scientific state:** metadata-source identity only, no new ecological or demographic endpoint. Parent counts are **unknown** until the one-shot audit. The HF453 field-status association was already opened in run #44540469560; this audit must not inspect any status, canopy, taxon, DBH, growth, mortality or response variables and cannot become an independent biological replication.

## Why this source-only check is necessary

The frozen HF453 2021 published panel has 30,808 distinct `StemTag` identifiers. Original HF253 2019 stem records matched all **30,808/30,808** HF453 tags literally via `stem.tag`, whereas original `tag` (tree tag) matched only **27,673/30,808**; tree-tag-only joins would omit 3,135 stem tags. See [the first exact original source result](../evidence/hf253_hf453_original_stem_tag_crosswalk_v2.json) and [original source-only workflow #44543555701](https://github.com/zuizui0223/sdmr/actions/runs/44543555701).

A successful stem-string match does **not** establish 30,808 independent physical trees: one original `tree.id` can own multiple `stem.id` and `stem.tag`. Therefore a defensible next unit is the original parent **tree ID**, retaining the original source's multiple-stem grouping.

## Frozen sources

- HF453 original Harvard 2021–24 single-forest file: SHA-256 `0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74`, MD5 `c6be7aa99e31ded2041a0aaea07c0205`, exactly **5,524,386 bytes**. Read only `StemTag` and `year` to reconstruct the **same** original 30,808-tag 2021 frame.
- HF253 original Harvard Forest 2019 stem records `hf253-06-stems-2019.csv`, EML `knb-lter-hfr.253.6`, DOI `10.6073/pasta/818789a882a318c1d7f3fc43a2289e12`, source URL `https://harvardforest.fas.harvard.edu/data/p25/hf253/hf253-06-stems-2019.csv`. The first prior original-source hash was SHA-256 `bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7`, file size **12,687,409 bytes**; first computed MD5 **is not publisher-verified**. Re-acquired bytes must match **the entire SHA-256 and length** before parsing original stem/tree identity fields. No alternate version, filename, source URL or fallback allowed.
- Both sources belong to the **same physical Harvard Forest**. The 2019 source census did not completely cover the central swamp; unmatched tags may reflect sampling rather than true absence.

## Predeclared source-only fields and decisions

Only HF253 original `stem.tag`, `stem.id` and `tree.id` are indexed, alongside HF453 original `StemTag` and `year`. Standard CSV tokenization touches other source cell strings transiently to maintain quoting, but no other values are used, retained, scored or logged. No output may contain original stem/tag/tree IDs or raw CSV data.

For the **entire fixed set of 30,808** HF453 2021 stems, not only a convenient matched subset:

1. Count exact `stem.tag` matches, unmatched tags and inconsistent/duplicate stem-to-parent `stem.id/tree.id` pairs. Never silently coalesce ambiguous stems.
2. Count original unique **`tree.id`** among unambiguous matched stems, and the number of `tree.id` with two or more matched `stem.id` members.
3. Publish only aggregate parent multiplicity histogram (one, two, three, four, five+ matched stems per original tree ID), largest matched-stem multiplicity and number of stems contributed by multi-stem tree IDs.
4. If any HF453 tag is unmatched, lacks a verified original parent ID, or maps ambiguously, return `parent_tree_identity_incomplete_source_hold`; **do not** turn that into zero trees, or narrow the panel to rescue a result.
5. Otherwise return `parent_tree_identity_mapped_source_only`. It authorizes a **method unit-definition audit only**—not proof that original tree IDs represent independent trees in ecology, and not an update to the earlier HF453 mortality effect.

No ecological coefficient, tree species or size variable, unmeasured sampling effort or site effects will be estimated. A parent-tree count is a **cluster frame** for future guarded inference, not a claim of forest-wide effective sample size.

## Reproducibility and evidence ceiling

- [Response-free original-source adapter](../scripts/hf253_hf453_parent_tree_grain_source_v1.py) verifies exact complete source digests **before** original ID extraction, uses a temporary source file removed at job exit, and emits aggregate JSON only.
- [Synthetic tests](../tests/test_hf253_hf453_parent_tree_grain_source_v1.py) verify the multistem-versus-tree grouping, ambiguity STOP, missing parent, biological-column mutation invariance and no-network preflight.
- A new once-only source contract requires exact code/test hashes, the unchanged original sources, a fixed source-only lock, and artifact archiving with `if-no-files-found: error`. No ordinary PR edit may retrigger another source GET.
- Preserve Product-A v2.8.4 `not_promoted`, Product B `blocked`, original M5 71/80, Structural synthetic 30/30 and prior consumed FIA/HF453 endpoints. No new biological replication is created.

**No raw parent IDs were inspected when this plan was frozen.**
