# Product-A manuscript spine

Status: **submission framing after completed counterfactual validation and replication**.

The empirical v2.8.4 endpoint remains `empirical_confirmation_not_supported`; separate promotion decision `not_promoted`; Product B remains blocked.

## One-sentence paper claim

**Environmental-process membership can be inferred from the ecological recovery lost when all declared representations of a process are removed from the prediction-adequate candidate class; after a predecessor failed a factorial truth test, this counterfactual estimator recovered 65/70 complete generating-process sets in an unchanged independent replication.**

## Main inferential objects

Keep four objects distinct throughout the manuscript:

1. **predictive adequacy** — can a model transfer to held-out occurrences?
2. **process necessity** — does an adequate explanation survive explicit exclusion of declared process information? This is the v2.4–v2.6 branch.
3. **process stability** — do independently defined ecological selectors support the same process information? This is the v2.7.2 predecessor branch.
4. **counterfactual process membership** — how much achievable ecological niche recovery is lost when every declared representation of one process is excluded from the prediction-adequate candidate class? This is the final positive estimator.

The fourth estimand is now the principal process-identification result. It must not be relabelled as physiological or causal necessity.

## Main Results spine

### R1. Prediction and stable response surfaces do not identify process truth

Use v1 as the information-barrier foundation and v2.1–v2.2 as the initial falsification.

Main sentence:

> Sealed occurrence transfer and stable environmental response surfaces remained compatible with incorrect generating-process attribution, so ecological interpretation required a target beyond predictive winner identity.

### R2. Better ecological model sets can create false necessity

Use v2.3 as the anti-conservative counterexample.

Main sentence:

> Ecological Pareto pruning made retained model sets sharper while losing truth/boundary coverage and could create a false necessary-process core, showing that agreement after performance filtering is not biological necessity.

### R3. Exclusion-based necessity controls false-required claims but can remain broad

Use v2.4–v2.6 as one falsification/abstention branch.

Main sentence:

> Explicit process-information knockouts eliminated false-required claims and retained all true processes when calibration was complete, but the safe possible-process set remained broad and `required_processes` was empty in 9/9 validation taxa.

Report possible-process precision ≈0.467 and wider calibrated intervals. This branch addresses **necessity**, not the final process-membership classifier.

### R4. A stronger factorial truth test falsified the consensus-first predecessor

Use v2.7.2 as the proof-of-concept predecessor, then the new factorial test as the deliberate stress test.

Required sequence:

- v2.7.2 stable core: 55/60 exact process sets; however temperature and water were invariant true processes and only soil varied in presence;
- stronger factorial generator: temperature, water and soil independently varied across all seven non-empty process sets;
- discovery/test seeds 4201–4205, 35 total cases;
- predecessor stable intersection exact only **22/35 = 62.9%**;
- AUC-selected winner exact **25/35 = 71.4%**.

Main sentence:

> When all three process identities were allowed to switch independently, the apparently strong consensus-first certificate failed the frozen factorial support criterion, showing that model-set agreement was still not a sufficiently direct estimator of process membership.

This failure is a scientific result and must not be hidden behind the earlier 55/60 headline.

### R5. Counterfactual niche-recovery loss identifies process membership

Define the final estimator before opening fresh validation truth.

For process `p`:

1. retain only candidates passing the frozen prediction-adequacy gate;
2. within each of five predeclared sampling/background perturbations, compare the best held-out Schoener-D niche overlap among candidates carrying `p` with the best overlap among candidates excluding every declared representation of `p`;
3. normalize this overlap loss by the overlap range among all adequate candidates;
4. average across perturbations;
5. classify process membership with thresholds frozen from discovery seeds 4201–4205 only.

Frozen thresholds:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

Fresh validation, seeds 4301–4305, n=35:

- counterfactual exact process sets: **30/35 = 85.7%**;
- old stable core: **23/35 = 65.7%**;
- AUC winner: **25/35 = 71.4%**;
- exact counterfactual recovery when ecological models disagreed: **15/18 = 83.3%**;
- every preregistered exact-set and per-process sensitivity/specificity gate passed.

Unchanged independent replication, seeds 4401–4410, n=70:

- counterfactual exact process sets: **65/70 = 92.9%**;
- AUC winner: **56/70 = 80.0%**;
- predecessor stable core: **49/70 = 70.0%**;
- exact counterfactual recovery under ecological-model disagreement: **27/30 = 90.0%**;
- temperature sensitivity/specificity: **1.000 / 0.933**;
- water sensitivity/specificity: **1.000 / 0.933**;
- soil sensitivity/specificity: **0.975 / 1.000**;
- paired exact sets versus AUC: both exact 51, counterfactual-only 14, AUC-only 5, both wrong 0.

