import numpy as np
import pandas as pd
import pytest

from sdmr.process_id.fresh.cohort_v4_background import (
    BACKGROUND_POINTS,
    PRIMARY_M_KM,
    build_backgrounds,
)


def _target(n=6000):
    lon=np.linspace(-2.0,2.0,n)
    return pd.DataFrame({
      "gx":np.arange(n),"gy":np.zeros(n,dtype=int),
      "gbifid":[str(100000+i) for i in range(n)],
      "longitude":lon,"latitude":np.zeros(n),
    })


def _model():
    rows=[]
    for i in range(90):
        rows.append({
          "scientific_name":f"Taxon {i}",
          "occurrence_id":f"{i}-1",
          "longitude":-0.4+(i%9)*0.1,
          "latitude":0.0,
        })
    return pd.DataFrame(rows)


def test_v4_background_is_exact_5000_for_candidate90():
    bg,summary=build_backgrounds(
        target_footprint=_target(),model_pool=_model(),
        taxa=[f"Taxon {i}" for i in range(90)],
    )
    assert len(bg)==90*BACKGROUND_POINTS
    assert bg.groupby("scientific_name").size().eq(BACKGROUND_POINTS).all()
    assert len(summary)==90
    assert bg["m_km"].eq(PRIMARY_M_KM).all()


def test_v4_background_fails_instead_of_relaxing_denominator():
    target=_target(1000)
    with pytest.raises(RuntimeError,match="without denominator relaxation"):
        build_backgrounds(
            target_footprint=target,
            model_pool=_model(),
            taxa=[f"Taxon {i}" for i in range(90)],
        )
