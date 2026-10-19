# What first real geographic-driver contrast actually shows (retrospective source audit)

**Status:** exploratory, non-confirmatory, **no niche or causal process claim**. This is an additional *post-source* audit of the existing pre-fixed `Quercus robur` DE and SE windows from PR #284. The effort exponent check was specified **after** the 2026-10-19 source results were inspected; it is a sensitivity diagnosis, **not** a prospective held-out result. The closed Product A, blocked Product B and M5 denominators remain untouched.

## Source exactness

GitHub Actions source run [39217679310](https://github.com/zuizui0223/sdmr/actions/runs/39217679310) produced artifact 12171000234. The artifact's `available_climate_cells.csv` and `source_receipt.json` have been included unchanged at `evidence/geographic_turnover_native_source_v1/` so that the study remains inspectable after Actions artifact expiry.

- Cell CSV SHA-256 `42747f07c030a09134a08703bf20e60a73fe661468c2047ccc1c1fd7628b85aa`.
- Source receipt SHA-256 `c0619957ff3e30d65810cec716067891973e6d991fb68ca6cf4b7b7bce82a8e5`.
- 187 finite CHELSA 1981–2010 BIO1/BIO12 cells across four original rectangles; fixed full-denominator source statuses remain intact. *P. sylvestris* FI has incomplete search source due to the declared 4,000 diagnostic cap and **is not silently dropped from the source receipt**.
- *Q. robur* DE/SE is the only eligible two-window source-complete pair in this pilot; choosing to analyze it after the source check is explicitly exploratory.
- Sentinel effort is the sum of records of three *other* plants (*Betula pendula, Salix caprea, Sorbus aucuparia*) within each grid cell, **not externally calibrated collection/detection effort**. No full GBIF occurrence snapshots or independent demography are implied by the aggregated cell archive.

## Data versus hypotheses

| Indicator | Central Germany | Southern Sweden |
|---|---:|---:|
| Fixed 25-km equal-area climate cells | 30 | 24 |
| Climate cells with ≥1 GBIF *Q. robur* record | 28 (93.3%) | 24 (100%) |
| Quality-controlled focal records allocated inside those cells | 264 | 3,310 |
| Independent *other-plant* sentinel record counts | 1,146 | 2,929 |
| Effective number of focal record cells, Kish/Simpson | 9.33 | 11.30 |
| Temperature range, sampled BIO1 (°C) | 6.65–9.45 | 5.85–7.05 |
| Annual precipitation, sampled BIO12 (mm-equivalent) | 587.5–1,271.4 | 690.5–1,215.3 |

**Environmental support**: with six-by-six pooled empirical-quantile temperature/precipitation bins and equal weights per climate cell, the overlap coefficient `sum_bin min(p_DE_bin, p_SE_bin)` is **0.10**. This is a coarse diagnostic that depends on bin choice, not a formal measure of fundamental niche overlap. The temperature-range intersection is just 6.65–7.05 °C (0.40 °C). Two rectangles with little shared environment cannot strongly identify physiological niche evolution from observational differences.

**Nearly saturated grid**: almost all climate cells have at least one occurrence record; this means the presence-only grid offers little observed occupied-versus-unsampled spatial contrast. Different *counts* are not independent abundance estimates because taxon-dependent collector preferences and effort remain unvalidated.

## Effort assumption changes the answer with all occurrence and climate data held fixed

A conditional multinomial record-intensity diagnostic compares a quadratic BIO1–BIO12 model to full temperature-information and full moisture-information knockouts (the interaction is deleted in both), using two nonrandom geographic folds. It holds the fitted-model family, response counts, window geometry, regularization and climate fixed, but changes only the *assumed* `effort = sentinel_record_count**alpha`. Three uncalibrated power choices are retrospectively inspected (`alpha=0, 0.5, 1`), rather than selecting one post hoc as the true effort process.

Positive `T` or `W` knockout gain means the full model scores better than the corresponding knockout on held-out **record intensity**; it is **not** evidence of a causal limiting process. Values are per record in natural-log-score units. For a model to carry even exploratory ecological information, the full model must also beat the `effort`-only geographic-fold baseline.

| Effort exponent | Germany: full−effort | Germany: T gain / W gain | Sweden: full−effort | Sweden: T gain / W gain | **Naive rank reversal**? |
|---|---:|---|---:|---|---|
| 0 (uniform) | −1.892 | −1.691 / −1.212 | **+0.122** | +0.042 / +0.266 | No (both W) |
| 0.5 | −1.185 | −0.919 / −0.888 | −0.146 | +0.016 / −0.093 | **Yes (DE W, SE T)** |
| 1 (raw sentinel counts) | −1.032 | −0.336 / −0.998 | −0.485 | +0.082 / −0.479 | No (both T) |

**The key source-backed diagnostic:** under otherwise identical data and learner settings, changing only an *uncalibrated collection-effort assumption* manufactures or eliminates the apparent German-versus-Swedish dominant-driver reversal. At the same time, the full model fails to improve over the effort-only baseline in **both regions** for exponents 0.5 and 1. Under uniform effort, the German full model still fails, while Swedish full is positive. Therefore **none** of these rankings warrants an ecological driver-switch conclusion.

For the previously used `alpha=1` interpretation, the original post-source 99-replicate plug-in bootstrap found no observed rank reversal (`observed spread=0.10156`, null median `0.44626`, upper 95% `0.57642`, one-sided p=`1.0`). This p value comes from a fitted, uncalibrated assumed effort process, a post-source non-prospective test, and two strongly unmatched environments; it is **not** a calibrated significance test of niche evolution.

## What this does, and does not, support

Supported narrowly as an observed-method sensitivity: apparent regional dominance of temperature versus precipitation is unstable to assumptions about collection effort; in the present source panel, process-attribution interpretation is blocked by absolute held-out adequacy, absence of independently measured effort/true biological `M`, nearly complete cell record coverage, and low shared environmental support.

**Not supported:** (1) the species has changed its physiological niche; (2) constraints actually switch temperature→water; (3) observed plant abundance is measured by GBIF record counts; (4) lack of prediction gain means temperature/moisture have no ecological effect; (5) the results generalize across plants.

## Executable result

```bash
python -m experiments.geographic_turnover_postsource_audit_v1 \
  --source-cells evidence/geographic_turnover_native_source_v1/available_climate_cells.csv \
  --source-receipt evidence/geographic_turnover_native_source_v1/source_receipt.json \
  --config configs/geographic_turnover_native_windows_v1.json \
  --output results/quercus_geographic_turnover_postsource_audit_v1.json
python -m pytest -q tests/test_geographic_turnover_postsource_audit_v1.py
```

Audit writes source/config SHA-256 and preserves each original region's source outcome and process-inference refusal. The `process_inference_status` is a **diagnostic output**, not an attempt to reopen Product A/M5.

## Required next ecological test (new, separately frozen programme)

A non-circular macro analysis must acquire an **independently defined species accessible area** and external observation protocol/effort, expand spatial extent to cover both occupied and accessible contrast locations, and prospectively define environmental common-support strata without choosing regions based on observed driver rankings. On prospectively unused species, compare global versus region-varying environmental responses using source-exposure/detection-aware models and matching full-vs-knockout adequacy; require positive predictive adequacy and matched-support confirmation before treating driver ranks as ecological. Physiology/reciprocal-transplant or demographic field data are needed before calling differences adaptive niche evolution.
