import pandas as pd
import pytest

from sdmr.process_id.fresh.cohort_v4_occurrence import (
    EXPECTED_CANDIDATES,
    load_candidates,
)
from sdmr.process_id.fresh.cohort_v3_occurrence import _freeze_taxon


def _candidates():
    return pd.DataFrame({
      "candidate_rank":range(1,EXPECTED_CANDIDATES+1),
      "scientific_name":[f"Taxon {i}" for i in range(EXPECTED_CANDIDATES)],
      "family":[f"Fam {i//2}" for i in range(EXPECTED_CANDIDATES)],
      "genus":[f"Gen {i}" for i in range(EXPECTED_CANDIDATES)],
      "selection_hash":[f"{i:064x}" for i in range(EXPECTED_CANDIDATES)],
    })


def _cells(n=60,taxon="Taxon 0"):
    return pd.DataFrame({
      "species":[taxon]*n,
      "cell_x":list(range(n)),
      "cell_y":list(range(n)),
      "n_occurrences_in_cell":[2]*n,
      "gbifid":[str(100000+i) for i in range(n)],
      "longitude":[-120+i*.2 for i in range(n)],
      "latitude":[30+(i%10)*.2 for i in range(n)],
    })


def test_v4_candidate_loader_requires_exact_90(tmp_path):
    p=tmp_path/"c.csv";_candidates().to_csv(p,index=False)
    c=load_candidates(p)
    assert len(c)==90
    assert c.candidate_rank.tolist()==list(range(1,91))


def test_v4_outer_split_keeps_answer_coordinates_out():
    model,ledger,summary=_freeze_taxon(_cells(),"Taxon 0")
    answer=set(ledger.loc[ledger.outer_role.eq("answer_check"),"occurrence_id"])
    assert not set(model.occurrence_id)&answer
    assert "longitude" not in ledger.columns
    assert "latitude" not in ledger.columns
    assert summary["model_pool_occurrences"]+summary["answer_check_occurrences"]==60


def test_v4_outer_split_fails_source_gate_without_replacement():
    cells=_cells(49)
    cells["n_occurrences_in_cell"]=10
    with pytest.raises(RuntimeError,match="failed source gate without replacement"):
        _freeze_taxon(cells,"Taxon 0")
