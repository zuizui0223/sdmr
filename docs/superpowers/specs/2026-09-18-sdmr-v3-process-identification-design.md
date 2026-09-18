# SDMR v3 process-information identification — scientific design

Date: 2026-09-18
Status: design specification; implementation not started
Branch: `design/sdmr-v3-process-identification`

## 1. Scope and non-retroactivity

SDMR v3 is a new scientific programme. It does not reopen, rescue, retune, reinterpret, or replace the completed Product-A v2.8.4 endpoint.

The following remain authoritative historical results:

- Product-A v2.8.4 terminal decision: `empirical_confirmation_not_supported`.
- Separate Product-A promotion decision: `not_promoted`.
- The historical Product-A fresh denominator, taxa, seeds, M definitions, thresholds, candidate library, and sealed outcomes remain frozen.
- Development seeds and exposed known-truth denominators used by v3.2, oracle diagnostics, and density-ratio v4 are burned for future prospective performance claims.

SDMR v3 may reuse generic software abstractions and scientific lessons from earlier development, but any prospective claim requires a new contract, new unused denominator, and new fresh empirical cohort.

## 2. Scientific question

The primary question changes from flat predictor selection to process-information identification.

Old question:

> Which predictor/model is best?

New question:

> Which declared ecological process information is replaceable, contributory, required, unresolved, or unavailable for reconstructing the realized environmental niche?

The primary object is not a single winning raster and not a causal physiological mechanism. It is a representation-conditioned identified state for each predeclared ecological process.

The initial empirical scope is vascular plants. Generalization to animals or other response types is outside the first prospective validation.

## 3. Process taxonomy and representation hierarchy

The initial process universe is frozen before prospective validation and contains:

- `thermal`
- `water`
- `seasonality`
- `radiation_energy`
- `soil_substrate`
- `productivity`

Predictors are linked to processes through a many-to-many registry. One predictor may carry multiple processes. Representation roles are:

- `direct`
- `derived`
- `proxy`
- `composite`

Example:

```text
thermal
├── direct temperature field
├── GDD                    [derived]
├── elevation              [proxy]
└── PET                     [shared composite]

water
├── precipitation          [direct]
├── climatic water balance [derived]
└── PET                     [shared composite]
```

Process closure for process P means removal of every registered predictor carrying P, including shared composites. Registry construction must be outcome-blind.

## 4. Core estimand

For process (P), define the full declared predictor system (X) and the closure-excluded system (X_{-P}).

Let (L) be a prespecified ecological reconstruction loss evaluated under a frozen learner, split, accessible-area definition, and observation-process treatment.

For each matched route:

[
Delta_P = L(X_{-P}) - L(X)
]

Positive (Delta_P) indicates worse ecological reconstruction after removing process information.

The process state is not based on a single fitted model. It is based on all predeclared process-free routes and their uncertainty.

Primary states:

### replaceable

At least one complete process-free route remains ecologically adequate and its uncertainty establishes non-inferiority relative to the full-information reference within the frozen margin.

### contributory

All otherwise viable process-free routes show positive evidence of meaningful ecological loss beyond the frozen margin, while at least one process-free route remains above the absolute adequacy floor.

### required

Every complete declared process-free route falls below the absolute ecological adequacy floor, with positive evidence that the loss is meaningful.

### unresolved

The evidence required to distinguish replaceable, contributory, and required is incomplete or interval-indeterminate. In particular:

```text
failure to establish non-inferiority
!=
evidence of meaningful inferiority
```

Any viable route whose uncertainty overlaps the non-inferiority boundary prevents a positive contributory classification.

### unavailable

The full declared predictor system, observation architecture, or required evidence fails the predeclared adequacy/completeness conditions needed to ask the process-identification question.

These states are conditional on the declared predictor/process registry, learner family, spatial design, accessible-area definition, and observation architecture. They are not causal or physiological truth states.

## 5. Two-stage hierarchy

### Stage P — process identification

Identify the state of each ecological process using process-closure knockouts.

No preferred raster is selected during Stage P.

