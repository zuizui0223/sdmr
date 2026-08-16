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
- boundary/envelope coverage as a descriptive diagnostic;
- known-truth response curves, optima and environmental limits where literal
  generating truth is available;
- known-truth ecological-process recovery.

Do not collapse these into an arbitrary weighted super-score. Product-A v2 uses
Pareto filtering followed by minimax rank logic for ecological recovery, while
retaining canonical and perturbation-robust ecological procedures as distinct
sources of evidence.

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

### Observation process is not the ecological niche

Sampling effort, detectability and collector-access variables may improve record
prediction without being plant-niche drivers. Product-A v2 therefore separates:

- the full observation-aware score used by conventional record-prediction
  diagnostics;
- the ecological suitability surface obtained after declared observation
  nuisance variables are marginalized;
- a candidate-independent observation audit that can reweight the held-out
  occurrence target when reproducible nuisance-only evidence is present.

If the observation process is independently validated, ecological candidate
models must explicitly declare that nuisance process so coefficient confounding
is not silently interpreted as niche structure.

### Prediction adequacy is scoped to the claim

Prediction remains a minimum requirement, not the ecological objective. Hard
record-prediction adequacy is required for within-domain sampling/background
perturbations. Fixed domain transfer remains mandatory ecological sensitivity
evidence, but below-chance record AUC under a shifted domain does not by itself
prove that the inferred ecological niche is wrong.

This separation was forced by known-truth falsification: an ecologically better
niche model can fail occurrence-record discrimination after a domain shift.

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

### Consensus-first ecological interpretation

Canonical ecological recovery and perturbation robustness are not averaged into a
new score. After both procedures select candidates, Product-A v2 reports an
**ecological inference certificate**:

- **stable process core** — ecological process groups supported by both
  procedures;
- **contested processes** — supported by only one ecological procedure;
- **model-form uncertainty** — different models/rasters can support the same
  ecological process;
- **abstention** — unresolved cases are not converted into negative evidence.

For literal environmental axes shared by both candidates, interpretation reports
selector ranges rather than means for niche centre, breadth, lower/upper limits
and marginal optimum. These are sensitivity ranges between procedures, not
confidence intervals. Raw binned marginal curves are retained so response shape
is not forced into an arbitrary category.

In fresh known-truth seeds 11–20, exact model consensus was 34/60 whereas process
set consensus was 48/60. The stable process core had mean precision 0.978, recall
0.967 and F1 0.970 against hidden generating processes. This supports using the
process core as the strong ecological claim while preserving contested processes
as explicit sensitivity.

### Current implementation

The Product-A engine implements:

- preassigned whole-spatial-block sealed occurrence tests;
- sealed-before-M/background construction;
- all-variable, VIF and predictive-forward-selection strategies;
- regularized logistic tuning over C, L1/L2 and linear/degree-2 response surfaces;
- repeated M sensitivity and unseen-taxon procedure transfer;
- AUC-equivalent, Boyce/CBI and OR10 diagnostics;
- direct comparison against conventional predictive selectors;
- frozen-source GBIF/CHELSA evidence and repeated stability governance;
- ecological niche-recovery diagnostics in a common model-pool-fitted audit
  environmental space;
- observation-process detection, target correction and ecological model
  admissibility;
- canonical and exogenous-perturbation ecological recovery;
- known-truth audits for full suitability rank/error, response curves, optima,
  environmental limits and process recovery;
- consensus-first ecological inference certificates;
- ecological response profiles and selector ranges for biological
  interpretation.

The frozen Product-A v1 remains prediction-transfer focused and is not
retroactively changed. Product-A v2 is developed on a separate lane so the two
targets can be compared cleanly.

## Product B: universal and conditional drivers of plant niches

### Claim target

Only after Product A is independently validated, freeze its procedure and
identify environmental dimensions that reproducibly structure plant realized
niches across a broad taxonomic/ecological sample.

### Two Product-B evidence lanes

The repository retains the earlier **predictive-driver baseline**. It aggregates
predictor/process selection frequency, incremental gain, drop-one predictive loss
and unseen-taxon predictive performance. These are useful comparators, but they do
not by themselves establish an ecological niche driver.

The v2 scientific main line is a separate **ecological certificate synthesis**.
For every taxon × process it records one of:

- `stable_core` — both canonical and robust ecological procedures support the
  process;
- `contested` — only one ecological procedure supports it;
- `not_supported` — neither supports it in an informative certificate;
- `unresolved_abstention` — Product A could not make a resolved ecological claim.

Abstention is never silently counted as absence. Cross-taxon summaries report
strong-support, any-support, contested and not-supported fractions but do **not**
apply an arbitrary fraction threshold to manufacture a universal driver.

### Predictor, process and substitutable groups are different objects

Product-B interpretation keeps three levels distinct:

1. **raw raster** — a literal CHELSA/BIOCLIM/soil/topographic variable;
2. **ecological process** — the broader biological constraint represented by a
   raster;
3. **substitutable/equivalence group** — predictors explicitly judged to carry
   overlapping information.

The existing candidate manifest remains the metadata source of truth. A
predeclared predictor-process registry reads that manifest and can add role,
units and explicit equivalence-group metadata. If no equivalence group is
predeclared, a raster remains a singleton rather than being merged post hoc.

Correlation-based equivalence groups remain a separate diagnostic for potentially
substitutable information. Correlation is not an automatic raster-admission or
process-equivalence rule.

### Evidence for every raster or process

Do not rely on model importance or AUC loss alone. Record whether adding/removing
a raster or process changes:

- predictor selection stability;
- sealed predictive performance;
- ecological certificate support state;
- niche centre and breadth recovery;
- environmental niche overlap;
- boundary/tail and optimum recovery;
- unseen-taxon transfer;
- heterogeneity among clades, growth forms, biomes, ranges and sampling regimes.

### Universality rule

A universal driver is not simply a variable selected often. It must contribute
reproducible ecological information and not depend on one taxonomic/geographic
stratum. Preferred output is hierarchical:

- **global core** — broadly supported stable environmental processes;
- **conditional core** — stable within declared ecological strata;
- **contested processes** — meaningful but selector/stratum sensitive;
- **substitutable groups** — overlapping indicators reported as groups rather than
  forcing one raster winner.

No support threshold is currently promoted as a universal-driver rule. Product-B
must first be run under a frozen empirical Product-A procedure on real taxa; only
then can a promotion rule be predeclared and independently validated.

## Separation of Product A and Product B

Product B must never be used to redesign Product A after universal-driver results
are visible. A material change to Product A requires rerunning Product B under a
new frozen procedure.

The intended final statements are therefore:

1. **methodological** — this procedure reconstructs unused-occurrence realized
   environmental niches more faithfully and/or more transferably than declared
   conventional tuning procedures;
2. **ecological synthesis** — under that independently validated procedure,
   these environmental processes form the stable global/conditional constraints
   on plant realized niches, with contested and substitutable evidence reported
   rather than hidden.
