# SDMR fresh empirical v3 — terminal feature-failure diagnosis

Fresh empirical v3 remains **terminal unavailable** at the 46-predictor feature gate.

## What failed

The prospectively selected final cohort contained 50 taxa. After all 46 frozen predictors were decoded:

- **48/50 taxa passed** the complete-case gate;
- *Luzula arcuata* and *Micranthes foliolosa* failed;
- answer-check access remained **false**;
- model fitting remained **false**;
- there was no taxon replacement, predictor deletion, threshold relaxation or new decoding rule.

## Why they failed

The diagnostic-only audit shows that the dominant missingness was **not SoilGrids**.

For *Luzula arcuata*:

- gdd10: **64.3%** missing in model-pool rows;
- ngd10: **64.3%**;
- gdgfgd10: **64.3%**;
- gst / fgd / gsl / lgd: each **20.7%**;
- largest SoilGrids missing fraction: only **2.4%**.

For *Micranthes foliolosa*:

- gdd10: **64.5%**;
- ngd10: **64.5%**;
- gdgfgd10: **64.5%**;
- gst / fgd / gsl / lgd: each **16.7%**;
- largest SoilGrids missing fraction: **8.1%**.

Thus the v3 design correctly solved the predecessor's SoilGrids-availability bottleneck, but exposed a second boundary: cold-range taxa can have extensive missingness in derived CHELSA growing-degree / growing-season variables even when base bioclimatic layers are complete.

## Scientific status

This is an **availability / identifiability result**, not evidence against the M5 method.

The M5 prospective known-truth result remains unchanged.

Fresh empirical v3 is not repaired or reopened.

## Future-design implication

A genuinely new empirical successor would need one of two prospectively justified designs:

1. pre-screen support for the **entire frozen predictor universe** before final taxon selection; or
2. define a new predictor universe before candidate selection that does not require structurally undefined cold-threshold variables.

Either route would be a new programme, not a v3 rescue.

## Provenance

Feature-gate run: 37128999833  
Feature artifact: 11278021879  
Diagnostic-only audit run: 37251666841  
Audit artifact: 11321360870
