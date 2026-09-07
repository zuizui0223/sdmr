import pandas as pd

from sdmr.counterfactual_process_recovery import counterfactual_process_gap
from sdmr.factorial_process_recovery_experiment import factorial_candidates


def test_counterfactual_gap_is_positive_when_excluding_temperature_loses_overlap():
    candidates = factorial_candidates(random_state=0)
    rows = []
    for perturbation in ("p1", "p2"):
        for candidate, auc, overlap in (
            ("temperature_quadratic", 0.70, 0.80),
            ("water_quadratic", 0.68, 0.40),
            ("soil_quadratic", 0.67, 0.35),
        ):
            for fold in range(3):
                rows.append(
                    {
                        "perturbation": perturbation,
                        "candidate": candidate,
                        "fold": fold,
                        "presence_rank": auc,
                        "niche_overlap_schoener_d_pc12": overlap,
                    }
                )
    result = counterfactual_process_gap(pd.DataFrame(rows), "temperature", candidates)
    assert result["n_scored_perturbations"] == 2
    assert result["case_score"] > 0.8
