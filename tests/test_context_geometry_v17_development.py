import pandas as pd

from sdmr.context_geometry_v17_development import _evaluate


def test_cell_disjoint_evaluator_returns_predictions_without_row_leakage():
    rows=[]
    statuses=["context_contributory","context_replaceable","context_unresolved"]
    for c in range(6):
        status=statuses[c%3]
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
    cfg={"supervised_classes":statuses,"classifier_C":1.0,"max_iter":1000}
    pred,metrics=_evaluate(frame,cfg)
    assert len(pred)==len(frame)
    assert metrics["n_predicted_contexts"]==len(frame)
    assert set(pred["truth"])==set(statuses)
    # each row is predicted exactly once by the fold holding out its full cell
    assert pred["row_index"].nunique()==len(frame)
