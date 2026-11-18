# New climate-only paired-source preflight: geographic driver turnover

**Status**: independent, outcome-blind environmental sampling design. This is NOT Product A/B recovery, a new M5 validation, an inference about niche evolution, or evidence that a plant is temperature/water limited.

The previous Germany–Sweden *Quercus robur* pilot had only 10% binned joint climate overlap and a nontransferable geographic holdout full model. A new observational test must not claim evolutionary shifts when measured climate environments do not overlap.

## Fixed candidate census (before occurrence outcomes)

The config `configs/geographic_turnover_common_support_v1.json` prospectively declares five **country-native compatible** rectangles each for *Quercus robur* and *Pinus sylvestris* (10 climate windows, 20 within-species unordered pairs). "Native-country compatible" does not establish that a specimen is a naturally recruited individual, that a taxon is uniformly native in each rectangle, or that these windows are its accessible M. Rectangles may intersect shores and nearby administrative borders; nominal country labels are NOT polygon clips. Direct physiological or demographic evidence would still be required for fitness-based inference.

The tool does NOT query GBIF, inspect species record density, fit occupancy models, or consume any earlier source-outcome variable. It samples CHELSA v2.1 BIO1/BIO12 from the entire fixed 25-km EPSG:6933 equal-area grid for every rectangle using the existing SDMR raster extractor. Each climate window records its success/failure and provenance; no rectangle is moved or dropped because its climate similarity is low.

## Pairwise selection rule

Within each species, keep every candidate pair and its failure reasons. Pair qualifies for **source follow-up**, not ecological inference, only when:

- both rectangles have >=35 two-axis climate-complete 25km cells, with >=4 exogenous geographic blocks;
- their centre-to-centre geographic separation is >=350 km;
- symmetric equal-area *binned joint climate overlap* >=0.28 in a pooled 6×6 climate quantile grid and >=0.20 in the separately reported 8×8 sensitivity grid;
- >=35% of cells in **each** region have another region's climate cell within standardized bivariate Euclidean distance <=0.5 using pooled climate SDs (symmetric nearest-support gate).

Within each species, identify the eligible pair with the largest 6×6 overlap, then 8×8 overlap, then nearest-cell coverage; break remaining ties lexicographically. No eligible pair => `selected_pair: null`. The selected pair remains a **climate-only source-opportunity candidate** and may still fail due to inhomogeneous sampling, plantations, accessible-area M, or lack of independent observation effort.

The thresholds above are exploratory, frozen before *this* environmental extraction, and NOT biological constants. They cannot be retuned after outcomes to rescue eligibility. Histograms will change if a new candidate panel is specified; never claim these are measured niche widths or ecological responses.

## Commands

```bash
python -m pytest -q tests/test_geographic_turnover_common_support_v1.py
python experiments/geographic_turnover_common_support_v1.py \
  --config configs/geographic_turnover_common_support_v1.json \
  --output-dir artifacts/geographic_common_support_v1
```

`source_selection.json` has all pair candidates, every exclusion, and one pair (or null) per taxon. `all_candidate_climate_cells.csv` retains equal-area climate cells from the initial candidate rectangles for auditing. Workflows run only when the new source files change or by manual dispatch. It is intentionally NOT automatic bulk GBIF acquisition.

**Next ecological gate**: only after establishing environmental common support, independently source native/wild species records and systematic observer effort. Use a newly declared dated sample frame or bulk GBIF archive and compare a globally invariant response to region-varying responses with spatially held-out scores and model adequacy. Do not choose region pairs by the focal species response or by whether a process-switch p-value is significant.
