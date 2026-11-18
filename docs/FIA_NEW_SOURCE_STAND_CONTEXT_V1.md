# FIA stand-context and actual-measurement-year study (new source snapshot)

## Scientific focus

The first fixed FIA 13-species/RI–VA–WI analysis reported 308,181 live-to-live diameter pairs, with more rapid mean inventory-year-normalized diameter change in WI than RI for several species even after broad size-band standardization. That was an observation about **survivor trees**, not a climatic niche claim. Crucially its rate denominator was `TREE.INVYR`, not directly measured elapsed time; and stand age, plot condition and site management were not controlled.

The independent PLOT/COND source gate (GitHub Actions [run 39454801553](https://github.com/zuizui0223/sdmr/actions/runs/39454801553)) completed **all three predefined RI, VA, WI states**, reading **133,582 PLOT visits** and linked condition records. It found **56,849 PLOT rows with a different actual measurement year from INVYR** (RI 453/1,408; VA 25,434/48,219; WI 30,962/83,955), **78,155 plot visit links with increasing actual MEASYEAR**, and 84,700 valid stand-age forest condition rows. These are source observations, **not** proof of error in the original tree-level rate estimates (because plot- and tree-level units differ).

## v1 independently pinned data contract

- `evidence/fia_plot_condition_source_v1.json`: immutable read-only first-open source receipt for the three pairs of PLOT/COND ZIPs, preserving original source URL, byte hashes, archive and exact table identity. This source is a *new lineage*, not the historical TREE original.
- `configs/fia_tree_plot_condition_join_v1.json`: fixed original 13 species codes and RI, VA, WI states, 1–20-year measured intervals and 4 diameter × 3 stand age categories for shared-stratum comparisons; no post-result replacement of states/species or thresholds.
- New current USDA `TREE` source snapshot is permitted only after all 6 frozen PLOT/COND hashes reproduce exactly. Its own SHA-256 is recorded and it is **not assumed identical to October 19 historic TREE ZIPs**. If any upstream SHA drifts, the run aborts before interpreting data.
- `TREE.CN/PREV_TRE_CN` links require same species and forward inventory year; `PLOT.CN/PREV_PLT_CN` must independently reproduce the plot visit succession for the same pair; `PLOT.MEASYEAR+MEASMON` gives a fractional-year measurement interval. Missing dates and nonmatching plot histories are not imputed.
- `COND.PLT_CN+CONDID` must match both visits; the source-derived **stand context** subset is forest `COND_STATUS_CD=1` and natural origin `STDORGCD=0` at both visits with a valid *prior* `STDAGE`.
- The response is **live-to-live log diameter change per measured interval year**; dead/removed/non-tallied are counted separately, never coded as zero growth. Survey weights, tree clustering, selection into repeat observation, disturbance, public-coordinate climate error and genetic differentiation remain uncorrected.
- The cross-state descriptive contrast is direct standardization within each species for initial-diameter × prior-stand-age strata with at least 10 observed matched trees in every state, weighted by pooled stratum counts. If no common strata survive, the result is `null/not_estimable`, not zero growth.

## Interpretation limits

This source-coherent experiment is **retrospective and exploratory** because the states/species and previous growth outcomes are already known. It is nevertheless materially stronger than a comparison of statewide raw means: it uses actual plot measurement dates and a defined stand-context subset. It does not test causal environmental pressure, or measure temperature/moisture physiology, and it is not a head-to-head validation of original Product A/B. It cannot be merged back into the historical 308,181 pair dataset as if the rows were guaranteed identical.

Evidence that a regional growth pattern persists after stand age correction motivates the next separately prospective test with FIA design weights, plot-clustered uncertainty, source-compatible temporal climate exposures and common environmental support. A sensitivity to stand structure would instead imply a large part of the earlier contrast is habitat composition, not local adaptation.

## Execute

```bash
python -m pytest -q tests/test_fia_tree_plot_condition_join_v1.py
python experiments/fia_tree_plot_condition_join_v1.py \
  --config configs/fia_tree_plot_condition_join_v1.json \
  --source evidence/fia_plot_condition_source_v1.json \
  --names evidence/geographic_tree_demography_source_gate_v1/fia_official_species_crosswalk.json \
  --output artifacts/fia_new_source_stand_age_growth_v1.json
```
