import pandas as pd

from sdmr.data.quality import thin_to_grid


def test_thin_to_grid_is_species_specific_and_input_order_invariant():
    frame = pd.DataFrame(
        {
            "species": ["a", "a", "a", "b", "b"],
            "gbifID": ["20", "10", "30", "5", "4"],
            "longitude": [10.021, 10.019, 10.081, 10.020, 10.018],
            "latitude": [20.021, 20.019, 20.081, 20.020, 20.018],
        }
    )
    first = thin_to_grid(frame, cell_size_degrees=0.05)
    shuffled = thin_to_grid(frame.sample(frac=1, random_state=99), cell_size_degrees=0.05)

    def signature(x):
        return sorted(zip(x["species"].astype(str), x["gbifID"].astype(str)))

    assert signature(first) == signature(shuffled)
    # Species sharing the same geographic cell must both be retained.
    assert set(first.loc[first["longitude"] < 10.05, "species"]) == {"a", "b"}
    assert len(first) == 3
