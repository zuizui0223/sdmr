# SDMR fresh empirical feature stage — terminal v2 result

Status: **terminal unavailable under the frozen 50-taxon / 46-predictor contract**.

The first environmental-value extraction opened only model-pool occurrences and frozen 300-km backgrounds. Answer-check occurrences remained sealed and no model was fitted.

## What failed first

The raw 46-layer complete-case gate failed 0/50 because several CHELSA variables use source encodings that collide with generic raster NODATA handling. A diagnostic-only audit established deterministic structural states:

- `fcf=0` where the coldest month is above 0 °C;
- `swe=0` where snow-cover days are 0;
- `fgd=1, lgd=365` where growing-season length is 365 days;
- `gdgfgd5=1` where `ngd5=365`;
- `gdgfgd10=1` where `ngd10=365`.

These six source-decoding rules corrected 725,654 cells without changing taxa, predictors, thresholds, or true missing cells.

## Result after source decoding

**37/50 taxa passed. 13/50 remained below the frozen completeness gate.**

The post-decoding coverage audit showed that all 13 failing taxa have individual blockers only in the four frozen SoilGrids topsoil layers:

- `sg_phh2o_0_5`
- `sg_clay_0_5`
- `sg_soc_0_5`
- `sg_nitrogen_0_5`

No CHELSA predictor is an individual blocker. Omitting any one predictor diagnostically would rescue **0/13 taxa**, showing that the problem is the shared soil-substrate support mask rather than one expendable predictor.

## Integrity decision

The frozen contract explicitly forbids taxon replacement, predictor deletion, and threshold relaxation after values are opened. Those operations were not performed.

Therefore this v2 cohort is closed as **terminal unavailable**. The correct continuation is a new independent fresh cohort whose taxon eligibility includes the frozen SoilGrids support mask *before* taxon selection and before any model fitting. All 50 v2 taxa must be excluded from that new cohort.

Answer-check access: **false**. Model fitting: **false**.
