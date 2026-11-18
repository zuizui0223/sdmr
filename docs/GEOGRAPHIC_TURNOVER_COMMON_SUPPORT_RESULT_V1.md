# First-open climate-only common-support screen (2026-10-19)

**Status:** complete *environmental source-opportunity* result; **zero eligible region pairs**, no occurrence-model evaluation and no ecological niche-driver evidence. The research design (`configs/geographic_turnover_common_support_v1.json`) was committed before source opening at PR #284 commit `e59a4d70ac82b95565eb935055cd7fd1a2450791`.

GitHub Actions source run: [39234811610](https://github.com/zuizui0223/sdmr/actions/runs/39234811610), artifact 12177154884, job `climate-only-preflight` **success**. All ten declared regional CHELSA BIO1/BIO12 rectangles were complete: **571 equal-area 25-km climate cells**. There are five regions per taxon, so ten within-taxon unordered comparisons per taxon, **20 total**. Every candidate remains in the archived receipt, including failures. **0/20** passed the predeclared joint climate-overlap, minimum distance and spatial-support conditions. No focal GBIF occurrences or sampling-effort weights were accessed by this workflow.

## Nearest source opportunities

| Taxon | Best 6×6 joint climate overlap | Distance | 8×8 overlap | Exact prospective gate |
|---|---|---:|---:|---|
| *Quercus robur* | Northeast France – Southwest Germany: **0.441** | **255 km** | 0.413 | **Failed**; 350-km minimum distance |
| *Pinus sylvestris* | Northeast Germany – Northwest Poland: **0.350** | **233 km** | 0.250 | **Failed**; 350-km minimum distance |

Among comparisons separated by at least 350 km, the highest 6×6 climate overlap was only **0.199** for *Q. robur* (7 qualifying-distance pairs) and **0.054** for *P. sylvestris* (9 qualifying-distance pairs); none reaches the frozen **0.28** overlap threshold. The minimum 8×8 overlap threshold was **0.20** and minimum symmetric nearest-common-climate coverage **0.35**. Eligibility is *not* redefined now to rescue any pair.

As a noninferential exploratory description, across the fixed ten dependent pairs per species, Spearman's distance–6×6-overlap association was **−0.800** for *Quercus* and **−0.244** for *Pinus*. Pairwise distances are correlated because each region participates in several pairs; these are not independent n=10 statistical samples, and no p-values/ecological global effect are claimed.

## Interpretation and limits

The result directly identifies a **geographic separation versus climate common-support bottleneck in this finite, preselected source panel**. A geographically distant comparison might look maximally informative about transfer or adaptation, but have too little shared environment for a non-extrapolative test of response divergence. The original DE–SE *Quercus* pilot had 0.10 overlap; the expanded climate-only census found no compliant alternative under this deliberately demanding fixed design.

This is **not** evidence that plants' physiological constraints actually alternate across regions, or that such comparisons never exist elsewhere. The preselected 10 rectangles were not a random sample of the world's land, include administrative-border/coast uncertainty and have not been validated as species-accessible `M`; their BIO1 and BIO12 historical averages are coarse substitutes for actual stress exposures. Local populations, plantation status, range-edge habitat and detection effort were not examined. No post-outcome source-window retuning, distance reduction or selected-pair promotion is justified as confirmation.

## Source reproducibility

- Frozen design + outcome-blind script: `configs/geographic_turnover_common_support_v1.json`, `experiments/geographic_turnover_common_support_v1.py`
- Exact output: `results/geographic_turnover_common_support_v1/source_selection.json`
- All **571** climate-source cells: `results/geographic_turnover_common_support_v1/all_candidate_climate_cells.csv`
- Raw source CSV SHA-256: `4b7d5bb9a23e3ef6c4c74448698409be4174d9199765d3ba7bd4eb4f9eddb633`

**Next separate independent design:** prioritize source panels combining substantial environmental common support with geographic separation by climate-first analog discovery across a broader, independently justified native and species-accessible geographic atlas. Selection must remain occurrence-blind; when possible use systematic plot-census or demographic data with known effort to estimate actual performance, not GBIF counts. Keep the current 0/20 result intact.
