import numpy as np
import pandas as pd

from sdmr.process_id.fresh.cohort_v5_background import (
    BACKGROUND_POINTS,
    EXPECTED_CANDIDATES,
    build_geometry_and_backgrounds,
)


def _candidates():
    return pd.DataFrame({
      "candidate_rank":range(1,EXPECTED_CANDIDATES+1),
      "scientific_name":[f"Taxon {i:03d}" for i in range(EXPECTED_CANDIDATES)],
      "family":[f"Family {i//2:03d}" for i in range(EXPECTED_CANDIDATES)],
      "genus":[f"Genus {i:03d}" for i in range(EXPECTED_CANDIDATES)],
      "selection_hash":[f"{i:064x}" for i in range(EXPECTED_CANDIDATES)],
    })


def _target(n=6000):
    return pd.DataFrame({
      "gx":np.arange(n),
      "gy":np.zeros(n,dtype=int),
      "gbifid":[str(100000+i) for i in range(n)],
      "longitude":np.linspace(-2,2,n),
      "latitude":np.zeros(n),
    })


def _model():
    rows=[]
    for i in range(EXPECTED_CANDIDATES):
        tax=f"Taxon {i:03d}"
        rows.extend([
          {"scientific_name":tax,"occurrence_id":f"{i}a","longitude":0.0,"latitude":0.0},
          {"scientific_name":tax,"occurrence_id":f"{i}b","longitude":0.2,"latitude":0.0},
        ])
    return pd.DataFrame(rows)


def _source_gate():
    return pd.DataFrame({
      "scientific_name":[f"Taxon {i:03d}" for i in range(EXPECTED_CANDIDATES)],
      "source_gate_passed":[True]*EXPECTED_CANDIDATES,
    })


def test_v5_geometry_keeps_individual_source_failure_without_aborting():
    sg=_source_gate()
    sg.loc[0,"source_gate_passed"]=False
    bg,audit=build_geometry_and_backgrounds(
        target_footprint=_target(),model_pool=_model(),source_gate=sg,candidates=_candidates()
    )
    first=audit.iloc[0]
    assert first["source_gate_passed"] == False
    assert first["geometry_eligible"] == False
    assert first["background_points"] == 0
    assert first["geometry_failure_reason"]=="source_gate_failed"
    assert audit["geometry_eligible"].sum()==EXPECTED_CANDIDATES-1
    assert len(bg)==(EXPECTED_CANDIDATES-1)*BACKGROUND_POINTS


def test_v5_geometry_marks_300km_shortfall_ineligible_without_relaxation():
    small=_target(4999)
    bg,audit=build_geometry_and_backgrounds(
        target_footprint=small,model_pool=_model(),source_gate=_source_gate(),candidates=_candidates()
    )
    assert not audit["geometry_eligible"].any()
    assert len(bg)==0
    assert audit["background_points"].eq(0).all()
    assert audit["geometry_failure_reason"].eq(
        "fewer_than_5000_target_group_cells_within_300km"
    ).all()


def test_v5_background_is_deterministic_for_eligible_candidates():
    a,sa=build_geometry_and_backgrounds(
        target_footprint=_target(),model_pool=_model(),source_gate=_source_gate(),candidates=_candidates()
    )
    b,sb=build_geometry_and_backgrounds(
        target_footprint=_target().sample(frac=1,random_state=3),
        model_pool=_model().sample(frac=1,random_state=4),
        source_gate=_source_gate().sample(frac=1,random_state=5),
        candidates=_candidates(),
    )
    assert a[["scientific_name","background_rank","gbifid"]].equals(
        b[["scientific_name","background_rank","gbifid"]]
    )
    assert sa.equals(sb)
