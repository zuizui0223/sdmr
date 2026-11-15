# First FIA source-only cohort: recovered joint support, county-drift STOP and source-only successor (2026-11-15)

**Status: source-only geographic opportunity; not a measured biological limiting process.** This is an independently source-frozen acquisition from three U.S. states of the 13 originally declared tree taxa. It neither reopens the historical FIA v4 growth endpoint nor changes SDMR Product A, Product B or M5.

## Exact first-open evidence

- First source-only workflow: [run 43696751589](https://github.com/zuizui0223/sdmr/actions/runs/43696751589), commit [ff41eeb](https://github.com/zuizui0223/sdmr/commit/ff41eeb781b3791404231d1cccd26090e18ff28f). Source-only acquisition succeeded in **RI/VA/WI (3/3)** and reported **89,630 prior-visit species × plot-chain × remeasurement-interval observations**: RI 1,471; VA 38,142; WI 50,017. Every species was represented in all three states. This does **not** count independent trees or biological effects.
- Original source artifact: [14155086669](https://github.com/zuizui0223/sdmr/actions/runs/43696751589/artifacts/14155086669); ZIP SHA-256 **85d8cc0b6efb120736166a581f608ad10d7de70dd3732bd68a8c7b3fc44acff3**. Original uncompressed CSV SHA-256 **cc68e0604287a49f32fd791bcf72ee60254809ab648a9f88946f1c8a2c72bf7f** and source receipt SHA-256 **0adcdeac7b974e91b83d986fca32ad0851000658f79fbe099407ce2fb37fa408**. Source receipt contains new FIA PLOT/TREE ZIP identities and the independently frozen NOAA county climate identity.
- The original one-shot job ended **failure**, not source non-availability: the source-only PLOT/TREE acquisition step succeeded and the *next* joint-support step raised \`ValueError: plot county identity changed between source intervals\`. The original failure and immutable input are preserved. Its run outcome must not be rewritten as success.

## Exact first-source geographic quality issue

A postsource, **biological-response-blind** inspection of all 89,630 source rows located **one** plot-chain identity with **two different Virginia county FIPS codes**, across four source remeasurement intervals. It contributes 14 taxon × interval records from five taxa. All other plot chains had one stable county identifier. Assigning all records to whichever county occurs more often, or treating each side as an independent new plot, would invent site identity. Both are prohibited.

An isolated successor under \`experiments/fia_joint_source_reconcile_v2.py\` uses the **uniform complete-chain exclusion rule**: whenever an original \`(state, plot_chain_id)\` maps to multiple county FIPS codes, all its taxon × interval observations are removed *before* evaluating any climate support. The rule does not inspect climatic values to decide which records survive. It archives the original denominator, the reason and the numbers excluded, as well as the exact derived CSV and receipt fingerprints. **No new DataMart download** occurs.

This is post-source QC, NOT a predeclared successful rerun of the original blocked workflow, and NOT a selection of favorable ecological outcomes. The old source-only STOP remains independently inspectable.

## Exploratory fixed-design source-support result (recomputed from archived first input)

The uniform rule excludes **14/89,630** taxon–interval observations and one Virginia plot chain. Remaining observations: **89,616**. The original fixed exploratory design checks **paired temperature × precipitation × five-year measurement cohort** cells, minimum two counties and five unique plots per cell, at least two jointly shared cells, at least five counties and 25 independent plot chains per state/species, and ≥20% shared-period **unique-plot** coverage per state. These development thresholds were selected after earlier v4 biological results and must not be called a pre-registered independent efficacy test.

| Taxon | RI counties | RI independent plot chains | 3-region common T–P–time cells | Source-only condition |
|---|---:|---:|---:|---|
| *Juniperus virginiana* (68) | 4 | 13 | 2 | Insufficient RI geographic units |
| *Pinus strobus* (129) | 5 | 72 | 9 | **Pass** |
| *Tsuga canadensis* (261) | 4 | 9 | 1 | Insufficient RI units and shared support |
| *Acer rubrum* (316) | 5 | 131 | 10 | **Pass** |
| *Acer saccharum* (318) | 3 | 12 | 1 | Insufficient RI units and shared support |
| *Betula alleghaniensis* (371) | 5 | 28 | 3 | **Pass** |
| *Fagus grandifolia* (531) | 3 | 13 | 2 | Insufficient RI units and WI coverage |
| *Fraxinus americana* (541) | 3 | 27 | 6 | Insufficient RI counties |
| *Populus grandidentata* (743) | 3 | 14 | 3 | Insufficient RI geographic units |
| *Prunus serotina* (762) | 4 | 26 | 6 | Insufficient RI counties |
| *Quercus alba* (802) | 5 | 95 | 9 | **Pass** |
| *Quercus rubra* (833) | 5 | 80 | 9 | **Pass** |
| *Quercus velutina* (837) | 5 | 72 | 9 | **Pass** |

**6/13** taxa meet this **descriptive opportunity gate**. All 13 share at least one time-aligned T–P cell at the specified coarse resolution, but that is insufficient for the declared independent geographic coverage requirements. All seven non-passing taxa fail the five-RI-county threshold; this is retained, not relaxed or reweighted after seeing the output. Among the six passing species, RI has **exactly five** counties, so spatial replication and external transfer remain limited.

These figures were obtained from an independent offline reimplementation immediately after detecting the original gate error, and are to be checked against the **canonical unchanged** source-only evaluator using a SHA-frozen derived artifact. If the canonical evaluator differs, keep both records and investigate; do not silently promote the favorable count.

## Reproducibility and scientific boundary

No \`TREE.STATUSCD\`, \`TREE.DIA\`, survival, growth rates, fitted ecological coefficients or sealed biological test results were accessed for this analysis. The supplier inputs come from *prior-visit species identity* and NOAA county climate. This is a **coarse observational common-support proxy**, not functional niche overlap, exact environmental equality within grid cells, adaptation, or a causal constraint switch.

Offline reproduction with the originally downloaded artifact extracted to a directory:

\`\`\`bash
python experiments/fia_joint_source_reconcile_v2.py \
  --source-dir path/to/extracted_artifact_14155086669 \
  --config configs/fia_joint_climate_support_gate_v1.json \
  --output-dir build/fia_joint_source_reconcile_v2
\`\`\`

To preserve historic failure and avoid mutable DataMart replay, the dedicated reconciliation workflow uses **only original GitHub artifact 14155086669** by run and artifact name, requires original exact CSV/source receipt SHA-256, and uploads the filtered source-only table and the quantitative evidence receipt. It contains **no call to the FIA or NOAA acquisition clients**.

**Next evidence boundary:** review the canonical source-only reconciliation artifact, verify its 13-species denominator, source identity, exclusions, temporal overlap and per-region support. Then design a new **separately frozen**, plot/county-clustered growth/survival comparison. Even a later favorable prediction contrast would remain a noncausal association absent independent physiological or experimental evidence.
