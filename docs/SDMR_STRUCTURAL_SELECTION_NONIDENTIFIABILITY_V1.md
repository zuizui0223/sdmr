# Exact SDMR × Structural observational nonidentifiability counterexample — v1

**New analytic result, 2026-11-19.** This proof is independent of the original M5 and 80-case Structural known-truth outcome. It reuses **zero** past seeds, forest responses, fitted models, or observed ecological effect sizes. The synthetic 80-case safety result is neither changed nor rescued.

## The target

Can an analyst identify whether a recorded association between a structural/environmental covariate \(X\) and an outcome \(Y\) is ecological rather than due to outcome-dependent recording \(S\), when the available data contain \(X,S\) for the sampling frame and \(Y\) only if \(S=1\)?

No, absent additional assumptions or measurement of the recording/selection mechanism. This holds even if the **marginal observation probability \(P(S=1\mid X)\) is known exactly**.

## Constructive proof with exact fractions

Let \(X\sim\mathrm{Bernoulli}(1/2)\), \(Y\) be the binary ecological outcome, and \(S=1\) mean that the outcome is recorded. Compare two different data-generating worlds:

| Quantity | World E: actual ecological response, ignorable recording | World O: no ecological response, outcome-dependent recording |
| --- | --- | --- |
| \(P(Y=1\mid X=0)\) | \(1/4\) | \(1/2\) |
| \(P(Y=1\mid X=1)\) | \(3/4\) | \(1/2\) |
| \(P(S=1\mid X=0,Y=0)\) | \(1/2\) | \(3/4\) |
| \(P(S=1\mid X=0,Y=1)\) | \(1/2\) | \(1/4\) |
| \(P(S=1\mid X=1,Y=0)\) | \(1/2\) | \(1/4\) |
| \(P(S=1\mid X=1,Y=1)\) | \(1/2\) | \(3/4\) |
| **Population \(Y\)-contrast across \(X\)** | **\(1/2\)** | **\(0\)** |

Both worlds have exactly the same observed joint record masses:

- \(P(X=0,Y=0,S=1)=3/16\)
- \(P(X=0,Y=1,S=1)=1/16\)
- \(P(X=1,Y=0,S=1)=1/16\)
- \(P(X=1,Y=1,S=1)=3/16\)

Both also have \(P(X=x,S=0)=1/4\) for **each** \(x=0,1\), and therefore \(P(S=1\mid X=0)=P(S=1\mid X=1)=1/2\). The **full observable distribution**, including explicit marginal recording opportunity, is identical. But the population ecological contrast differs by \(1/2\).

Thus no procedure acting only on those observables (including perfect predictive fitting, AUC, model agreement, process-group knockouts or a marginal effort offset) can distinguish these worlds reliably. Richer spatial or temporal labels only help if they add independently informative assumptions or observations that separate the selection processes.

## Why this strengthens the methodological paper

1. It explains why **positive heldout predictive information is not proof of ecological-process identity**: both worlds would yield the same *observable* target.
2. It clarifies why the 80-case synthetic gate obtains 0/50 false calls partly from a **simulation-supplied observation-selection quality flag**; an actual data source does not supply such a flag automatically.
3. It provides a hard boundary for future methods: a source audit can **refuse unknown/unsafe selection**, but a passing source metadata check **cannot mathematically prove absence of hidden outcome-dependent selection**.
4. The rigorous next test is not another tuning of \(C\), AUC, CBI, OR10 or AICc; it is independently measured selection opportunity or strong, explicit, falsifiable assumptions about missingness, detection and the endpoint operator.

This binary proof assumes \(Y\) is observed for both positive and negative recorded units, which is **more informative than presence-only data**. Nonidentifiability under this richer observation scheme also applies when only recorded presences are available, absent stronger assumptions. The example proves existence of indistinguishable mechanisms, **not that every forest or GBIF dataset is biased**.

## Reproducible exact audit

- Code: [\`src/sdmr/structural_selection_counterexample_v1.py\`](../src/sdmr/structural_selection_counterexample_v1.py)
- Tests: [\`tests/test_structural_selection_counterexample_v1.py\`](../tests/test_structural_selection_counterexample_v1.py)
- Entry: \`from sdmr.structural_selection_counterexample_v1 import verify_exact_counterexample; verify_exact_counterexample()\`
- Uses Python \`fractions.Fraction\`; exact equality, no random seeds, fitted models, external data, or biological response opening.

**Scientific ceiling:** formal identification limitation under a constructed pair of finite observation laws. The separate empirical claim that a particular plant or forest mechanism is identified remains unestablished. Product A remains \`not_promoted\`, Product B blocked, original M5 71/80 and Structural synthetic 30/30 unmodified.
