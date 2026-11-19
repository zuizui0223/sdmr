"""Synthetic-only contracts for the Structural x SDMR method bridge.

No real forest outcomes or historical M5 receipts are rescored.
"""
from dataclasses import replace

import pandas as pd
import pytest

from sdmr.contextual_structure_evidence import (
    PairedHeldoutLoss,
    StructuralContextContract,
    audit_contextual_structure,
    integration_scope,
    unit_ledger_sha256,
)
from sdmr.process_information_closure import process_information_closure


def _rows(n=6, *, positive=0.5):
    return [
        PairedHeldoutLoss("unit_" + str(i), "block_" + str(i), 1.0, 1.0 - positive)
        for i in range(n)
    ]


def _contract(rows, **kw):
    defaults = dict(
        system="synthetic_forest",
        endpoint="tree_growth",
        operator="survivor_growth",
        process="stand_structure",
        candidate="basal_area",
        reference="climate_size_age",
        evidence_family_id="toy_first_open",
        source_receipt_sha256="a" * 64,
        expected_unit_ledger_sha256=unit_ledger_sha256(rows),
        expected_blocks=tuple(dict.fromkeys(r.block_id for r in rows)),
        validation_axis="spatial",
        evidence_class="prospective",
        metric="squared_error",
    )
    return StructuralContextContract(**(defaults | kw))


def test_positive_exact_six_independent_blocks_not_six_independent_forests():
    rows = _rows()
    result = audit_contextual_structure(rows, _contract(rows))
    assert result.n_units == 6
    assert result.n_blocks == 6
    assert result.gain_block_equal == pytest.approx(0.5)
    assert result.signed_block_test == "exact_signed_block"
    assert result.signed_block_p == pytest.approx(2 / 64)
    assert result.status == "conditional_predictive_gain"


def test_retrospective_result_must_not_be_promoted_by_a_small_p():
    rows = _rows()
    result = audit_contextual_structure(
        rows, _contract(rows, evidence_class="retrospective", outcome_blind_design=False)
    )
    assert result.signed_block_p < 0.05
    assert result.status == "retrospective_diagnostic_only"



def test_synthetic_evidence_cannot_be_promoted_to_biological_support():
    rows = _rows()
    result = audit_contextual_structure(rows, _contract(rows, evidence_class="synthetic"))
    assert result.signed_block_p == pytest.approx(2 / 64)
    assert result.status == "synthetic_diagnostic_only"


def test_equal_block_not_tree_count_weighted():
    rows = (
        [PairedHeldoutLoss("a_" + str(i), "a", 1, 0.8) for i in range(20)]
        + [PairedHeldoutLoss("b", "b", 1, 1.6)]
    )
    result = audit_contextual_structure(
        rows, _contract(rows, minimum_blocks=2)
    )
    assert result.gain_block_equal == pytest.approx(-0.2)
    assert result.n_units == 21
    assert result.n_blocks == 2


def test_frozen_ledger_and_block_rejection():
    rows = _rows()
    contract = _contract(rows)
    with pytest.raises(ValueError, match="unit ledger differs"):
        audit_contextual_structure(rows[:-1], contract)
    with pytest.raises(ValueError, match="block denominator"):
        audit_contextual_structure(
            rows, replace(contract, expected_blocks=("block_0",))
        )


def test_duplicate_units_and_nonfinite_losses_fail_closed():
    rows = _rows()
    contract = _contract(rows)
    with pytest.raises(ValueError, match="duplicate held-out"):
        audit_contextual_structure(rows + rows[:1], contract)
    invalid = rows.copy()
    invalid[0] = replace(invalid[0], candidate_loss=float("nan"))
    changed = replace(contract, expected_unit_ledger_sha256=unit_ledger_sha256(invalid))
    with pytest.raises(ValueError, match="finite"):
        audit_contextual_structure(invalid, changed)


def test_refuse_temporal_leakage_and_nonadditive_rmse():
    rows = _rows()
    with pytest.raises(ValueError, match="future endpoint"):
        _contract(rows, target_time="future", feature_time="contemporaneous")
    with pytest.raises(ValueError, match="never RMSE"):
        _contract(rows, metric="rmse")
    with pytest.raises(ValueError, match="outcome-blind"):
        _contract(rows, outcome_blind_design=False)


def test_insufficient_declared_blocks_is_not_scored_as_null():
    rows = _rows()
    result = audit_contextual_structure(rows, _contract(rows, minimum_blocks=7))
    assert result.signed_block_p is None
    assert result.status == "not_estimable"


def test_deterministic_monte_carlo_for_larger_geographic_panels():
    rows = _rows(17)
    contract = _contract(rows, minimum_blocks=8, mc_draws=1999, mc_seed=8)
    a = audit_contextual_structure(rows, contract)
    b = audit_contextual_structure(list(reversed(rows)), contract)
    assert a.signed_block_test == "mc_signed_block"
    assert a.signed_block_p == b.signed_block_p
    assert a.status == "conditional_predictive_gain"


def test_sd_fia_and_structural_beetles_share_method_not_numeric_effect():
    rows = _rows()
    tree = audit_contextual_structure(rows, _contract(rows))
    beetle = audit_contextual_structure(
        rows,
        _contract(
            rows, endpoint="beetle_guild_composition", operator="community_composition",
            process="deadwood_resource", candidate="vd10", metric="hellinger_squared",
            evidence_family_id="finland_beetles",
        ),
    )
    assert integration_scope(tree, beetle).startswith("methodological_alignment_only")


def test_same_forest_cohort_spatial_and_temporal_are_not_replicates():
    rows = _rows()
    spatial = audit_contextual_structure(rows, _contract(rows))
    temporal = audit_contextual_structure(
        rows, _contract(rows, validation_axis="temporal", target_time="future", feature_time="prior")
    )
    assert integration_scope(spatial, temporal) == "shared_source_not_independent_replication"


def test_distinct_sources_never_automatically_meta_analyzed():
    rows = _rows()
    first = audit_contextual_structure(rows, _contract(rows))
    second = audit_contextual_structure(
        rows, _contract(rows, evidence_family_id="toy_independent_source")
    )
    assert integration_scope(first, second) == "candidate_for_external_harmonization_not_automatic_pooling"


def test_shared_predictor_carries_biotic_and_site_process_information():
    # A deadwood / stand-density proxy may also carry site-history information.
    registry = pd.DataFrame([
        {"predictor": "basal_area", "process": "crowding", "role": "direct"},
        {"predictor": "basal_area", "process": "stand_history", "role": "proxy"},
        {"predictor": "host_tree", "process": "resource_identity", "role": "direct"},
        {"predictor": "host_tree", "process": "stand_history", "role": "proxy"},
    ])
    closure = process_information_closure(registry, "stand_history")
    assert set(closure) == {"basal_area", "host_tree"}
