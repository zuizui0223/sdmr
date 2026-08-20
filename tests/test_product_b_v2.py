import pandas as pd
import pytest

from sdmr.product_b_v2 import (
    discover_validate_process_core,
    pair_process_knockout_losses,
    repeat_process_core_splits,
    summarize_taxon_process_support,
)


RECOVERY = {
    "niche_overlap_schoener_d_pc12": 0.80,
    "centroid_distance": 0.20,
    "breadth_log_sd_error": 0.10,
    "quantile_profile_error": 0.20,
}


def _base_rows(taxa=("a",), Ms=("m0",), folds=(0,)):
    rows = []
    for taxon in taxa:
        for M in Ms:
            for fold in folds:
                rows.append(
                    {
                        "taxon": taxon,
                        "M": M,
                        "fold": fold,
                        "candidate": "eco",
                        "presence_rank": 0.70,
                        **RECOVERY,
                    }
                )
    return pd.DataFrame(rows)


def _knockout_rows(taxa=("a",), Ms=("m0",), folds=(0,), process="thermal", better=False):
    rows = []
    for taxon in taxa:
        for M in Ms:
            for fold in folds:
                if better:
                    metrics = {
                        "niche_overlap_schoener_d_pc12": 0.90,
                        "centroid_distance": 0.10,
                        "breadth_log_sd_error": 0.05,
                        "quantile_profile_error": 0.10,
                    }
                    rank = 0.75
                else:
                    metrics = {
                        "niche_overlap_schoener_d_pc12": 0.60,
                        "centroid_distance": 0.40,
                        "breadth_log_sd_error": 0.30,
                        "quantile_profile_error": 0.50,
                    }
                    rank = 0.60
                rows.append(
                    {
                        "taxon": taxon,
                        "M": M,
                        "fold": fold,
                        "candidate": f"eco::exclude::{process}",
                        "base_candidate": "eco",
                        "excluded_process_domain": process,
                        "presence_rank": rank,
                        **metrics,
                    }
                )
    return pd.DataFrame(rows)


def test_process_knockout_loss_directions_are_ecological_not_auc_only():
    paired = pair_process_knockout_losses(
        _base_rows(),
        _knockout_rows(),
        frozen_candidate="eco",
        expected_taxa=["a"],
        expected_M=["m0"],
        expected_folds=[0],
    )
    row = paired.iloc[0]
    assert row["presence_rank_loss"] == pytest.approx(0.10)
    assert row["loss_niche_overlap_schoener_d_pc12"] == pytest.approx(0.20)
    assert row["loss_centroid_distance"] == pytest.approx(0.20)
    assert row["loss_breadth_log_sd_error"] == pytest.approx(0.20)
    assert row["loss_quantile_profile_error"] == pytest.approx(0.30)
    assert bool(row["niche_pareto_worsened_by_drop"])
    assert not bool(row["niche_pareto_improved_by_drop"])
    assert row["niche_axes_worsened"] == 4


def test_process_drop_that_improves_niche_is_not_called_required():
    paired = pair_process_knockout_losses(
        _base_rows(),
        _knockout_rows(better=True),
        frozen_candidate="eco",
    )
    row = paired.iloc[0]
    assert bool(row["niche_pareto_improved_by_drop"])
    assert not bool(row["niche_pareto_worsened_by_drop"])
    assert row["niche_axes_improved"] == 4


def test_taxon_process_support_requires_complete_M_fold_denominator():
    taxa = ("a",)
    Ms = ("m0", "m1", "m2")
    folds = (0, 1, 2, 3)
    paired = pair_process_knockout_losses(
        _base_rows(taxa, Ms, folds),
        _knockout_rows(taxa, Ms, folds),
        frozen_candidate="eco",
    )
    summary = summarize_taxon_process_support(
        paired,
        expected_M=Ms,
        expected_folds=folds,
    )
    assert len(summary) == 1
    row = summary.iloc[0]
    assert bool(row["complete_M_fold_evidence"])
    assert row["n_pairs"] == 12
    assert row["pareto_worsening_fraction"] == 1.0
    assert row["status"] == "supported_process_constraint"

    incomplete = paired.iloc[:-1].copy()
    summary_bad = summarize_taxon_process_support(
        incomplete,
        expected_M=Ms,
        expected_folds=folds,
    )
    assert not bool(summary_bad.iloc[0]["complete_M_fold_evidence"])
    assert summary_bad.iloc[0]["status"] == "unresolved"


def test_unseen_taxon_core_confirmation_is_separate_from_discovery():
    taxa = [f"sp{i}" for i in range(12)]
    rows = []
    for taxon in taxa:
        rows.append(
            {
                "taxon": taxon,
                "process_domain": "thermal",
                "status": "supported_process_constraint",
                "complete_M_fold_evidence": True,
            }
        )
        rows.append(
            {
                "taxon": taxon,
                "process_domain": "wind",
                "status": "supported_process_constraint" if taxon in {"sp0", "sp1"} else "unresolved",
                "complete_M_fold_evidence": True,
            }
        )
    summary = pd.DataFrame(rows)
    result = discover_validate_process_core(
        summary,
        validation_fraction=1 / 3,
        min_taxon_support_fraction=2 / 3,
        random_state=17,
    )
    thermal = result.process_summary.set_index("process_domain").loc["thermal"]
    wind = result.process_summary.set_index("process_domain").loc["wind"]
    assert bool(thermal["discovery_core_candidate"])
    assert bool(thermal["validation_confirmed"])
    assert not bool(wind["validation_confirmed"])
    assert set(result.discovery_taxa).isdisjoint(result.validation_taxa)
    assert set(result.discovery_taxa) | set(result.validation_taxa) == set(taxa)


def test_repeated_taxon_splits_report_validation_stability():
    taxa = [f"sp{i}" for i in range(12)]
    rows = [
        {
            "taxon": taxon,
            "process_domain": "water",
            "status": "supported_process_constraint",
            "complete_M_fold_evidence": True,
        }
        for taxon in taxa
    ]
    result = repeat_process_core_splits(pd.DataFrame(rows), seeds=(11, 22, 33))
    stability = result.process_stability.iloc[0]
    assert stability["n_splits"] == 3
    assert stability["discovery_core_stability"] == 1.0
    assert stability["validation_confirmation_stability"] == 1.0
