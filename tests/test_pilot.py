import numpy as np
import pandas as pd

from sdmr.data.background import occurrence_buffer_membership
from sdmr.data.quality import OccurrenceAdmissionConfig
from sdmr.pilot import prepare_product_a_pilot, select_configured_taxa


def test_occurrence_buffer_membership_uses_geodesic_distance():
    focal = pd.DataFrame({"longitude": [0.0], "latitude": [0.0]})
    points = pd.DataFrame({"longitude": [0.0, 1.0, 5.0], "latitude": [0.0, 0.0, 0.0]})
    mask = occurrence_buffer_membership(points, focal, buffer_km=150.0)
    assert mask.tolist() == [True, True, False]


def test_taxon_selection_prefers_key_and_preserves_zero_match_ledger():
    records = pd.DataFrame(
        {
            "species": ["Alpha beta", "Gamma delta"],
            "acceptedTaxonKey": ["11", "22"],
            "taxonKey": ["11", "22"],
            "longitude": [0.0, 1.0],
            "latitude": [0.0, 1.0],
        }
    )
    taxa = pd.DataFrame(
        {
            "scientific_name": ["Configured alpha", "Gamma delta", "Missing species"],
            "taxon_key": ["11", np.nan, np.nan],
        }
    )
    selected, ledger = select_configured_taxa(records, taxa)
    assert set(selected["species"]) == {"Configured alpha", "Gamma delta"}
    indexed = ledger.set_index("scientific_name")
    assert indexed.loc["Configured alpha", "selection_mode"] == "taxon_key"
    assert bool(indexed.loc["Missing species", "matched"]) is False
    assert int(indexed.loc["Missing species", "matched_rows"]) == 0


def test_prepare_product_a_pilot_builds_explicit_gate_and_background():
    rng = np.random.default_rng(12)
    focal_frames = []
    taxa_rows = []
    for i, name in enumerate(["sp_a", "sp_b", "sp_c", "sp_d"]):
        n = 18
        focal_frames.append(
            pd.DataFrame(
                {
                    "species": name,
                    "longitude": rng.normal(i * 3.0, 0.4, n),
                    "latitude": rng.normal(0.0, 0.4, n),
                    "occurrenceStatus": "PRESENT",
                    "basisOfRecord": "HUMAN_OBSERVATION",
                }
            )
        )
        taxa_rows.append({"scientific_name": name})
    records = pd.concat(focal_frames, ignore_index=True)
    target_group = pd.DataFrame(
        {
            "species": ["target"] * 500,
            "longitude": rng.uniform(-4, 14, 500),
            "latitude": rng.uniform(-5, 5, 500),
            "occurrenceStatus": "PRESENT",
            "basisOfRecord": "HUMAN_OBSERVATION",
        }
    )
    result = prepare_product_a_pilot(
        records,
        pd.DataFrame(taxa_rows),
        admission_config=OccurrenceAdmissionConfig(),
        min_occurrences=12,
        min_unique_cells=10,
        gate_cell_size_degrees=0.05,
        m_strategy="buffer",
        target_group_pool=target_group,
        occurrence_buffer_km=900.0,
        background_points=30,
        background_cell_size_degrees=0.05,
        random_state=3,
        strict_background=True,
    )
    assert result.species_gate["eligible"].all()
    assert result.occurrences["species"].nunique() == 4
    assert result.background["species"].nunique() == 4
    assert set(result.background_ledger["status"]) == {"ok"}
