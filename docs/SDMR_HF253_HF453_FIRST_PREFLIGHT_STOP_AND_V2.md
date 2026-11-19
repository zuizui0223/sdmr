# HF253×HF453 original 2019 source-only first source STOP and v2 technical successor

**First v1 terminal:** [run #44542568429](https://github.com/zuizui0223/sdmr/actions/runs/44542568429), GitHub conclusion FAILURE **before any external HF253 GET**. The exact preregistered [source-only first config](../configs/hf253_hf453_source_identity_prefreeze_v1.json) intentionally states \`drop_ambiguous_matches=false\`: every exact literal HF453–HF253 source match must be **counted**, with ambiguous historical \`tree.id\` / \`stem.id\` mappings reported instead of being silently pruned.

## Failure → cause → limited repair

1. First executable v1 [\`scripts/hf253_hf453_original_tag_crosswalk_v1.py\`](../scripts/hf253_hf453_original_tag_crosswalk_v1.py), Git blob \`05ba4e6c3f202112adc45bb10d790111e24beb2b\`, mistakenly placed \`drop_ambiguous_matches\` among **flags required TRUE**. This inverted a scientific-safety Boolean already fixed FALSE in source config and made three synthetic tests fail.
2. The workflow correctly did **not** proceed to preflight or provider original file GET. There is **no HF253 raw file SHA**, no original source-count result, no source tag match denominator or additional field outcome. Permanent [first STOP receipt](../evidence/hf253_hf453_original_tag_source_v1_preflight_stop.json).
3. The separate [v2 parser](../scripts/hf253_hf453_original_tag_crosswalk_v2.py) changes only that Boolean contract: \`drop_ambiguous_matches\` **must be literal \`False\`**, alongside no case-folding or leading-zero normalization. Same source, URL, keys, max file size, original HF453 SHA, identity categories and no-outcome policy. This is **not** new a posteriori cohort/model/threshold selection; v1 never acquired HF253 original data.
4. [v2 tests](../tests/test_hf253_hf453_original_tag_crosswalk_v2.py) verify this inversion, multiple-stem same-tree identity handling, ambiguous tree IDs, strict tag and stem.tag candidate intersection, zero dependence on species/DBH/status and no-network preflight. Three original v1 tests are now explicitly strict-XFAIL with documented terminal reason; the v1 code and scientific failure are not rewritten.
5. The new [one-shot v2 workflow](../.github/workflows/sdmr-hf253-hf453-tag-crosswalk-one-shot-v2.yml) enforces the exact **new v2 Git blob fingerprints** plus unchanged original scientific config, then performs synthetic no-network checks **before any provider GET**. The original 2019 raw file becomes a new first source only when these pass. Raw source rows or biological outcome values are never archived.

## Scientific interpretation if source access succeeds

A literal link between prior HF253 \`tag\` or \`stem.tag\` and later HF453 \`StemTag\` is **only a candidate key match**. It cannot prove a tree- or stem-level biological identity or rescue the already opened 2021→2022 HF453 canopy/mortality association. HF253 2019 was an earlier census with incomplete swamp coverage. All matched, ambiguous and unmatched source tags must remain in the count. Any future species/size adjustment would be **post-outcome, one-forest exploratory**, never a confirmatory independent field replication or a causal density/competition result.

Product-A v2.8.4 remains not promoted, Product B remains blocked, original M5 71/80 and Structural 30/30 preserved. PR #286 remains draft.
