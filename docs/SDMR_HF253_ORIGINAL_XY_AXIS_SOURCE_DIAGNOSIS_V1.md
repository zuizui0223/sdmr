# HF253 source-only coordinate-axis diagnosis after the first 100m spatial STOP

**Scope:** original 2019 source geometry ONLY, not a new canopy/death/SDM model. Freeze before inspecting any new coordinate values under this successor.

The original 100m spatial-vs-parent sensitivity [run #44749714741](https://github.com/zuizui0223/sdmr/actions/runs/44749714741) had a **scientific source-design STOP**, although its workflow itself completed successfully. It admitted only **14,519/21,769** previously eligible known-status stems (66.69576%) when the code assumed \`gx\` ranged 0–500m and \`gy\` 0–700m. It prespecified 80% coverage. Consequently **zero new spatial or parent-comparator model fits occurred**, no spatial Δ logloss was produced, and no conclusion about geographic robustness of the earlier +0.000695237 was justified. This is not a negative ecological result.

## Concrete uncertainty

HF253's official original field description says the plot is **500 m × 700 m** and that \`gx\` and \`gy\` are plot-relative positions in meters, but a generic dimension pair does not establish that \`gx\` must correspond to the first 500m edge. The first source-only result counted **9,396/30,808 source stems outside that particular assumed x500/y700 rectangle** and no missing numeric positions. This could indicate a **wrong x/y orientation**, not actual off-plot trees or survey attrition. Do not label these trees absent, dead, nonhabitat, outside the surveyed site or evidence that spatial data are missing.

## Prespecified response-free diagnostic

The immutable HF253 2019 original source SHA256 is \`bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7\`, 12,687,409 bytes. The corresponding original HF453 2021-tag source SHA is \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, 5,524,386 bytes. **Both must match completely before any source coordinate field is read.**

Original source columns allowed: HF453 \`StemTag\` and \`year\` only; HF253 \`stem.tag\`, \`tree.id\`, \`gx\`, \`gy\` only. Use **all exact 30,808 source tags and their fixed 27,688 original parent tree IDs**, not a Y-selected subset. Compare exactly two declared *source-coordinate geometry hypotheses*:

- \`assumed_x500_y700\`: original \`0 ≤ gx ≤ 500\`, \`0 ≤ gy ≤ 700\`, 100m parent-centroid cell assignment (5×7).
- \`alternate_x700_y500\`: original \`0 ≤ gx ≤ 700\`, \`0 ≤ gy ≤ 500\`, 100m parent-centroid cell assignment (7×5).

Report minimum and maximum original \`gx\` and \`gy\`, counts outside each dimension, blank/nonfinite original coordinate values, exact source-tag coverage and **complete-parent coverage** under each source geometry, and number of 100m cells. Every stem in a parent must satisfy the declared frame before that parent is source-coordinate eligible. Output **only nonidentifying aggregates**, no per-tree coordinates, identifiers, 2021 canopy, 2022 status, species, size or model scores. This is a **diagnostic of the assumed coordinate frame**, not a test of 2022 mortality and not a procedure that searches for a favorable biological model.

## Possible implications

- If \`gx\` really extends toward 700m and \`gy\` toward 500m, the earlier x500/y700 STOP is a **design geometry bug** rather than absence of biological opportunity; preserve its original exact receipt and record separately justified source geometry. A future **new, explicitly post-outcome developmental** version may use an author-verifiable coordinate orientation to test the same science. The earlier biological outcome remains consumed; no confirmation is recreated by this repair.
- If neither orientation adequately covers original tags, retain source geographic nonestimability; do not shrink the denominator, shift block origin, relax the 80% source threshold or change block resolution to improve the existing CP gain.
- Range compatibility alone **does not prove** axis orientation and cannot create independent forest replication, causal information or out-of-biome transfer. Confirm coordinate direction against original survey grid metadata if possible.

The first STOP's [machine evidence](../evidence/hf453_spatial100_first_geometry_source_hold_v1.json) is immutable. Original HF453 [status](../docs/SDMR_HF453_FIRST_STATUS_RESULT_20261119.md) and [prior-covariate](SDMR_HF453_PRIOR_SPECIES_SIZE_FIRST_RESULT_20261120.md) results remain exactly unchanged. Product-A \`not_promoted\`; Product B blocked; original M5 and Structural results never reopened.
