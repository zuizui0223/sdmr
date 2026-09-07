# Product A final claim spine

Status: **authoritative manuscript logic after factorial falsification, fresh counterfactual validation, unchanged independent replication, and completed frozen real positive-control audit**

## One-sentence claim

**Product A identifies environmental-process membership under controlled truth by measuring the ecological recovery lost when every declared representation of a process is excluded: with temperature, water and soil varied independently, the frozen estimator recovered 65/70 complete generating-process sets in an unchanged independent replication, versus 56/70 for AUC-selected winners; prospectively frozen real positive controls did not support general empirical process identification.**

## What Product A now solves

Product A began as a model-selection problem: choose a complete occurrence-only SDM procedure that predicts withheld records and transfers to unseen taxa. Development showed that this was not the right ecological estimand. Prediction, response stability and model agreement can all coexist with incorrect environmental-process attribution.

The final controlled-truth solution therefore does **not** infer a process from the identity of a winning fitted model. It asks a counterfactual question:

> **How much of the best attainable held-out ecological niche recovery disappears when every declared representation of this process is forbidden, among models that remain prediction-adequate?**

This turns process membership into an explicit process-specific estimand. The empirical audit separately tests whether the present occurrence-data implementation and representation registry can recover externally supported processes in real systems.

## Result 1 — Prediction and selected-model identity were insufficient

Earlier controlled-truth tests established three failures.

1. Predictive transfer and stable environmental response surfaces could coexist with wrong generating-process attribution.
2. Restricting interpretation to ecologically better-recovery models could sharpen the retained model set while losing truth coverage and creating false necessary-process claims.
3. A consensus-first `stable_process_core` could recover process information more reliably than exact model identity in the original six-family suite, but that suite did not vary all major process identities independently.

The original v2.7.2 proof-of-concept returned exact stable process sets in **55/60** unused cases versus **50/60** for the AUC-selected fitted candidate, including **19/22** exact process sets when the two ecological selectors chose different fitted models. However, temperature and water were generating processes in all 60 cases; only soil varied in presence. The pooled v2.7.2 precision/recall values therefore could not establish general presence-versus-absence identification for all three processes.

## Result 2 — A stronger factorial truth test falsified the predecessor

To test actual process membership rather than retention of invariant processes, the complete non-empty process-set universe was prospectively frozen as:

`{temperature}`, `{water}`, `{soil}`, `{temperature,water}`, `{temperature,soil}`, `{water,soil}`, `{temperature,water,soil}`.

Discovery seeds `4201`–`4205` generated **35 cases**. Candidate library, process aliases, perturbations, simulation sizes and denominator were fixed before outcome.

The predecessor stable-core rule failed this stronger test:

- exact complete process-set recovery: **22/35 = 62.9%**;
- AUC-selected winner: **25/35 = 71.4%**;
- exact stable truth under ecological-model disagreement: **12/20 = 60.0%**;
- temperature sensitivity/specificity: **1.00 / 0.667**;
- water sensitivity/specificity: **0.70 / 0.867**;
- soil sensitivity/specificity: **1.00 / 0.867**.

This non-support is retained. The earlier `55/60` result is no longer the primary process-identification headline.

## Result 3 — Counterfactual ecological-recovery loss solved the tested identification problem

For process `p`, Product A now compares prediction-adequate models that carry `p` with prediction-adequate models that exclude **every declared representation** of `p`.

For each of five predeclared sampling/background perturbations:

1. impose the existing prediction-adequacy gate: mean presence-background rank ≥0.51 and mean−SEM ≥0.50;
2. find the best held-out Schoener-D niche overlap among adequate candidates containing `p`;
3. find the best held-out Schoener-D niche overlap among adequate candidates excluding `p` and all aliases/proxies in the frozen registry;
4. normalize their difference by the overlap range among adequate candidates;
5. average the normalized gap across perturbations.

For ordinary comparable perturbations:

`g_pq = (best D containing p − best D excluding p) / range(D among adequate candidates)`.

The score contains no hidden process truth. Hidden truth was used only in the `4201`–`4205` discovery lane to freeze one threshold per process.

Frozen thresholds were:

- temperature: **0.2653964368**;
- water: **0.0671670999**;
- soil: **0.3342415841**.

