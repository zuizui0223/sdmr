import json
from pathlib import Path

import pandas as pd

from sdmr.v2_8_1_fresh_taxon_eligibility import (
    CALIBRATED_SEALED_FRACTION,
    EXPECTED_RANKS,
    EXPECTED_STRATA,
    select_panel,
    validate_preoutcome_contract,
)

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "configs/product_a_v2_8_1_fresh_taxon_candidates.csv"
PILOT = ROOT / "configs/product_a_pilot_taxa_v1.csv"
CONSUMED = ROOT / "configs/product_a_v2_7_1_fresh_taxon_candidates.csv"
CONTRACT = ROOT / "configs/product_a_v2_8_1_fresh_taxon_eligibility_contract.json"
EXECUTION = ROOT / "configs/product_a_v2_8_1_fresh_taxon_eligibility_execution.json"
WORKFLOW = ROOT / ".github/workflows/product-a-v2-8-1-fresh-taxon-eligibility.yml"


EXPECTED_AUTHORIZED_IDENTITY = {
    "implementation_sha": "2e501f090de9160627c912bbf8273e5a32500a2d",
    "frozen_ref": "frozen/product-a-v2-8-1-fresh-taxon-eligibility-2e501f09",
    "workflow_blob_sha": "9dcc6e679c14308a1a81e1104650f0164981f710",
    "module_blob_sha": "4d8fdaa9429086ae8d7827fc385de610aaaca257",
    "candidate_registry_blob_sha": "38d888d189320a09a48a590e287fa81966e2fc4f",
    "eligibility_contract_blob_sha": "eb3a8accc56b5eecda63c35a6decf6dd11752f1f",
    "pilot_registry_blob_sha": "56effb13d132b60e261a9b69aefd2a980840f468",
    "consumed_registry_blob_sha": "ee43c9731eb8ad3673d2fa9271e0c3a8503bd0e0",
}


def test_candidate_registry_is_closed_before_count_query():
    candidates = pd.read_csv(CANDIDATES)
    assert len(candidates) == 36
    assert candidates["scientific_name"].is_unique
    assert set(candidates["validation_stratum"]) == EXPECTED_STRATA
    assert not (set(candidates["scientific_name"]) & set(pd.read_csv(PILOT)["scientific_name"]))
    assert not (
        set(candidates["scientific_name"])
        & set(pd.read_csv(CONSUMED)["scientific_name"])
    )
    for _, group in candidates.groupby("validation_stratum"):
        assert len(group) == 3
        assert set(group["candidate_rank"].astype(int)) == EXPECTED_RANKS
    assert candidates["selection_basis"].str.contains(
        "fixed before eligibility query", regex=False
    ).all()


def test_v281_contract_inherits_frozen_eligibility_and_calibrated_fraction():
    contract = validate_preoutcome_contract(
        candidates_path=CANDIDATES,
        pilot_path=PILOT,
        consumed_path=CONSUMED,
        contract_path=CONTRACT,
    )
    assert contract["thresholds"] == {
        "minimum_occurrences": 80,
        "minimum_unique_0_05_degree_cells": 50,
    }
    assert (
        contract["geometry_calibration_receipt"]["selected_global_sealed_fraction"]
        == CALIBRATED_SEALED_FRACTION
    )
    assert contract["geometry_calibration_receipt"]["retuning_allowed"] is False
    assert contract["future_confirmation_design"]["global_sealed_fraction"] == 0.25
    assert contract["future_confirmation_design"]["fraction_is_taxon_specific"] is False


def test_selection_is_lowest_predeclared_eligible_rank_and_fails_closed():
    candidates = pd.read_csv(CANDIDATES)
    rows = []
    for _, row in candidates.iterrows():
        rank = int(row["candidate_rank"])
        rows.append(
            {
                "species": row["scientific_name"],
                "n_occurrences": 70 if rank == 1 else 100,
                "n_unique_0_05_degree_cells": 45 if rank == 1 else 60,
            }
        )
    audit, selected, unavailable = select_panel(
        candidates=candidates,
        counts=pd.DataFrame(rows),
        minimum_occurrences=80,
        minimum_unique_cells=50,
    )
    assert not unavailable
    assert len(selected) == 12
    assert set(selected["candidate_rank"].astype(int)) == {2}
    assert audit["eligible"].sum() == 24

    failed_stratum = sorted(EXPECTED_STRATA)[0]
    counts = pd.DataFrame(rows)
    failed_names = set(
        candidates.loc[
            candidates["validation_stratum"] == failed_stratum, "scientific_name"
        ]
    )
    counts.loc[counts["species"].isin(failed_names), ["n_occurrences", "n_unique_0_05_degree_cells"]] = [0, 0]
    _, selected2, unavailable2 = select_panel(
        candidates=candidates,
        counts=counts,
        minimum_occurrences=80,
        minimum_unique_cells=50,
    )
    assert unavailable2 == [failed_stratum]
    assert len(selected2) == 11


def test_execution_is_closed_or_exactly_post_merge_authorized():
    execution = json.loads(EXECUTION.read_text())
    assert execution["purpose"] == "product_a_v2_8_1_fresh_taxon_eligibility_execution_authorization"
    assert execution["one_shot"] is True
    assert execution["selected_global_sealed_fraction"] == 0.25

    if execution["execution_allowed"] is True:
        for key, expected in EXPECTED_AUTHORIZED_IDENTITY.items():
            assert execution[key] == expected
    else:
        assert execution["execution_allowed"] is False
        for key in EXPECTED_AUTHORIZED_IDENTITY:
            assert execution[key] is None

    for key in (
        "environmental_values_allowed",
        "candidate_model_fitting_allowed",
        "candidate_scores_allowed",
        "sealed_ecological_outcomes_allowed",
        "scientific_confirmation_allowed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        assert execution[key] is False


def test_workflow_is_manual_external_authorization_only():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "authorization_commit_sha" in text
    assert "expected_runtime_sha" in text
    assert "expected_frozen_ref" in text
    assert "selected_global_sealed_fraction" in text
    assert "0.25" in text
    assert "product-a-v2-8-1-fresh-taxon-eligibility" in text
