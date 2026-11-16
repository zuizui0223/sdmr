# VA/WI five-fold county source-readiness for a biological response comparison

**Status (2026-11-16):** postsource, outcome-blind *design feasibility*, NOT a prospective or confirmatory biological effect. No new FIA/NOAA download, TREE diameter/status/survival opening, or SDMR Product A/B/M5 reclassification.

## Testable next biological question and a necessary design distinction

The real question is whether **within-species** tree growth or observed survival in VA and WI are better predicted by (a) one shared response to temperature, precipitation and forest density (plus region intercepts), or (b) regional modifications of those response slopes. This is an association-level predictive contrast; it cannot demonstrate genetic adaptation or physiological limitation.

RI is an **external geographical check of the shared response only**. Estimating an **RI-specific** response coefficient from exclusively VA/WI training would be mathematically impossible: that parameter is unidentified. A direct comparison of an RI-specific fitted response with the stationary model on RI without RI calibration would be invalid. Even if RI climate is covered by VA/WI observed climate cells, RI growth outcomes and design information still must be independently acquired and assessed.

## Existing immutable source and preflight

Use exactly the prior source-only, county-stable artifact [run 43711159676](https://github.com/zuizui0223/sdmr/actions/runs/43711159676), artifact 14160283759. Verified source-only CSV SHA-256 \`44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7\`, source receipt SHA-256 \`f167966bdd19529fe39955863effd666943e624cf939bd7c80ac8908b6a3f453\`. Exactly 89,616 prior-visit species × plot-chain × interval source rows, of which RI is **never used** to construct VA/WI training climate cells. The original failed run and exclusion of one whole county-unstable VA plot chain remain unchanged.

\`experiments/fia_VA_WI_county_source_folds_v1.py\` reproduces the **original v4 outcome-blind county fold allocation**: the first four bytes of \`SHA256(FIPS county)\`, modulo 5. Within each of 13 previously declared species and each of 5 county folds, remove **all** observations from both states' heldout counties, build candidate temperature × precipitation × five-year cells on the training counties in VA and WI separately, require ≥2 counties and ≥5 independent plot chains in a cell per region, and intersect the qualified VA/WI training cells. Then test what fraction of unique heldout VA and WI plot chains fall inside that **training-derived** intersection. No heldout environmental record can select a training bin.

This preserves a fixed 65-cell denominator, including missing and inestimable folds. All source-defined taxa remain present; the preidentified five most source-robust species are \`129/316/802/833/837\`, and the other eight are reported rather than discarded.

## Preliminary non-biological result, separately frozen for deterministic replay

The original *minimal environmental support criterion* (heldout VA+WI counties exist, ≥2 VA/WI training-shared joint climate-time bins, each heldout state has ≥20% covered unique plot chains) was met in **65/65** species-fold cells on the archived source. However, this is not the same as a **credible demographic-response design**. Under a stricter, explicitly postsource development gate requiring **≥20 training counties and ≥3 test counties in each region, ≥20 heldout independent plot chains in each region, at least two common training cells, and ≥20% heldout plot coverage**, the independent offline preflight returns **47/65** species-fold cells.

**All five folds of the five preidentified robust taxa pass (25/25)**. Other taxa vary, especially VA-sparse *Betula alleghaniensis* (0/5 with ≥20 VA heldout plots), WI-sparse *Fagus grandifolia* (0/5 with ≥20 WI training counties), and *Populus grandidentata* (0/5 with ≥20 VA heldout plots). Never relax thresholds after inspecting either structural or biological outcomes merely to restore all 13 species.

| Species | Minimum VA source plot coverage across five county holdouts | Minimum WI source plot coverage |
|---|---:|---:|
| *Pinus strobus* (129) | 93.5% | 99.5% |
| *Acer rubrum* (316) | 98.0% | 99.7% |
| *Quercus alba* (802) | 98.2% | 99.0% |
| *Quercus rubra* (833) | 97.2% | 99.5% |
| *Quercus velutina* (837) | 92.7% | 97.6% |

These are fractions of **source-observed plot chains**, not recorded trees that necessarily provide paired growth or survival data. The results will be confirmed by a separate SHA-frozen GitHub run; only that run should be treated as the canonical machine-generated source audit. The current five-source-taxon subset was selected after other source/outcome analyses and is **not** a fresh randomly drawn biological sample.

## What cannot yet be inferred, and how to advance

- **Data gap:** this source-only CSV cannot provide matched prior/current DIA, previous live/current alive-dead-removed, management history, FIA plot expansion factors, crown/physiology, nor growth of trees not reobserved. Historical v4 opened an overlapping source but retained only aggregated conditional survivor growth, not the exact raw data for a new independent split.
- **Sampling risk:** same plot-chain sampled through multiple intervals is one spatial cluster, not independent evidence. Counties vary in plot numbers; inverse-HHI descriptions and equal-county predictive scores are not substitutes for county-cluster intervals.
- **Correct model comparison:** within VA/WI and predeclared disjoint county folds, compare stationary and region-dependent response surfaces; keep a minimum worthwhile **out-of-county** improvement fixed before *new* outcomes are inspected, and report both numerical prediction and cluster-level uncertainty. Preserve growth conditional on live-to-live separately from mortality/status transitions among all previously live linked trees. Missing follow-up and removals are not deaths.
- **RI transfer:** use a shared VA/WI model without any RI-specific coefficient. If assessing a region-varying model on RI, separately predefine an RI-calibration cohort and genuinely disjoint RI evaluation counties; do not borrow test data for fitting.
- **Provenance:** another current USDA DataMart ZIP is a *new mutable source version*, not an independent set of tree outcomes or a replacement for historical SHA-frozen source. Source version does not equal sample independence. A future run must seal the full raw accession and eligibility before opening response, keep all original negatives and follow a distinct versioned study contract.

Thus the positive source-level finding makes **biological testing technically plausible**, not scientifically passed. No statement about niche evolution, causally dominant stress, growth/survival transfer or Product-B driver universality is promoted.

## Reproduce without accessing any response

\`\`\`bash
python -m pytest -q tests/test_fia_VA_WI_county_source_folds_v1.py
python experiments/fia_VA_WI_county_source_folds_v1.py \
  --source-dir build/frozen_source_only \
  --config configs/fia_joint_climate_support_gate_v1.json \
  --output build/fia_VA_WI_county_source_folds_v1.json
\`\`\`

The one-shot workflow reads only archive 14160283759 and emits the full 13 × five-fold numerical and exclusion-reason audit. The output is a *source-readiness ledger*, not a fitted ecological result.