No threshold, candidate, perturbation, process set or seed was changed after fresh validation was opened.

## Result 4 — Fresh 35-case validation passed every predeclared gate

Unused seeds `4301`–`4305` were evaluated across the same seven process sets (`n=35`). The primary gate required:

- full 35/35 denominator;
- exact process-set recovery ≥0.80;
- sensitivity ≥0.80 for each of temperature, water and soil;
- specificity ≥0.80 for each process.

**All gates passed.**

- counterfactual exact process-set recovery: **30/35 = 85.7%**;
- predecessor stable core: **23/35 = 65.7%**;
- AUC-selected winner: **25/35 = 71.4%**;
- ecological fitted models disagreed in 18 cases; counterfactual process truth remained exact in **15/18 = 83.3%**.

Per-process counterfactual identification:

- temperature: sensitivity **1.000**, specificity **0.933**;
- water: sensitivity **1.000**, specificity **0.800**;
- soil: sensitivity **1.000**, specificity **0.933**.

Paired exact-set counts versus AUC were 24 both exact, 6 counterfactual-only exact, 1 AUC-only exact and 4 both wrong.

Authoritative validation: workflow `34015684015`, artifact `9983844728`, digest `sha256:9a53abc38c45e93eb8696f1de7af5051776881c59ec5079f45b4ecc029068554`.

## Result 5 — Unchanged 70-case replication strengthened the result

After the 35-case validation, the method and all thresholds were frozen unchanged. New seeds `4401`–`4410` were prospectively declared across the same seven process sets, yielding **70 independent replication cases**.

**All replication support gates passed.**

### Complete process-set recovery

- counterfactual estimator: **65/70 = 92.9%**;
- AUC-selected winner: **56/70 = 80.0%**;
- predecessor stable core: **49/70 = 70.0%**.

### Process-specific classification

Temperature (`40` true, `30` false):

- TP=40, FN=0, TN=28, FP=2;
- sensitivity **1.000**;
- specificity **0.933**.

Water (`40` true, `30` false):

- TP=40, FN=0, TN=28, FP=2;
- sensitivity **1.000**;
- specificity **0.933**.

Soil (`40` true, `30` false):

- TP=39, FN=1, TN=30, FP=0;
- sensitivity **0.975**;
- specificity **1.000**.

### Recovery despite model ambiguity

Canonical and robust ecological selectors chose different fitted candidates in **30/70** replication cases. Counterfactual process membership nevertheless exactly matched the complete generating-process set in **27/30 = 90.0%**.

### Paired outcome against AUC

- both exact: **51**;
- counterfactual only exact: **14**;
- AUC only exact: **5**;
- both wrong: **0**.

This paired result is descriptive; the preregistered replication gate concerned absolute exact-set recovery and process-specific sensitivity/specificity, not a universal superiority test against AUC.

### Failure envelope

Only five of 70 replication cases were not exact:

- `{temperature}`: two cases falsely added water;
- `{water}`: two cases falsely added temperature;
- `{temperature,water,soil}`: one case missed soil.

Exact recovery by process set was `{T}` 8/10, `{W}` 8/10, `{S}` 10/10, `{T,W}` 10/10, `{T,S}` 10/10, `{W,S}` 10/10 and `{T,W,S}` 9/10.

Authoritative replication: workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

## Result 6 — Observation-process separation remains a concrete mechanism result

The earlier observation-confounded suite remains relevant mechanistically. Hidden ecological truth was `{temperature,water}` in all 10 cases while `recording_bias` altered record detectability.

AUC selected `observer_only` in **5/10**, yielding driver-process precision, recall and F1 of **0.0** in those five cases. Product A's ecological/observation separation selected `niche_plus_observer` in **10/10** and recovered `{temperature,water}` in **10/10**.

This result is not the main process-membership performance estimate after the new factorial work, but it shows why record prediction can choose the wrong explanatory object.

## Result 7 — Necessity remains a separate falsification problem

The v2.4–v2.6 process-exclusion certificate addresses a stronger question than process membership: whether a process is required under a frozen evidence contract.

In v2.6:

- false-required processes = **0**;
- possible-process recall = **1.0**;
- possible-process precision ≈ **0.467**;
- `required_processes` was empty in **9/9** validation taxa.

