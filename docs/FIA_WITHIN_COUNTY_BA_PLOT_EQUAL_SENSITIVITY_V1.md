# FIA within-county BALIVE information: plot-chain-equal sensitivity (2026-11-17)

**Stage:** separately frozen, postoutcome *sensitivity* to tree-count weighting. It is not a new biological sample, a prospective test, a survival analysis or a causal estimate of inter-tree competition. The original SDMR Product A and M5 endpoints remain untouched; Product B is blocked.

## Why this check is needed

The [source-frozen county-decomposition audit](FIA_WITHIN_VS_BETWEEN_COUNTY_BA_V1.md) found a positive out-of-county predictive increment from within-county deviations of stand basal area for five of five fixed tree taxa, even after including county-mean stand BA. The original fit treated **counties equally, states equally, but individual selected tree measurements within a county still received equal relative weight**. A plot condition with many trees could therefore dominate the within-county gradient. Because BALIVE is a plot/condition-level exposure, treating each tree as a fully independent neighborhood replicate is unwarranted.

This sensitivity holds the same 170,994 linked live→live growth observations, 88,145 prior-visit source rows, five species, five fixed FIPS-hash county folds, and source-only training climate cells. It changes exactly **training and evaluation weighting**, not outcomes or inclusion.

For a selected tree row i in plot chain p, county c and state s, fit weight is proportional to

\[
w_i = \frac{1}{2\,N_{\mathrm{county},s}\,N_{\mathrm{plot},c}\,N_{\mathrm{tree},p}}.
\]

Thus each state totals 50% of fitted weight, every county within a state has equal weight, every *distinct plot chain* within a county has equal weight, and rows of one plot share its weight. On held-out counties, first average squared errors within a plot chain, then equally over plot chains, counties and states; finally take the square root. The county means of BA are still computed from distinct sampled plot chains and the exact, already selected survivor cohort.

The five candidate families are reduced to four for this sensitivity: nuisance variables without BA; original single BA; county mean BA only; county mean + within-county deviation BA. Both mean and within-county BA coefficients are learned only on heldout-county-disjoint training rows. Target-climate cells are precomputed from **training source-only rows**, never from test response.

## Exploratory independent calculation (fixed original input, before GitHub replay)

| Taxon | Within-county BA increment after county mean (equal plots) | 95% postfit county-resampled interval |
|---|---:|---:|
| *Pinus strobus* | **+2.503%** | +1.356 to +3.594% |
| *Acer rubrum* | **+1.095%** | +0.409 to +1.830% |
| *Quercus alba* | **+0.823%** | +0.364 to +1.208% |
| *Quercus rubra* | **+1.521%** | +0.803 to +2.223% |
| *Quercus velutina* | **+0.825%** | +0.121 to +1.546% |

All five have positive increment even under plot-equal scoring. Original 999 county-bootstrap draws resample *precomputed heldout scores* within VA and WI, not full fitted models; bounds are descriptive and can be optimistic about spatial/temporal dependence. Species were previously selected, and postresponse county-mean predictors are **transductive to a conditional-survivor cohort**. No local BA coefficient is randomized independently from site fertility, stand composition, soil or forest management.

**Interpretation:** the positive within-county BA predictor-information signal is not solely a byproduct of recording many trees in a few dense sampled plots. It is still *observational*, contains potential site/forest-history confounding and does not show that competition is causally limiting growth or that climatic niche parameters are stationary.

## Frozen archival execution

\`experiments/fia_plot_equal_BA_sensitivity_v1.py\` imports the source-integrity checker from the first archival replay and verifies the exact prior response/source SHA-256 values. A focused synthetic test proves that a 10-tree plot and a 1-tree plot each have the same total weight within a county; heldout county error averages plots before counties. The one-shot workflow retrieves **only** the original first-open derived CSVs from [run 43886130089](https://github.com/zuizui0223/sdmr/actions/runs/43886130089). It does not redownload raw FIA source or open new growth/survival outcomes. It preserves all five taxa and every scored county, including adverse results, with a complete source/run receipt.

Run manually from exact archived CSVs:

\`\`\`bash
python -m pytest -q tests/test_fia_plot_equal_BA_sensitivity_v1.py
python experiments/fia_plot_equal_BA_sensitivity_v1.py \
  --source-dir build/frozen_first_open_derived \
  --out-dir build/fia_BA_plot_equal_v1
\`\`\`
