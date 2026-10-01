import numpy as np
import pandas as pd
import pytest

from sdmr.process_id.fresh.cohort_v3_background import (
    BACKGROUND_POINTS,
    PRIMARY_M_KM,
    build_backgrounds,
)


def _target(n=6000):
    lon=np.linspace(-2.0,2.0,n)
    return pd.DataFrame({
        "gx":np.arange(n),
        "gy":np.zeros(n,dtype=int),
        "gbifid":[str(100000+i) for i in range(n)],
        "longitude":lon,
        "latitude":np.zeros(n),
    })


def _model():
    return pd.DataFrame({
        "scientific_name":["Taxon A","Taxon A","Taxon B","Taxon B"],
        "occurrence_id":["A1","A2","B1","B2"],
        "longitude":[0.0,0.2,0.5,0.7],
        "latitude":[0.0,0.0,0.0,0.0],
    })


def test_v3_background_is_exact_5000_and_deterministic():
    target=_target()
    model=_model()
    a,s1=build_backgrounds(target_footprint=target,model_pool=model,taxa=["Taxon A","Taxon B"])
    b,s2=build_backgrounds(
        target_footprint=target.sample(frac=1.0,random_state=7),
        model_pool=model.sample(frac=1.0,random_state=9),
        taxa=["Taxon A","Taxon B"],
    )
    assert len(a)==2*BACKGROUND_POINTS
    assert a.groupby("scientific_name").size().eq(BACKGROUND_POINTS).all()
    assert a[["scientific_name","background_rank","gbifid"]].equals(
        b[["scientific_name","background_rank","gbifid"]]
    )
    assert s1.equals(s2)
    assert a["m_km"].eq(PRIMARY_M_KM).all()


def test_v3_background_fails_instead_of_relaxing_denominator():
    target=_target(1000)
    with pytest.raises(RuntimeError,match="without denominator relaxation"):
        build_backgrounds(target_footprint=target,model_pool=_model(),taxa=["Taxon A"])
