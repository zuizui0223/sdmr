import pandas as pd

from sdmr.niche_recovery_perturbation import (
    select_perturbation_robust_niche_recovery_protocol,
)


def _row(candidate, perturbation, perturbation_type, overlap, centroid, breadth, quantile, auc):
    return {
        "candidate": candidate,
        "perturbation": perturbation,
        "perturbation_type": perturbation_type,
        "fold": 0,
        "niche_overlap_schoener_d_pc12": overlap,
        "centroid_distance": centroid,
        "breadth_log_sd_error": breadth,
        "quantile_profile_error": quantile,
        "presence_rank": auc,
        "n_predictors": 3,
    }


def test_domain_transfer_record_failure_can_remain_ecological_robustness_diagnostic():
    frame = pd.DataFrame(
        [
            _row(
                "ecology_star", "sampling_standard", "sampling_or_background",
                0.92, 0.10, 0.10, 0.10, 0.64,
            ),
            _row(
                "ecology_star", "source_to_shifted", "domain_transfer",
                0.90, 0.11, 0.11, 0.11, 0.45,
            ),
            _row(
                "record_transfer", "sampling_standard", "sampling_or_background",
                0.80, 0.25, 0.25, 0.25, 0.64,
            ),
            _row(
                "record_transfer", "source_to_shifted", "domain_transfer",
                0.78, 0.27, 0.27, 0.27, 0.62,
            ),
        ]
    )

    legacy = select_perturbation_robust_niche_recovery_protocol(
        frame,
        auc_sem_multiplier=0.0,
    )
    assert legacy.candidate == "record_transfer"

    scoped = select_perturbation_robust_niche_recovery_protocol(
        frame,
        auc_sem_multiplier=0.0,
        prediction_adequacy_perturbation_types=("sampling_or_background",),
    )
    assert scoped.candidate == "ecology_star"
    assert set(scoped.eligible_candidates) == {"ecology_star", "record_transfer"}

    transfer_audit = scoped.adequacy_summary.loc[
        scoped.adequacy_summary["perturbation"].eq("source_to_shifted")
    ]
    assert not transfer_audit["hard_prediction_gate"].any()
    ecology_transfer = transfer_audit.loc[
        transfer_audit["candidate"].eq("ecology_star")
    ].iloc[0]
    assert not bool(ecology_transfer["passes_prediction_adequacy"])
    assert bool(ecology_transfer["eligible_hard_gate_perturbations"])


def test_scoped_prediction_gate_still_requires_complete_ecological_transfer_evidence():
    frame = pd.DataFrame(
        [
            _row(
                "partial", "sampling_standard", "sampling_or_background",
                0.95, 0.10, 0.10, 0.10, 0.70,
            ),
            _row(
                "complete", "sampling_standard", "sampling_or_background",
                0.82, 0.20, 0.20, 0.20, 0.70,
            ),
            _row(
                "complete", "source_to_shifted", "domain_transfer",
                0.80, 0.22, 0.22, 0.22, 0.40,
            ),
        ]
    )
    result = select_perturbation_robust_niche_recovery_protocol(
        frame,
        auc_sem_multiplier=0.0,
        prediction_adequacy_perturbation_types=("sampling_or_background",),
    )
    assert result.eligible_candidates == ("complete",)
    assert result.candidate == "complete"
