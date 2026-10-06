import pandas as pd
import pytest

from sdmr.process_id.fresh.model_pool_v5 import (
    _nearest_occurrence_blocks,
    attach_occurrence_spatial_blocks,
    sdmr_retained_predictors,
    stable_process_states,
    validate_model_design,
    vif_prune,
    final_predictor_sets,
    TaxonModelFreeze,
)


def test_v5_model_design_runtime_matches_frozen_contract():
    c=validate_model_design("configs/sdmr_fresh_empirical_v5_model_design.json")
    assert c["cohort_binding"]["exact_taxa"]==50
    assert c["predictor_and_process_universe"]["predictor_count"]==46
    assert c["process_identification"]["stage_p"]["n_inner_splits"]==3
    assert c["process_identification"]["stage_p"]["full_system_authorization"]["n_permutations"]==999
    assert c["model_pool_background_split"]["training_rows_per_taxon"]==4000


def test_stable_states_fail_closed_on_disagreement_and_unavailable():
    routes=pd.DataFrame([
        {"learner_route":"penalized_logistic","process":"thermal","state":"required"},
        {"learner_route":"shallow3_hgb","process":"thermal","state":"required"},
        {"learner_route":"penalized_logistic","process":"water","state":"replaceable"},
        {"learner_route":"shallow3_hgb","process":"water","state":"contributory"},
        {"learner_route":"penalized_logistic","process":"seasonality","state":"unavailable"},
        {"learner_route":"shallow3_hgb","process":"seasonality","state":"required"},
        {"learner_route":"penalized_logistic","process":"radiation_energy","state":"replaceable"},
        {"learner_route":"shallow3_hgb","process":"radiation_energy","state":"replaceable"},
        {"learner_route":"penalized_logistic","process":"soil_substrate","state":"contributory"},
        {"learner_route":"shallow3_hgb","process":"soil_substrate","state":"contributory"},
        {"learner_route":"penalized_logistic","process":"productivity","state":"unresolved"},
        {"learner_route":"shallow3_hgb","process":"productivity","state":"replaceable"},
    ])
    stable=stable_process_states(routes).set_index("process")
    assert stable.loc["thermal","stable_state"]=="required"
    assert stable.loc["water","stable_state"]=="unresolved"
    assert stable.loc["seasonality","stable_state"]=="unavailable"
    assert stable.loc["radiation_energy","stable_state"]=="replaceable"
    assert stable.loc["soil_substrate","stable_state"]=="contributory"
    assert stable.loc["productivity","stable_state"]=="unresolved"


def test_sdmr_drops_predictor_only_when_every_mapped_process_replaceable():
    registry=pd.DataFrame([
        {"predictor":"a","process":"thermal","role":"direct"},
        {"predictor":"b","process":"thermal","role":"proxy"},
        {"predictor":"b","process":"water","role":"composite"},
        {"predictor":"c","process":"water","role":"direct"},
    ])
    states=pd.DataFrame([
        {"process":"thermal","stable_state":"replaceable"},
        {"process":"water","stable_state":"required"},
    ])
    retained=sdmr_retained_predictors(
        registry=registry,
        stable_states=states,
        predictors=("a","b","c"),
    )
    assert retained==("b","c")


def test_nearest_occurrence_block_assignment_uses_frozen_occurrence_labels():
    occ=pd.DataFrame({
        "occurrence_id":["b","a"],
        "longitude":[1.0,0.0],
        "latitude":[0.0,0.0],
        "spatial_block":[7,3],
    })
    bg=pd.DataFrame({"longitude":[0.1,0.9],"latitude":[0.0,0.0]})
    blocks=_nearest_occurrence_blocks(occ,bg)
    assert blocks.tolist()==[3,7]


def test_attach_occurrence_spatial_blocks_is_one_to_one(tmp_path):
    source=pd.DataFrame({
        "scientific_name":["Taxon A","Taxon A"],
        "occurrence_id":["a","b"],
        "spatial_block":[2,5],
    })
    p=tmp_path/"occ.csv";source.to_csv(p,index=False)
    index=pd.DataFrame({
        "scientific_name":["Taxon A","Taxon A"],
        "occurrence_id":["b","a"],
        "location_id":[11,10],
        "complete_case":[True,True],
    })
    out=attach_occurrence_spatial_blocks(index,occurrence_model_pool_path=p)
    got=dict(zip(out.occurrence_id,out.spatial_block))
    assert got=={"a":2,"b":5}


