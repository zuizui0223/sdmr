"""No real outcomes, remote data acquisition, or post-hoc niche promotion."""
import csv
import hashlib
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import fia_joint_support_gate_v1 as gate


def config():
    return json.loads((ROOT / "configs/fia_joint_climate_support_gate_v1.json").read_text())


def rows_for(tax="68", disjoint=False):
    out = []
    for state, prefix in gate.STATES.items():
        for i in range(6):
            county = prefix + f"{i + 1:03d}"
            for j in range(5):
                # Every region shares two jointly occupied bins, except deliberately
                # disjoint VA: the marginals have identical spans but T/P pairing flips.
                k = i % 2
                temp = 0.2 + 2 * k
                prec = 10.2 + 200 * (1-k if (disjoint and state == "VA") else k)
                out.append(dict(species_code=tax, state=state, county_fips=county,
                                plot_chain_id=f"{state}-{i}-{j}", interval_id="window1",
                                temperature_anomaly_c=temp, precipitation_anomaly_mm=prec))
    return out


def test_same_joint_support_enough_independent_counties():
    conf=config(); conf["species_codes"]=["68"]
    result=gate.evaluate_source_only(rows_for(),conf)
    sp=result["species"][0]
    assert sp["status"]=="descriptive_source_support_eligible"
    assert sp["n_shared_joint_bins"]==2
    assert all(z["shared_cell_coverage_fraction"]==1 for z in sp["regions"].values())
    assert not result["biological_promotion_authorized"]


def test_identical_marginal_bounds_do_not_prove_joint_support():
    conf=config();conf["species_codes"]=["68"]
    rows=rows_for(disjoint=True)
    va={(x["temperature_anomaly_c"],x["precipitation_anomaly_mm"]) for x in rows if x["state"]=="VA"}
    ri={(x["temperature_anomaly_c"],x["precipitation_anomaly_mm"]) for x in rows if x["state"]=="RI"}
    assert not (va & ri)
    for col in ("temperature_anomaly_c","precipitation_anomaly_mm"):
        assert (min(z[0 if col=="temperature_anomaly_c" else 1] for z in va),max(z[0 if col=="temperature_anomaly_c" else 1] for z in va)) == (min(z[0 if col=="temperature_anomaly_c" else 1] for z in ri),max(z[0 if col=="temperature_anomaly_c" else 1] for z in ri))
    sp=gate.evaluate_source_only(rows,conf)["species"][0]
    assert sp["status"]=="not_eligible_design_support"
    assert "insufficient_shared_joint_bins" in sp["reasons"]
    assert sp["n_shared_joint_bins"]==0


def test_no_missing_taxa_silently_dropped_and_negative_bins():
    conf=config(); conf["species_codes"]=["68","129"]
    rows=rows_for();rows[0]["temperature_anomaly_c"]=-0.2
    assert gate.grid_cell(rows[0],conf)[0]==-1
    out=gate.evaluate_source_only(rows,conf)
    assert len(out["species"])==2
    assert out["species"][1]["status"]=="not_eligible_design_support"
    assert out["species"][1]["regions"]["RI"]["plot_interval_count"]==0


def test_source_receipt_hash_and_whitelist_required(tmp_path):
    conf=config();conf["species_codes"]=["68"]
    p=tmp_path/"source.csv"; rc=tmp_path/"receipt.json"
    with p.open("w", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=sorted(gate.FIELDS));writer.writeheader();writer.writerows(rows_for())
    receipt={"status":"source_only_pre_response", "no_status_diameter_growth_read":True,
             "species_identity_only_not_survivor_selected":True,"climate_source":conf["climate_source"],
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    rc.write_text(json.dumps(receipt))
    assert len(gate.read_source_only_csv(p,rc,conf)) == 90
    receipt["sha256"]="0"*64;rc.write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match="receipt"):
        gate.read_source_only_csv(p,rc,conf)
    receipt["sha256"]=hashlib.sha256(p.read_bytes()).hexdigest();rc.write_text(json.dumps(receipt))
    with p.open("a") as f: f.write("68,RI,44001,BAD,window1,1,1\n")
    with pytest.raises(ValueError,match="receipt"):
        gate.read_source_only_csv(p,rc,conf)


def test_tree_level_repeats_and_response_columns_rejected(tmp_path):
    conf=config();conf["species_codes"]=["68"]
    row=rows_for()[0]
    p=tmp_path/"q.csv"; r=tmp_path/"r.json"
    for fields,records,message in [
        (sorted(gate.FIELDS),[row,row],"tree-level duplicates"),
        (sorted(gate.FIELDS | {"growth"}),[{**row,"growth":"0.02"}],"incorrect source-only schema")]:
        with p.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
        r.write_text(json.dumps({"status":"source_only_pre_response",
           "no_status_diameter_growth_read":True,"species_identity_only_not_survivor_selected":True,
           "climate_source":conf["climate_source"],"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}))
        with pytest.raises(ValueError,match=message):gate.read_source_only_csv(p,r,conf)


def test_legacy_archive_fail_closed_wrong_digest(tmp_path):
    conf=config();p=tmp_path/"untrusted.zip";p.write_bytes(b"untrusted")
    with pytest.raises(ValueError,match="SHA changed"):
        gate.legacy_boundary(p,conf)
    assert conf["stage"]=="future_source_only_design_not_frozen_empirical"


def test_thresholds_not_silent_defaults():
    conf=config();del conf["min_shared_bins"]
    with pytest.raises(ValueError,match="threshold"):
        gate.verify_config(conf)



def test_archived_boundary_denominator_and_receipt_are_not_reinterpreted():
    import csv as csvmod
    result=json.loads((ROOT/"results/fia_joint_climate_support_legacy_v4_boundary_v1.json").read_text())
    with (ROOT/"results/fia_joint_climate_support_legacy_v4_marginal_intervals_v1.csv").open(newline="") as f:
        cells=list(csvmod.DictReader(f))
    assert result["source_artifact_zip_sha256"]==gate.LEGACY_ARCHIVE_SHA
    assert result["source_response_json_sha256"]==gate.LEGACY_RESPONSE_SHA
    assert result["frozen_species_count"]==len(config()["species_codes"])==13
    assert result["marginal_temperature_and_precipitation_intersection_count"]==13
    assert result["measured_joint_support_count"]==0
    assert result["joint_support_unavailable_count"]==13
    assert result["measured_joint_support_count_means_data_absent_not_negative"] is True
    assert result["biological_promotion_authorized"] is False
    assert {s["species_code"] for s in cells}==set(config()["species_codes"])
    assert all(s["joint_status"]=="unavailable" for s in cells)
    assert all(float(s["marginal_tanom3_lo"])<float(s["marginal_tanom3_hi"])
               and float(s["marginal_panom200_lo"])<float(s["marginal_panom200_hi"]) for s in cells)
    assert all(3<=int(s["RI_counties"])<=5 for s in cells)
