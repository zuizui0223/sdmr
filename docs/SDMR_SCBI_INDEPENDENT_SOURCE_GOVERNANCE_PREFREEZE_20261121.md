# SCBI ForestGEO: independent-forest source governance admission v1

**Freeze: 2026-11-21. Source metadata only, zero original tree/stem rows opened.** This is an independent physical forest from Harvard HF453, but NOT an independent biological process test yet.

## Why this source and what we can really validate

The Smithsonian Conservation Biology Institute (SCBI) 25.6 ha Forest Dynamics Plot in Virginia has published public *copies* of original repeated census stem tables:

| Census period | Pinned public copy (SCBI-ForestGEO-Data) | Git file size | Git blob SHA-1 (NOT raw SHA-256) |
| --- | --- | ---: | --- |
| 2008–2010 | \`scbi.stem1.csv\` | 5,927,551 | \`75006d1cf423d6f0783c23bb73fd07adc999892f\` |
| 2013 | \`scbi.stem2.csv\` | 6,219,513 | \`2f3f9408e912d1b35d7cfec73470116515f7ef99\` |
| 2018 | \`scbi.stem3.csv\` | 6,598,542 | \`10982d2ffcca5b55535b19272ba611ce5f86cab6\` |
| 2023 | separate \`SCBI-ForestGEO/2023census\` published **release tag 2024.05**, \`processed_data/scbi.stem4.csv\` | 35,463,140 | \`cbaa4d92fb4588788895cc95f3542c9de1f80f32\` |

The earlier public-copy Git tree is frozen at full commit \`9c6437afed3da292741840ab5ce327a4b54eff98\`. The 2023 published \`2024.05\` release is frozen at **tag commit** \`6ac8718dcab0c5c653c56d55a1e093a6c20150e2\` (released 2024-05-14, [Zenodo DOI 10.5281/zenodo.11192302](https://doi.org/10.5281/zenodo.11192302)). This is **not** mutable 2026 \`main\`.

The values above were obtained from the publicly accessible **Git tree metadata**, with **no CSV header/row opening**. A **Git blob SHA-1** is a Git object checksum and is **not a complete original-file SHA-256**. The public-copy check does not prove the file is an approved ForestGEO master version, or that it is current, source-effort-complete, an independently sampled tree census, or permitted for this publication.

The site is **one independent physical forest** relative to Harvard, not four independent ecosystems because it was censused in four time periods.

## Scientific and collaboration rights: source availability is not research authorization

The [official SCBI ForestGEO data-request form](https://ctfs.si.edu/datarequest/index.php/request/form/9) and [Terms and Conditions](https://ctfs.si.edu/datarequest/index.php/request/terms/9) require a **data-use request**, written research and analysis plans, approved dataset version, specified collaborators, non-transferability, and inclusion of plot investigators as collaborators/coauthors unless otherwise agreed. The official [SCBI repository README](https://github.com/SCBI-ForestGEO/SCBI-ForestGEO-Data/blob/master/tree_main_census/README.md) says the GitHub files are *copies* and that the current master resides at the ForestGEO data portal; it directs prospective publication users to obtain the official version.

The separate [2023census tagged Zenodo release](https://github.com/SCBI-ForestGEO/2023census/releases/tag/2024.05) declares **CC BY 4.0** for its posted source, but public release licensing should **not be confused with having fulfilled the field project's requested collaboration, approved master version, or version citation workflow**. This repo voluntarily blocks source analysis for its intended manuscript until those protocol-use conditions are documented. This is a scientific governance decision, not legal advice on the scope of a Creative Commons license.

**Different data use family:** the [annual SCBI mortality collection](https://github.com/SCBI-ForestGEO/SCBImortality) reports CC BY 4.0 for 2014–2019 and 2021; 2020 and **2022 onward** are under a custom data-use agreement, with first-publication/coauthor obligations. This PR must **not** open those records to bypass the master-census authorization. No mortalities, species, disease status, individual tag, plot coordinates or original tree rows are opened.

## Independent biological question, explicitly blocked before admission

If SCBI original approval is obtained and a separate source-opportunity protocol is frozen, the new *independent forest* can assess whether **baseline-alive trees, future recruits, measured zero/negative statuses, deaths and not-found states** can be independently distinguished under 2013→2018 and 2018→2023 transitions, with original individual versus stem-level identifiers and physical survey opportunities audited. Census 1 (2008 label) spans **2008–2010**, so a naive five-year risk interval is not exact. No biological endpoint is preselected from the public CSV contents; original status ontology and actual census effort remain **unverified**.

**Do not directly replicate the HF453 canopy-status signal using a biased 2018 SCBI crown sample.** The public 2018 crown information derives from a cored/dendroband subset (about 989 tree records in the project README, with additional project-specific filters); this is not the complete tagged-tree opportunity frame. Even if it can be joined, it must not become a forest-wide CP exposure by assuming unmeasured crowns are random.

The correct study-unit hierarchy is source: one SCBI plot → original spatial sampling blocks/quadrats → original trees → possibly multiple stems → census occasions. Neither stem count nor spatial block count is the number of independent **forests**. A new field comparison would require proper original tree IDs, prior-only covariates, verified observed vs inferred death and unit-level attrition, missingness bounds, and new outcome-blind blocks.

## Executable source-only gate

1. Read **only immutable Git tree JSON metadata** for the two exact frozen commits listed above. No GitHub \`contents\` request, raw CSV download, stem-level data row, active Git \`main\` ref or outcome path is accepted.
2. Verify exact public-copy file paths, immutable **Git blob SHA-1 object values and object-byte sizes**, complete untruncated trees.
3. Output only **source provenance metadata**. The terminal scientific status is \`public_snapshots_Git_tree_metadata_verified_but_master_approval_pending\` even when all source Git checks pass.
4. Do not authorize publication analysis, model fitting, biological outcome opening, process identification or M5/Product A/B promotions. Any Git-source metadata inconsistency is a separate source STOP.

[Config](../configs/scbi_independent_forest_governance_prefreeze_v1.json) · [Script](../scripts/scbi_independent_source_governance_metadata_v1.py) · [Synthetic-only tests](../tests/test_scbi_independent_source_governance_metadata_v1.py).

## Request status and next external dependency

Current approved master-source version: **UNKNOWN**, not presumed the 2024.05 public release. Collaboration/data-use approval: **NOT RECORDED**. The [SCBI data request draft](SDMR_SCBI_DATA_REQUEST_DRAFT_20261121.md) prepares three fields for the official web form; it is **not submitted** and does not invent a collaborator's approval.

Original Product A remains not promoted; Product B blocked; M5 71/80 and Structural prospective synthetic 30/30 untouched; Harvard's one-forest positive but mixed score evidence unchanged. The BCI 2026 Dryad v5 source remains HTTP401 stopped. SCBI public metadata PASS does **not** count as external field validation.
