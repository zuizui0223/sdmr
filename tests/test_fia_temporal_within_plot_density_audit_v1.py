"""Synthetic known-data controls for archived within-plot temporal BA audit."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_temporal_within_plot_density_audit_v1 as m


def fixture_panel(with_density_signal=True):
    """One frozen species, two measured periods per independent plot chain."""
    rng=np.random.default_rng(20261117)
    s=[]
    p=[]
    for state, prefix in (("VA","51"),("WI","55")):
        for county in range(1,61):
            fips=f"{prefix}{county:03d}"
            band=county%2
            for plot in range(5):
                chain=f"{state}-{county}-{plot}"
                year0=2007+county%3
                gap=5+plot%3
                year1=year0+gap
                temp=.4+2*band
                rain=10+200*band
                cells=((int(temp//1),int(rain//100),(year0-1990)//5),
                       (int(temp//1),int(rain//100),(year1-1990)//5))
                for step,year in enumerate((year0,year1)):
                    s.append({"species_code":"129","state":state,
                              "county_fips":fips,"plot_chain_id":chain,
                              "interval_id":f"event-{chain}-{step}",
                              "interval_end_year":year,
                              "temperature_anomaly_c":temp,
                              "precipitation_anomaly_mm":rain,
                              "source_cell":cells[step],
                              "fold":m.county_fold(fips)})
                delta_ba=rng.normal(0,.45)
                ba0=.5+rng.uniform(0,1)
                y0=.02+rng.normal(0,.01)
                delta_size=rng.normal(0,.1)
                delta_age=rng.normal(0,.1)
                delta_interval=rng.normal(0,.2)
                delta_temp=rng.normal(0,.2)
                delta_rain=rng.normal(0,.2)
                yr0=(year0-2005)/20
                truth=(.01 + .7*y0 - .002*ba0 + .001*delta_size
                       + .002*delta_age + .001*delta_interval
                       + .002*delta_temp -.001*delta_rain
                       + .001*gap/10 + .002*yr0
                       + ( -.014*delta_ba if with_density_signal else 0)
                       + rng.normal(0,.002))
                p.append({"sp":"129","state":state,"county":fips,
                          "plot_chain_sha256":hashlib.sha256(chain.encode()).hexdigest(),
                          "source_cell_0":cells[0],"source_cell_1":cells[1],
                          "fold":m.county_fold(fips),
                          "growth_0":y0,"growth_1":truth,"ba_0":ba0,"d_ba":delta_ba,
                          "d_ln_dia":delta_size,"d_age":delta_age,
                          "d_interval":delta_interval,"d_temp":delta_temp,
                          "d_rain":delta_rain,"elapsed_decades":gap/10,
                          "first_year_centered":yr0})
    return pd.DataFrame(p),pd.DataFrame(s)


def test_source_eligibility_uses_training_counties_not_heldout():
    pair,source=fixture_panel()
    cells=m.train_support(source,"129",0)
    assert len(cells)>=2
    unchanged=source.copy()
    changed=unchanged.loc[~((unchanged.species_code=="129") & (unchanged.fold==0))].copy()
    assert m.train_support(changed,"129",0)==cells


def test_lag_model_fixed_covariates_and_density_extension():
    pair,_=fixture_panel()
    assert m.model_matrix(pair,False).shape==(len(pair),11)
    assert m.model_matrix(pair,True).shape==(len(pair),12)
    assert set(m.BASELINE_FEATURES) == {
        "d_ln_dia","d_age","d_interval","d_temp","d_rain",
        "elapsed_decades","first_year_centered","ba_0","growth_0"}


def test_detect_known_synthetic_density_change_signal(monkeypatch):
    pair,source=fixture_panel(True)
    monkeypatch.setattr(m,"PRIMARY",("129",))
    output,ledger,kept=m.evaluate(pair,source,{"first_two_eligible_event_candidates":len(pair),
                                               "first_open_growth_rows":0})
    assert output["n_primary_complete"]==1
    s=output["species"][0]
    assert s["n_complete_folds"]==5
    assert s["n_heldout_scored_plot_pairs"]>0
    assert s["incremental_density_change_relative_RMSE_gain_percent"]>3
    assert s["county_postfit_bootstrap95_percent"][0]>0
    assert len({(r["species_code"],r["county_fips"]) for r in ledger.to_dict("records")})==len(ledger)
    assert not output["biological_promotion_authorized"]


def test_no_hidden_test_county_or_RI_response_leakage():
    pair,source=fixture_panel()
    assert set(pair.state)=={"VA","WI"}
    assert set(source.state)=={"VA","WI"}
    country="51001"
    fold=m.county_fold(country)
    excluded=source.loc[source.fold!=fold]
    assert country not in excluded.county_fips.values


def test_same_plot_chain_cannot_count_twice_in_pair_cohort(monkeypatch):
    # Source-only scan tests complete fixed denominators separately; this
    # synthetic first-pair unit tests one plot chain across 2 PLOT events.
    monkeypatch.setattr(m,"EXPECTED_CANDIDATE_PAIRS",{"129":1})
    monkeypatch.setattr(m,"EXPECTED_ALL_SOURCE_TAXA",("129",))
    chain="original-plot-chain"
    h=hashlib.sha256(chain.encode()).hexdigest()
    rows=[]
    src=[]
    for j,(year,ba) in enumerate(((2010,.7),(2015,.9))):
        for k in range(3):
            plot=f"interval-{j}"
            rows.append({"sp":"129","state":"VA","county":"51001",
                "plot_chain_sha256":h,"plot":plot,
                "growth":.02+j*.003+k*.001,
                "ba100":ba,
                "year_centered":(year-2005)/20,
                "ln_dia10":.5+k*.05,"age60":.6+j*.12,
                "interval":5.0,"tanom3":.2,"panom200":.1})
        src.append({"species_code":"129","state":"VA","county_fips":"51001",
                    "plot_chain_id":chain,"interval_id":f"interval-{j}",
                    "interval_end_year":year,"temperature_anomaly_c":.6,
                    "precipitation_anomaly_mm":20.,"source_cell":(0,0,(year-1990)//5),
                    "fold":m.county_fold("51001")})
    pp,audit=m.aggregate_events(pd.DataFrame(rows),pd.DataFrame(src))
    assert len(pp)==1
    assert audit["first_two_eligible_event_candidates"]==1
    assert pp.d_ba.iloc[0]==pytest.approx(.2)
    assert pp.growth_1.iloc[0]>pp.growth_0.iloc[0]


def test_unstable_source_and_outcome_cohort_cannot_be_faked(tmp_path):
    for name in ("primary_five_conditional_growth_inputs_v1.csv",
                 "new_source_only_taxon_plot_intervals.csv",
                 "VA_WI_growth_result_v1.json"):
        (tmp_path/name).write_text("changed")
    with pytest.raises(ValueError,match="identity mismatch"):
        m.prepare_inputs(tmp_path)


def test_provenance_and_secondary_species_retained():
    assert m.SOURCE_RUN == 43886130089
    assert m.SOURCE_ARTIFACT == 14234926861
    assert len(m.EXPECTED_ALL_SOURCE_TAXA)==13
    assert m.EXPECTED_CANDIDATE_PAIRS == {"129":519,"316":2448,"802":767,"833":741,"837":269}
    assert m.BOOTSTRAP_DRAWS==999
    assert set(m.EXPECTED_ALL_SOURCE_TAXA)-set(m.PRIMARY)
