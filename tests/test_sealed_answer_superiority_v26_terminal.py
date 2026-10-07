import pandas as pd
import pytest

from sdmr.sealed_answer_superiority_v26_terminal import score_prospective_terminal


FAMILIES = [
    "gaussian", "asymmetric", "soft_threshold", "interaction",
    "omitted_driver", "observation_confounded",
]


def _gate(authorized=True):
    return {
        "purpose": "sealed_answer_superiority_v26_determinism_gate",
        "deterministic_match": bool(authorized),
        "truth_open_authorized": bool(authorized),
        "mismatched_fields": [] if authorized else ["context_refinements_sha256"],
    }


def _full_tables(*, delete_true=False):
    refinements = []
    evidence = []
    for family in FAMILIES:
        for seed in range(20001, 20021):
            for block in range(8):
                base = "temperature+water+noise"
                refined = "temperature+water"
                removed = "noise"
                if delete_true and family == "gaussian" and seed == 20001 and block == 0:
                    refined = "water"
                    removed = "temperature+noise"
                refinements.append(
                    {
                        "family": family,
                        "seed": seed,
                        "target_block": block,
                        "base_supported_set": base,
                        "refined_supported_set": refined,
                        "removed_set": removed,
                        "base_set_size": 3,
                        "refined_set_size": len(refined.split("+")),
                        "set_contraction": len(removed.split("+")),
                        "contracted": True,
                        "refinement_state": "contracted",
                    }
                )
                for process in removed.split("+"):
                    evidence.append(
                        {
                            "family": family,
                            "seed": seed,
                            "target_block": block,
                            "target_process": process,
                            "separator_id": "sealed_answer_superiority_v26",
                            "evidence_state": "exclude",
                            "qualified": True,
                            "source_disjoint_from_v21_support_inputs": True,
                            "decision_rule_frozen_before_separator_outcomes": True,
                        }
                    )
    return pd.DataFrame(refinements), pd.DataFrame(evidence)


def test_terminal_refuses_to_open_truth_without_deterministic_authorization():
    refinements, evidence = _full_tables()
    with pytest.raises(ValueError, match="truth opening"):
        score_prospective_terminal(refinements, evidence, _gate(False))


def test_terminal_passes_only_with_zero_true_deletion_and_at_least_one_false_removal():
    refinements, evidence = _full_tables()
    result = score_prospective_terminal(refinements, evidence, _gate(True))
    assert result["n_contexts"] == 960
    assert result["n_removed_true_members"] == 0
    assert result["n_contexts_with_true_member_deletion"] == 0
    assert result["n_removed_false_members"] == 960
    assert result["all_removals_qualified"] is True
    assert result["prospective_gate_passed"] is True


def test_terminal_fails_on_even_one_true_member_deletion():
    refinements, evidence = _full_tables(delete_true=True)
    result = score_prospective_terminal(refinements, evidence, _gate(True))
    assert result["n_removed_true_members"] == 1
    assert result["n_contexts_with_true_member_deletion"] == 1
    assert result["all_removals_qualified"] is True
    assert result["prospective_gate_passed"] is False


def test_terminal_fails_closed_when_any_reported_removal_lacks_qualified_exclude():
    refinements, evidence = _full_tables()
    evidence.loc[0, "qualified"] = False
    result = score_prospective_terminal(refinements, evidence, _gate(True))
    assert result["all_removals_qualified"] is False
    assert result["prospective_gate_passed"] is False


def test_terminal_refuses_incomplete_or_replaced_denominator():
    refinements, evidence = _full_tables()
    refinements = refinements.iloc[:-1].copy()
    with pytest.raises(ValueError, match="960"):
        score_prospective_terminal(refinements, evidence, _gate(True))
