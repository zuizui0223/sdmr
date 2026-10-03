import json
import numpy as np
import pandas as pd

import sdmr.process_id.fresh.model_pool_v3 as m


def test_freeze_contract_is_pre_answer_check():
    c=m.validate_freeze("configs/sdmr_fresh_empirical_v3_model_freeze.json")
    assert c["data_boundary"]["answer_check_occurrence_coordinates_opened"] is False
    assert c["data_boundary"]["answer_check_environmental_values_opened"] is False
    assert c["process_identification"]["stage_p"]["split_mode"] == "spatial"


def test_stability_disagreement_abstains():
    a=pd.DataFrame({"process":["thermal","water","seasonality"],"state":["contributory","replaceable","unavailable"]})
    b=pd.DataFrame({"process":["thermal","water","seasonality"],"state":["required","replaceable","contributory"]})
    x=m.combine_stability(a,b)
    assert x.stable_state.tolist()==["unresolved","replaceable","unavailable"]


def test_predictor_retention_requires_all_mapped_processes_replaceable():
    registry=pd.DataFrame([
        {"predictor":"a","process":"thermal","role":"direct"},
        {"predictor":"shared","process":"thermal","role":"composite"},
        {"predictor":"shared","process":"water","role":"composite"},
        {"predictor":"w","process":"water","role":"direct"},
    ])
    states=pd.DataFrame({
        "process":["thermal","water"],
        "logistic_state":["replaceable","contributory"],
        "hgb_state":["replaceable","contributory"],
        "stable_state":["replaceable","contributory"],
        "stable_sharp":[True,True],
    })
    assert m.retained_sdmr_predictors(registry,states)==("shared","w")


def test_background_group_assignment_is_deterministic():
    occ=pd.DataFrame({
      "occurrence_id":["a","b"],"longitude":[0.,10.],"latitude":[0.,0.],"spatial_block":[1,2]
    })
    bg=pd.DataFrame({"longitude":[0.1,9.9],"latitude":[0.,0.]})
    assert m.assign_background_groups(occ,bg).tolist()==[1,2]


def test_forward_selector_prefers_deterministic_evaluable_prefix(monkeypatch):
    occ=pd.DataFrame({"label":[]})
    bg=pd.DataFrame()
    def fake(o,b,go,gb,predictors,metric):
        # score improves from a to a+b then worsens.
        key=tuple(predictors)
        return {("a",):0.6,("b",):0.55,("c",):0.52,
                ("a","b"):0.7,("a","c"):0.65,
                ("a","b","c"):0.69}.get(key,float("nan"))
    monkeypatch.setattr(m,"score_predictors_cv",fake)
    selected,trace=m.forward_select(occ,bg,np.array([]),np.array([]),("a","b","c"),metric="balanced_log_score",max_predictors=3)
    assert selected==("a","b")
    assert len(trace)==3