Thus v2.6 is a false-necessity safety result, not the source of the 92.9% process-membership recovery result. Counterfactual process membership and exclusion-based necessity must remain distinct estimands.

## Result 8 — Frozen real positive controls did not validate general empirical process identification

The earlier v2.8.4 empirical endpoint remains `empirical_confirmation_not_supported` / `not_promoted`, with ecological and AUC roles selecting the same candidate and predictor set in **108/108** matched taxon × accessible-area × seed cells.

A later prospectively frozen positive-control test supplied an actual one-sided biological answer key for eight real taxa. Its unchanged historical rule required all three 150/300/500-km M scores, expected-process mean >0, at least two positive M scores, and within each four-taxon lane at least three recovered taxa plus recovery in both temperature and water groups.

The frozen outcomes were:

- **plants: 2/4 recovered** — temperature 2/2, water 0/2;
- **nonplants: 1/4 recovered** — temperature 1/2, water 0/2;
- both lanes therefore failed the original support gates;
- the combined **3/8** is descriptive only and is not an accuracy estimate or new pooled endpoint.

This was not simply a failed execution. All **24/24 taxon × M pipelines** completed technically, but only **21/24** contained at least one prediction-adequate candidate. Bombus/150 km, Plethodon/500 km and Cepaea/300 km had empty adequate-model classes. Water also failed where all three M comparisons existed: Quercus had mean expected-process score **−0.276692**, and Silene ciliata **−0.000704**.

The positive controls constrain sensitivity-like recovery only. They provide no negative labels or complete generating-process sets, so they cannot establish specificity or complete process identification; an always-positive rule would recover every positive control. The implemented endpoint also scored process recovery using **model-pool inner spatial CV**, not an invoked outer-sealed transfer evaluation. Thus it is independent literature-backed checking of inner-CV process scores, not a demonstrated outer-transfer result.

The correct empirical conclusion is therefore **non-support of general real-data process identification by the current estimator/representation system**, not proof that the externally supported processes are biologically absent and not proof that the counterfactual estimand is invalid. The observed bottlenecks are adequate-alternative availability, water-process representation/recovery, incomplete requested fold support in one plant cell, and the lack of a two-sided empirical truth set.

The eight external labels are now consumed. Any empirical successor learned from these outcomes requires a newly frozen biological validation set.

## Final synthesis

The final Product-A sequence is now:

`predictive winner`  
→ falsified as ecological identifier  
`agreement among good models`  
→ falsified as necessity and then falsified under independently varying process truth  
`process-specific counterfactual ecological-recovery loss`  
→ **30/35 fresh validation exact, then 65/70 unchanged independent replication exact under controlled truth**  
`frozen real positive controls`  
→ **2/4 plant and 1/4 nonplant recovery; general empirical validation not supported**.

The method separates five objects:

1. **predictive adequacy** — can candidate models recover withheld records?
2. **process membership under controlled truth** — does excluding every declared representation of a process materially reduce attainable ecological recovery?
3. **process necessity** — does any adequate explanation survive process exclusion under the stronger necessity contract?
4. **empirical process recovery** — does the frozen occurrence-data implementation recover externally supported real processes without changing the rule after outcome?
5. **unresolved / empirical non-identification** — when evidence, representation closure or realized adequate alternatives are insufficient, which claims must remain open?

## Claim boundary

The supported headline is:

> **Counterfactual ecological-recovery loss identified complete generating-process sets in 65/70 independent controlled-truth replication cases, with sensitivity 0.975–1.000 and specificity 0.933–1.000 across independently varying temperature, water and soil. Prospectively frozen real positive controls did not support general empirical process identification with the current occurrence-data implementation.**

The paper does **not** claim:

- physiological or causal necessity;
- recovery of a fundamental niche;
- complete closure over every real-world proxy/composite representation;
- direct generating-process validation in real occurrence data;
- empirical specificity from positive-only controls;
- demonstrated outer spatial-transfer process recovery in the v1 real-control endpoint;
- universal superiority over AUC from a post hoc paired comparison;
- that the earlier v2.7.2 `55/60` result is the final estimator's validation.

The old `55/60` stable-core result is predecessor evidence. The primary positive result is the prospectively frozen controlled-truth counterfactual validation and unchanged 70-case replication. The empirical result is a separate, retained non-support boundary rather than an attempted rescue.
