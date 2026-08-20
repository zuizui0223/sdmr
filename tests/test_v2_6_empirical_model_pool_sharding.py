import json
from pathlib import Path

import pandas as pd

from sdmr.v2_6_empirical_model_pool_merge import merge_m_workers
from sdmr.v2_6_empirical_model_pool_worker import M_NAMES


def _write_shard(root: Path, m_name: str, *, predictors=("bio1", "bio12")) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"candidate": ["c"], "M": [m_name], "fold": [0]}).to_csv(root / "base_fold_metrics.csv", index=False)
    pd.DataFrame({"candidate": ["c::exclude::thermal"], "M": [m_name], "fold": [0]}).to_csv(root / "knockout_fold_metrics.csv", index=False)
    pd.DataFrame({"M": [m_name], "group": ["base"], "status": ["success"]}).to_csv(root / "worker_status.csv", index=False)
    pd.DataFrame({"predictor": list(predictors), "coverage": [1.0] * len(predictors)}).to_csv(root / "predictor_coverage.csv", index=False)
    pd.DataFrame({"candidate": ["c"], "M": [m_name]}).to_csv(root / "selection_trace.csv", index=False)
    contract = {
        "purpose": "product_a_v2_6_empirical_model_pool_worker",
        "taxon": "Plantus example",
        "taxon_index": 2,
        "part_seed": 2026081901,
        "M_specs": [m_name],
        "n_admissible_predictors": len(predictors),
        "admissible_predictors": list(predictors),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "old_real_model_outputs_reused": False,
        "old_real_sealed_outcomes_read": False,
    }
    (root / "contract.json").write_text(json.dumps(contract), encoding="utf-8")


def test_merge_m_workers_reconstructs_original_taxon_worker_shape(tmp_path):
    shards = tmp_path / "shards"
    for i, name in enumerate(M_NAMES):
        _write_shard(shards / f"m{i}", name)
    out = tmp_path / "merged"
    result = merge_m_workers(worker_root=shards, output_dir=out)
    assert result["M_specs"] == list(M_NAMES)
    assert result["computational_sharding"] == "taxon_x_M_then_exact_merge"
    assert result["sealed_occurrence_environment_read"] is False
    assert set(pd.read_csv(out / "base_fold_metrics.csv")["M"]) == set(M_NAMES)


def test_merge_m_workers_rejects_predictor_set_drift(tmp_path):
    shards = tmp_path / "shards"
    _write_shard(shards / "m0", M_NAMES[0])
    _write_shard(shards / "m1", M_NAMES[1])
    _write_shard(shards / "m2", M_NAMES[2], predictors=("bio1",))
    try:
        merge_m_workers(worker_root=shards, output_dir=tmp_path / "merged")
    except ValueError as exc:
        assert "admissible predictor" in str(exc)
    else:
        raise AssertionError("predictor-set drift must fail closed")