### Stage R — representation refinement

Only for processes classified `contributory` or `required`, compare predeclared within-process representations using a frozen inner-transfer criterion computed entirely inside the model-pool data.

The Stage R question is:

> Which tested representation of already-supported process information transfers best to unseen occurrences?

Stage R must not be used to change the Stage P process state. The selected representation or representation set is frozen before the outer answer-check is opened; the sealed answer-check is used only once for final evaluation, never for representation selection.

A valid final result can therefore be:

```text
thermal = contributory
water = required
seasonality = replaceable
soil = unresolved

preferred tested thermal representation = GDD
preferred tested water representation = climatic water balance
```

## 6. Observation-process separation

Occurrence data are not treated as unbiased samples of the ecological niche.

The architecture retains a strict distinction between:

- ecological process predictors;
- observation/sampling-process predictors;
- accessible-area/background construction;
- occurrence answer-check data.

Observation-process covariates are never silently included in ecological process closures.

When observation bias is not adequately separable from an ecological gradient, the corresponding ecological process state must remain `unresolved` or `unavailable`, rather than being promoted from a confounded association.

## 7. Occurrence information barrier

The outer occurrence split is frozen using occurrence identity and coordinates before environmental feature selection, process selection, learner fitting, accessible-area tuning, or answer-check outcome access.

Chronology:

```text
all occurrence identities + coordinates
        ↓
coordinate-only outer spatial freeze
        ↓
model-pool occurrences
        ↓
process registry + learner + route selection
        ↓
freeze process states and Stage-R choices
        ↓
open sealed answer-check once
```

The sealed answer-check is not a tuning fold.

Existing generic answer-check split and fail-closed provenance machinery may be reused, but no historical Product-A scientific threshold is inherited automatically.

## 8. Known-truth architecture

Prospective known-truth validation must include worlds where generating-process membership and representation-level identifiability differ.

Minimum primary world families:

### W1 — unique-process

A process carries unique information that cannot be reconstructed from other declared predictors.

Expected oracle state: `contributory` or `required`, depending on the absolute adequacy floor.

### W2 — redundant-representation

A process is present in the generating equation, but declared proxies/alternative representations outside its closure reconstruct the truth surface within margin.

Expected oracle state: `replaceable`.

### W3 — shared-carrier

A composite predictor carries information about more than one process. The representation system does not support unique process attribution.

Expected oracle state: set-valued/contested evidence represented by `unresolved` unless the closure design separately identifies each process.

### W4 — null-correlated

A nongenerating process is strongly correlated with a generating process.

Expected oracle state: `replaceable`.

Primary safety question: does SDMR avoid false positive process attribution?

### W5 — interaction

The niche depends jointly on two process domains, for example thermal × water.

Expected oracle state: both process domains retained as supported; no single-process winner is forced.

### W6 — observation-confounded

The ecological field and record-generation effort share a spatial gradient.

Expected occurrence-level state: `unresolved` unless the frozen observation architecture contains enough independent information to separate ecology and observation.

Secondary stress worlds:

### W7 — omitted-driver

The declared predictor universe cannot adequately reconstruct the truth surface.

Expected state: `unavailable`; process ranking is forbidden.

### W8 — geographic/process shift

A proxy relation valid in model-pool geography breaks in a held-out geography.

Expected result: proxy dependence is exposed by sealed transfer; Stage R must not promote the unstable proxy as the preferred representation.

## 9. Oracle target

Known-truth evaluation does not score raw generating-process membership as the sole truth target.

The hierarchy is:

```text
generating-process membership
        ↓
complete true suitability surface
        ↓
truth-surface process-closure oracle
        ↓
oracle process state
        ↓
occurrence-only SDMR process state
```

The primary target is agreement with the oracle process state, conditional on the frozen representation system.

A generating process may correctly be oracle-`replaceable` if its information is reconstructable from the remaining declared predictor system.

The oracle itself must be frozen before prospective seeds are opened.

## 10. Known-truth prospective gates

Development denominators and prospective validation denominators are disjoint.

