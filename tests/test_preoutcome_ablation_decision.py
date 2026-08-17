from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.preoutcome_ablation_decision import summarize_preoutcome_ablation


RECOVERY = {
    "niche_overlap_schoener_d_pc12": 0.8,
    "centroid_distance": 0.2,
    "breadth_log_sd_error": 0.1,
    "quantile_profile_error": 0.1,
}


def _write_panel(root: Path, *, bad_candidate_missing_fold=False, ecology_nan=False):
    status_rows = []
    metric_rows = []
    for species in ("sp1", "sp2"):
        for perturbation in ("m150", "m300"):
            status_rows.append(
                {
                    "species": species,
                    "perturbation": perturbation,
                    "status": "success",
                }
            )
            for candidate in ("good", "partial"):
                folds = (0, 1)
                if (
                    bad_candidate_missing_fold
                    and candidate == "partial"
                    and species == "sp2"
                    and perturbation == "m300"
                ):
                    folds = (0,)
                for fold in folds:
                    row = {
                        "species": species,
                        "perturbation": perturbation,
                        "candidate": candidate,
                        "fold": fold,
                        "presence_rank": 0.7,
                        **RECOVERY,
                    }
                    if ecology_nan and candidate == "good" and fold == 1:
                        row["centroid_distance"] = np.nan
                    metric_rows.append(row)
    pd.DataFrame(status_rows).to_csv(
        root / "discovery_benchmark_status.csv", index=False
    )
    pd.DataFrame(metric_rows).to_csv(
        root / "discovery_procedure_fold_metrics.csv", index=False
    )


def test_complete_fold_decision_rejects_partial_candidate(tmp_path):
    _write_panel(tmp_path, bad_candidate_missing_fold=True)
    decision, candidates = summarize_preoutcome_ablation(
        tmp_path, expected_outer_folds=2
    )
    assert decision.status == "ready_for_known_truth"
    assert decision.complete_prediction_candidates == ("good",)
    assert decision.complete_ecological_candidates == ("good",)
    indexed = candidates.set_index("candidate")
    assert bool(indexed.loc["good", "complete_ecological_evidence"])
    assert not bool(indexed.loc["partial", "complete_prediction_evidence"])
    assert decision.uses_sealed_outcomes is False
    assert decision.scientific_promotion_run is False


def test_prediction_complete_but_ecology_incomplete_abstains(tmp_path):
    _write_panel(tmp_path, bad_candidate_missing_fold=True, ecology_nan=True)
    decision, _ = summarize_preoutcome_ablation(
        tmp_path, expected_outer_folds=2
    )
    assert decision.complete_prediction_candidates == ("good",)
    assert decision.complete_ecological_candidates == ()
    assert decision.status == "abstain_no_complete_ecological_candidate"


def test_sealed_artifact_is_rejected_even_when_candidates_are_complete(tmp_path):
    _write_panel(tmp_path)
    pd.DataFrame(
        {
            "species": ["validation"],
            "sealed_presence_rank": [0.9],
        }
    ).to_csv(tmp_path / "validation_outer_sealed.csv", index=False)
    decision, _ = summarize_preoutcome_ablation(
        tmp_path, expected_outer_folds=2
    )
    assert decision.status == "invalid_sealed_artifact_present"
    assert decision.sealed_artifacts_detected


def test_missing_candidate_metrics_is_explicit_abstention(tmp_path):
    pd.DataFrame(
        {
            "species": ["sp1"],
            "perturbation": ["m150"],
            "status": ["abstain_no_evaluable_outer_folds"],
        }
    ).to_csv(tmp_path / "discovery_benchmark_status.csv", index=False)
    decision, candidates = summarize_preoutcome_ablation(tmp_path)
    assert decision.status == "abstain_no_candidate_fold_metrics"
    assert candidates.empty
