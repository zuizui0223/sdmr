# Product A Nature submission package index

Status: **scientific and reporting package complete on current manuscript branch; Product-A endpoints unchanged**

Target: **Nature Ecology & Evolution — Article**

Authoritative scientific logic: `docs/product_a_final_claim_spine.md`

## Core manuscript files

- `docs/product_a_nature_ecology_evolution_article_draft.md` — Nature Article draft.
- `docs/product_a_nature_online_methods.md` — Online Methods.
- `docs/product_a_nature_cover_letter.md` — cover-letter draft.
- `docs/product_a_nature_figure_legends.md` — main-figure legends.
- `docs/product_a_nature_extended_data_plan.md` — Extended Data structure.

## Claim and novelty controls

- `docs/product_a_final_claim_spine.md` — authoritative manuscript logic.
- `docs/product_a_nature_claim_audit.md` — claim ceiling and forbidden overreach.
- `docs/product_a_nature_logic_consistency_audit.md` — separation of exclusion-based necessity and consensus-first process stability.
- `docs/product_a_nature_novelty_audit.md` — novelty boundary against prediction/explanation, functional accuracy, variable importance and Rashomon prior art.
- `docs/product_a_nature_reference_boundary.md` — verified reference positioning.

## Main scientific spine

1. Predictive adequacy and stable response surfaces do not guarantee correct process attribution.
2. Agreement among performance-filtered ecological models can create false necessity.
3. Exclusion-based necessity (v2.4–v2.6) controlled false-required claims under known truth while retaining broad identified sets.
4. Consensus-first process stability (v2.7.2), a separate estimand, showed that process information can remain highly stable without unique fitted-model identity.
5. Fresh empirical v2.8.4 remained `empirical_confirmation_not_supported` / `not_promoted`; ecological and AUC selectors collapsed to the same realized candidate and predictor set in 108/108 matched cells.

The v2.7.2 P=0.9889 / R=0.9833 values are **not** process-exclusion necessity-estimator performance.

## Reporting and reproducibility

- `.github/workflows/nature_product_a_reporting.yml` — rebuilds reporting figures and source data from frozen artifacts.
- `scripts/build_nature_product_a_figures.py` — reproducible main-figure generation.
- `scripts/check_nature_product_a_manuscript.py` — fail-closed Nature-format and claim QA.
- `docs/product_a_nature_reporting_summary_draft.md` — reporting-summary draft.
- `docs/product_a_nature_software_checklist_draft.md` — software-checklist draft.
- `docs/product_a_nature_data_code_availability.md` — Data/Code Availability draft.
- `CITATION.cff` — citation metadata.

## Source-data files

- `docs/nature_source_data_fig2.csv`
- `docs/nature_source_data_fig3.csv`
- `docs/nature_source_data_fig4.csv`
- `docs/nature_source_data_fig4_parts.csv`
- key Extended Data source-data CSVs recorded in the Extended Data plan.

## Validated scientific/reporting state

Validated manuscript/reporting state: `ebfcd4a48c2ec20cb1a7fde223db2dba64bb363f`

All submission-facing validation succeeded on that state:

- Nature Product-A reporting figures — **success** (run 33851979388).
- Standard repository tests — **success** across Python 3.10, 3.11, 3.12, 3.13 and geo-rasterio (run 33851979406).
- Real GBIF × CHELSA API diagnostic smoke — **success** (run 33851979385).

The Nature Article QA records abstract 194 words and main text 2,121 words.

Subsequent commits `027be15208bd8ee30e037e167d16a993aed50027` and this index-only update modify submission metadata/index text only; they do not alter scientific code, frozen endpoints, manuscript claims, or figure source data.

## Scientific hard stop

No new Product-A scientific experiment is required or permitted by this submission package. Do not rerun, retune, change taxa, candidate libraries, M values, thresholds, denominators or frozen endpoints to improve publication outcome. Product B remains separate.

## Author metadata already recoverable from the repository

Software/manuscript repository metadata identify the current named author as **ZHANG RUIQI** (`CITATION.cff`, `pyproject.toml`). No affiliation, corresponding-author designation, CRediT statement or funding information is recorded in the repository, so those fields must not be guessed.

## Remaining submission inputs

Only external/human submission metadata remain:

- final author list and order (confirm whether ZHANG RUIQI is the sole manuscript author);
- affiliations and corresponding author;
- CRediT contributions;
- funding and acknowledgements;
- competing-interests declaration;
- co-author approval if applicable;
- immutable release/permanent archive DOI for citation at submission or revision.
