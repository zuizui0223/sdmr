# FIA habitat and competition: archived, no-refit ecological comparison

**Status: source-verified retrospective synthesis / hypothesis-generating only.** This is derived entirely from the first opened, exact nine-archive FIA measurement/plot/condition experiment, **not** a biological validation replicate, causal effect estimate or physiological niche inference.

## Exact evidence

- Source: [FIA stand structure extension GitHub Actions 39458699203](https://github.com/zuizui0223/sdmr/actions/runs/39458699203), archived `evidence/fia_habitat_structure_extension_v1/aggregate.json` (514,436 bytes), SHA-256 **`2534ee724e177c15a9399b6d538f0cbdb765bfe018d21cc73ee2a9575917bb62`**.
- Three states (RI, VA, WI), fixed thirteen tree species, identical previously verified TREE, PLOT and COND source content; same 13-species trees, intervals measured from PLOT date, natural forest condition, stem diameter and condition stand age. All analysis is conditional on live→live remeasurement.
- `BALIVE`: source basal-area density (ft²/acre) in three bands `[0,60)`, `[60,120)`, `120+`. `PHYSCLCD`: FIA physiographic dry (`11–19`), mesic (`21–29`) or hydric (`31–39`) source site types. These are **not measured annual water balance, competitive effect or physiological drought stress**.
- Source result rederived independently from archived per-species × region × size × age × density × physiography bin counts and mean increments, retaining the original `>=10` paired-survivor observations in *all* three states per matched regional bin.

## Primary observed descriptive contrasts

| Comparison | Species with common strata | WI growth larger than RI | WI-higher matched strata |
|---|---:|---:|---:|
| Same species × tree size × stand age × stand basal-area density | **12/13** | **10/12** | **63/76** |
| Same species × tree size × stand age × physiographic site class | **13/13** | **11/13** | **55/64** |

The size/age/density-matched effect is positive in most, not all, taxa. Its exceptions are **Tsuga canadensis** and **Fagus grandifolia**, where WI is lower than RI in this sampling cohort. **Populus grandidentata** lacks a shared density class meeting the fixed minimum and stays unestimable in that arm. Matched classes are correlated observations, **not** 76 independent population experiments.

### Robustness to stricter bin support (retrospective, not a new selection rule)

| Minimum live→live pairs per matched bin *in each state* | Density: WI higher/estimable | Physiography: WI higher/estimable |
|---|---:|---:|
| 10 (original frozen minimum) | 10/12 | 11/13 |
| 20 | 7/9 | 8/10 |
| 30 | 6/6 | 6/7 |
| 50 | 5/5 | 6/6 |
| 100 | 4/4 | 5/5 |

Across all thresholds, weighting the matched bins by pooled tree observations, equally by stratum, or by minimum state count gives the **same within-species sign tallies**. This is directional robustness **among the shrinking eligible subsets**, not evidence that the pattern generalizes to all trees or species. No confidence interval, species-level independence or significance is claimed.

## New positive gradient: the stand-density association is directionally consistent

This separate, fully within-species-and-state contrast compares **prior stand basal area** bands, while holding **tree initial diameter band, prior stand-age band and dry/mesic/hydric physiographic class** fixed. Every source class has >=10 observed live-to-live tree intervals. The unit is a *species × state* descriptive contrast; multiple tree/plot strata are **dependent**. Higher-minus-lower contrasts refer to annualized log stem-diameter growth.

| Higher vs lower stand density (ft²/acre) | Species×state with greater growth at lower density | Individual matched classes with greater growth at lower density |
|---|---:|---:|
| 60–<120 vs 0–<60 | **27/27** | **225/244** |
| ≥120 vs 60–<120 | **33/33** | **337/385** |
| ≥120 vs 0–<60 | **27/27** | **196/205** |

Among 205 exact species×state×size×age×physiography combinations with adequate support in **all three** density categories, **184/205** exhibit strict decreases in growth with increasing stand density. Not every individual stratum is monotonic; none of these are independent replicated experiments.

### Post-result support tightening

| Required tree pairs in *each* matched density group | Low→middle: lower density higher growth | Middle→high: lower density higher growth | Strictly decreasing, all three |
|---|---:|---:|---:|
| 10 | 27/27 species×state | 33/33 | 184/205 strata |
| 20 | 22/22 | 30/30 | 130/140 |
| 30 | 22/22 | 30/30 | 112/118 |
| 50 | 19/19 | 29/29 | 81/83 |
| 100 | 15/15 | 25/25 | 43/43 |

These are **strong, source-backed associations** between tree growth and basal-area crowding within the observed survivor cohort. They are compatible with competition restricting growth, but they are **not a causal competition experiment**: basal area may reflect stand/site quality, species mixture, prior mortality/harvest and sampling-selection processes, and it is not necessarily independent of focal-tree size. The stricter thresholds above were investigated **after outcomes were available**.

Contrasting this strong density association with the mixed dry-versus-mesic source effect below is more informative than claiming every climate or site factor has a universal response: in this cohort, the local forest-structure gradient is consistently signed, while physiographic water-site contrasts are heterogeneous. This does not rank the causal strength of biotic competition against climatic drought.

## Moisture-related site context: no universal advantage

A separate comparison holds **species + state + initial stem diameter + stand age + basal area** equal, and compares *mesic* versus *xeric* site-condition groups with >=10 surviving observations in both source classes. The dry/mesic contrast is **not a climatic drought experiment**.

- RI: **0** estimable species-by-state comparisons. Do not substitute zero effects.
- VA: **11** species, **6** with mesic growth above xeric.
- WI: **10** species, **6** with mesic growth above xeric.
- Across all eligible **21** species-by-state comparisons, mesic growth is higher in **12**, lower in **9**. Among the **9 species** comparable in both VA and WI, **4** have **opposite mesic–xeric difference signs** in the two states.

These are potentially meaningful context-dependent associations, not proof of different local adaptive optima or a physiographic effect. The mixed sign is an observed counterexample to **descriptive universal mesic advantage in this panel**, not a population-wide falsification.

## Ecological meaning and unresolved explanations

A geographical growth contrast can remain within common tree-size, stand-age, and stand-density bands without implying genetic niche evolution. Likewise, physiographic source categories have mixed associations within species, showing that **a single dry/mesic source label does not explain growth uniformly** across the candidate forest communities. Both observations motivate the more substantive test: **can a stationary, shared species-specific growth response to temperature and water availability explain region-specific growth and site effects?**

**Not controlled:** FIA sample design weights, plot and tree dependence, tree survivorship/observation selection, community composition, management, plot condition transitions, measurement-error, climate during the actual two-census interval, spatially perturbed public plot coordinates and true physiological fitness. Conditioning on surviving trees can itself produce an apparent growth advantage. Because no exact environmental exposure or direct physiological measurements enter these results, do not label the differences as a temperature/moisture constraint switch. The closed SDMR Product A, M5 and blocked Product B remain unchanged.

## Reproducibility

```bash
python -m pytest -q tests/test_fia_habitat_archived_synthesis_v1.py
python experiments/fia_habitat_archived_synthesis_v1.py \
  --source evidence/fia_habitat_structure_extension_v1/aggregate.json \
  --output results/fia_habitat_archived_synthesis_v1.json
```

The archive-only CI reruns tests and checks exact output **without contacting the mutable USDA DataMart source**. The raw source-dependent workflow should be manual-only when the archived outcome is frozen. Biological promotion would require an independent plot-clustered, survey-design-aware temporal climate exposure model, with reliable common environmental support and independently sampled holdouts.