This is the principal quantitative result.

### R6. Fresh empirical occurrence data bound external validity

Use v2.8.4 without rescue.

Main sentence:

> The full fresh plant denominator was evaluable, but strict ecological improvement occurred in 0/3 preregistered parts and ecological/AUC roles selected identical candidates and predictor sets in 108/108 matched cells; empirical superiority was therefore not supported and literal real-data process truth remained unavailable.

## Discussion spine

### D1. The final method arose by falsifying simpler estimands

The project did not merely reframe a failed tuner. It successively falsified:

- predictive winner identity as process truth;
- stable surface recovery as process truth;
- agreement among ecologically good models as necessity;
- consensus-first stable intersection as a sufficiently general process-membership classifier under independently varying process presence.

The final counterfactual estimator directly tests process information by removing it from the adequate candidate class.

### D2. Prediction metrics remain useful

AUC, CBI/Boyce, OR10 and AICc retain valid roles in prediction/model evaluation. Product A uses prediction as an adequacy gate. The claim is not that AUC is invalid, but that predictive winner identity is a different estimand from ecological process membership.

### D3. Counterfactual process membership is not causal necessity

The final estimator is relative to the declared process representation registry and candidate class. Temperature exclusion includes `temp_proxy` through the frozen alias registry, but the paper does not claim closure over every possible real-world proxy or composite.

### D4. Necessity remains a separate stronger question

v2.6 asks whether adequate explanation survives a process knockout and permits broad/unresolved sets. The final counterfactual classifier asks whether exclusion causes enough loss of ecological recovery to support process membership. Do not collapse these into one certainty scale.

### D5. Error structure is part of the result

In the 70-case replication, the five counterfactual exact-set errors were concentrated in simple/saturated edges:

- `{temperature}`: 8/10 exact;
- `{water}`: 8/10 exact;
- `{temperature,water,soil}`: 9/10 exact;
- `{soil}`, `{temperature,water}`, `{temperature,soil}`, `{water,soil}`: 10/10 exact.

Thus 92.9% is not a universal perfect classifier.

### D6. Model non-uniqueness need not destroy process identification

Ecological models disagreed in 30/70 replication cases, yet counterfactual process sets were exact in 27/30. The inferential object can therefore remain stable even when exact fitted-model identity is not.

### D7. Empirical plant data remain an external-validity boundary

The controlled-truth estimator is now strongly validated, but fresh occurrence data provide no literal generating-process labels and no realized selector contrast. The 108/108 empirical collapse must remain visible rather than being treated as confirmation.

## Manuscript title

**Counterfactual niche recovery identifies environmental processes beyond model selection**

## Abstract logic

1. prediction and ecological interpretation are distinct;
2. earlier winner/set/stability approaches are prospectively falsified;
3. factorial independent process variation falsifies the predecessor at 22/35 exact;
4. define process-specific counterfactual niche-recovery loss;
5. fresh validation reaches 30/35 exact;
6. unchanged independent replication reaches 65/70 exact, with high T/W/S sensitivity and specificity;
7. empirical plant endpoint remains non-supported/observationally equivalent;
8. conclude that process membership can be estimated beyond model identity under a declared representation system.

## Figure order

1. **Identification logic** — prediction, necessity, stability and counterfactual process membership.
2. **False necessity** — why good-model agreement is insufficient.
3. **Counterfactual process recovery** — 35-case fresh validation, 70-case unchanged replication, process sensitivity/specificity and seven process-set results.
4. **Fresh empirical boundary** — 108/108 selector identity, strict improvement 0/3, `not_promoted`.

## Non-negotiable wording boundaries

Do not write:

- “SDMR outperforms AUC on empirical plants.”
- “AUC is an invalid SDM metric.”
- “65/70 proves causal environmental drivers.”
- “Counterfactual process membership equals fundamental-niche necessity.”
- “v2.8.4 validates the counterfactual estimator empirically.”
- “The process registry excludes every possible proxy.”
- “The predecessor 55/60 remains the final primary result.”

Do write:

- “the predecessor failed a stronger factorial process-presence test at 22/35 exact”;
- “the counterfactual estimator passed fresh validation at 30/35 exact”;
- “the unchanged estimator independently replicated at 65/70 exact”;
- “process membership is defined relative to the declared candidate/process representation registry”;
- “fresh empirical strict advantage over AUC remained not supported.”
