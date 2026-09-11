import pandas as pd

from sdmr.attribution_eligibility_v18_development import _binary_label, _evaluate


def test_v18_binary_status_mapping():
    cfg={"positive_status":"context_contributory","negative_statuses":["context_replaceable","context_unresolved"]}
    assert _binary_label("context_contributory",cfg)=="eligible"
    assert _binary_label("context_replaceable",cfg)=="not_eligible"
    assert _binary_label("context_unresolved",cfg)=="not_eligible"
    assert _binary_label("insufficient",cfg) is None


def test_v18_cell_disjoint_evaluator_predicts_each_row_once():
    rows=[]
    for c in range(6):
        status="context_contributory" if c%2==0 else "context_replaceable"
        for b in range(4):
            rows.append({
                "family":f"f{c}","seed":15001+c,"target_process":"water","target_block":b,"context_status":status,
                "conditional_residual_shift":float(c+b/10),
                "conditional_residual_scale_ratio":1.0+0.1*c,
                "conditional_target_r2":0.2*c,
                "process_support_shift":0.3*c,
                "conditioning_support_shift":0.4*c,
            })
    frame=pd.DataFrame(rows)
    cfg={
        "positive_status":"context_contributory",
        "negative_statuses":["context_replaceable","context_unresolved"],
        "classifier_C":1.0,"max_iter":1000,"decision_threshold":0.5,
    }
    pred,metrics=_evaluate(frame,cfg)
    assert len(pred)==len(frame)
    assert pred["row_index"].nunique()==len(frame)
    assert metrics["n_predicted_contexts"]==len(frame)
