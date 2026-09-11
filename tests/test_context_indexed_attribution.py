import pandas as pd

from sdmr.context_indexed_attribution import (
    CONTEXT_CONTRIBUTORY,
    CONTEXT_REPLACEABLE,
    CONTEXT_UNRESOLVED,
    classify_target_context,
    summarize_context_indexed_attribution,
)


def _pairs():
    rows = []
    # target 0: every source says non-contributory -> context_replaceable
    for source in (1, 2, 3):
        rows.append({"family":"f","seed":1,"target_process":"water","source_block":source,"target_block":0,"evaluable":True,"reproduces_v8_noncontributory":True})
    # target 1: every source says contributory -> context_contributory
    for source in (0, 2, 3):
        rows.append({"family":"f","seed":1,"target_process":"water","source_block":source,"target_block":1,"evaluable":True,"reproduces_v8_noncontributory":False})
    # target 2: mixed -> context_unresolved
    for source, value in zip((0,1,3),(True,False,True),strict=True):
        rows.append({"family":"f","seed":1,"target_process":"water","source_block":source,"target_block":2,"evaluable":True,"reproduces_v8_noncontributory":value})
    return pd.DataFrame(rows)


def test_target_context_states_are_not_collapsed_globally():
    frame = _pairs()
    targets, sources, cells = summarize_context_indexed_attribution(frame, minimum_evaluable_sources=3)
    by_target = dict(zip(targets.target_block.astype(int), targets.context_status.astype(str), strict=True))
    assert by_target[0] == CONTEXT_REPLACEABLE
    assert by_target[1] == CONTEXT_CONTRIBUTORY
    assert by_target[2] == CONTEXT_UNRESOLVED
    assert int(cells.iloc[0].n_context_replaceable) == 1
    assert int(cells.iloc[0].n_context_contributory) == 1
    assert int(cells.iloc[0].n_context_unresolved) == 1
    assert len(sources) == 4


def test_insufficient_context_fails_closed():
    frame = _pairs().loc[lambda x: x.target_block.eq(0)].iloc[:2]
    assert classify_target_context(frame, minimum_evaluable_sources=3) == "insufficient"
