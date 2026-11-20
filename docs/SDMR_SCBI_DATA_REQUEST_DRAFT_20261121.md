# SCBI ForestGEO official master census data request — ready-to-edit draft

**Status: NOT SUBMITTED.** This document is a request draft, not scientific permission, an accepted coauthorship agreement or a source-download instruction. Complete the request only with the research PI's approved personal/institutional information and collaborators. The official SCBI request form is https://ctfs.si.edu/datarequest/index.php/request/form/9 and official terms are https://ctfs.si.edu/datarequest/index.php/request/terms/9 .

## Research project description (≤1500 characters)

Methods development in species distribution and forest ecological models (SDMR): testing whether ecological process information can be separated from prediction accuracy, observation/selection bias and nonindependent physical sampling units. Synthetic benchmarks and a previous single-forest analysis at Harvard Forest motivate a prospectively separate forest census evaluation. The proposed SCBI component will assess verifiable tree identities, census opportunities, missing/unfound states, and structural predictors using strictly pre-outcome information. The objective is to test the conditions under which methodological conclusions can transfer across forests, not to claim that canopy exposure causes mortality. SCBI data will be used only within the approved project and will not be redistributed.

## Planned analyses (≤1500 characters)

First audit the official source version, tree/stem identifiers, dates, census effort, status ontology, entrants/recruits and missing observations without examining the response comparison. Define source-verified baseline-alive risk sets for 2013→2018 and 2018→2023, distinguishing observed death from presumed death and unobserved outcomes. Specify tree-level and spatial-block holdouts before opening a new response endpoint. Compare a fixed baseline model of prior habitat/species/size information against a prespecified eligible structural-context model, including sharp missing-outcome bounds and heldout log loss/Brier guardrails. Report negative or inconclusive findings. Do not use the annually surveyed 2022+ mortality records without separate authorization. The 2018 selected crown-subsample will not be treated as forest-wide canopy coverage. Provide PI collaboration and manuscript review per SCBI terms.

## Data requested (≤1500 characters)

Please provide the approved official master versions (with version number and citable metadata) of the full SCBI ForestGEO stem/tree censuses for 2008–2010, 2013, 2018 and 2023, if available; historical and current tree/stem identifiers, original plot/quadrat coordinates, census dates, observed status and quality codes, entry/threshold rules, survey effort/coverage and attrition metadata, and prior species/diameter/structural measurements when observed. Please clarify original direct-vs-presumed death and not-found codes, whether corrections supersede public GitHub snapshots, and any separate permissions or conditions for using 2023 records. If crown-position data are available, specify whether they cover the full risk set or a selected subgroup. Please provide the required collaborator/coauthor and manuscript review process.

## Still required from the applicant

1. Authorized principal investigator name, institution, email, and collaborating investigators.
2. Confirmation of the project's exact intended use and the SCBI data-use/collaboration terms.
3. Submission through the official SCBI portal. Record the approval reference, approved master dataset version and investigator requirements before any field response analysis.

## Pre-submission scientific guardrails

The public 2018 CSV at GitHub commit `9c6437afed3da292741840ab5ce327a4b54eff98` and the published 2023census tag `2024.05` (commit `6ac8718dcab0c5c653c56d55a1e093a6c20150e2`) are **not treated as approved ForestGEO masters**. Git blob SHA-1 and sizes are metadata, not original SHA-256. No raw original tree responses have been opened in this SCBI workflow.

The 2018 crown survey is selected from the cored/dendroband cohort. Any analysis must avoid presenting it as a representative 25.6-ha baseline exposure. HF453 initial effects and Product A/M5 remain frozen, Product B blocked.
