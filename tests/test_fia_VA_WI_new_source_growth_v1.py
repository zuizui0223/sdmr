"""The new FIA source two-phase runtime must refuse outcome on missing source."""
import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_VA_WI_new_source_growth_v1 as mod


def cfg():
    return json.loads((ROOT/"configs/fia_VA_WI_shared_regional_growth_v1.json").read_text())


def test_scientific_contract_is_explicit_and_historical_v4_immutable():
    c=cfg()
    mod.verify_contract(c)
    assert mod.STATES==("VA","WI")
    assert len(mod.SPECIES)==13
    assert mod.PRIMARY==("129","316","802","833","837")
    assert c["historical_v4_cannot_be_reinterpreted"]
    assert c["new_source_version_not_independent_individual_sample"]
    assert c["scientific_status"]=="postpriorFIAoutcome_exploratory_noncausal_development"


def test_contract_cannot_silently_adopt_new_taxon_or_learner():
    original=cfg()
    cases=[
       ("primary_five_species",["129"]),
       ("states",["RI","VA","WI"]),
       ("models",["baseline","causal_random_forest"]),
       ("min_practical_shared_and_region_rmse_gain_percent",0),
       ("n_bootstrap",0),
       ("source_only_gate_requires_all_primary_25_folds",False),
       ("new_source_version_not_independent_individual_sample",False),
    ]
    for key,val in cases:
        c=dict(original);c[key]=val
        with pytest.raises(ValueError,match="contract mismatch"):
            mod.verify_contract(c)


def test_missing_source_abstains_before_any_tree_biological_columns(monkeypatch,tmp_path):
    calls=[]
    def unavailable(state,table,folder,fetcher=None):
        calls.append((state,table))
        return {"status":"unavailable","error":"synthetic upstream source unavailable"},tmp_path/"none.zip"
    monkeypatch.setattr(mod.gate,"fetch_zip",unavailable)
    result,paths,rows=mod.no_outcome_source_phase(
         tmp_path, {},{}, {},fetcher=lambda *args: b"")
    assert result["status"]=="source_stop_no_tree_response_opened"
    assert result["n_source_states_ready"]==0
    assert all(x["TREE_DIA_STATUSCD_unread"] for x in result["sources"])
    assert rows==[]
    assert calls==[("VA","PLOT"),("WI","PLOT")]
    assert (tmp_path/"source_phase_receipt.json").exists()


def test_biological_response_requires_complete_prior_source_gate(monkeypatch,tmp_path):
    def forbidden(*a,**kw):
        raise AssertionError("TREE response must not be read when source gate fails")
    monkeypatch.setattr(mod.growth_reader,"tree_outcomes",forbidden)
    result=mod.biological_outcome_phase(
        {"status":"source_insufficient_no_tree_response_opened"},
        {},[],{}, {},tmp_path)
    assert result["status"]=="not_opened_source_gate_failed"
    assert result["n_primary_complete"]==0
    assert result["biological_promotion_authorized"] is False


def test_success_source_only_county_contract_imports_required_ledger():
    assert mod.PROGRAM=="fia_VA_WI_new_source_two_phase_conditional_growth_v1"
    assert mod.NOAA_CSV_SHA256=="623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8"
    assert tuple(mod.model.MODELS)==("baseline","stationary_climate","state_varying_climate")
