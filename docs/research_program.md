# SDMR research program

SDMR is organized as two linked but distinct scientific products.

## Product A: tuning methodology for ecological niche recovery

### Claim target

Develop and falsify a reproducible **model-building procedure** that recovers the
realized environmental niche of plants from occurrence-only data more faithfully
than conventional model-selection procedures.

The target is not a new evaluation statistic. AUC, Boyce/CBI, OR10, AICc and
related criteria remain useful ways to evaluate or select fitted models. SDMR
asks a different question:

> Which predictor universe, variable-selection rule, regularization and response
> complexity recover the **environmental niche itself** — its location, breadth,
> shape and limits — and keep doing so when space, M/background assumptions and
> taxa change?

### Two classes of evidence

#### Prediction/model criteria

Report these, but do not equate them with niche recovery:

- AUC / presence-background rank discrimination;
- binned Boyce and continuous Boyce/CBI;
- OR10 / omission-based overfitting diagnostics;
- AICc or other information criteria when the model family supplies a valid
  likelihood/parameter count;
- local nested spatial-CV performance.

#### Ecological niche-recovery evidence

Evaluate every candidate procedure in a common environmental audit space that is
fitted from model-pool environments only. Current recovery dimensions are:

- niche centroid error;
- niche breadth error;
- environmental quantile-profile error;
- Schoener D environmental niche overlap;
- boundary/envelope coverage as a descriptive diagnostic.

Do not collapse these into an arbitrary weighted super-score. Product-A v2 uses
Pareto filtering followed by a minimax rank rule to select a balanced recovery
procedure.

See `docs/niche_recovery_tuning.md`.

### Information barrier

Before any tuning decision:

1. admit records and deterministically thin them within species;
2. assign whole spatial blocks to `model` vs `sealed` roles;
3. build M and target-group background from **model-pool occurrences only**;
4. prevent the complete predeclared focal-taxon panel from returning through the
   broader target-group background;
5. perform all predictor selection, regularization and response-complexity tuning
   inside the model pool;
6. open sealed occurrence/reference rows only after a candidate procedure is
   frozen.

The holdout fraction is not itself a scientific parameter. Repeat across several
fractions and seeds. For method-family selection, discovery taxa may determine
which procedure is promoted, but validation taxa remain unavailable until that
procedure is fixed.

### M is a sensitivity condition

Alternative accessible-area/background assumptions change the difficulty and
meaning of presence-background evaluation. SDMR therefore does not choose the M
that gives the best raw score. Candidate methods compete within matched species ×
M cases and must remain useful across the predeclared M sensitivity set.

### Candidate tuning dimensions

- environmental raster universe and subset;
- regularization strength;
- response complexity / feature flexibility;
- number of predictors / stopping rule;
- background strategy and sampling-bias correction;
- model family, when compared behind the same information barrier.

### Conventional selectors to beat or falsify against

At minimum compare against:

1. all variables;
2. correlation/VIF filtering;
3. local nested-spatial-CV AUC selection;
4. canonical-M AUC selection;
5. canonical-M Boyce/CBI selection;
6. OR10-based selection where applicable;
7. AICc-based selection where a valid likelihood/parameterization exists;
8. same-size random predictor sets.

If SDMR cannot repeatedly improve ecological recovery or transfer relative to
these baselines, the valid conclusion is **no demonstrated niche-recovery
advantage for this corpus**.

### Two validation tiers

#### Tier 1 — known-truth simulation

Real GBIF data do not expose the fundamental niche directly. Simulate known
niche-generating response surfaces and vary collinearity, noise variables,
sampling bias, M truncation, spatial autocorrelation and response complexity.
Ask whether AUC/CBI/OR10/AICc or SDMR niche-recovery tuning chooses the model
closest to the known generating niche.

This tier supports literal claims about recovery of a known niche.

#### Tier 2 — real sealed-occurrence transfer

For empirical plants, use the narrower term **realized environmental niche
recovery**. Require transfer across sealed spatial blocks, M/background
assumptions, repeated seeds/holdout fractions and unseen taxa.

### Current implementation

The Product-A engine implements:

- preassigned whole-spatial-block sealed occurrence tests;
- sealed-before-M/background construction;
- all-variable, VIF and predictive-forward-selection strategies;
- regularized logistic tuning over C, L1/L2 and linear/degree-2 response surfaces;
- repeated M sensitivity and unseen-taxon procedure transfer;
- AUC-equivalent, binned Boyce and continuous Boyce diagnostics;
- direct comparison against canonical AUC/Boyce and local nested-AUC selectors;
- frozen-source GBIF/CHELSA evidence and repeated stability governance;
- ecological niche-recovery diagnostics in a common model-pool-fitted audit
  environmental space;
- Pareto + minimax multi-objective niche-recovery selection scaffold.

The currently running confirmatory v1 remains prediction-transfer focused and is
not retroactively changed. Niche-recovery tuning is developed as Product-A v2 on
the same frozen evidence so the two targets can be compared cleanly.

## Product B: universal and conditional drivers of plant niches

### Claim target

Only after Product A is independently validated, freeze its procedure and
identify environmental dimensions that reproducibly structure plant realized
niches across a broad taxonomic/ecological sample.

### Evidence for every raster or process

Do not rely on model importance or AUC loss alone. Record whether adding/removing
a raster changes:

- predictor selection stability;
- sealed predictive performance;
- niche centroid recovery;
- niche breadth recovery;
- environmental niche overlap;
- boundary/tail recovery;
- unseen-taxon transfer;
- heterogeneity among clades, growth forms, biomes, ranges and sampling regimes.

### Universality rule

A universal driver is not simply a variable selected often. It must contribute
reproducible ecological information and not depend on one taxonomic/geographic
stratum. Preferred output is hierarchical:

- **global core** — broadly necessary environmental processes;
- **conditional core** — consistent within declared ecological strata;
- **substitutable groups** — correlated variables carrying overlapping
  information, reported as an equivalence group rather than forcing one winner.

## Separation of Product A and Product B

Product B must never be used to redesign Product A after universal-driver results
are visible. A material change to Product A requires rerunning Product B under a
new frozen procedure.

The intended final statements are therefore:

1. **methodological** — this procedure reconstructs unused-occurrence realized
   environmental niches more faithfully and/or more transferably than declared
   conventional tuning procedures;
2. **ecological synthesis** — under that independently validated procedure,
   these environmental dimensions are the most general constraints on plant
   realized niches.
