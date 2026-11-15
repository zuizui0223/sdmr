"""FIA source-only opportunity: prior-visit species identity and NOAA joint climate.

This is a NEW data cohort, separate from the frozen v4 growth sample.
No TREE diameter, survival/status, individual linked outcome, or model fitting.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import io
import json
from collections import defaultdict, Counter
from pathlib import Path
from zipfile import ZipFile
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
STATES = ("RI", "VA", "WI")
FIPS = {"RI":"44","VA":"51","WI":"55"}
SPECIES = ("68","129","261","316","318","371","531","541","743","762","802","833","837")
CLIMATE_SOURCE = "NOAA_20261006_county_interval_anomalies"
COLUMNS = ("species_code","state","county_fips","plot_chain_id","interval_id",
           "interval_end_year","temperature_anomaly_c","precipitation_anomaly_mm")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_plots_identity(path, member, state):
    metadata = {}
    with ZipFile(path) as z, z.open(member) as f:
        rd = csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
        if {"CN","PREV_PLT_CN","STATECD","COUNTYCD","MEASYEAR","MEASMON"} - set(rd.fieldnames or []):
            raise ValueError("PLOT identity schema missing")
        for row in rd:
            cn=(row.get("CN") or "").strip()
            if not cn or cn in metadata:
                raise ValueError("duplicate/missing PLOT CN")
            old=(row.get("PREV_PLT_CN") or "").strip()
            try:
                st=str(int(float(row["STATECD"])))
                county=int(float(row["COUNTYCD"]))
                year=int(row["MEASYEAR"])
                month=int(row["MEASMON"])
                if st!=str(int(FIPS[state])) or not 1<=county<=999 or not 1850<year<=2030 or not 1<=month<=12:
                    raise ValueError()
                fips=FIPS[state]+f"{county:03d}"
            except (ValueError,TypeError):
                fips,year=None,None
            metadata[cn]=(old,fips,year)
    return metadata


def plot_roots(metadata):
    roots={}
    visiting=set()
    def root(cn):
        if cn in roots:return roots[cn]
        if cn in visiting:raise ValueError("cyclic plot history")
        visiting.add(cn)
        prior=metadata[cn][0]
        ans=root(prior) if prior in metadata else cn
        visiting.remove(cn)
        roots[cn]=ans
        return ans
    for cn in metadata:root(cn)
    return roots


def read_tree_species_only(path,member,prior_plots):
    """Parse ONLY column offsets SPCD and PLT_CN, never response columns."""
    species_by_plot=defaultdict(set)
    counts=Counter()
    with ZipFile(path) as z,z.open(member) as f:
        rd=csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
        headers=next(rd,[])
        if len(headers)!=len(set(headers)) or {"SPCD","PLT_CN"}-set(headers):
            raise ValueError("TREE identity schema missing")
        pidx,sidx=headers.index("PLT_CN"),headers.index("SPCD")
        for fields in rd:
            counts["n_tree_identity_rows_read"]+=1
            if len(fields)!=len(headers):raise ValueError("TREE malformed row")
            plot=fields[pidx].strip()
            if plot not in prior_plots:continue
            try:species=str(int(float(fields[sidx])))
            except (ValueError,TypeError):
                counts["n_invalid_species_id_at_prior_plot"]+=1
                continue
            if species in SPECIES:species_by_plot[plot].add(species)
    counts["n_prior_plots_with_species"]=len(species_by_plot)
    return species_by_plot,dict(counts)


def baselines(climate):
    county_data=defaultdict(list)
    for (county,year,month),(temp,precip) in climate.items():
        if 1991<=year<=2020:
            county_data[county].append((year,month,temp,precip))
    if len(county_data)!=209:raise ValueError("NOAA fixed 209-county denominator changed")
    baseline={}
    for county,rows in county_data.items():
        if len(rows)!=180 or len({(y,m) for y,m,_,_ in rows})!=180:
            raise ValueError("NOAA county baseline incomplete")
        baseline[county]=(sum(x[2] for x in rows)/180,sum(x[3] for x in rows)/30)
    return baseline


def assemble_source_rows(state,eligible,metadata,species_by_prior_plot,county_baselines):
    if state not in STATES:raise ValueError("undeclared state")
    roots=plot_roots(metadata)
    result=[]
    for current,(prior,county,exposure) in sorted(eligible.items()):
        if current not in metadata or prior not in metadata or metadata[current][0]!=prior:
            raise ValueError("PLOT recensus linkage inconsistent")
        if metadata[current][1]!=county or metadata[prior][1]!=county:
            raise ValueError("PLOT county changed")
        year=metadata[current][2]
        if year is None or not 1991<=year<=2026:continue
        if county not in county_baselines:raise ValueError("NOAA county baseline missing")
        bt,bp=county_baselines[county]
        # Only BEFORE measurements. Using current TREE presence would
        # create a persistence/survival-conditioned sample.
        for sp in sorted(species_by_prior_plot.get(prior,set()),key=int):
            if sp not in SPECIES:raise ValueError("unregistered species in source")
            result.append({"species_code":sp,"state":state,"county_fips":county,
                           "plot_chain_id":roots[current],"interval_id":current,
                           "interval_end_year":year,
                           "temperature_anomaly_c":exposure["temperature_c"]-bt,
                           "precipitation_anomaly_mm":exposure["precipitation_mm_per_six_months"]-bp})
    return result


def run(noaa_csv,noaa_receipt,output,*,fetcher=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    meta=json.loads(Path(noaa_receipt).read_bytes())
    if (meta.get("study")!="fia_noaa_county_climate_pre_response_v1"
        or meta.get("snapshot")!="20261006"
        or meta.get("climate_csv_rows")!=43890
        or meta.get("climate_csv_sha256")!=sha(noaa_csv)):
        raise ValueError("frozen independent NOAA receipt changed")
    spec=importlib.util.spec_from_file_location("fia_v3_identity_gate",HERE/"fia_climate_tree_source_gate_v3.py")
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    climate=gate.load_climate(noaa_csv)
    county_baselines=baselines(climate)
    data=[];states=[]
    try:
        with TemporaryDirectory(prefix="sdmr_joint_no_outcomes_") as temporary:
            folder=Path(temporary)
            for state in STATES:
                report={"state":state,"status":"source_unavailable",
                        "no_tree_growth_or_status_read":True}
                states.append(report)
                for table in ("PLOT","TREE"):
                    source,path=gate.fetch_zip(state,table,folder,fetcher=fetcher)
                    report[table.lower()+"_source"]=source
                    if source["status"]!="ready":
                        raise ValueError(f"{state} {table} archive not available")
                psrc,tsrc=report["plot_source"],report["tree_source"]
                ppath=folder/f"{state}_PLOT.zip"
                tpath=folder/f"{state}_TREE.zip"
                if gate.sha(ppath)!=psrc["sha256"] or gate.sha(tpath)!=tsrc["sha256"]:
                    raise ValueError("archive bytes changed before source-only extraction")
                plot_intervals,plot_qc=gate.read_plots(ppath,psrc["member"],state,climate)
                plot_meta=read_plots_identity(ppath,psrc["member"],state)
                # IMPORTANT: never derive candidate taxa from current-visit TREE.
                prior_plot_ids={prior for prior,_,_ in plot_intervals.values()}
                species,tree_qc=read_tree_species_only(tpath,tsrc["member"],prior_plot_ids)
                rows=assemble_source_rows(state,plot_intervals,plot_meta,species,county_baselines)
                data.extend(rows)
                report.update({"status":"source_only_ready","plot_metadata":plot_qc,
                               "tree_prior_identity_metadata":tree_qc,"n_taxon_plot_intervals":len(rows)})
            if len(states)!=3 or any(r["status"]!="source_only_ready" for r in states):
                raise ValueError("incomplete three-state source")
            path=output/"fia_new_cohort_joint_source_only.csv"
            with path.open("w",encoding="utf-8",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=COLUMNS,lineterminator="\n")
                writer.writeheader()
                writer.writerows(sorted(data,key=lambda x:(int(x["species_code"]),x["state"],x["county_fips"],x["plot_chain_id"],x["interval_id"])))
            receipt={"program":"fia_joint_source_only_v1","status":"source_only_pre_response",
                     "no_status_diameter_growth_read":True,
                     "species_identity_only_not_survivor_selected":True,
                     "climate_source":CLIMATE_SOURCE,"sha256":sha(path),
                     "NOAA_source_receipt_sha256":sha(noaa_receipt),
                     "NOAA_csv_sha256":sha(noaa_csv),
                     "fixed_species_codes":list(SPECIES),"fixed_states":list(STATES),
                     "states":states,"n_taxon_plot_intervals":len(data),
                     "no_growth_or_survival_estimation":True,
                     "new_cohort_not_original_v4":True}
            (output/"source_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
            return receipt
    except Exception as e:
        (output/"fia_new_cohort_joint_source_only.csv").unlink(missing_ok=True)
        result={"program":"fia_joint_source_only_v1","status":"source_unavailable_or_changed",
                "fixed_species_codes":list(SPECIES),"fixed_states":list(STATES),"states":states,
                "error":f"{type(e).__name__}: {str(e)[:300]}",
                "no_status_diameter_growth_read":True,
                "species_identity_only_not_survivor_selected":True,
                "no_new_biological_outcome_opened":True}
        (output/"source_stop.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--noaa-csv",type=Path,default=Path("results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv"))
    p.add_argument("--noaa-receipt",type=Path,default=Path("results/fia_noaa_county_climate_v1/source_receipt.json"))
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    r=run(args.noaa_csv,args.noaa_receipt,args.output)
    print(r["status"],r.get("n_taxon_plot_intervals"))
    if r["status"]!="source_only_pre_response":raise SystemExit(2)


if __name__=="__main__":main()
