import pandas as pd
import pytest

from sdmr.process_id.fresh.cohort_v5_occurrence import (
    EXPECTED_CANDIDATES,
    load_candidates,
)
from sdmr.process_id.fresh.cohort_v3_occurrence import _freeze_taxon


def _candidate_frame():
    return pd.DataFrame({
      "candidate_rank":range(1,EXPECTED_CANDIDATES+1),
      "scientific_name":[f"Taxon {i:03d}" for i in range(EXPECTED_CANDIDATES)],
      "family":[f"Family {i//2:03d}" for i in range(EXPECTED_CANDIDATES)],
      "genus":[f"Genus {i:03d}" for i in range(EXPECTED_CANDIDATES)],
      "selection_hash":[f"{i:064x}" for i in range(EXPECTED_CANDIDATES)],
    })


def _cells(n=60,taxon="Taxon 000"):
    return pd.DataFrame({
      "species":[taxon]*n,
      "cell_x":range(n),"cell_y":range(n),
      "n_occurrences_in_cell":[2]*n,
      "gbifid":[str(100000+i) for i in range(n)],
      "longitude":[-120.0+i*0.2 for i in range(n)],
      "latitude":[30.0+(i%10)*0.2 for i in range(n)],
    })


def test_v5_candidate_loader_requires_exact120(tmp_path):
    p=tmp_path/"c.csv";_candidate_frame().to_csv(p,index=False)
    c=load_candidates(p)
    assert len(c)==120
    assert c.candidate_rank.tolist()==list(range(1,121))


def test_v5_outer_split_persists_only_model_pool_coordinates():
    model,ledger,summary=_freeze_taxon(_cells(),"Taxon 000")
    assert summary["model_pool_occurrences"]+summary["answer_check_occurrences"]==60
    answer=set(ledger.loc[ledger.outer_role.eq("answer_check"),"occurrence_id"])
    assert not set(model.occurrence_id)&answer
    assert {"longitude","latitude"}<=set(model.columns)
    assert "longitude" not in ledger.columns and "latitude" not in ledger.columns


def test_v5_outer_split_is_order_invariant():
    a_m,a_l,a_s=_freeze_taxon(_cells(),"Taxon 000")
    b_m,b_l,b_s=_freeze_taxon(_cells().sample(frac=1,random_state=7),"Taxon 000")
    assert a_s["split_digest"]==b_s["split_digest"]
    assert set(a_m.occurrence_id)==set(b_m.occurrence_id)