def test_vif_pruning_is_deterministic_on_collinear_background():
    x=pd.DataFrame({
        "a":[0.,1.,2.,3.,4.,5.],
        "b":[0.,2.,4.,6.,8.,10.],
        "c":[1.,0.,1.,0.,1.,0.],
    })
    first=vif_prune(x,("a","b","c"),threshold=5.0)
    second=vif_prune(x.sample(frac=1.0,random_state=7),("a","b","c"),threshold=5.0)
    assert first==second
    assert len(first)>=1


def test_background_groups_are_anchored_before_complete_case_filtering():
    from sdmr.process_id.fresh.model_pool_v5 import _taxon_training_tables

    # Satisfy the frozen production denominator (>=50 complete model rows and
    # >=50 training-background rows) while retaining one deliberately
    # incomplete occurrence as the only right-side spatial anchor.
    model_n=51
    background_n=63
    model_location_ids=list(range(1,model_n+1))
    background_location_ids=list(range(model_n+1,model_n+background_n+1))
    complete_left_longitudes=[i*0.01 for i in range(50)]
    model_index=pd.DataFrame({
        "scientific_name":["Taxon A"]*model_n,
        "occurrence_id":[f"left-{i:02d}" for i in range(50)]+["right"],
        "longitude":complete_left_longitudes+[10.0],
        "latitude":[0.0]*model_n,
        "spatial_block":[1]*50+[9],
        "location_id":model_location_ids,
        # The right anchor is environmentally incomplete but must still define
        # background CV grouping before complete-case filtering.
        "complete_case":[True]*50+[False],
    })
    bg_longitudes=[0.1,9.9]+[0.2+(i%20)*0.005 for i in range(background_n-2)]
    background_index=pd.DataFrame({
        "scientific_name":["Taxon A"]*background_n,
        "background_rank":list(range(1,background_n+1)),
        "longitude":bg_longitudes,
        "latitude":[0.0]*background_n,
        "location_id":background_location_ids,
        "complete_case":[True]*background_n,
    })
    locations=pd.DataFrame({
        "location_id":model_location_ids+background_location_ids,
        "p":[0.0]*model_n+[0.2+0.001*i for i in range(background_n)],
    })

    model,bg=_taxon_training_tables(
        taxon="Taxon A",
        locations=locations,
        model_index=model_index,
        background_index=background_index,
        predictors=("p",),
    )
    assert len(model)==50
    assert len(bg)>=50
    got=dict(zip(bg.background_rank,bg.spatial_block))
    assert got[1]==1
    assert got[2]==9


def test_route_failure_is_recorded_as_unavailable_not_taxon_drop(monkeypatch):
    import sdmr.process_id.fresh.model_pool_v5 as m

    class Dummy:
        pass

    def fail(*args, **kwargs):
        raise ValueError("insufficient spatial groups")

    monkeypatch.setattr(m, "evaluate_full_system_permutation_gate", fail)
    states, evidence, auth = m._learner_process_states(Dummy(), learner="shallow3_hgb")
    assert len(states) == 6
    assert states["state"].eq("unavailable").all()
    assert set(states["process"]) == set(m.DEFAULT_PLANT_PROCESSES)
    assert evidence.empty
    assert auth["authorized"] is False


def test_full46_capacity_control_uses_exact_full_predictor_universe():
    predictors=tuple(f"p{i:02d}" for i in range(46))
    frozen=TaxonModelFreeze(
        taxon="T",
        route_states=pd.DataFrame(),
        stable_states=pd.DataFrame(),
        process_evidence=pd.DataFrame(),
        authorization=pd.DataFrame(),
        sdmr_predictors=("p00","p01"),
        flat_balanced_predictors=("p00",),
        flat_auc_predictors=("p01",),
        vif_predictors=("p02",),
        selector_audit=pd.DataFrame(),
    )
    routes=final_predictor_sets(frozen=frozen,predictors=predictors)
    assert routes["full_46_flat_hgb"]==predictors
    assert len(routes["full_46_flat_hgb"])==46
    assert routes["sdmr_process_first"]==("p00","p01")


def test_capacity_control_amendment_does_not_change_emp_gates():
    import json
    from pathlib import Path
    p=json.loads(Path("configs/sdmr_fresh_empirical_v5_capacity_control_amendment.json").read_text())
    assert p["status"]=="frozen_pre_model_fit_pre_answer_check"
    assert p["original_promotion"]["EMP_A_to_EMP_F_unchanged"] is True
    assert p["added_report_only_route"]["name"]=="full_46_flat_hgb"
    assert p["interpretation_boundary"]["does_not_affect_EMP_promotion"] is True
