"""Source-only FIA PLOT/TREE identity guardrails: no growth or survival oracle."""
from pathlib import Path
import sys
from zipfile import ZipFile
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_joint_source_only_v1 as m


def plot_history():
    return {"p0":("","44001",2005),"p1":("p0","44001",2010),
            "p2":("p1","44001",2015)}


def test_fixed_prior_visit_taxon_not_survival_selected():
    metadata=plot_history()
    eligible={"p1":("p0","44001",{"temperature_c":10.5,
        "precipitation_mm_per_six_months":600}),
        "p2":("p1","44001",{"temperature_c":11,
        "precipitation_mm_per_six_months":620})}
    # A species newly recorded at p1 cannot be back-selected into p0.
    observed={"p0":{"68"},"p1":{"129"},"p2":{"261"}}
    rows=m.assemble_source_rows("RI",eligible,metadata,observed,{"44001":(9,500)})
    assert len(rows)==2
    assert {(x["interval_id"],x["species_code"]) for x in rows}=={("p1","68"),("p2","129")}
    assert {x["plot_chain_id"] for x in rows}=={"p0"}
    assert {x["interval_end_year"] for x in rows}=={2010,2015}
    assert rows[0]["temperature_anomaly_c"]==pytest.approx(1.5)
    assert rows[1]["precipitation_anomaly_mm"]==pytest.approx(120)


def test_plot_recensus_county_change_or_cycle_fails():
    meta=plot_history();meta["p1"]=("p0","44003",2010)
    with pytest.raises(ValueError,match="county changed"):
        m.assemble_source_rows("RI",{"p1":("p0","44001",{
            "temperature_c":10,"precipitation_mm_per_six_months":300})},
            meta,{"p0":{"68"}},{"44001":(10,300)})
    meta=plot_history();meta["p0"]=("p2","44001",2005)
    with pytest.raises(ValueError,match="cyclic"):
        m.plot_roots(meta)


def test_tree_status_diameter_are_not_touched(tmp_path):
    path=tmp_path/"tree.zip"
    with ZipFile(path,"w") as z:
        # STATUSCD/DIA are dummy poison strings: parsing only SPCD/PLT_CN works.
        z.writestr("RI_TREE.CSV","PLT_CN,SPCD,STATUSCD,DIA\np0,68,POISON,POISON\np0,68,POISON,POISON\np1,129,POISON,POISON\n")
    by,counts=m.read_tree_species_only(path,"RI_TREE.CSV",{"p0"})
    assert by=={"p0":{"68"}}
    assert counts["n_prior_plots_with_species"]==1
    assert counts["n_tree_identity_rows_read"]==3


def test_plot_dates_derived_from_measured_year(tmp_path):
    path=tmp_path/"plot.zip"
    with ZipFile(path,"w") as z:
        z.writestr("RI_PLOT.CSV",
          "CN,PREV_PLT_CN,STATECD,COUNTYCD,MEASYEAR,MEASMON\np0,,44,1,2005,7\np1,p0,44,1,2010,5\n")
    meta=m.read_plots_identity(path,"RI_PLOT.CSV","RI")
    assert meta["p1"]==("p0","44001",2010)
    assert m.plot_roots(meta)["p1"]=="p0"


def test_baseline_uses_fixed_1991_2020_county_months():
    climates={(f"{prefix}{county:03d}",y,m):(10.0,100.0)
              for prefix,n in (("44",5),("51",95),("55",109))
              for county in range(1,n+1)
              for y in range(1991,2021) for m in range(4,10)}
    b=m.baselines(climates)
    assert len(b)==209
    assert b["44001"]==pytest.approx((10,600))


def test_source_output_contract_excludes_biological_fields():
    assert set(m.COLUMNS)=={
       "species_code","state","county_fips","plot_chain_id","interval_id",
       "interval_end_year","temperature_anomaly_c","precipitation_anomaly_mm"}
    assert "DIA" not in m.COLUMNS and "STATUSCD" not in m.COLUMNS
    assert m.STATES==("RI","VA","WI") and len(m.SPECIES)==13
