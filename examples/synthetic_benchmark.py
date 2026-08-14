"""Small synthetic example showing the two-level holdout API."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sdmr import benchmark_taxon_split


def make_data(seed: int = 7):
    rng = np.random.default_rng(seed)
    occ_rows = []
    bg_rows = []
    for i, species in enumerate(["plant_a", "plant_b", "plant_c", "plant_d", "plant_e", "plant_f"]):
        shift = i * 6.0
        lon_b = rng.uniform(-12 + shift, 12 + shift, 300)
        lat_b = rng.uniform(-12, 12, 300)
        env_signal_b = lat_b + rng.normal(0, 1.5, 300)
        noise_b = rng.normal(0, 1, 300)
        for lon, lat, sig, noise in zip(lon_b, lat_b, env_signal_b, noise_b):
            bg_rows.append((species, lon, lat, sig, noise))

        lon_p = rng.uniform(-12 + shift, 12 + shift, 100)
        lat_p = rng.uniform(2, 12, 100)
        env_signal_p = lat_p + rng.normal(0, 1.0, 100)
        noise_p = rng.normal(0, 1, 100)
        for lon, lat, sig, noise in zip(lon_p, lat_p, env_signal_p, noise_p):
            occ_rows.append((species, lon, lat, sig, noise))

    columns = ["species", "longitude", "latitude", "env_signal", "noise"]
    return pd.DataFrame(occ_rows, columns=columns), pd.DataFrame(bg_rows, columns=columns)


if __name__ == "__main__":
    occurrences, background = make_data()
    result = benchmark_taxon_split(
        occurrences,
        background,
        ["env_signal", "noise"],
        max_predictors=2,
        common_top_k=1,
        random_state=7,
    )
    print("common:", result.common_predictors)
    print(result.validation_outer)
