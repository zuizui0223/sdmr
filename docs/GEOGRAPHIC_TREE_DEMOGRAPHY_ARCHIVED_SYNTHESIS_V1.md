# FIA: geographic growth heterogeneity within the same trees' species

**Status:** post-outcome, descriptive, not confirmatory. This is a second-stage synthesis of the **already opened** FIA RI/VA/WI first-response aggregate. The biological interpretation is deliberately narrower than regional physiological adaptation or niche-driver turnover. No historical SDMR Product A, Product B, or M5 endpoint was reopened.

## Source and audit contract

- Authoritative CI source: [GitHub Actions run 39244950162](https://github.com/zuizui0223/sdmr/actions/runs/39244950162), artifact **12183086705** from the corrected first-response build.
- The exact **79,672-byte** original aggregate JSON is committed at `evidence/geographic_tree_demography_first_response_v1/aggregate.json`, SHA-256 **`57259fe905a610e311934b6cbc3a54143677629d2a87df7e7ee6bbe7cc64d414`**.
- The script `experiments/geographic_tree_demography_archived_synthesis_v1.py` verifies the original file SHA, the three original USDA TREE ZIP hashes, **exactly 13 species × three states**, source counts, no duplicate taxa, the linked live/dead status denominator, the exact size-band membership and reconstruction of pooled-weight size-standardized means. It does **not** download new source data or refit models.
- The full first-response source gate was nominated from forward-year same-tree `PREV_TRE_CN → CN` links, before diameter/status outcomes opened. Source-eligible codes were `68,129,261,316,318,371,531,541,743,762,802,833,837`. The earlier 22-code *display* bug has been removed: extra species are not stored as zero-response observations in the corrected source.

## What is observed

Across three US states (Rhode Island = RI, Virginia = VA, Wisconsin = WI), the first response contains **308,181** observed live→live diameter pairs for 13 named taxa (5,190 / 100,189 / 202,802 by state). Growth is annualized change of **log stem diameter**, *not* annual wood biomass productivity or a physiological tolerance curve. One- to twenty-year inventory-year intervals are admitted; period, site, plot, management, density, source measurement and climatic exposure are **not matched**.

Nine of 13 species have at least one initial-diameter size band (1–<5, 5–<10, 10–<20, 20+ inches) with **≥30 observed live→live pairs in every state**. Four species do *not* meet this condition: they remain *unestimable*, not zero growth. Within each eligible species, size-standardized means reweight its common bands by that species' pooled observed matched-pair counts.

| Species | Common diameter bands | RI log growth/y | VA | WI | WI > RI in all common bands? |
|---|---:|---:|---:|---:|---|
| *Pinus strobus* | 4 | 0.01566 | 0.02048 | 0.02312 | yes |
| *Tsuga canadensis* | 2 | 0.01234 | 0.00995 | 0.01128 | no (1/2) |
| *Acer rubrum* | 3 | 0.00911 | 0.01286 | 0.01621 | yes |
| *Betula alleghaniensis* | 3 | 0.00942 | 0.00970 | 0.01209 | yes |
| *Fagus grandifolia* | 1 | 0.01830 | 0.01723 | 0.01566 | no (0/1) |
| *Fraxinus americana* | 1 | 0.00838 | 0.01576 | 0.01880 | yes (1 band only) |
| *Quercus alba* | 2 | 0.00687 | 0.01080 | 0.00942 | yes |
| *Quercus rubra* | 3 | 0.01136 | 0.01336 | 0.01536 | yes |
| *Quercus velutina* | 2 | 0.00979 | 0.01211 | 0.01468 | yes |

The 9 species contain **21** selected species×size-band contrasts for WI versus RI; **19 are positive**. Importantly these are **correlated within species**, *not* 21 independent biological experiments.

**Cross-taxon descriptive pattern:** WI exceeds RI size-standardized growth for **7/9** comparable taxa; among **7 taxa with ≥2 common bands**, **6** have WI > RI **in every eligible band**. Six of the nine comparable taxa show a strict RI < VA < WI ranking. Minimum-band sensitivity is WI > RI for 7/9 (≥1 band), 6/7 (≥2 bands), and 4/4 (≥3 bands). These numbers are statements about *this fixed sample*, **not** population prevalence or a universal species response.

The linked fraction `dead/(observed live+observed dead)` after a prior-live recorded tree is **RI ≈0.1202**, **VA ≈0.1308**, **WI ≈0.1199** when pooling fixed 13 taxa. This is *not* annualized mortality and *not* population mortality: survey intervals, missing links, non-tallied and removed stems, and FIA expansion factors are not adjusted. Across the **nine** species with comparable growth, each region pair contains **three taxa where growth and linked-death fraction are both higher** and **four where growth is higher but linked-death fraction is lower**; growth rankings do not map one-to-one to this status endpoint. Thus these data **do not establish** a general growth–mortality trade-off.

## Biological interpretation (bounded)

**A positive descriptive fact:** regionally differentiated observed growth **persists within repeated size bands of the same tree species** for several taxa. Thus a simple *between-size-class composition* artifact cannot fully explain the direction of those means in the observed survivor cohort. A falsifiable ecological hypothesis is whether local stand structure, disturbance and temporal drought/thermal exposure account for these same-species contrasts with a *single shared growth response function*—rather than genetically diverged local optima.

**Not established:** (i) the Wisconsin trees are more productive in standardized forest populations; (ii) cooler climate causes higher growth; (iii) physiological growth constraints switch with geography; (iv) mortality changes are caused by the growth differences; (v) niches evolved or remained invariant. Spatial units are US states, not matched ecological climates; FIA public coordinates are intentionally fuzzed.

**Selection concern:** live→live growth is conditional on surviving and remaining observed, whereas dead status is aggregated over linked prior-live trees. Survivor selection can create size- or site-dependent apparent growth differences. Year intervals and plots are not exchangeable, nor have plot design weights, environmental exposure, forest disturbance or genetic composition been controlled.

## Reproduce locally without opening any new outcome

```bash
python -m pytest -q tests/test_geographic_tree_demography_archived_synthesis_v1.py
python experiments/geographic_tree_demography_archived_synthesis_v1.py \
  --source evidence/geographic_tree_demography_first_response_v1/aggregate.json \
  --output results/fia_archived_regional_growth_status_synthesis_v1.json
```

Everything required is text in this branch, not an expiring Actions artifact. A CI job compares the newly generated JSON to the committed output **without fetching an additional FIA ZIP**.

## Next empirical test, if pursued as a separate prospectively frozen programme

1. Use FIA **plot, condition, cycle and remeasurement interval** records to define temporal and stand-level strata; do not treat two tree links in the same plot as independent.
2. Join an independently justified **environmental exposure** with its spatial uncertainty to plots, not state averages. Public FIA spatial perturbation makes fine-resolution climate matching unsafe without an explicit error model.
3. Estimate **growth conditional on live status** separately from **survival over the observation interval**, explicitly handling removals and missing follow-up and FIA design weights.
4. Compare a **stationary environmental response**, regional interaction, and environmental-availability-only null, using truly unseen plots/sites and a common climate-support check. Use independently measured physiology or field trials before claiming evolved climatic tolerances.

Do not lower original common-environment/eligibility thresholds because this first observed outcome looks suggestive. No inference to SDMR's blocked Product B is made.
