# FIA external-region transfer: VA/WI source environments → RI projection (2026-11-15)

**Scientific status:** postsource design diagnostic, **not** transfer prediction of growth, survival, physiological optimum, or process identity. SDMR Product A remains closed/not promoted; Product B is blocked; canonical M5 endpoints are unchanged.

## Why a three-region cross-validation claim fails

The prior fixed three-region common-support screen admitted six of 13 species. All six had **exactly five** distinct RI counties, matching the predeclared minimum of five. If one RI county is held out within that same three-region design, there are only **four RI counties** left for training, which violates the original geographic-support contract. There is no valid way to claim a fully independent RI-county fold *under that unchanged five-county-per-training-region gate*. Do **not** relax that minimum after reviewing the source.

A separate, explicitly directional **VA+WI training / RI external projection** can be characterized without using RI to choose any training environmental cells. This projection does not test growth: it asks **what fraction of previously sampled RI plot chains fall within temperature × precipitation × five-year bins supported by multiple VA counties and multiple WI counties**.

## Source, unit, and information barrier

Read the *already archived* first-source-only reconciliation [run 43711159676](https://github.com/zuizui0223/sdmr/actions/runs/43711159676), [artifact 14160283759](https://github.com/zuizui0223/sdmr/actions/runs/43711159676/artifacts/14160283759). Required CSV SHA-256 \`44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7\` and derived source receipt SHA-256 \`f167966bdd19529fe39955863effd666943e624cf939bd7c80ac8908b6a3f453\`. These represent 89,616 **prior-visit species × plot chain × measurement interval** observations, after excluding all 14 records of one county-unstable VA plot chain from the original 89,630 source records.

For each fixed species and one of eight previously used 1°C × 100-mm × five-year phase origins, build joint-environment source cells using **VA/WI observations exclusively**. One cell must have at least **two distinct counties and five plot chains in each training state**. Intersect VA and WI qualified cells; *only then* project the unchanged RI source observations into this intersection. RI is never used to construct, choose or prune the training cells. Count RI unique county+plot chains, rather than counting each remeasurement year as another spatial replicate. Report each species even when no eligible RI source exists; never silently drop zeros or absent taxa.

Report **both** the nominal number of distinct RI counties and the inverse-Herfindahl effective county count based on each county's number of unique RI plot chains:

\[
N_{\mathrm{eff,county}}=\frac{(\sum_c n_c)^2}{\sum_c n_c^2}.
\]

This quantity measures how uneven the sampled *plots* are among counties; it is **not** a statistical effective sample size or a substitute for independent county-cluster uncertainty in a growth/survival model.

## First independent calculation (to be verified by frozen-source GitHub Actions)

Among the **five species previously passing all eight three-region source-support origins**, RI source-only plot chains represented within VA/WI common environmental bins are:

| Species | RI plots | Minimum projected RI plot fraction across eight phases | Maximum | Effective RI counties |
|---|---:|---:|---:|---:|
| *Pinus strobus* (129) | 72 | 69/72 = **95.8%** | 100% | **2.95** |
| *Acer rubrum* (316) | 131 | 131/131 = **100%** | 100% | **2.88** |
| *Quercus alba* (802) | 95 | 94/95 = **98.9%** | 100% | **2.90** |
| *Quercus rubra* (833) | 80 | 79/80 = **98.8%** | 100% | **2.42** |
| *Quercus velutina* (837) | 72 | 70/72 = **97.2%** | 100% | **2.74** |

Those five species are **not** discovered by this projection; they were already selected for *earlier* source-only grid-origin robustness. The full 13-taxon denominator must be archived, including *Betula alleghaniensis* (371), which had variable support in the previous three-region test. This comparison direction and the eight phase options were also chosen **after source exposure**, so this is exploratory and cannot be labeled a prospective validation of niche conservation or adaptation.

The source-only result establishes that a **measurable subset** of RI plot-climate opportunities is represented in the two training regions. It cannot guarantee adequate independent training biological outcomes, comparable detection/stand conditions, valid proxy carriers, unbiased tree survival selection or biologically meaningful response prediction. The forest physiology question remains **unidentified**.

## Implementation and next decision

\`experiments/fia_external_region_support_v1.py\` verifies the frozen CSV and receipt SHA-256, uses the unchanged environmental-support configuration, and compares *VA/WI training bins* to *RI projection only*. \`tests/test_fia_external_region_support_v1.py\` tests source isolation, time-only mismatches, repeat-interval inflation, and missing taxa. A lock-triggered no-network GitHub Action preserves the full 13-taxon × eight-phase JSON output.

**Feasibility conclusion (limited):** VA/WI→RI is a plausible *future direction* for an externally designed demographic test on these species; a within-RI 5-county training design cannot preserve the original minimum after withholding a county. A subsequent biological study would require a newly frozen response acquisition, strict absence of future-survival conditioning, independent spatial units, forest-context adjustment, raw-source reproducibility, and a **predeclared minimum worthwhile RMSE improvement** before opening holdout growth/survival. Do not import the old v4 selected-survivor outcome into this new source-only cohort.
