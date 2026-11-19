# HF253 × HF453 parent-tree identity source audit — first original result (2026-11-19)

**Evidence status:** independently versioned original-source *physical unit/identifier audit PASS*. **Not a new biological process or causal result.** This resolves the previously unknown distinction between original **stem tags** and **parent tree IDs** for the one-forest Harvard source.

## Frozen source and first opening

- The full Harvard Forest HF453 2021–24 original file was reverified at SHA-256 `0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74`, prior publisher MD5 `c6be7aa99e31ded2041a0aaea07c0205`, 5,524,386 bytes.
- The original 2019 HF253 v6 stem file was independently reverified at first archived SHA-256 `bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7`, 12,687,409 bytes. Its originally computed MD5 is **not** represented as publisher-verified.
- One-shot [run #44544941037](https://github.com/zuizui0223/sdmr/actions/runs/44544941037), source commit `c4eb99273483e6422eb89bf5ce787e17ea6242ee`, **SUCCESS**: exact source SHA and synthetic physical-ID ambiguity tests passed before reading any original mechanical tag fields.
- Result artifact **#14539477449**, ZIP SHA-256 `1528147b05ef632b468a51d5c77400c8041f5842bf5cd36047c202edfbe92930`, original result JSON SHA-256 `a60b2adb646876cac411c60be635393f3a56322a22c1df8683033275820ea2aa`. [Permanent machine evidence](../evidence/hf253_hf453_parent_tree_grain_v1.json) and [pre-result frozen contract](SDMR_HF253_HF453_PARENT_TREE_GRAIN_PREFREEZE_20261119.md).
- Source-only original fields actually indexed: HF253 `stem.tag`, `stem.id`, `tree.id`; HF453 `StemTag`, `year`. Tree species, size, status, CP, death, growth, and other biological fields were **not interpreted or retained**. No raw original stem/tree identifiers or per-individual rows were archived.

## Main result: 30,808 original stem tags represent fewer original parent IDs

| Source-verified identifier metric | Count |
| --- | ---: |
| HF453 original unique 2021 `StemTag` | **30,808** |
| Exact original HF253 `stem.tag` matches | **30,808/30,808** |
| Missing, contradictory or ambiguous original `stem.id → tree.id` parent mapping | **0** |
| Distinct original parent `tree.id` of all 30,808 stems | **27,688** |
| Extra source stem tags beyond unique original parent IDs | **3,120**, approximately **10.13%** of stem tags |
| Parent IDs with ≥2 matched stems | **2,331**, approximately **8.42%** of parent IDs |
| Stem tags belonging to these multi-stem parent IDs | **5,451**, approximately **17.69%** of stem tags |
| Largest matched number of stems under one original parent ID | **8** |

Full multiplicity by original parent ID:

| Matched stems per parent ID | Number of parent IDs |
| --- | ---: |
| 1 | 25,357 |
| 2 | 1,775 |
| 3 | 404 |
| 4 | 101 |
| ≥5 | 51 |
| **Total** | **27,688** |

The 51 parent IDs in the ≥5 group contribute 285 matched stem tags. Weighted totals reconcile to the full **30,808** matched tags; 2,331 multi-stem parents contribute **5,451** tags.

The earlier literal `HF453 StemTag → HF253 tag` comparison matched only **27,673** strings, whereas the direct original `tree.id` count here is **27,688**. These are **different quantities**, not a 15-tree error: a string match with the tree-tag column is neither the complete parent-ID set nor a substitute for explicit original stem→tree lineage. No matching key was reselected using the later HF453 status effect.

## Inference consequences

The predeclared [HF453 2021→2022 recorded-dead/status association](SDMR_HF453_FIRST_STATUS_RESULT_20261119.md) (lower-light CP1/2 323/10,452 vs more-exposed CP3/4/5 138/11,390, sharp unknown-status sign negative) remains a **per-stem-tag** original-source contrast. It is not a tree-level mortality rate, randomized canopy contrast or 30,808 independent tree responses. Stems within one source parent `tree.id` may share latent health, genotype, microsite, history, exposure and observer processes.

This source-only audit **does not alter** the earlier numerator/denominator for the frozen per-stem estimand or its algebraic missingness bounds. It **does** bar the interpretation of each source stem tag as an independent tree for p-values or confidence intervals, and makes parent-tree clustering mandatory for any separately designed **post-outcome exploratory** statistical uncertainty check. A parent-tree ID is not proof of ecosystem-level independence, because all records are from one 35-ha forest.

The source metadata do not by themselves establish complete field detection, absent trees, true tree-level death states or environmental process identity. No physiological competition, forest-transfer or cross-biome generalization is identified. Original Product-A remains `not_promoted`, Product B blocked, M5 71/80 and Structural synthetic 30/30 unchanged. [PR #286](https://github.com/zuizui0223/sdmr/pull/286) stays Draft.

## Next independent methodological action

A properly labeled **post-HF453-outcome exploratory** robustness study may compare per-stem recorded-dead contrasts with parent-tree clustered scores, but cannot make this first positive association into preregistered evidence. It must predefine the complete 30,808-stem parent-cluster denominator, how to handle different CP values for stems of the same tree, unknown `DN` status, and assumptions of spatial nonindependence. An actual independent forest-provider/biome validation is still needed to show transferability or a general mechanism.
