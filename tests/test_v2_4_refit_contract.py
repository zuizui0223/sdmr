import json
from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_4_refit_contract import (
    FULL_FIT_CODE,
    SOURCE_ARTIFACTS,
    SOURCE_HEAD_SHA,
    SOURCE_RUN_ID,
    load_frozen_group_candidates,
    load_refit_contract,
    refit_seed,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs" / "product_a_v2_4_refit_contract.json"


def test_refit_contract_freezes_source_artifacts_and_truth_barriers():
    payload = load_refit_contract(CONTRACT)

    assert payload["source_discovery"]["run_id"] == SOURCE_RUN_ID
    assert payload["source_discovery"]["head_sha"] == SOURCE_HEAD_SHA
    assert payload["source_discovery"]["panels"] == SOURCE_ARTIFACTS
    assert payload["discovery_generating_truth_read_before_raw_envelope_freeze"] is False
    assert payload["validation_taxa_simulated_or_read"] is False
    assert payload["validation_truth_read"] is False
    assert payload["fit_modes"]["spatial_refit"]["n_refits"] == 5
    assert payload["fit_modes"]["full_fit"]["fit_code"] == FULL_FIT_CODE


def test_refit_seed_is_deterministic_and_role_separated():
    d = refit_seed(
        panel="panel_D1",
        role="discovery",
        taxon_index=0,
        group="base",
        candidate_index=0,
        m_index=0,
        fit_code=0,
    )
    assert d == 210000
    assert refit_seed(
        panel="panel_D1",
        role="discovery",
        taxon_index=0,
        group="base",
        candidate_index=0,
        m_index=0,
        fit_code=FULL_FIT_CODE,
    ) == 210009
    assert refit_seed(
        panel="panel_D1",
        role="validation",
        taxon_index=0,
        group="base",
        candidate_index=0,
        m_index=0,
        fit_code=0,
    ) == 260000
    assert refit_seed(
        panel="panel_D3",
        role="discovery",
        taxon_index=2,
        group="water",
        candidate_index=3,
        m_index=2,
        fit_code=4,
    ) == 435324


def _write_discovery_artifact(root: Path):
    (root / "contract.json").write_text(
        json.dumps(
            {
                "panel": "panel_D1",
                "discovery_generating_truth_read": False,
                "validation_taxa_simulated_or_read": False,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "product": "complete_adequate_certificate",
                "status": "frozen",
                "candidates": "base_b,base_a,base_c,base_d",
            }
        ]
    ).to_csv(root / "base_products.csv", index=False)

    rows = []
    registry = []
    admitted_by_process = {
        "noise": 4,
        "seasonality": 4,
        "soil": 4,
        "temperature": 5,
        "water": 3,
    }
    for process, count in admitted_by_process.items():
        for index in range(8):
            candidate = f"base_{index}::exclude::{process}"
            rows.append(
                {
                    "candidate": candidate,
                    "base_candidate": f"base_{index}",
                    "excluded_process": process,
                    "excluded_predictors": process,
                    "admitted_knockout": index < count,
                }
            )
            registry.append(
                {
                    "candidate": candidate,
                    "base_candidate": f"base_{index}",
                    "excluded_process": process,
                    "excluded_predictors": process,
                }
            )
    pd.DataFrame(rows).to_csv(root / "knockout_candidate_summary.csv", index=False)
    pd.DataFrame(registry).to_csv(root / "knockout_registry.csv", index=False)


def test_frozen_group_candidates_preserve_exact_base_and_knockout_denominators(tmp_path):
    _write_discovery_artifact(tmp_path)

    base = load_frozen_group_candidates(
        tmp_path,
        panel="panel_D1",
        group="base",
    )
    assert base.candidates == ("base_a", "base_b", "base_c", "base_d")
    assert all(value is None for value in base.excluded_processes)

    temperature = load_frozen_group_candidates(
        tmp_path,
        panel="panel_D1",
        group="temperature",
    )
    assert len(temperature.candidates) == 5
    assert set(temperature.excluded_processes) == {"temperature"}
    assert all(values == ("temperature",) for values in temperature.excluded_predictors)


def test_frozen_group_candidates_rejects_count_drift(tmp_path):
    _write_discovery_artifact(tmp_path)
    products = pd.read_csv(tmp_path / "base_products.csv")
    products.loc[0, "candidates"] = "base_a,base_b"
    products.to_csv(tmp_path / "base_products.csv", index=False)

    with pytest.raises(ValueError, match="base candidate count differs"):
        load_frozen_group_candidates(
            tmp_path,
            panel="panel_D1",
            group="base",
        )


def test_refit_contract_rejects_source_or_truth_mutation(tmp_path):
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    payload["source_discovery"]["run_id"] = "other"
    path = tmp_path / "bad-source.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="source run changed"):
        load_refit_contract(path)

    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    payload["validation_truth_read"] = True
    path = tmp_path / "bad-truth.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="validation_truth_read=false"):
        load_refit_contract(path)
