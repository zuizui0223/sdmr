import pandas as pd

from sdmr.v2_6_empirical_decision import empirical_confirmation_decision


def _parts(*, prediction=0.0, nondominated=6, strict=6):
    rows = []
    for i in range(6):
        rows.append({
            "part_id": f"p{i}",
            "all_12_taxa": True,
            "all_3_M_specs": True,
            "mean_presence_rank_delta_vs_auc": prediction,
            "ecologically_nondominated_vs_auc": i < nondominated,
            "strict_ecological_improvement_vs_auc": i < strict,
        })
    return pd.DataFrame(rows)


def _process(modal_fail=False):
    rows = []
    for taxon in ("a", "b"):
        for domain in ("thermal", "water"):
            for i in range(6):
                status = "refuted_as_necessary"
                if modal_fail and taxon == "a" and domain == "thermal" and i >= 3:
                    status = "unresolved"
                rows.append({"part_id": f"p{i}", "taxon": taxon, "process_domain": domain, "status": status})
    return pd.DataFrame(rows)


def test_empirical_confirmation_supported_only_when_all_frozen_gates_pass():
    d = empirical_confirmation_decision(_parts(nondominated=4, strict=3), _process()).iloc[0]
    assert d["decision"] == "empirical_confirmation_supported"
    assert not d["scientific_promotion_allowed"]
    assert not d["product_b_unblocked"]


def test_empirical_confirmation_keeps_prediction_as_guardrail():
    d = empirical_confirmation_decision(_parts(prediction=-0.011), _process()).iloc[0]
    assert d["decision"] == "empirical_confirmation_not_supported"
    assert not d["prediction_guardrail"]


def test_empirical_confirmation_requires_process_modal_fraction_two_thirds():
    d = empirical_confirmation_decision(_parts(), _process(modal_fail=True)).iloc[0]
    assert d["decision"] == "empirical_confirmation_not_supported"
    assert not d["process_reproducibility_support"]


def test_empirical_confirmation_fails_closed_on_missing_part():
    d = empirical_confirmation_decision(_parts().iloc[:-1], _process()).iloc[0]
    assert d["decision"] == "empirical_confirmation_unavailable"