All historical seeds exposed in v3.2/oracle/v4 development are excluded from future prospective claims.

The prospective gate is a strict conjunction.

### KT-A — oracle availability and internal validity

- Full-system truth reconstruction meets its frozen adequacy floor in all primary worlds except W7, where unavailability is expected.
- Oracle state transitions match the designed world semantics.

### KT-B — positive-process recovery

For oracle-`contributory|required` cells, the occurrence learner must recover a positive supported state at a predeclared minimum rate.

### KT-C — false-positive safety

For oracle-`replaceable` cells, false `contributory|required` calls must remain below a predeclared maximum rate.

### KT-D — abstention calibration

For oracle-`unresolved` cells, over-resolution into replaceable/contributory/required must remain below a predeclared maximum rate.

### KT-E — false unique-attribution control

Shared-carrier and interaction worlds must not be collapsed to one uniquely supported process unless the oracle itself supports unique attribution.

### KT-F — sealed transfer

Process states frozen from model-pool data must retain their intended ecological reconstruction behavior on independent sealed occurrence data.

Threshold values for KT-B through KT-F are selected during development/power analysis and frozen before prospective outcomes. They must not be tuned against prospective results.

## 11. Ecological reconstruction metric

The primary ecological metric must measure reconstruction of the unseen occurrence environment, not generic classification accuracy.

Candidate metric families to evaluate during development are:

- balanced presence/background density-ratio log score;
- energy distance;
- kernel maximum mean discrepancy;
- Wasserstein distance under a fixed low-dimensional process representation.

Exactly one primary metric and any secondary diagnostics are frozen before the fresh empirical cohort is opened.

AUC and related discrimination scores are prediction guardrails/secondary diagnostics rather than the primary ecological estimand.

## 12. Learner dependence and process stability

SDMR v3 is not itself a new SDM learner.

The process-identification layer must be testable across a small frozen learner panel, initially:

- penalized logistic / MaxEnt-like learner;
- GAM;
- one strong nonlinear tree/boosting learner.

The process state is reported separately by learner and then summarized by a prespecified stability rule.

A process can be scientifically promoted as stable only when the required fraction of eligible independent learner/design routes supports the same bounded state.

Learner disagreement is not averaged away; it contributes to `unresolved` or an explicit instability flag.

## 13. Fresh empirical cohort

The first empirical validation is plant-only and uses a completely fresh taxon cohort not used in Product-A scientific confirmation or method development.

Target cohort size: development/power analysis determines one exact final denominator before any focal answer-check outcomes are opened; the planning range is 30–50 eligible taxa. The exact denominator and replacement prohibition are then frozen prospectively.

Taxon identity, data provider, geographic eligibility, temporal window, occurrence QC, accessible-area construction, process registry, learner panel, and outer split rules are frozen before focal answer-check outcomes are opened.

Consumed or insufficient taxa are not replaced after outcome access.

## 14. Fresh empirical comparators

All methods use the same model-pool information and are evaluated on the same sealed answer-check only after their decisions are frozen:

- model-pool occurrence rows;
- outer answer-check occurrence rows, unavailable to fitting/selection until final evaluation;
- accessible-area/background definitions;
- predictor universe;
- learner family where comparison requires matched learners;
- spatial evaluation units.

Minimum comparator set:

1. AUC-oriented flat predictor selection;
2. correlation/VIF-style flat filtering;
3. a strong flat predictive selector using the same learner family;
4. SDMR v3 process-first identification.

The empirical claim is not universal superiority over every possible SDM. It is a prospectively bounded comparison against these declared baselines.

## 15. Fresh empirical promotion gate

The primary empirical question is:

> Does process-first identification improve sealed ecological niche reconstruction relative to flat predictor-selection baselines without sacrificing prediction safety?

Promotion requires a strict conjunction of:

### EMP-A — ecological reconstruction

SDMR v3 shows a prospectively defined positive paired improvement in sealed ecological reconstruction against the primary flat comparator.

### EMP-B — uncertainty

The taxon-level paired uncertainty interval satisfies the frozen directional criterion.

