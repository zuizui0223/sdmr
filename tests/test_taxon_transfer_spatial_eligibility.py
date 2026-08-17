import numpy as np

from sdmr.taxon_transfer_spatial_eligibility import (
    assign_outcome_blind_taxon_roles,
    spatial_support_fold_ledger,
)


def test_spatial_support_gate_records_background_failure_without_model_scores():
    presence_groups = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    background_groups = np.array([0] * 10 + [1] * 10 + [2] * 1 + [3] * 1)
    ledger = spatial_support_fold_ledger(
        presence_groups,
        background_groups,
        outer_folds=2,
        minimum_background_rows_per_side=5,
        minimum_presence_rows_per_side=2,
    )
    assert len(ledger) == 2
    assert not ledger["eligible_fold"].all()
    assert ledger["failure_reason"].str.contains("background_").any()
    assert "presence_rank" not in ledger.columns


def test_spatial_support_gate_accepts_balanced_raw_support():
    presence_groups = np.repeat(np.arange(4), 5)
    background_groups = np.repeat(np.arange(4), 10)
    ledger = spatial_support_fold_ledger(
        presence_groups,
        background_groups,
        outer_folds=2,
    )
    assert ledger["eligible_fold"].all()
    assert (ledger["n_background_train"] >= 5).all()
    assert (ledger["n_background_test"] >= 5).all()


def test_role_assignment_is_deterministic_after_model_free_gate():
    eligible = [
        "Nothofagus pumilio",
        "Eucalyptus pauciflora",
        "Rhizophora mangle",
        "Larrea tridentata",
    ]
    roles = assign_outcome_blind_taxon_roles(
        eligible,
        seed=20260814,
        validation_fraction=0.25,
    ).set_index("scientific_name")["role"]
    assert set(roles[roles.eq("validation")].index) == {
        "Rhizophora mangle",
        "Larrea tridentata",
    }
    assert set(roles[roles.eq("discovery")].index) == {
        "Nothofagus pumilio",
        "Eucalyptus pauciflora",
    }
