# Nature Portfolio software submission checklist — Product A draft

Status: **submission-production aid; complete against the journal's current form at submission**.

Newly developed software is central to the manuscript. The final submission should therefore include the Nature Portfolio software checklist.

## Software identity

- software name: `sdmr`
- manuscript role: prospective occurrence-only SDM fitting/evaluation; exclusion-based process-necessity certificates; consensus-first process-stability certificates; observation-process correction; deterministic scientific confirmation; frozen empirical confirmation; reporting-only manuscript reconstruction
- repository: `https://github.com/zuizui0223/sdmr`
- license: MIT
- package version: `0.3.0.dev0`
- language: Python
- supported Python: >=3.10

## Scientific-estimator boundary

The software implements two distinct process-level certificate families used in the manuscript.

1. **Exclusion-based necessity** (`v2.4–v2.6` lineage): explicit process knockouts test whether adequate explanations survive without declared process information. v2.6 frozen performance is reported through false-required counts, possible-process recall/precision, boundary coverage and width.
2. **Consensus-first process stability** (`v2.7.2`): `stable_process_core` is the intersection of process sets supported by canonical and perturbation-robust ecological selectors. Its frozen P=0.9889 and R/F1=0.9833 quantify process stability against hidden truth; they are not the precision/recall of the exclusion-based necessity estimator.

## Exact scientific implementations

The manuscript is not defined by the moving default branch alone. Scientific evidence is tied to frozen implementation identities.

### Exclusion-based known-truth validation

- v2.6 workflow run: `32251711573`
- terminal artifact: `9364873176`
- digest: `sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba`

### Deterministic consensus-first controlled-truth result

- implementation SHA: `9b40393dda3d03943a403d0e7875e2d616b914e7`
- frozen ref: `frozen/product-a-v2-7-2-known-truth-9b40393d`
- workflow run: `32629842082`
- replicate-A artifact: `9490817718`
- digest: `sha256:78b261f95c31d6c1df1f29aa02988abba2398bfca2765e7afdfe83d0acf74d4e`
- terminal artifact: `9490827277`
- terminal digest: `sha256:033b5393444f0d7365d6823d068e08778454496213f0f438188680740f846a17`

### Fresh empirical endpoint

- scientific execution ID: `product-a-v2-8-4-fresh-confirmation-v1`
- authoritative frozen SHA: `1496a6c63b19bf7711511a864ccb448fc123c963`
- workflow run: `33364164527`, attempt 1
- terminal artifact: `9750071472`
- terminal digest: `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

Core dependencies:

- `numpy>=1.24`
- `pandas>=2.0`
- `scikit-learn>=1.3`

Optional groups include rasterio, pyarrow and duckdb. Nature reporting additionally installs Matplotlib.

## Automated tests

Repository tests are under `tests/` and configured through `pyproject.toml`.

```bash
pytest
```

Scientific contracts fail closed on mismatched source identities, altered invariants, invalid evidence states and deterministic parity failures. A predecessor process-dependent selected-predictor difference was retained as a failed implementation state rather than rescued by tolerance widening.

## Deterministic execution

The v2.7.2 scientific successor fixes:

- scikit-learn model `random_state=0`;
- selection-process NumPy seed `0`;
- `liblinear` solver inherited from the predecessor;
- exact discrete parity across independent processes;
- numeric parity tolerance `rtol=1e-10`, `atol=1e-10`.

Observed differences in successful v2.7.2 confirmation were 0.0 for all audited floating outputs and exact for audited discrete outputs.

## Nature reporting reproduction

The reporting workflow reconstructs figures/source data only from frozen scientific artifacts. It does not refit candidates or alter Product-A endpoints.

Scripts:

```text
scripts/build_nature_product_a_concept_figures.py
scripts/build_nature_product_a_figures.py
scripts/check_nature_manuscript_format.py
```

Core artifact-based command:

```bash
python scripts/build_nature_product_a_figures.py \
  --v272-dir frozen/v272 \
  --v284-part frozen/v284/part1 \
  --v284-part frozen/v284/part2 \
  --v284-part frozen/v284/part3 \
  --output-dir nature_reporting
