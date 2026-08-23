from pathlib import Path

CONSTRAINTS=Path('configs/product_a_v2_7_2_runtime_constraints.txt')
PROBE=Path('.github/workflows/product-a-v2-7-2-determinism-probe.yml')
BUILD=Path('.github/workflows/product-a-v2-7-2-presealed-shard-build.yml')
CONT=Path('.github/workflows/product-a-v2-7-2-post-shard-continuation.yml')


def test_runtime_constraints_pin_primary_fresh_stack():
    lines={line.strip() for line in CONSTRAINTS.read_text().splitlines() if line.strip() and not line.startswith('#')}
    for item in {
        'numpy==2.5.2','pandas==3.0.5','scikit-learn==1.9.0','scipy==1.18.1',
        'joblib==1.5.3','threadpoolctl==3.6.0','pyarrow==25.0.1',
        'duckdb==1.5.5','rasterio==1.5.1',
    }:
        assert item in lines


def test_all_deterministic_scientific_workflows_pin_python_seed_and_constraints():
    for path in (PROBE,BUILD,CONT):
        text=path.read_text()
        assert "python-version: '3.12.14'" in text
        assert 'configs/product_a_v2_7_2_runtime_constraints.txt' in text
    assert "SDMR_LOGISTIC_RANDOM_STATE: '271'" in PROBE.read_text()
    assert "SDMR_LOGISTIC_RANDOM_STATE: '271'" in BUILD.read_text()
    assert "SDMR_LOGISTIC_RANDOM_STATE: '271'" in CONT.read_text()
