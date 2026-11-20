# HF453 canopy-status signal vs prior species, diameter and health — post-outcome exploratory v1

**Research status (2026-11-20): analysis, fixed before *new 2019 biological covariate opening*, but designed AFTER the original 2021→2022 HF453 death/CP result was already observed. This is NOT prospectively independent biological confirmation.**

The original SDMR v2.8.4 Product-A \`not_promoted\`, blocked Product B, M5 synthetic 71/80, Structural synthetic 30/30, and first HF453 field-status effect are immutable. All analyses below are **one Harvard Forest 35-ha plot**.

## Why the next question matters

The source-locked original HF453 2021→2022 reported dead-status contrast was CP1/2 (understory) **323/10,452** versus CP3/4/5 (more exposed) **138/11,390**. Five next-year DN/unknown observations gave a sharp missing-outcome association interval excluding zero. The first source-only HF253→HF453 parent audit found **30,808 stem tags mapping to 27,688 parent tree IDs**. These positive *source records* do not identify independent tree mortality or a causal canopy-light effect.

A plausible rival explanation is **starting tree health, species composition and size**. HF253's 2019 source field \`sp\` is the species mnemonic; \`dbh\` is stem diameter in **cm**. HF453's 2021 \`A\` means observed alive without known visible health issues, and \`AU\` means observed alive with a health issue. These are all **predate the 2022 event**, but the 2019 census is not concurrent with 2021 health. [Official HF253](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF253) and [HF453](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF453) publisher dictionaries govern the meanings, not inferred field aliases.

## Fixed source identity and denominator

The original 2019 HF253 \`hf253-06-stems-2019.csv\` must match whole-file SHA-256 \`bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7\`, **12,687,409 bytes**; its MD5 in our archive is **computed, not provider verified**. The original 2021–2024 HF453 source must match SHA-256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, provider MD5 \`c6be7aa99e31ded2041a0aaea07c0205\`, **5,524,386 bytes**.

Only the exact original 30,808 2021 HF453 \`StemTag\` identities and matching 2019 HF253 \`stem.tag\` identities are admissible; source parent \`tree.id\` is mandatory for group splits. Unmatched or ambiguous rows halt the cohort. No normalization of species codes or stem tags, no switch to the incompletely matching \`tag\` (tree tag) key.

Preserve the original outcome denominator **21,846 observed alive 2021 stems**, including known-dead 461, DN/unknown 5, and 4 unknown prior CP; 10,452 CP1/2 and 11,390 CP3/4/5. The prior-covariate-complete subset is only defined by nonmissing original 2019 \`sp\` and finite positive \`dbh\` in cm. Report both its numerator/denominator and all exclusions. Do **not** reinterpret excluded individuals as biological absence.

## Question 1 (primary): incremental out-of-parent predictive information

Among known 2022 \`DC/DS\` or \`A/AU\` responses with measured 2021 CP and complete 2019 \`sp/dbh\`:

- **Frozen baseline:** one-hot 2019 species mnemonic \`sp\` + \`log1p(dbh_cm)\` + 2021 baseline \`AU\` indicator.
- **One added candidate:** binary CP from 2021 (CP1/2 vs CP3/4/5). No interactions, scanning or alternate feature thresholds.
- **Same fixed learner on both sides:** sklearn LogisticRegression, isotropic L2, \`C=1\`, \`lbfgs\`, \`max_iter=1000\`, no class balancing, original parent-tree equal weighting \`1/(number of included stems per tree.id)\`.
- **Five GroupKFold splits by original \`tree.id\`**. The same parent cannot be simultaneously in train and test; all known-source eligible stem responses scored exactly once. This is **within the same forest, unknown-parent holdout only**, not independent forests, spatial-block holdout, ecological causation or niche-driver recovery.
- **Primary scalar:** mean out-of-fold negative log loss, equal-weighting original parent IDs, \(\Delta=\mathrm{loss}_{baseline}-\mathrm{loss}_{+CP}\). Positive = a **descriptive predictive increment** on this previously consumed one-forest endpoint; zero/negative = no gain under these frozen choices. Brier-score change is a secondary descriptive guardrail.
- Stop/return unavailable if insufficient binary outcome classes or learner convergence fails. No post-outcome learner retuning to improve CP.
- Five \`DN\`/unknown next states remain in the original source ledger and secondary partial-identification bound, but are not relabeled to fit a binary predictive model.

A positive log-loss increment is **not** evidence of a causal competition/physiology mechanism or superiority over every conditional/group-importance method. A negative log-loss increment does not establish that light never affects survival.

## Question 2 (secondary): conditional sign under fixed species × diameter × health strata

Use exactly the four original 2019 DBH bands in cm: \((0,10)\), \([10,20)\), \([20,40)\), \([40,\infty)\), together with the exact original species mnemonic and original 2021 \`A/AU\` state. These are **not selected from the outcome**.

For each \(h=(species, size\ bin, baseline\ health)\), calculate the observed-dead, observed-alive and unknown-next counts separately for both CP groups. The main common-support threshold is **at least 10 original stems in each CP group per stratum**. As a predefined sensitivity, use at least one per group. Report how many strata and stems fail the overlap rule. The estimand is the **pooled-original-stratum-size-standardized association** *only in the admitted subset*, not the full 21,846 original stems.

For each stratum, let \(p_{gh}\) be observed 2022 \`DC/DS\`, \(m_{gh}\) unknown status, \(n_{gh}\) baseline eligible CP-measured stems. All possible allocations of unknown next status give sharp associational bounds

\[
\delta_h\in[
p_{1h}/n_{1h}-(p_{0h}+m_{0h})/n_{0h},\quad
(p_{1h}+m_{1h})/n_{1h}-p_{0h}/n_{0h}
].
\]

Average these endpoints over strata with weights \(w_h=n_{0h}+n_{1h}\), normalized by their total. If the resulting interval excludes zero, its sign is robust **only to missing next-year state among eligible matched stems in the fixed overlap subset**, not to unmeasured ecological confounding, source selection or finite sample variability. These are identification bounds, **not confidence intervals**; no causal intervention is being identified.

## Honest result boundaries

- Original source-level counts are fixed; 2019 source species and DBH missingness are not yet inspected. If joint covariate availability is poor, output a source/overlap hold, not a favorable rescue by reselecting a subgroup.
- A source row showing \`DN\` does **not** prove death was visually observed; \`A/AU\` and \`DC/DS\` are distinct and fixed.
- Parent GroupKFold prevents a known parent tag appearing on both sides; neighboring trees remain correlated through the same forest, site and observers. Equal-parent scoring does not create independence across biomes.
- Species codes may represent several taxonomic resolutions. We use literal original mnemonics and make no post-hoc translation or taxonomic regrouping.
- The first HF453 field association remains *per-stem*, not an individual-parent mortality estimate. This extension operates on the original stem endpoint and uses parent IDs **only to enforce validation grouping and equalize scoring weights**.
- This is **post-original-outcome exploratory**. Its data, strata, targets and comparators will not be reclassified as a prospective biological replication. No original SDMR product or M5 decisions can be changed.

## Reproducibility

- Frozen method/source contract: [\`configs/hf453_prior_species_size_postoutcome_v1.json\`](../configs/hf453_prior_species_size_postoutcome_v1.json)
- Implementation: [\`scripts/hf453_prior_species_size_confounding_postoutcome_v1.py\`](../scripts/hf453_prior_species_size_confounding_postoutcome_v1.py)
- Synthetic tests: [\`tests/test_hf453_prior_species_size_confounding_postoutcome_v1.py\`](../tests/test_hf453_prior_species_size_confounding_postoutcome_v1.py)
- One-shot workflow and exact run-lock will be activated separately **after** the code/contract/test hashes have been pinned and synthetic tests pass. Archive only aggregate signed source receipts, source-level category counts and held-out score summaries. **No tree IDs, stem tags, raw original source rows or row predictions will be exported**.
