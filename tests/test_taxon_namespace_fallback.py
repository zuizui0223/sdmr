import pandas as pd

from sdmr.pilot import select_configured_taxa


def test_taxon_key_namespace_mismatch_falls_back_to_exact_name_with_ledger():
    records = pd.DataFrame(
        {
            "species": ["Arabidopsis thaliana", "Arabidopsis thaliana", "Plantago major"],
            "scientificName": ["Arabidopsis thaliana", "Arabidopsis thaliana", "Plantago major"],
            "taxonKey": [3052436, 3052436, 3189866],
            "acceptedTaxonKey": [3052436, 3052436, 3189866],
            "longitude": [1.0, 2.0, 3.0],
            "latitude": [50.0, 51.0, 52.0],
        }
    )
    taxa = pd.DataFrame({"scientific_name": ["Arabidopsis thaliana"], "taxon_key": ["G26R"]})
    selected, ledger = select_configured_taxa(records, taxa)
    assert len(selected) == 2
    assert ledger.loc[0, "selection_mode"] == "taxon_key_fallback_exact_name"
    assert ledger.loc[0, "key_match_rows"] == 0
    assert ledger.loc[0, "name_match_rows"] == 2
