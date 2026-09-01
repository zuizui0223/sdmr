# Four-chapter research program

Program ID: `niche-to-survey-four-chapter-v1`

This document fixes the chapter order and scientific division of labor across four repositories. The chapter numbers are not interchangeable.

| Chapter | Repository | Scientific role | Core question | Primary output |
|---|---|---|---|---|
| **1** | `zuizui0223/sdmr` | environmental niche-driver selection | **Which environmental dimensions most defensibly define a species' realized environmental niche?** | interpretable predictor/process set and niche representation |
| **2** | `zuizui0223/odsp` | multidimensional niche geometry | **How much niche structure is hidden when occurrence/support is projected onto a flat x-y map?** | niche thickness, axis-specific information, projection-loss diagnostics |
| **3** | `zuizui0223/eog` | distributional worlds and reachability | **Given supported local states, which distributional/transition worlds remain compatible with evidence, and what states are reachable?** | possible/robust/unresolved world support and forecasts |
| **4** | `zuizui0223/acsp` | survey action | **Where should field effort be directed next?** | bounded candidate survey patches / survey priorities |

## Chapter 1 — SDMR: recover interpretable environmental niche drivers

SDMR is not positioned as a generic model-accuracy contest. Its central object is the **environmental variable set used to interpret the niche**.

The occurrence evidence is deliberately divided into two roles:

1. **model pool** — available for fitting and environmental-variable/model-choice decisions;
2. **sealed answer-check pool** — hidden from those decisions and opened only after the niche representation is frozen.

Background/reference environments are required to fit and project relative suitability, but they are **not the biological answer key**. The answer-check is whether the frozen environmental representation reconstructs the environmental distribution occupied by previously unseen occurrences.

The target is therefore closer to `niche-driver recovery` than to maximizing AUC. Ordinary predictive performance remains a safety/adequacy guardrail. Known-truth simulation is the only lane where literal generating drivers and a literal generating niche are known; empirical data support claims about realized environmental niche representation, not fundamental-niche truth.

### Fixed Chapter-1 goal

Develop and communicate a leakage-resistant, interpretable procedure for choosing environmental dimensions of a realized niche, with a clean distinction between fitting evidence and answer-check evidence.

### Current boundary

The completed Product-A endpoint and separate decision remain authoritative. No new Product-A experiment, taxa/M/seed/fraction/threshold/candidate retuning, or Product-B activation is authorized by this chapter map. Chapter-1 implementation work is limited to manuscript/positioning, reusable interfaces, and documentation that do not reinterpret the frozen result.

## Chapter 2 — ODSP: measure niche thickness and dimensionality

ODSP asks what a flat distribution/niche map loses. A conventional map represents support as `S(x,y)`, but organisms can occupy states indexed by additional axes such as vertical stratum/depth `z`, observation/activity time `t`, and structural microhabitat.

The central object is therefore an axis-resolved support distribution such as:

```text
S(x, y, z, t, ...)
```

and the information lost by projecting it to `x,y`.

Key targets include:

- vertical niche thickness: information/effective states in `z` conditional on `x,y`;
- temporal niche thickness: information/effective states in `t` conditional on `x,y`;
- joint thickness: extra information in `z × t` beyond the planar projection;
- habitat structural capacity: how many distinguishable ecological states a horizontal cell can contain;
- projection loss: cases where two taxa or two habitats look similar in 2D but differ strongly in added axes.

Forest-canopy systems are a motivating case: equal horizontal area need not contain equal ecological state space. A vertically layered forest may carry more niche-support states than a structurally simple grassland even when their x-y footprint is identical.

## Chapter 3 — EOG: infer compatible distributional worlds

EOG begins after local support/possibility has been declared. It does not decide which environmental variables define the niche. It asks how local support, current positive evidence, and declared transition/barrier rules combine into a finite set of compatible distributional worlds.

Its products are world compatibility, reachability, robust/possible/unresolved states, sequential contraction/falsification, and forecasts under retained worlds.

## Chapter 4 — ACSP: convert knowledge into survey action

ACSP is the action layer. It identifies bounded candidate patches or survey priorities rather than estimating a niche or a historical route. The validated Japanese product remains a candidate-patch generator; route, budget and exact occupancy claims remain outside its validated boundary.

## Interface principle

The chapters may exchange products without becoming one mandatory pipeline:

```text
occurrence evidence
      │
      ├── Chapter 1 / SDMR: which environmental axes define the niche?
      ├── Chapter 2 / ODSP: how thick/multidimensional is the niche state space?
      └──────────────┬─────────────────────────────
                     ▼
          Chapter 3 / EOG: which distributional worlds are possible/reachable?
                     ▼
          Chapter 4 / ACSP: where should we survey next?
```

Each chapter must retain its own estimand and validation boundary. A downstream result may not retroactively tune an upstream scientific decision.
