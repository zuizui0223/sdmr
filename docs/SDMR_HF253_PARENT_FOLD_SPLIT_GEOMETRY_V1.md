# HF253/HF453 parent-tree split geometry: exact hypothetical five-fold leakage pressure

**Theoretical source-grain design diagnostic — NOT a measurement of realized prediction leakage.** Uses the already archived HF253 original parent-ID counts only; no source CSV, species, status, canopy, diameter, mortality, SDM training split or fitted model is opened.

## Verified original structure

30,808 original HF453 stem tags map to **27,688** original HF253 parent \`tree.id\` candidates, and **2,331** parents contain two or more of those stems. Multiplicity histogram: one=25,357; two=1,775; three=404; four=101; five-or-more=51; maximum 8. The 51 large families together contribute 285 stems, inferred *exactly* from the saved source totals. Source and first-result receipts are in [the original source-only parent audit](SDMR_HF253_HF453_PARENT_TREE_GRAIN_FIRST_RESULT_20261119.md).

## Question and exact formula

What fraction of source parent IDs would be **split between two or more validation folds** if an analyst incorrectly assigned each *stem* independently and uniformly to \`K\` folds?

For a parent with \`m\` matched stem tags, the probability all those tags land in the **same** fold is \`K × (1/K)^m = K^(1-m)\`. Therefore:

\[
 P(\mathrm{parent\ spans\ multiple\ folds}\mid m,K)
 = 1-K^{1-m}.
\]

This is purely a random-assignment property. It does **not** prove that an ecological outcome or predictor signal leaked into a model, and it is not an estimated intracluster correlation, actual effective sample size, bias, p-value or confidence interval.

For an illustrative **independent stem-wise 5-fold CV** design, exact group probabilities are 0 for one stem, 0.8 for two, 0.96 for three, and 0.992 for four. With the fixed observed histogram and only a bounded unknown distribution for the 51 five-plus families (minimum five and maximum eight stems, 285 total), sharp expected number of parent IDs spanning multiple folds is:

\[
\boxed{1958.966272 \le E[N_\mathrm{split\ parent}] \le 1958.988800.}
\]

The extremes reflect two possible arrangements of the 285 stems among the 51 five-plus parent IDs, both obeying original source counts: minimum with 10 eight-stem + 41 five-stem parents, maximum with 30 six-stem + 21 five-stem parents. The result is approximately **1,959 parent IDs**, or **84.0% of the 2,331 multi-stem parents**. Actual realized random seeds, fold allocation, tree correlation and source ecology are **not** inspected.

The factor \`30,808 / 27,688 = 1.112684…\` indicates **11.27% more nominal stems than parent IDs**, not a known variance inflation factor. Even parent-wise splitting could be ecologically insufficient, because whole forest plots, spatial blocks and observation efforts may share latent conditions.

## Executable no-outcome implementation

- [Exact fraction calculator](../scripts/hf253_parent_random_fold_split_theory_v1.py): verifies original source parent denominators; computes \`1-K^(1-m)\` and exact lower/upper expectations for the unresolved 5+ bucket using the concavity of the split-probability function. Reports only hypothetical fold-design expectations.
- [Unit tests](../tests/test_hf253_parent_random_fold_split_theory_v1.py): exhaustive small-histogram enumeration checks the interval extrema; verifies the source 30,808/27,688 counts, both expected value boundaries, and that results are not presented as observed information leakage or model performance.
- No original source GET, no ecological outcome read, no model refit; original HF453 \`DC/DS\` versus CP field-status association and the M5/Structural known-truth denominators are unchanged.

## Methodological implication

The original source demonstrates a **concrete, auditable physical-grain mismatch**: \`stem.tag\` and parent \`tree.id\` are not equivalent. Randomly holding out individual stems is not a defensible way to demonstrate transfer to unseen parent trees, much less unseen forests. Parent-grouped and site/spatial-blocked validation must be defined **before** inspecting a new target, and the ecological observation process must remain separately audited.

This check is a reproducible *design warning*, not an empirical biological mechanism, causal selection finding or automatic validation of SDMR against AUC/CBI. Original Product A remains \`not_promoted\`, Product B blocked, and PR #286 remains Draft.
