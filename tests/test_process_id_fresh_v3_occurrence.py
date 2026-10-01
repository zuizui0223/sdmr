import pandas as pd
import pytest

from sdmr.process_id.fresh.cohort_v3_occurrence import (
    EXPECTED_CANDIDATES,
    MIN_THINNED_CELLS,
    _freeze_taxon,
    load_candidates,
)


def _candidate_frame():
    return pd.DataFrame({
        "candidate_rank": range(1, EXPECTED_CANDIDATES + 1),
        "scientific_name": [f"Taxon {i:02d}" for i in range(EXPECTED_CANDIDATES)],
        "family": [f"Family {i//2:02d}" for i in range(EXPECTED_CANDIDATES)],
        "genus": [f"Genus {i:02d}" for i in range(EXPECTED_CANDIDATES)],
        "selection_hash": [f"{i:064x}" for i in range(EXPECTED_CANDIDATES)],
    })


def _cells(n=60, taxon="Taxon 00"):
    return pd.DataFrame({
        "species": [taxon] * n,
        "cell_x": list(range(n)),
        "cell_y": list(range(n)),
        "n_occurrences_in_cell": [2] * n,
        "gbifid": [str(100000 + i) for i in range(n)],
        "longitude": [-120.0 + i * 0.2 for i in range(n)],
        "latitude": [30.0 + (i % 10) * 0.2 for i in range(n)],
    })


def test_candidate_loader_requires_exact_80(tmp_path):
    p=tmp_path/"c.csv"
    _candidate_frame().to_csv(p,index=False)
    c=load_candidates(p)
    assert len(c)==80
    assert c.candidate_rank.tolist()==list(range(1,81))


def test_outer_split_persists_only_model_pool_coordinates():
    model,ledger,summary=_freeze_taxon(_cells(),"Taxon 00")
    assert summary["raw_occurrences"]==120
    assert summary["thinned_occurrences"]==60
    assert summary["model_pool_occurrences"]+summary["answer_check_occurrences"]==60
    assert set(ledger.outer_role)=={"model_pool","answer_check"}
    answer=set(ledger.loc[ledger.outer_role.eq("answer_check"),"occurrence_id"])
    assert not set(model.occurrence_id)&answer
    assert {"longitude","latitude"}<=set(model.columns)
    assert "longitude" not in ledger.columns and "latitude" not in ledger.columns


def test_source_gate_fails_closed_without_candidate_replacement():
    cells=_cells(MIN_THINNED_CELLS-1)
    cells["n_occurrences_in_cell"]=10
    with pytest.raises(RuntimeError,match="failed source gate without replacement"):
        _freeze_taxon(cells,"Taxon 00")


def test_outer_split_is_row_order_invariant():
    cells=_cells()
    a_m,a_l,a_s=_freeze_taxon(cells,"Taxon 00")
    b_m,b_l,b_s=_freeze_taxon(cells.sample(frac=1.0,random_state=13),"Taxon 00")
    assert a_s["split_digest"]==b_s["split_digest"]
    assert a_l.sort_values("occurrence_id").reset_index(drop=True).equals(
        b_l.sort_values("occurrence_id").reset_index(drop=True)
    )
    assert set(a_m.occurrence_id)==set(b_m.occurrence_id)
