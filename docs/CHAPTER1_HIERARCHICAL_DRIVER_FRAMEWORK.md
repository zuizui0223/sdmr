# Chapter 1 hierarchical niche-driver framework

Status: **interpretation and future-method design only**. This document does not reopen or retune the completed Product-A endpoint.

Chapter 1 / SDMR asks which environmental dimensions most defensibly define a species' realized environmental niche. The preferred interpretation is hierarchical rather than a flat competition among every available raster.

## Why a hierarchy is needed

Environmental predictors do not all have the same scientific role. Elevation, temperature, growing-degree days and a BIOCLIM summary may be strongly associated because they represent different stages or compressions of the same ecological system. Throwing all of them into one undifferentiated selector can preserve prediction while obscuring what has actually been learned.

The Chapter-1 interpretation therefore separates **process selection** from **representation selection**:

```text
which process/domain matters?
        ↓
which observable representation of that process generalizes best?
```

A selected raster is not automatically a causal driver. It is evidence for a declared process only within its recorded representation role and validation boundary.

## Representation hierarchy

### Level 1 — geophysical template

Relatively persistent properties of place that structure downstream environmental fields:

- elevation;
- slope;
- aspect;
- terrain roughness / topographic position;
- geology;
- soil/substrate properties.

These can have direct biological relevance, but often also act as proxies for multiple downstream conditions.

### Level 2 — direct environmental fields

Environmental states or fluxes experienced more directly by organisms:

- temperature;
- precipitation / moisture;
- radiation;
- humidity;
- wind;
- other directly measured climatic fields.

### Level 3 — integrated biological exposure

Derived variables that integrate environmental fields into biologically interpretable exposures:

- growing-degree days;
- VPD;
- PET;
- climatic moisture index / water balance;
- snow duration or snow load summaries;
- growing-season duration;
- productivity.

### Level 4 — composite summary representation

Compressed summaries that can be useful predictors but may mix several lower-level processes:

- BIOCLIM variables;
- climate principal components;
- composite climatic or ecological indices.

The levels describe representation structure, not a ranking of biological importance.

## Predictor-role tags

Future Chapter-1 candidate registries should be able to label a predictor with one or more explicit roles:

- `spatial_geometry` — physical geometry/topography of place;
- `substrate` — soil/geology/material environment;
- `direct_environment` — measured environmental state or flux;
- `derived_exposure` — biologically integrated derivative of environmental fields;
- `proxy` — variable retained primarily as a proxy for one or more processes;
- `composite_summary` — intentionally compressed multi-condition representation.

A proxy may be useful and reproducible without being interpreted as the underlying mechanism.

## Chapter-1 selection logic

A future hierarchy-aware method should preserve the current information-barrier principle:

1. **model pool occurrences** are available for process and representation selection;
2. the candidate process registry and representation roles are fixed before answer-check access;
3. process/domain support is evaluated before choosing a preferred representation within a supported process;
4. a selected representation is frozen;
5. **sealed answer-check occurrences** evaluate whether the frozen representation reconstructs the realized environmental niche of unseen occurrences;
6. background/reference environments support fitting and projection but are not the biological answer key.

Ordinary predictive performance remains an adequacy/guardrail layer rather than the sole ecological interpretation target.

## Example

A flat selector might report that elevation, BIO5 and GDD are interchangeable predictors. The hierarchical interpretation instead asks:

```text
thermal / energy process required?
    ├─ elevation        [proxy / spatial geometry]
    ├─ BIO5             [direct/composite temperature representation]
    └─ GDD              [derived biological exposure]
```

The scientific result can then be phrased as, for example, “thermal information generalizes, and GDD is the most transferable tested representation,” rather than claiming that one correlated raster is necessarily the causal driver.

## Boundary with Chapter 2 / ODSP

Elevation is normally one value attached to an x-y surface cell. It belongs here as geophysical template/proxy information.

ODSP's vertical `z` axis is different: it represents **multiple ecological states inside the same horizontal location**, such as forest floor, herb layer, shrub layer, understory and canopy, or multiple water/soil depths. Chapter 1 chooses environmental dimensions; Chapter 2 asks how many spatial/temporal niche states are hidden by a planar projection.

## Frozen Product-A boundary

The completed Product-A v2.8.4 empirical decision remains `empirical_confirmation_not_supported`, with the separate decision `not_promoted` and Product B blocked. This hierarchy is **not** a post-outcome rescue, reanalysis, retuning or reinterpretation of that endpoint. It is the fixed conceptual architecture for Chapter-1 manuscript framing and any genuinely new future method that would require a new prospective contract and independent evidence.
