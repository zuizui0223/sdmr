# FIA forest competition and physiographic water-site extension — source-exact design

**Status:** exploratory new-source successor, not a separate independent biological replication. No observed water limitation or physiological species differences may be claimed before source and common-stratum gates succeed.

## Next question

The growth of 12/13 species was larger in WI than RI even after same-species size × stand-age matching and measured-date correction. Two alternative ecological explanations can be tested using independent source-defined condition measurements:

1. **Stand-density / competition composition:** Does WI still show greater growth after also matching *prior live-tree basal area* (FIA `COND.BALIVE`, ft²/acre) in predetermined bands [0,60), [60,120), ≥120?
2. **Water-site physiography:** Does the WI–RI direction persist after matching the field-recorded *physiographic moisture setting* (`COND.PHYSCLCD` groups: xeric 11–19, mesic 21–29, hydric 31–39)? Independently, do mesic and xeric source-condition sites differ in repeated-survivor increment within the same species, state, initial diameter, stand age and basal-area band?

These are **associational proxies**, not actual measurements of soil water, drought stress or competitive interactions. Physiographic classes reflect topographic/soil-moisture setting; class and temporal exposure should not be equated.

## Data controls

- Same 13 tree species, same three RI/VA/WI states, same tree two-census links, PLOT actual measurement intervals and natural forest condition eligibility.
- Every one of nine source ZIPs must reproduce the SHA-256 recorded in independently archived `fia_plot_condition_source_v1.json` and `fia_new_source_stand_context_v1/aggregate.json`. A single mismatch prevents new claims and forbids selective state changes.
- Primary size × stand age × basal area direct standardization requires **at least 10** measured surviving individuals in *every state* of the common cell, with within-species pooled counts as weights. Forest physiography standardization is separately reported with the same eligibility; cells without common environments return `null`.
- Mesic vs xeric contrasts are computed **within each state and species**, matching initial diameter, prior stand age and prior basal-area band. Only pairs with ≥10 each in both categories enter; hydric is not classified as a dry/wet monotonic effect.
- State species pair counts and site-class counts are descriptive, dependent tree/plot observations; no p-values, design-based weights or survival selection corrections are supplied.

Reference official FIA [PHYSCLCD categories](https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/cselected) and [DataMart](https://research.fs.usda.gov/products/dataandtools/fia-datamart).

## Reproduce

```bash
python -m pytest -q tests/test_fia_basaldensity_moisture_context_v1.py
python experiments/fia_basaldensity_moisture_context_v1.py \
 --config configs/fia_habitat_structure_extension_v1.json \
 --plot-cond evidence/fia_plot_condition_source_v1.json \
 --first-tree evidence/fia_new_source_stand_context_v1/aggregate.json \
 --output artifacts/fia_habitat_structure_extension_v1.json
```

If successful, the result is new **descriptive within-species environmental context**, not proof of niche evolution or that thermal and water stress are causal limitations. Frozen Product A, M5 and blocked Product B are unaffected.
