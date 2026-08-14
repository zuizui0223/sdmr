import pandas as pd

from sdmr.data import admit_occurrences


def test_real_gbif_like_object_columns_keep_boolean_admission_mask():
    frame = pd.DataFrame(
        {
            "species": pd.Series(["Plant a", "Plant a", "Plant b"], dtype="object"),
            "longitude": pd.Series([10.0, 10.0, 11.0], dtype="object"),
            "latitude": pd.Series([20.0, 20.0, 21.0], dtype="object"),
            "occurrenceStatus": pd.Series(["PRESENT", "PRESENT", "PRESENT"], dtype="object"),
            "basisOfRecord": pd.Series(["HUMAN_OBSERVATION"] * 3, dtype="object"),
        }
    )
    result = admit_occurrences(frame)
    assert len(result.accepted) == 2
    assert "duplicate_coordinate" in result.rejected["rejection_reason"].iloc[0]
