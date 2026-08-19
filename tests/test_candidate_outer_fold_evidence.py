import pandas as pd

from sdmr.candidate_outer_fold_evidence import require_complete_outer_fold_evidence


def _row(candidate, species, perturbation, fold, rank=0.7, overlap=0.8):
    return {
        "candidate": candidate,
        "species": species,
        "perturbation": perturbation,
        "fold": fold,
        "presence_rank": rank,
        "niche_overlap_schoener_d_pc12": overlap,
    }


def test_one_fold_survivor_cannot_enter_two_fold_selector():
    rows = []
    for species in ("sp1", "sp2"):
        for perturbation in ("m1", "m2"):
            rows.extend(
                [
                    _row("complete", species, perturbation, 0),
                    _row("complete", species, perturbation, 1),
                ]
            )
            rows.append(_row("partial", species, perturbation, 0, rank=0.99, overlap=0.99))
    result = require_complete_outer_fold_evidence(
        pd.DataFrame(rows),
        discovery_taxa=("sp1", "sp2"),
        perturbations=("m1", "m2"),
        required_columns=("presence_rank",),
        expected_outer_folds=2,
    )
    assert result.eligible_candidates == ("complete",)
    partial = result.candidate_summary.set_index("candidate").loc["partial"]
    assert not bool(partial["eligible_complete_outer_evidence"])
    assert partial["n_cells_with_complete_fold_ids"] == 0


def test_nonfinite_ecological_axis_rejects_ecological_evidence_only():
    rows = []
    for species in ("sp1", "sp2"):
        for perturbation in ("m1", "m2"):
            for fold in (0, 1):
                overlap = float("nan") if (species, perturbation, fold) == ("sp2", "m2", 1) else 0.8
                rows.append(_row("candidate", species, perturbation, fold, overlap=overlap))
    frame = pd.DataFrame(rows)
    prediction = require_complete_outer_fold_evidence(
        frame,
        discovery_taxa=("sp1", "sp2"),
        perturbations=("m1", "m2"),
        required_columns=("presence_rank",),
        expected_outer_folds=2,
    )
    ecology = require_complete_outer_fold_evidence(
        frame,
        discovery_taxa=("sp1", "sp2"),
        perturbations=("m1", "m2"),
        required_columns=("presence_rank", "niche_overlap_schoener_d_pc12"),
        expected_outer_folds=2,
    )
    assert prediction.eligible_candidates == ("candidate",)
    assert ecology.eligible_candidates == ()
    bad_cell = ecology.cell_ledger.loc[
        ecology.cell_ledger["species"].eq("sp2")
        & ecology.cell_ledger["perturbation"].eq("m2")
    ].iloc[0]
    assert not bool(bad_cell["finite_required_columns"])
    assert "niche_overlap_schoener_d_pc12" in bad_cell["missing_or_nonfinite_columns"]


def test_duplicate_rows_do_not_substitute_for_missing_fold_id():
    frame = pd.DataFrame(
        [
            _row("candidate", "sp1", "m1", 0),
            _row("candidate", "sp1", "m1", 0),
        ]
    )
    result = require_complete_outer_fold_evidence(
        frame,
        discovery_taxa=("sp1",),
        perturbations=("m1",),
        required_columns=("presence_rank",),
        expected_outer_folds=2,
    )
    assert result.eligible_candidates == ()
    cell = result.cell_ledger.iloc[0]
    assert cell["n_observed_outer_folds"] == 1
    assert cell["observed_fold_ids"] == "0"