### EMP-C — prediction safety

SDMR v3 is non-inferior on the frozen prediction guardrail.

### EMP-D — process stability

A prespecified minimum proportion of eligible taxa/process cells show stable process-level conclusions across the frozen learner/design panel.

### EMP-E — abstention integrity

Unresolved/unavailable states are preserved and are not converted into favorable calls for aggregation.

### EMP-F — denominator integrity

All declared taxa contribute according to the frozen failure/evaluability rules. Failed or unavailable units are not silently dropped to improve the result.

Only if EMP-A through EMP-F all pass may the new process-first method be scientifically promoted. Fresh empirical evaluation is not opened unless the prospective known-truth gate KT-A through KT-F has already passed under its frozen contract.

## 16. Representation-refinement empirical endpoint

Representation refinement is secondary to the Stage-P promotion claim.

Within a supported process, candidate representations are compared only after the process state is frozen, using model-pool-only inner transfer. The chosen representation or tied representation set is then frozen before the outer answer-check is opened.

The result may identify a most-transferable tested representation, but must preserve the distinction:

```text
representation selected
!=
representation is the causal mechanism
```

If several representations are empirically indistinguishable, the result remains a set rather than forcing a winner.

## 17. Reusable existing components

The design may reuse or adapt generic components already present in the repository:

- coordinate-only/sealed occurrence split machinery;
- process-information registry proposal/freeze logic;
- many-to-many process closure;
- process knockout route generation;
- truth-surface oracle process-identifiability machinery;
- provenance receipts and fail-closed evidence ledgers;
- observation-process correction primitives;
- known-truth simulation infrastructure.

Historical Product-A promotion logic, burned development thresholds, and final scientific conclusions are not inherited.

## 18. New module boundary

New implementation should live under a dedicated namespace rather than extending the Product-A version chain.

Proposed package layout:

```text
src/sdmr/process_id/
    __init__.py
    taxonomy.py
    registry.py
    routes.py
    evidence.py
    states.py
    stability.py
    representation.py

src/sdmr/process_id/known_truth/
    worlds.py
    oracle.py
    benchmark.py
    promotion.py

src/sdmr/process_id/fresh/
    cohort.py
    freeze.py
    evaluate.py
    promotion.py
```

Compatibility wrappers may call existing generic modules, but the new scientific API must not masquerade as Product-A v2.x.

## 19. Primary scientific contribution if successful

The intended contribution is not that one environmental raster is universally superior.

The intended claim is:

> Predictor identity may be unstable while ecological process information remains identifiable at a broader level. A process-first, abstention-aware procedure can separate replaceable, contributory, required, unresolved, and unavailable information before choosing among representations, and this structure can improve reconstruction of the realized environmental niche in unseen occurrences.

A stronger empirical wording is authorized only if the prospective fresh gate passes.

## 20. Failure interpretation

The protocol is scientifically useful even if promotion fails.

Examples:

- If known-truth gates fail, the method is not ready for fresh empirical testing.
- If known-truth passes but EMP-A fails, process identification may be internally coherent without providing empirical reconstruction gain.
- If ecological gain is positive but stability fails, the method may improve prediction/reconstruction without supporting stable process interpretation.
- If abstention rates are high, the conclusion is that occurrence-only data often do not identify the process state under the declared representation system.

No failed gate may be repaired by changing taxa, margins, process taxonomy, representation roles, learner panel, or denominator after outcome access.

## 21. Separation from ODSP, EOG, ACSP, 284b, and esdm

SDMR v3 remains N1: what process information belongs in the interpretable environmental niche.

- ODSP starts after niche dimensions exist and asks how much state structure is lost by projection.
- EOG asks where supported states can become realized under accessibility/world structure.
- ACSP converts bounded uncertainty into justified next-observation candidate sets.
- 284b governs when independently generated ecological answers may support a downstream relation.
- esdm may later consume process-level conclusions as provenance or validation concepts, but SDMR v3 retains its own estimand and empirical validation boundary.

No downstream result may retroactively tune this SDMR protocol.
