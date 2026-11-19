# HF453 one-forest first real observed-status result — original first opening 2026-11-19

**Disposition:** the preregistered within-HF453 **observed-status association direction is identified under unrestricted missing NEXT-Y status**, but **no causal process, physiologically limiting driver, forest-wide inference to untagged trees or cross-forest transfer is established**. This is a new single-forest *descriptive field result*, different from and not pooled with original M5 known-truth, Structural 80-case synthetic, or consumed FIA growth endpoints.

## Original source, design and one opening

- Source: Harvard Forest HF453 v1, original published annual July visual tree-health census in one 35-ha ForestGEO plot, DOI \`10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193\`; exact original full byte SHA256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, publisher MD5 \`c6be7aa99e31ded2041a0aaea07c0205\`, 5,524,386 bytes.
- Prespecified [new endpoint/CP/source contract](../configs/hf453_demographic_transition_first_open_v1.json), [scientific prefreeze](SDMR_HF453_FIRST_STATUS_TRANSITION_PREFREEZE_20261119.md) and [one-shot code](../scripts/hf453_first_status_transition_v1.py), all locked **before** reading any original HF453 \`status\` or \`CP\` values.
- Authoritative **first** source-status opening: [GitHub run #44540469560](https://github.com/zuizui0223/sdmr/actions/runs/44540469560), head commit \`ffc4011c52272dab7166740666bc254a78283bdc\`, **SUCCESS**, artifact #14537667449, ZIP SHA256 \`0cad2360db08d2549600af088a44e0b6d5bb7ac19aef241dc3b8c6316a9d4e73\`, inner original result SHA256 \`6992650efb0f5b8b23106969aae8853ed6aaa339a3a4b9d8c77425ac0d298cab\`. No raw stem-level rows exported.
- Full frozen [machine checkpoint](../evidence/hf453_first_observed_status_transition_v1.json). A **separate archive-only, zero-refit saved-count checker** recomputed all source annual code counts, baseline-at-risk partitions, canopy group/unknown counts and exact fractions: [run #44541316089](https://github.com/zuizui0223/sdmr/actions/runs/44541316089), artifact #14538946614, ZIP SHA256 \`b4d3e547939830ec916276c51c385301101e5dafc2f019e5d14209332228adee\`. This is **arithmetic consistency, not independent ecological replication**.

## Prespecified primary endpoint: 2021→2022

30,808 source tags occur in each year's original source table, but tags do not imply living trees or a successful visual detection every year. Of the 30,808 tags in 2021, **21,846** had observed-alive starting codes \`A/AU\`, **8,688** already had directly coded dead \`DC/DS\`, and **274** had \`DN\`/missing or unknown state; these groups sum to 30,808.

For the 21,846 starting alive risk-events, the next-year code was **461 DC/DS observed-dead**, **21,380 A/AU observed-alive**, **5 DN/unknown**. Just **4** of the eligible start-year alive events lacked usable canopy position; they are retained separately.

| Prior canopy \`CP\` | Original eligible start-alive events | Next-year \`DC/DS\` | Next-year \`A/AU\` | Next-year \`DN\` / unknown | Recorded \`DC/DS\` / all risk-events |
| --- | ---: | ---: | ---: | ---: | ---: |
| \`1/2\` (lower-light) | **10,452** | 323 | 10,125 | 4 | 3.0903% |
| \`3/4/5\` (more exposed) | **11,390** | 138 | 11,251 | 1 | 1.2116% |
| unknown prior CP | **4** | 0 | 4 | 0 | not in the CP contrast |

Primary **difference in recorded-dead proportions** (more-exposed minus lower-light): **−1.8787 percentage points**. Treating every \`DN\`/unknown next outcome as arbitrarily alive or dead gives the exact sharp **identification interval** \([-\frac{5677}{296140},\,-\frac{16613}{888420}]\) = **−1.9170 to −1.8699 percentage points**. This interval excludes zero, so the **direction of the source-coded status association among baseline-CP-measured tagged trees is robust to those five unknown next outcomes**.

**This interval is NOT a statistical confidence interval,** and it does not cover uncertainty in the original tree opportunity frame, an unrecorded individual, classification differences among species or field-worker observers, correlated trees, or downstream survival/size selection.

## Independently predeclared secondary descriptions

| Fixed annual interval | Start-alive \`A/AU\` events | Recorded next \`DC/DS\` | Unknown next outcome | Lower-light \`DC/DS\` / N | More-exposed \`DC/DS\` / N | Sharp missingness interval, more minus lower (percentage points) |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 2022→2023 | 21,386 | 538 | 3 | 366 / 9,384 (3.9003%) | 172 / 11,998 (1.4336%) | **−2.4880 to −2.4583** |
| 2023→2024 | 20,845 | 519 | 0 | 377 / 9,757 (3.8639%) | 142 / 11,082 (1.2814%) | **−2.5825 (point identified for recorded next status)** |

These are repeated observations on the **same HF453 tags** with changing eligibility/canopy. They are *not* three independent forests, years of randomized exposure, three independent species replicates, or a replicated causal canopy/competition effect. The apparent progressive difference may reflect cohort depletion, canopy shifts, species differences, tree size/age, health, infestation history, or other source-specific selection.

## Correct methodological contribution

The positive result earned is **narrow but real**: in a correctly versioned original single-forest **tagged cohort** with a complete original four-year table and explicitly separated observed-dead, observed-alive and unknown/not-found states, the signed **associational response difference survives arbitrary outcome assignment to the measured missing next-status events**. It demonstrates an empirical use of the *same partial-identification formulation* motivated by the earlier exact observation-selection counterexample, without claiming recovery of latent ecological mechanisms.

It does **not** show that canopy light causally prevents death. Exposure \`CP\` is a measured tree state, not a manipulated predictor and not an exhaustive ecological process carrier set; the method's original synthetic \`observation_selection_known\` flag has no empirical equivalent here. Nor does the positive sign itself establish transfer to other forests or biomes.

## Mandatory next scientific check (separate exploratory extension)

A potential source of confounding is tree **taxon and diameter** before the 2021 field outcome. Harvard Forest [HF253 (v6)](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF253) documents 2019 original \`tag\`, \`stem.tag\`, \`sp\`, \`dbh\`, \`gx/gy\`, \`quadrat\` and prior field \`df.status\`, with **different tree- vs stem-level grain** and incomplete 2019 swamp census. First verify the **pre-outcome identity crosswalk** to HF453 \`StemTag\` without accessing any HF453 \`status/CP\` or HF253 species/size/outcome values. Unmatched and ambiguous tags must stay in the denominator. Only after independent source-version identity gates can a **post-outcome exploratory**, cluster-aware species/size adjustment be considered. It would not become a new prospective replication of the already-opened HF453 outcome.

The main project publication ceiling is unchanged: Product A v2.8.4 \`not_promoted\`; Product B formally blocked; original M5 71/80 and Structural prospective synthetic 30/30 remain separate fixed evidence; earlier FIA BA positives and temporal nonuniversality remain retrospective. Keep PR #286 **Draft** pending distinct independently sampled real forest outcomes.
