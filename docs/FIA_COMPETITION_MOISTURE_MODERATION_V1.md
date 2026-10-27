# Does physiographic moisture context modify forest crowding–growth associations?

**Status: source-verified, post-outcome exploratory FIA synthesis — NOT a test of physiological niche evolution or causal competition.** Independent programme within SDMR's *draft* PR #284; its old Product A, blocked Product B and primary M5 endpoints are unchanged.

## Research question and novel distinction

A stable negative growth–stand-density association may persist across regions even if the **additional penalty associated with crowding depends on local moisture setting**. We ask whether a mesic setting *consistently mitigates* a high-density growth disadvantage compared with xeric conditions, after holding tree species, state, initial diameter class, and stand-age class constant. The null need not be zero crowding; the competing predictions are *a uniformly signed moisture × density interaction* versus *regionally heterogeneous moderation*. The data permit a descriptive comparison, **not a causal test**, because neither stand basal area nor site class was randomized or equivalent to measured soil moisture.

## Exact source and frozen units

- Input: `evidence/fia_habitat_structure_extension_v1/aggregate.json` from successful [GitHub Actions 39458699203](https://github.com/zuizui0223/sdmr/actions/runs/39458699203), **514,436 bytes**; SHA-256 `2534ee724e177c15a9399b6d538f0cbdb765bfe018d21cc73ee2a9575917bb62`.
- Existing archive-specific original summaries are reverified before any new comparisons. Input stems and stand conditions originated from nine source-identity-verified FIA TREE/PLOT/COND ZIPs; **no new occurrence/outcome data are acquired**. There are 13 fixed tree species and fixed RI, VA, WI states.
- Response: mean annualized log stem diameter increment **conditional on live→live remeasurement**, in source-provided size × age × density × physiographic bins. See `docs/FIA_STAND_CONTEXT_SYNTHESIS_V1.md` for measurement-year and stand-condition details.
- Densities (`BALIVE`, ft²/acre): low `[0,60)`, middle `[60,120)`, high `>=120`. FIA condition `PHYSCLCD` classified into **xeric** `11–19` versus **mesic** `21–29`. `PHYSCLCD` is a categorical physiography indicator, not a soil-water measurement or climate anomaly. Hydric sites are deliberately outside this two-context interaction.
- Primary eligibility requires at least **10 survivor–survivor tree observations in *each of the four* density × site cells** within the *same* species, state, tree diameter class and stand age class. Missing any one cell yields *unavailable*, never a fabricated zero. Prespecified density contrasts are low→middle, middle→high, and low→high. Retrospective sensitivity uses minimum 20, 30, 50 and 100 in **each** four-way cell; it cannot promote positive evidence.

Let `g_{d,m}` denote source mean observed log growth for density `d` and xeric/mesic site `m`, within a fixed species × state × size × age stratum. Define

\[
\Delta_{d,m}=g_{\mathrm{high},m}-g_{\mathrm{low},m},\qquad
I=\Delta_{d,\mathrm{mesic}}-\Delta_{d,\mathrm{xeric}}.
\]

A negative density increment (`Δ < 0`) is lower observed growth in more densely stocked stands. A **positive** `I` means this difference is *less negative* in mesic than xeric sites; a **negative** `I` means the reverse. This difference-in-differences is an **associational contrast**, not a causal `water × competition` effect. The `>=10` rule applies to every exact four-cell set. Species×state summaries weight independent *strata* by their minimum cell count to discourage a single very large mesic cell from dominating; exact raw stratum contrasts are also archived. No p-value is computed.

## Results from the original full fixed panel

| Higher-density vs lower-density | Four-cell size×age contrasts | Both xeric and mesic slopes negative | Mesic crowding penalty less severe | Xeric penalty less severe | Species×state groups |
|---|---:|---:|---:|---:|---:|
| Middle vs low | 54 | **48** | 26 | 28 | 16 |
| High vs middle | 94 | **79** | 43 | 51 | 19 |
| High vs low | 37 | **36** | 21 | 16 | 13 |

No Rhode Island stratum had enough source records in all four cells; **RI is unestimable, not zero** in this interaction analysis. The four-cell contrasts are available in VA and WI, not independent tree-level trials. As stand density rises, lower growth is common in **both** physiographic contexts; however, **which moisture context experiences the stronger density association has no uniform direction**.

### Between-state comparison on the *same size and age stratum*

For a more stringent descriptive comparison, require exactly the *same species × size × stand-age stratum* to satisfy all four source cells independently in **both VA and WI** (eight source cells, at least 10 records per cell). Reversals refer to the **mesic-versus-xeric moderation `I` sign**, not to an overall density penalty sign.

| Density contrast | 8-cell VA–WI matched strata | Moderation sign opposite | Opposite with \|I\| ≥0.002 log units/y in *both* states |
|---|---:|---:|---:|
| Middle vs low | 12 | **9** | **5/6** eligible |
| High vs middle | 27 | **11** | **2/4** eligible |
| High vs low | 8 | **4** | **1/2** eligible |

The 0.001/0.002 sensitivity thresholds are **post-outcome descriptive filters**, not a significance definition. Several raw signs are close to zero, and clusters are dependent. In particular, do not rephrase 9/12 as a probability or as proof of true regional competition changes. It is evidence of **nonuniform observed moderation under strict source matching**.

### Sample-size sensitivity

For high vs low density, the number of four-cell size/age strata showing *lower growth at high density in both xeric and mesic sites* is **36/37** (n≥10 in every cell), **20/20** (n≥20), **13/13** (n≥30), **8/8** (n≥50), and **2/2** (n≥100). These are shrinking matched support sets, not biological sampling frequencies. The sign of the moisture moderation itself remains mixed across support thresholds. Exact denominators, individual source-cell counts, and the full nonzero sensitivity set are in the JSON result.

## Interpretive ceiling and next source link

This bounded result supports the statement that **the source stand-density growth gradient is broadly shared across xeric and mesic sites, while its relative strength is geographically and taxonomically variable**. It neither estimates true soil moisture limitation nor identifies physiological niche evolution. Plot/tree dependence, non-random forest stocking, management, unmeasured site quality, initial condition changes, the fact that only survivors enter growth, and non-uniform FIA design weights are unresolved. `PHYSCLCD` may reflect vegetation/topography rather than a continuous moisture stress variable.

The archived aggregate contains **no plot identifiers, public plot coordinates or tree-level residual variance**. Therefore **a genuine climate × crowding interaction cannot be estimated from this aggregate**. It requires a separate, versioned plot-level cohort, plot-design/cluster adjustment and a defensible climate linkage. Public FIA plot coordinates are intentionally fuzzed (usually 0.5 mile, sometimes 1 mile) and up to 25% of private forest plots may have within-county location swaps. The [official FIA Spatial Data Services documentation](https://research.fs.usda.gov/programs/fia/sds) explicitly warns that true plot locations are confidential and advises coarse-resolution overlays; point extraction from 4-km PRISM at public coordinates is not an exact plot-level exposure. Prefer an independent **county or ecoregion × measurement-year climate source**, validate common environmental support, predeclare sensitivity to spatial displacement and county swapping, and keep any new current DataMart ZIPs separate from the immutable 2026-10-19 source.

## Reproduce without source re-download

```bash
python -m pytest -q tests/test_fia_competition_moisture_interaction_v1.py
python experiments/fia_competition_moisture_interaction_v1.py \
  --source evidence/fia_habitat_structure_extension_v1/aggregate.json \
  --output results/fia_density_physiography_moderation_v1.json
```

The archive-only Actions job installs pytest, rederives the result and checks deterministic JSON content. Original FIA DataMart replay stays **manual-only** because historical ZIP bytes can drift; no prior scientific source contract is overwritten.
