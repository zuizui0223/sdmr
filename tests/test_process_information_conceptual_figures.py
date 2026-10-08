"""Protect scope and scientific identity of M5 conceptual Figures 1 and 2."""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/"manuscript/figures/build_process_information_conceptual_figures.py"
PAPER=ROOT/"manuscript/PROCESS_INFORMATION_MEE_SUBMISSION_V1.md"
PLAN=ROOT/"manuscript/PROCESS_INFORMATION_FIGURE_PLAN_V1.md"
CONTRACT=ROOT/"configs/sdmr_v6_prospective_kt_v2.json"

def _frozen_rows():
    tree=ast.parse(BUILDER.read_text(encoding="utf-8"))
    matches=[node for node in tree.body
             if isinstance(node,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=="WORLDS" for t in node.targets)]
    assert len(matches)==1
    return ast.literal_eval(matches[0].value)

def test_eight_frozen_worlds_and_predeclared_roles():
    rows=_frozen_rows()
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    names=[row[0].lower().replace(" ","_") for row in rows]
    assert names==contract["worlds"]
    assert len(names)==8 and len(set(names))==8
    for name,process,challenge,role in rows:
        assert process and challenge
        key=name.lower().replace(" ","_")
        if key in contract["informative_controls"]:
            assert role=="Informative"
        elif key==contract["report_only_world"]:
            assert role=="Report-only"
        elif key==contract["null_world"]:
            assert role=="Null control"
        else:
            raise AssertionError(f"unexpected world: {key}")
    assert "omitted_driver" not in contract["informative_controls"]

def test_process_closure_versus_variable_deletion_distinction():
    code=BUILDER.read_text(encoding="utf-8")
    ast.parse(code)
    assert "Drop T only: E and P remain." in code
    assert "Thermal-closure knockout: remove {T, E, P}." in code
    assert "Deleting T alone cannot certify a thermal process state." in code
    body=PAPER.read_text(encoding="utf-8")
    plan=PLAN.read_text(encoding="utf-8")
    assert "deleting either predictor alone does **not** establish" in body
    assert "Only after excluding the **entire declared process-information closure**" in body
    assert "This alone never certifies **process** replaceability" in plan
    assert "biological" in body.lower()
    assert "No head-to-head benchmark" in body

def test_four_figures_are_explained_without_new_outcome_claims():
    s=PAPER.read_text(encoding="utf-8")
    for n in range(1,5):
        assert f"**Figure {n}." in s
    assert "not a spatial-transfer panel" in s
    assert "observation-confounded world authorized 1/20" in s
    assert "No favorable false call occurred among 700" in s
    assert "9 remained unrecovered" in s
    source=BUILDER.read_text(encoding="utf-8")
    for forbidden in ("results/sdmr_", "fresh_empirical", "model_refit", "promotion_failed"):
        assert forbidden not in source