```

Current expected workflow products include:

- `nature_fig1_identification_logic.png` and `.pdf`
- `nature_fig2_false_necessity.png` and `.pdf`
- `nature_fig3_known_truth.png` and `.pdf`
- `nature_fig4_empirical_identity.png` and `.pdf`
- `nature_source_data_fig2.csv`
- `nature_source_data_fig3.csv`
- `nature_source_data_fig4.csv`
- `nature_source_data_fig4_parts.csv`

Figure 3 reports the **consensus-first process-stability** certificate. The reporting code asserts:

- six controlled-truth families and 60 cases;
- stable-core pooled precision `0.988888...` and recall `0.983333...`;
- exact-model consensus `38/60`;
- process-set consensus `50/60`.

These assertions must not be interpreted as exclusion-necessity performance. The separate v2.6 exclusion result is retained in `source_data/nature_extended_v26_certificate.csv`.

For the empirical endpoint, the reporting code asserts:

- exactly three frozen seeds;
- 108 matched empirical cells;
- ecological/AUC candidate identity and selected-predictor identity in all 108 cells;
- common candidate `all|logit_l2_C0.1_degree1_rs0`;
- sealed presence-rank identity;
- nondomination in 3/3 parts, strict improvement in 0/3 and mean presence-rank delta 0.0.

The GitHub Actions reporting workflow `.github/workflows/nature-product-a-reporting.yml` has recorded successful runs and previously reproduced the four main figures, source data and manuscript format assertions from pinned evidence. The current corrected manuscript head is revalidated separately before submission.

## Input data required for reporting reproduction

### Consensus-first controlled truth

Pinned v2.7.2 artifact `9490817718` contains `ecological_inference_certificates.csv` and observation summaries used for Figure 3.

### Exclusion-based Extended Data

The frozen v2.6 result/receipt supplies the exclusion-certificate safety/breadth values; the reporting extract is `source_data/nature_extended_v26_certificate.csv`.

### Fresh empirical reporting

Pinned finalized v2.8.4 artifacts:

- seed `2026082201`: `9750048481`
- seed `2026082202`: `9749405054`
- seed `2026082203`: `9749815263`

Repository reporting extracts include `source_data/nature_fig3.csv`, `source_data/nature_fig4_summary.csv`, `source_data/nature_fig4_full.csv` and Extended Data source tables. The Figure-4 full table contains 108 matched taxon × M × seed rows and is reporting-only.

## Hardware / computational resources

No GPU is required for the reported logistic-regression scientific core or reporting reconstruction. Scientific workflows used standard hosted CPU runners. Final hardware/runtime details should be copied only from recorded workflow metadata; do not infer unrecorded hardware specifications.

## User interaction / non-default settings

Scientific results are driven through frozen machine-readable contracts/workflow inputs rather than interactive GUI choices. Key non-default settings—taxa, seeds, M, sealed fraction, candidate library, thresholds and RNG identities—were fixed before corresponding outcomes were opened.

## Documentation

Primary submission documentation:

- `docs/product_a_nature_ecology_evolution_article_draft.md`
- `docs/product_a_nature_ecology_evolution_online_methods.md`
- `docs/product_a_nature_logic_consistency_audit.md`
- `docs/product_a_nature_data_code_availability.md`
- `docs/product_a_nature_reporting_summary_draft.md`
- `docs/product_a_nature_reference_boundary.md`
- frozen contracts/results under `docs/`, `configs/` and `evidence/`.

## Permanent archival requirement

Before submission, create a permanent DOI archive of the exact submission state including source code, manuscript/reporting scripts, small source-data tables, `CITATION.cff`, dependency metadata and reproduction instructions. Insert the resulting DOI into Code Availability. Do not invent a DOI before the archive exists.

## Claim-safety boundary

Software availability does not authorize scientific reruns. Product-A v2.8.4 is consumed and closed. Reporting may reconstruct figures/tables from immutable artifacts but may not change taxa, candidate library, thresholds, M, sealed fraction, seeds, denominator, source provider or process registry to seek another outcome.