import pandas as pd
import pytest

from sdmr.separating_evidence_refinement_v24 import (
    refine_context_sets,
    score_known_truth_refinement,
)


def _base():
    return pd.DataFrame([
        {"family":"gaussian","seed":17001,"target_block":0,"supported_set":"temperature+water+seasonality","supported_set_size":3},
        {"family":"gaussian","seed":17001,"target_block":1,"supported_set":"temperature+water","supported_set_size":2},
        {"family":"gaussian","seed":17001,"target_block":2,"supported_set":"","supported_set_size":0},
    ])


def _evidence():
    rows=[]
    for block, members in [(0,["temperature","water","seasonality"]),(1,["temperature","water"])]:
        for process in members:
            for sid in ("sep_a","sep_b"):
                rows.append({
                    "family":"gaussian","seed":17001,"target_block":block,
                    "target_process":process,"separator_id":sid,
                    "evidence_state":"compatible","qualified":True,
                    "source_disjoint_from_v21_support_inputs":True,
                    "decision_rule_frozen_before_separator_outcomes":True,
                })
    return pd.DataFrame(rows)


def test_only_unanimous_qualified_exclusion_removes_member():
    evidence=_evidence()
    mask=(evidence.target_block.eq(0)&evidence.target_process.eq("seasonality"))
    evidence.loc[mask,"evidence_state"]="exclude"
    refined,audit=refine_context_sets(_base(),evidence,required_separator_ids=("sep_a","sep_b"))
    first=refined.loc[refined.target_block.eq(0)].iloc[0]
    assert first.refined_supported_set=="temperature+water"
    assert first.removed_set=="seasonality"
    assert first.set_contraction==1
    decision=audit.loc[(audit.target_block.eq(0))&(audit.target_process.eq("seasonality")),"member_decision"].iloc[0]
    assert decision=="remove_unanimous_exclusion"


def test_one_indeterminate_or_missing_separator_preserves_member():
    evidence=_evidence()
    season=evidence.target_block.eq(0)&evidence.target_process.eq("seasonality")
    evidence.loc[season,"evidence_state"]="exclude"
    evidence.loc[season&evidence.separator_id.eq("sep_b"),"evidence_state"]="indeterminate"
    refined,_=refine_context_sets(_base(),evidence,required_separator_ids=("sep_a","sep_b"))
    assert "seasonality" in refined.loc[refined.target_block.eq(0),"refined_supported_set"].iloc[0]

    missing=evidence.loc[~(season&evidence.separator_id.eq("sep_b"))].copy()
    refined,_=refine_context_sets(_base(),missing,required_separator_ids=("sep_a","sep_b"))
    assert "seasonality" in refined.loc[refined.target_block.eq(0),"refined_supported_set"].iloc[0]


def test_unqualified_separator_preserves_and_reused_v21_source_is_rejected():
    evidence=_evidence()
    mask=evidence.target_block.eq(0)&evidence.target_process.eq("seasonality")
    evidence.loc[mask,"evidence_state"]="exclude"
    evidence.loc[mask&evidence.separator_id.eq("sep_b"),"qualified"]=False
    refined,_=refine_context_sets(_base(),evidence,required_separator_ids=("sep_a","sep_b"))
    assert "seasonality" in refined.loc[refined.target_block.eq(0),"refined_supported_set"].iloc[0]

    bad=_evidence()
    bad.loc[0,"source_disjoint_from_v21_support_inputs"]=False
    with pytest.raises(ValueError,match="reuses v21"):
        refine_context_sets(_base(),bad,required_separator_ids=("sep_a","sep_b"))


def test_refinement_is_monotone_and_cannot_add_processes():
    evidence=_evidence()
    extra=pd.DataFrame([{
        "family":"gaussian","seed":17001,"target_block":1,"target_process":"seasonality",
        "separator_id":"sep_a","evidence_state":"compatible","qualified":True,
        "source_disjoint_from_v21_support_inputs":True,
        "decision_rule_frozen_before_separator_outcomes":True,
    }])
    evidence=pd.concat([evidence,extra],ignore_index=True)
    refined,_=refine_context_sets(_base(),evidence,required_separator_ids=("sep_a","sep_b"))
    for row in refined.itertuples(index=False):
        base=set(filter(None,row.base_supported_set.split("+")))
        new=set(filter(None,row.refined_supported_set.split("+")))
        assert new.issubset(base)
    assert "seasonality" not in refined.loc[refined.target_block.eq(1),"refined_supported_set"].iloc[0]


def test_known_truth_score_separates_useful_contraction_from_false_deletion():
    evidence=_evidence()
    season=evidence.target_block.eq(0)&evidence.target_process.eq("seasonality")
    evidence.loc[season,"evidence_state"]="exclude"
    refined,_=refine_context_sets(_base(),evidence,required_separator_ids=("sep_a","sep_b"))
    truth=[]
    for block in (0,1,2):
        for process in ("temperature","water","seasonality","noise"):
            truth.append({
                "family":"gaussian","seed":17001,"target_block":block,"target_process":process,
                "generating_process_true":process in {"temperature","water"},
            })
    score=score_known_truth_refinement(refined,pd.DataFrame(truth))
    assert score["n_removed_true_members"]==0
    assert score["n_removed_false_members"]==1
    assert score["true_base_member_false_deletion_rate"]==0.0
    assert score["false_base_member_removal_rate"]==1.0
    assert score["fraction_of_contexts_contracted"]==pytest.approx(1/3)


def test_all_true_exclusion_is_visible_as_false_deletion_not_success():
    evidence=_evidence()
    temp=evidence.target_block.eq(1)&evidence.target_process.eq("temperature")
    evidence.loc[temp,"evidence_state"]="exclude"
    refined,_=refine_context_sets(_base(),evidence,required_separator_ids=("sep_a","sep_b"))
    truth=[]
    for block in (0,1,2):
        for process in ("temperature","water","seasonality","noise"):
            truth.append({"family":"gaussian","seed":17001,"target_block":block,"target_process":process,
                          "generating_process_true":process in {"temperature","water"}})
    score=score_known_truth_refinement(refined,pd.DataFrame(truth))
    assert score["n_removed_true_members"]==1
    assert score["context_any_true_deletion_rate"]==pytest.approx(1/3)
