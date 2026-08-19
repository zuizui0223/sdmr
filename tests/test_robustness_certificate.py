from types import SimpleNamespace

import pandas as pd

from sdmr.robustness_certificate import build_perturbation_robustness_certificate


def _row(candidate, perturbation, auc):
    return {
        "candidate": candidate,
        "perturbation": perturbation,
        "fold": 0,
        "presence_rank": auc,
    }


def test_certificate_reports_cross_perturbation_prediction_incompatibility():
    metrics = pd.DataFrame(
        [
            _row("alpha", "sampling", 0.70),
            _row("alpha", "background", 0.68),
            _row("alpha", "transfer", 0.49),
            _row("beta", "sampling", 0.69),
            _row("beta", "background", 0.49),
            _row("beta", "transfer", 0.66),
            _row("gamma", "sampling", 0.48),
            _row("gamma", "background", 0.67),
            _row("gamma", "transfer", 0.48),
        ]
    )
    certificate = build_perturbation_robustness_certificate(metrics)

    assert certificate.status == "abstain_cross_perturbation_prediction_incompatibility"
    assert certificate.selected_candidate is None
    assert certificate.n_perturbations == 3
    assert certificate.max_passed_perturbations == 2
    assert certificate.fully_adequate_candidates == ()
    assert certificate.near_complete_candidates == ("alpha", "beta")
    assert certificate.critical_perturbations == ("background", "transfer")
    assert set(
        certificate.candidate_adequacy.loc[
            certificate.candidate_adequacy["near_complete"], "candidate"
        ]
    ) == {"alpha", "beta"}


def test_certificate_preserves_selected_status_without_reoptimizing():
    metrics = pd.DataFrame(
        [
            _row("alpha", "sampling", 0.70),
            _row("alpha", "transfer", 0.65),
            _row("beta", "sampling", 0.68),
            _row("beta", "transfer", 0.64),
        ]
    )
    # The certificate records an already-made ecological selection; it does not
    # run a second selector or change the winner.
    selection = SimpleNamespace(candidate="beta")
    certificate = build_perturbation_robustness_certificate(
        metrics,
        selection=selection,
    )
    assert certificate.status == "selected"
    assert certificate.selected_candidate == "beta"
    assert certificate.fully_adequate_candidates == ("alpha", "beta")
    assert certificate.critical_perturbations == ()
