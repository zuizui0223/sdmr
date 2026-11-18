# Source-verified first measured tree outcomes: FIA RI / VA / WI

**Status:** exploratory, outcome-opened only for a source-eligible, fixed 13-taxon panel. **Not** an estimate of causal climate constraint, niche evolution, a physiological response, a statewide mortality rate or a climate-driven range shift. The earlier closed Product A / blocked Product B / M5 studies are unchanged.

## Central question and design

The ultimate research question is whether regional environmental stress contributions can change while one species retains a shared physiological response. A convincing test must observe actual growth or survival, not just GBIF record occurrence density. This first FIA analysis tests the **repeated-individual-data prerequisite** and produces a bounded, real demographic pattern. Climate response modelling is **not attempted in this gate**.

The three geographically predeclared states are Rhode Island (RI), Virginia (VA), and Wisconsin (WI). The read-only source gate, completed before any tree diameter/status outcome was accessed, counted forward-inventory links via current `PREV_TRE_CN`→prior `CN` on identical `SPCD`. Source archive eligibility was RI 10,112, VA 441,063, WI 640,345 links. Its independent WI successor used a larger technical archive cap, not a changed taxon or outcome gate. Taxa with ≥30 matched links in **every** state yield a frozen 13-code universe:

`68, 129, 261, 316, 318, 371, 531, 541, 743, 762, 802, 833, 837`.

Names come from the independent FIA `REF_SPECIES` table, not guessed from species codes. Study contract: `configs/geographic_tree_demography_first_response_v1.json`. The exact three source ZIP SHA-256 values are checked **again before response opening**, alongside a fixed source-row total. No species, state, measurement interval or outcome subset can be replaced after observing a growth result.

## Observed responses and exact interpretation

Each actual linked tree uses an earlier `TREE` row and one later `TREE` row with year strictly increasing. Eligibility requires same USDA species code and inventory interval 1–20 years. The public `TREE.STATUSCD` is interpreted as current live (`1`), dead (`2`), not currently tallied (`0`), or human removed (`3`), with missing/other states retained separately. `PREV_TRE_CN` link presence is not treated as survival, nor is an absent current link treated as death.

1. **Observed linked current state:** among *prior-live* linked trees, report counts with current live, current dead, current removed, not tallied, missing/other. The count of current dead divided by the sum of linked current dead and linked current live is a **linked-pair fraction**, **not** annual mortality risk or population mortality; current removals are not labelled natural deaths.
2. **Measured diameter response:** among confirmed live→live linked pairs with diameter `DIA` reported both times and initial `DIA ≥1 inch`, calculate `log(DIA_current / DIA_prior) / (INVYR_current − INVYR_prior)`, in log diameter units per year, and absolute diameter change in inches/year. Negative growth remains negative; measurement artifacts are not silently erased. The diameter height code `DIAHTCD` is recorded for comparability but the primary summary still includes pairs without matched height code, requiring later sensitivity.
3. **Size-composition control:** in each of 13 species, four predeclared initial-diameter bands (`1–<5`, `5–<10`, `10–<20`, `20+` inches). Direct standardization combines only bands with at least 30 live→live pairs in *each* of all three states, using pooled observed-pair band frequencies. A band failing any state is **excluded from the comparison**, not imputed. State mean estimates are descriptive, not independent observation-level inference.

No plot-level design weights, FIA sampling stratification, elapsed survey date beyond inventory-year integer, plot clustering, exact field coordinates, tree recruitment, interval-censored hazard model, environmental covariates, or physiologically anchored fitness curves are used. The results **cannot** be attributed to temperature versus moisture or interpreted as local adaptation. Species × state differences may reflect diameter distribution, management, measurement protocols, demography, nonrandom missingness, and other context.

## Exact provenance and reproducibility

Input receipts in `evidence/geographic_tree_demography_source_gate_v1/`:

- `fia_ri_va_wi_identity_linkages.json` — RI/VA/WI first, pre-response eligibility (WI technical cap stop retained).
- `fia_wi_size_cap_successor_v2.json` — WI 159.61-MB ZIP independently validated at expanded technical cap, same RI/VA sources, 13 eligible taxa in all states.
- `fia_official_species_crosswalk.json` — 22 prior-eligible USDA species codes matched to `REF_SPECIES` (includes the 13-state universe).

To rerun with internet access to USDA DataMart:

```bash
python -m pytest -q tests/test_geographic_tree_demography_first_response_v1.py
python experiments/geographic_tree_demography_first_response_v1.py \
  --config configs/geographic_tree_demography_first_response_v1.json \
  --source evidence/geographic_tree_demography_source_gate_v1/fia_wi_size_cap_successor_v2.json \
  --crosswalk evidence/geographic_tree_demography_source_gate_v1/fia_official_species_crosswalk.json \
  --output artifacts/fia_three_state_first_measured_response_v1.json
```

The GitHub Actions `geographic-tree-demography-first-response-v1` job runs unit checks, then the full three-state source SHA and row-denominator validation before archiving **only aggregate outcomes** as a short JSON (no individual tree rows).

## Next scientific decision

Only after three-state measured-response data are available, assess tree size, inventory-year intervals, repeated plots, and statuses as potential confounders; consider FIA public plot coordinate limitations and management/detection. An independent follow-up must prospectively specify plot/forest-condition-level environmental exposure and density-independent tree-performance estimands before fitting stationary versus region-dependent response curves. Use no data-dependent taxon replacement or threshold relaxation to obtain a favorable result.
