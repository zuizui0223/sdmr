# Product-A novelty boundary

## What SDMR does **not** claim

Product A does **not** claim to invent model transferability, spatially structured
cross-validation, AUC, Boyce/CBI, MaxEnt/SDM tuning, or the idea that model
complexity/background choice can affect transferability.

Relevant prior work already establishes those points:

- Wenger & Olden (2012, *Methods in Ecology and Evolution*, DOI
  `10.1111/j.2041-210X.2011.00170.x`) explicitly proposed non-random
  cross-validation as a transferability assessment and noted that it can be used
  for both validation and model selection.
- Hirzel et al. (2006, *Ecological Modelling*, DOI
  `10.1016/j.ecolmodel.2006.05.017`) developed the continuous Boyce index as a
  threshold-independent presence-only evaluator.
- ENMeval 2.0 (Kass et al. 2021, *Methods in Ecology and Evolution*, DOI
  `10.1111/2041-210X.13628`) supports reproducible niche-model tuning and
  recommends spatial cross-validation or fully withheld geographic data when
  transfer is the objective.
- Sequeira et al. (2018, *Methods in Ecology and Evolution*, DOI
  `10.1111/2041-210X.12998`) reviews transfer across location, time and taxon and
  emphasizes that internal model fit need not imply transferability.

Accordingly, a final SDMR paper must not use wording such as "first transferability
assessment" or "AUC/CBI replacement".

## Candidate methodological contribution to test

The contribution being tested is the **selection target and information barrier**:

1. admit and deterministically thin focal occurrences;
2. assign whole spatial blocks to model vs outer-sealed roles **before** M or
   target-group background is constructed;
3. prevent sealed focal taxa/locations from returning through the background;
4. tune candidate environmental universes, variable-selection strategies and
   model complexity only inside the model pool;
5. treat multiple plausible M definitions as a sensitivity set rather than
   choosing the M that gives the easiest evaluation score;
6. select one `environmental universe × tuning strategy` from discovery taxa;
7. test the frozen procedure on unseen taxa and the same preassigned outer
   sealed cases;
8. compare directly against canonical-M AUC/Boyce selection and a strong
   per-species nested-spatial-CV AUC selector;
9. require repeated seed/holdout stability before promotion;
10. only after Product A is promoted, freeze that procedure for Product B's
    cross-species search for transferable environmental drivers.

Thus the object being evaluated is not merely a fitted SDM but a **model-building
procedure that is required to survive space, M/background assumptions and taxa**.

## Falsification boundary

The project is not committed to SDMR winning.

- If `sdmr_m_robust` repeatedly beats canonical AUC/Boyce and local nested AUC on
  identical unseen taxon × M × outer-sealed cases, the evidence supports a
  procedure-level transfer advantage.
- If it is stable but not better, Product A may still provide a reproducible
  protocol but cannot claim superior predictive selection.
- If it is unstable or inferior, the result is that species-specific/nested
  tuning remains preferable for this corpus; Product B must not inherit a
  universal SDMR recipe.

## Why AUC/CBI remain useful

AUC-equivalent ranking and Boyce/CBI are model-evaluation statistics. SDMR's
candidate distinction is orthogonal: **which information may be used to choose a
model-building procedure, and across which distribution shifts must that
procedure remain useful?**

The same outer-sealed evidence can therefore report AUC-equivalent performance,
binned Boyce and continuous Boyce. A difference in metric name is not itself an
SDMR contribution.
