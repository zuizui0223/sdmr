# Nature Portfolio software submission checklist — Product A draft

Status: **submission-production aid; complete against the journal's current form at submission**.

Newly developed software is central to the manuscript. The final submission should therefore include the Nature Portfolio software checklist with the following information.

## Software identity

- software name: `sdmr`
- manuscript role: prospective occurrence-only SDM fitting/evaluation, known-truth process recovery, falsification-first ecological certificates, observation-process correction, deterministic scientific confirmation and reporting-only manuscript reconstruction
- repository: `https://github.com/zuizui0223/sdmr`
- license: MIT
- package version in `pyproject.toml`: `0.3.0.dev0`
- language: Python
- supported Python declared by package: Python >=3.10

## Exact scientific implementations

The manuscript is not defined by the moving default branch alone. Scientific evidence is tied to frozen implementation identities.

### Deterministic controlled-truth result

- implementation SHA: `9b40393dda3d03943a403d0e7875e2d616b914e7`
- frozen ref: `frozen/product-a-v2-7-2-known-truth-9b40393d`
- workflow run: `32629842082`
- frozen replicate-A artifact: `9490817718`
- artifact digest: `sha256:78b261f95c31d6c1df1f29aa02988abba2398bfca2765e7afdfe83d0acf74d4e`
- terminal artifact: `9490827277`
- terminal digest: `sha256:033b5393444f0d7365d6823d068e08778454496213f0f438188680740f846a17`

### Fresh empirical endpoint

- scientific execution ID: `product-a-v2-8-4-fresh-confirmation-v1`
- authoritative frozen SHA: `1496a6c63b19bf7711511a864ccb448fc123c963`
- workflow run: `33364164527`, attempt 1
- terminal artifact: `9750071472`
- terminal digest: `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`

## Installation

From a clean checkout:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

Core runtime dependencies declared in `pyproject.toml`:

- `numpy>=1.24`
- `pandas>=2.0`
- `scikit-learn>=1.3`

Optional dependency groups:

- geospatial: `rasterio>=1.3`
- parquet: `pyarrow>=14`
- cloud/source processing: `duckdb>=1.2`, `pyarrow>=14`

Nature reporting figures additionally require Matplotlib; the reporting workflow installs NumPy, pandas and Matplotlib explicitly.

## Automated tests

Repository tests are under `tests/` and configured through `pyproject.toml`.

Basic command:

```bash
pytest
```

Scientific contracts and workflow tests fail closed on mismatched source identities, altered scientific invariants, invalid evidence states and selected deterministic parity failures. The manuscript does not rely on a tolerance-widened rescue of the v2.7.1 predecessor.

## Deterministic execution

The deterministic scientific successor fixes:

- scikit-learn model `random_state=0`;
- selection-process NumPy seed `0`;
- `liblinear` solver inherited from the frozen predecessor;
- exact discrete-output parity across independent processes;
- numeric parity tolerance `rtol=1e-10`, `atol=1e-10`.

Observed differences in the successful v2.7.2 confirmation were 0.0 for all audited floating outputs and exact for audited discrete outputs.

## Reporting reproduction

Nature reporting source data/figures are reconstructed only from frozen artifacts.

Script:

```text
scripts/build_nature_product_a_figures.py
```

Expected command after extracting the pinned artifacts:

```bash
python scripts/build_nature_product_a_figures.py \
  --v272-dir frozen/v272 \
  --v284-part frozen/v284/part1 \
  --v284-part frozen/v284/part2 \
  --v284-part frozen/v284/part3 \
  --output-dir nature_reporting
```

Expected outputs:

- `nature_source_data_fig3.csv`
- `nature_source_data_fig4.csv`
- `nature_fig3a_family_recovery.png`
- `nature_fig3b_consensus.png`
- `nature_fig4_empirical_identity.png`

The script asserts before rendering:

- exactly six controlled-truth families and 60 cases;
- pooled stable-core precision `0.988888...`;
- pooled recall `0.983333...`;
- exact-model consensus `38/60`;
- process-set consensus `50/60`;
- exactly three empirical seeds;
- exactly 108 matched empirical cells;
- ecological/AUC candidate identity in all 108 cells;
- ecological/AUC selected-predictor identity in all 108 cells;
- common candidate `all|logit_l2_C0.1_degree1_rs0`;
- sealed presence-rank identity.

A GitHub Actions reporting workflow is staged at `.github/workflows/nature-product-a-reporting.yml`. It is a reporting workflow only and cannot modify any Product-A endpoint. At the time of this draft, no successful run of this newly staged reporting workflow has yet been recorded; frozen source artifacts themselves remain independently pinned and audited.

## Input data required for reproduction

### Controlled truth

Pinned v2.7.2 artifact `9490817718` contains the scientific tables used for Figure 3, including `ecological_inference_certificates.csv` and observation summaries.

### Fresh empirical reporting

Pinned v2.8.4 finalized artifacts:

- seed `2026082201`: `9750048481`
- seed `2026082202`: `9749405054`
- seed `2026082203`: `9749815263`

The repository also contains manuscript source-data extracts:

- `source_data/nature_fig3.csv`
- `source_data/nature_fig4_summary.csv`
- `source_data/nature_fig4_full.csv`

The full Figure-4 source-data file contains one row per matched taxon × M × seed cell (108 rows plus header); it reports only already frozen selector identity and sealed presence-rank values and is not a new scientific analysis.

## Hardware / computational resources

No GPU is required for the reported logistic-regression-based scientific core or reporting reconstruction. GitHub Actions scientific workflows used standard hosted CPU runners. Exact runtime/memory specifications should be copied from the archived workflow environment or reported conservatively in the final software checklist; do not infer hardware details that are not recorded.

## User interaction / non-default settings

The scientific results are driven through frozen machine-readable contracts and workflow inputs rather than interactive GUI choices. Key non-default scientific settings (taxa, seeds, M, sealed fraction, candidate library, thresholds and random state) are stored in versioned repository contracts and were fixed before the corresponding outcomes were opened.

## Documentation

Primary scientific documentation for submission:

- `docs/product_a_nature_ecology_evolution_online_methods.md`
- `docs/product_a_nature_data_code_availability.md`
- `docs/product_a_nature_reporting_summary_draft.md`
- `docs/product_a_nature_reference_boundary.md`
- frozen contract/result documents under `docs/`, `configs/` and `evidence/`.

## Permanent archival requirement before submission

Create a permanent DOI archive of the exact Nature-submission source state, including:

- source code;
- exact manuscript/reporting scripts;
- small source-data tables;
- `CITATION.cff`;
- environment/dependency metadata;
- a README giving the reporting reproduction command.

The DOI must be inserted into the final Code Availability statement. Do not invent or predeclare a DOI before the archive actually exists.

## Claim-safety boundary

Software availability does not authorize scientific reruns. Product-A v2.8.4 is consumed and closed. The submission package may reconstruct figures/tables from immutable artifacts but may not change taxa, candidate library, thresholds, M, sealed fraction, seeds, denominator, source provider or process registry to seek a different outcome.