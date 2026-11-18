"""FIA PA/MI external holdout source-only opportunity, never demographic response.

Freeze *previously unopened-state* USDA FIA PLOT/COND/TREE ZIP byte fingerprints
and byte-identical October-06-2026 NOAA county files, then inspect only PLOT
visit identity/dates, COND file schema, and prior-visit TREE species identity.
No TREE.DIA/STATUSCD, growth, death, mortality, outcome-fitting or niche claim.

PA/MI are chosen as geographic neighbors of previously opened VA/WI before
any PA/MI biological response. A new FIA state is geographically disjoint,
not randomized and not a physiological experiment.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from urllib.request import Request, urlopen
from zipfile import ZipFile

import fia_joint_support_gate_v1 as joint
import fia_joint_source_only_v1 as source
import fia_noaa_county_climate_source_v1 as noaa
import fia_climate_tree_source_gate_v3 as climate_gate

STATES = ("PA", "MI")
FIPS = {"PA":"42", "MI":"26"}
NOAA_ORDINAL = {"36":"42", "20":"26"}
TRAIN_STATES = ("VA", "WI")
PRIOR_13 = ("68","129","261","316","318","371","531","541","743","762","802","833","837")
PRIOR_5 = ("129","316","802","833","837")
RAW_NOAA = {
    "temperature":("climdiv-tmpccy-v1.0.0-20261006",
                   "edf9a954c7d7a5bed5ad32e448cfc78aacbf01261b94a4c5224094535108a489"),
    "precipitation":("climdiv-pcpncy-v1.0.0-20261006",
                     "739fc3e9b529e04d406e914be1add2736ca3129c1103246ccebc2e5c76fd9d3a"),
}
NOAA_BASE = "https://www.ncei.noaa.gov/monitoring-content/data/us/climdiv/monthly/current/"
FIA_BASE = "https://apps.fs.usda.gov/fia/datamart/CSV/"
SOURCE_CSV_SHA = "44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7"
SOURCE_RECEIPT_SHA = "f167966bdd19529fe39955863effd666943e624cf939bd7c80ac8908b6a3f453"
ORIGINAL_NOAA_RECEIPT_SHA = "623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8"
MIN_HOLDOUT_COUNTIES = 5
MIN_HOLDOUT_PLOTS = 25
MIN_COVERAGE = .20
MIN_JOINT_CELLS = 2
MIN_NOAA_COMPLETE_COUNTIES = {"PA":30, "MI":40}
MAX_NOAA_BYTES = 70_000_000
MAX_FIA_BYTES = {"PLOT":320_000_000, "COND":320_000_000, "TREE":360_000_000}
MAX_UNPACKED_CSV = 3_800_000_000
OUTPUT_COLS = ("species_code","state","county_fips","plot_chain_id","interval_id",
               "interval_end_year","temperature_anomaly_c","precipitation_anomaly_mm")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_settings(config: dict) -> None:
    expected = {
        "study":"fia_PA_MI_unopened_external_source_only_v1",
        "holdout_states":list(STATES), "fips":FIPS,
        "ncei_ordinal_to_fips":NOAA_ORDINAL,
        "training_states":list(TRAIN_STATES),
        "prior_species":list(PRIOR_13), "prior_primary_five":list(PRIOR_5),
        "noaa_snapshot":"20261006",
        "noaa_first_source_raw_sha256":{k:v[1] for k,v in RAW_NOAA.items()},
        "source_training_run":43711159676,"source_training_artifact":14160283759,
        "source_training_csv_sha256":SOURCE_CSV_SHA,
        "source_training_receipt_sha256":SOURCE_RECEIPT_SHA,
        "source_only_no_tree_outcomes":True,
        "historical_FIA_and_M5_untouched":True,
        "product_B_blocked":True,
        "no_automatic_retries":True,
    }
    for key,val in expected.items():
        if config.get(key)!=val:
            raise ValueError("unfrozen external source-only contract: "+key)
    if (config.get("min_holdout_counties") != MIN_HOLDOUT_COUNTIES or
        config.get("min_holdout_plots") != MIN_HOLDOUT_PLOTS or
        config.get("minimum_holdout_coverage") != MIN_COVERAGE or
        config.get("minimum_training_joint_time_cells") != MIN_JOINT_CELLS):
        raise ValueError("external opportunity thresholds changed after source selection")


def fetch_exact_noaa(out: Path, downloader=None) -> tuple[dict,dict,dict]:
    """Download same prior NOAA snapshot; every byte MUST match old SHA."""
    out.mkdir(parents=True,exist_ok=True)
    config={
      "source_variables":{
        "temperature":{"element":"02","file":RAW_NOAA["temperature"][0],
                       "source_units":"degree_fahrenheit"},
        "precipitation":{"element":"01","file":RAW_NOAA["precipitation"][0],
                         "source_units":"inches_per_month"},
      },
      "ncei_ordinal_state_to_fips_state":NOAA_ORDINAL,
      "growing_season_months":[4,5,6,7,8,9],
      "year_start":1991,"year_end":2025,
      "baseline_start":1991,"baseline_end":2020,
      "states_fips":FIPS,
      "minimum_complete_counties":MIN_NOAA_COMPLETE_COUNTIES,
    }
    parsed={}
    receipts={}
    for var,(name,digest) in RAW_NOAA.items():
        url=NOAA_BASE+name
        if downloader:
            raw=downloader(url)
        else:
            with urlopen(Request(url,headers={"User-Agent":"sdmr-PA-MI-source-only-v1"}),timeout=110) as reply:
                raw=reply.read(MAX_NOAA_BYTES+1)
        if not isinstance(raw,bytes) or len(raw)>MAX_NOAA_BYTES or hashlib.sha256(raw).hexdigest()!=digest:
            raise ValueError("previously SHA-locked NOAA raw climate source unavailable or mutated: "+var)
        parsed[var],stats=noaa.parse_climdiv_county(raw,var,config)
        receipts[var]={"url":url,"raw_sha256":digest,"bytes":len(raw),**stats}
    monthly, qc=noaa.merge_validate_temperature_rainfall(parsed["temperature"],
                                                         parsed["precipitation"],config)
    county_months=defaultdict(list)
    climate={}
    for fips,year,month,t,p in monthly:
        climate[(fips,year,month)]=(t,p)
        if 1991<=year<=2020:county_months[fips].append((year,month,t,p))
    baseline={}
    for fips,months in county_months.items():
        if len(months)!=180 or len({(y,m) for y,m,_,_ in months})!=180:
            raise ValueError("incomplete NOAA 1991–2020 baseline at holdout county: "+fips)
        baseline[fips]=(sum(v[2] for v in months)/180,sum(v[3] for v in months)/30)
    path=out/"PA_MI_NOAA_20261006_county_growing_months.csv"
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.writer(handle,lineterminator="\n")
        writer.writerow(("fips_county","year","month","temperature_c","precipitation_mm"))
        writer.writerows(monthly)
    qc.update({"raw_sources":receipts,"derived_sha256":sha(path),
               "n_monthly_source_rows":len(monthly),"n_baseline_counties":len(baseline),
               "no_biological_outcomes_opened":True})
    return climate,baseline,qc


def fetch_fia_zip(state: str, table: str, folder: Path, fetcher=None) -> tuple[Path,dict]:
    if state not in STATES or table not in MAX_FIA_BYTES:
        raise ValueError("not a predeclared holdout FIA state/table")
    path=folder/f"{state}_{table}.zip"
    url=FIA_BASE+path.name
    digest=hashlib.sha256()
    n=0
    if fetcher:
        stream=io.BytesIO(fetcher(state,table))
    else:
        stream=urlopen(Request(url,headers={"User-Agent":"sdmr-unopened-PA-MI-source-v1"}),timeout=110)
    with stream,path.open("wb") as handle:
        while True:
            chunk=stream.read(1024*1024)
            if not chunk:break
            n+=len(chunk)
            if n>MAX_FIA_BYTES[table]:
                raise ValueError("new holdout FIA ZIP exceeded predeclared source size cap")
            digest.update(chunk);handle.write(chunk)
    with ZipFile(path) as z:
        candidates=[i for i in z.infolist() if not i.is_dir() and
                    i.filename.upper().endswith(f"{state}_{table}.CSV")]
        if len(candidates)!=1 or candidates[0].file_size>MAX_UNPACKED_CSV:
            raise ValueError("ambiguous/missing/too-large FIA CSV source member")
        member=candidates[0].filename
        size=candidates[0].file_size
    return path,{"state":state,"table":table,"url":url,"zip_sha256":digest.hexdigest(),
                 "size_bytes":n,"csv_member":member,"csv_unpacked_bytes":size}


def plot_source(path:Path,member:str,state:str) -> tuple[dict,dict,dict]:
    """FIA PLOT source ID, previous plot, county, exact measurement YEAR+MONTH."""
    allplots={}
    counters=Counter()
    with ZipFile(path) as z,z.open(member) as stream:
        reader=csv.DictReader(io.TextIOWrapper(stream,encoding="utf-8-sig",newline=""))
        required={"CN","PREV_PLT_CN","STATECD","COUNTYCD","MEASYEAR","MEASMON"}
        if required-set(reader.fieldnames or []):
            raise ValueError("missing source-only PLOT visit identity/date fields")
        for row in reader:
            counters["n_plot_source_rows"]+=1
            cn=(row.get("CN") or "").strip()
            if not cn or cn in allplots:
                raise ValueError("missing/duplicate PLOT CN")
            prior=(row.get("PREV_PLT_CN") or "").strip()
            county,date=None,None
            try:
                st=str(int(float(row["STATECD"])))
                c=int(float(row["COUNTYCD"]))
                y=int(row["MEASYEAR"]);m=int(row["MEASMON"])
                if st!=FIPS[state] or not 1<=c<=999 or not 1850<y<=2030 or not 1<=m<=12:
                    raise ValueError()
                county=FIPS[state]+f"{c:03d}"
                date=(y,m)
            except (ValueError,TypeError):
                counters["invalid_county_or_measurement_date"]+=1
            allplots[cn]=(prior,county,date)
    roots=source.plot_roots({cn:(v[0],v[1],v[2][0] if v[2] else None)
                            for cn,v in allplots.items()})
    per_root=defaultdict(set)
    for cn,(_,county,_) in allplots.items():
        per_root[roots[cn]].add(county or "")
    unstable={root for root,counties in per_root.items() if len(counties)!=1 or "" in counties}
    counters["whole_chains_with_missing_or_unstable_county"]=len(unstable)
    counters["all_distinct_plot_chains"]=len(per_root)
    return allplots,roots,{"counts":dict(counters),"unstable_plot_chains":unstable}


def inspect_cond_source_header(path:Path,member:str)->list[str]:
    """COND presence only; DO NOT inspect basal-area or outcome values."""
    with ZipFile(path) as z,z.open(member) as stream:
        reader=csv.reader(io.TextIOWrapper(stream,encoding="utf-8-sig",newline=""))
        header=next(reader,[])
    required={"PLT_CN","CONDID","COND_STATUS_CD","STDAGE","BALIVE"}
    if len(header)!=len(set(header)) or not required.issubset(header):
        raise ValueError("new external COND source schema incompatible")
    return sorted(required)


def source_state(state:str,plots:dict,roots:dict,unstable:set,treezip:Path,
                 tree_member:str,climate:dict,baseline:dict)->tuple[list[dict],dict]:
    if state not in STATES:raise ValueError("undeclared external state")
    counters=Counter()
    eligible={}
    for current,(prior,county,end) in plots.items():
        if not prior:continue
        counters["n_plot_links_with_predecessor_key"]+=1
        if prior not in plots:
            counters["prior_plot_not_in_same_archive"]+=1;continue
        pcounty=plots[prior][1]
        if roots[current] in unstable or roots[prior] in unstable or county!=pcounty:
            counters["plot_chain_county_unstable_excluded"]+=1;continue
        if county not in baseline or end is None or plots[prior][2] is None:
            counters["invalid_date_or_missing_NOAA_baseline"]+=1;continue
        if not 1991<=end[0]<=2025:
            counters["outside_pinned_NOAA_year_coverage"]+=1;continue
        exposure=climate_gate.interval_exposure(climate,county,plots[prior][2],end)
        if exposure is None:
            counters["no_complete_intervening_growing_climate"]+=1;continue
        eligible[current]=(prior,county,end,exposure)
    prev_plot_ids={v[0] for v in eligible.values()}
    prior_species,treeqc=source.read_tree_species_only(treezip,tree_member,prev_plot_ids)
    out=[]
    for current,(prior,county,end,exp) in eligible.items():
        bt,bp=baseline[county]
        for sp in sorted(prior_species.get(prior,set()),key=int):
            row={"species_code":sp,"state":state,"county_fips":county,
                 "plot_chain_id":roots[current],"interval_id":current,
                 "interval_end_year":end[0],
                 "temperature_anomaly_c":exp["temperature_c"]-bt,
                 "precipitation_anomaly_mm":exp["precipitation_mm_per_six_months"]-bp}
            if not math.isfinite(row["temperature_anomaly_c"]) or not math.isfinite(row["precipitation_anomaly_mm"]):
                raise ValueError("nonfinite source-only FIA environmental exposure")
            out.append(row)
    counters["n_county_climate_eligible_plot_intervals"]=len(eligible)
    counters["n_source_only_taxon_plot_intervals"]=len(out)
    return out,{"plot_eligibility":dict(counters),"prior_TREE_species_identity":treeqc,
                "no_status_DIA_growth_mortality_evaluated":True}


def cell(row:dict,cfg:dict)->tuple[int,int,int]:
    return (*joint.grid_cell(row,cfg),joint.period_bin(row,cfg))


def compare_train_holdout(train:list[dict],holdout:list[dict],cfg:dict)->dict:
    """Never use PA/MI records to select shared VA+WI T/P/time bins."""
    joint.verify_config(cfg)
    if set(x["state"] for x in train)!={"RI","VA","WI"}:
        raise ValueError("original three-state training source panel missing")
    if {x["state"] for x in holdout}-set(STATES):
        raise ValueError("unknown geographic holdout state")
    result=[]
    for sp in cfg["species_codes"]:
        qualified={}
        for st in TRAIN_STATES:
            bins=defaultdict(lambda:{"county":set(),"plot":set()})
            for r in train:
                if r["species_code"]!=sp or r["state"]!=st:continue
                v=bins[cell(r,cfg)]
                v["county"].add(r["county_fips"])
                v["plot"].add((r["county_fips"],r["plot_chain_id"]))
            qualified[st]={k for k,v in bins.items() if
                           len(v["county"])>=cfg["min_bin_counties"] and
                           len(v["plot"])>=cfg["min_bin_plots"]}
        common=qualified["VA"] & qualified["WI"]
        state_results={}
        for st in STATES:
            rows=[r for r in holdout if r["species_code"]==sp and r["state"]==st]
            allplots={(r["county_fips"],r["plot_chain_id"]) for r in rows}
            supported={(r["county_fips"],r["plot_chain_id"]) for r in rows if cell(r,cfg) in common}
            counties={r["county_fips"] for r in rows}
            fraction=len(supported)/len(allplots) if allplots else None
            reasons=[]
            if len(counties)<MIN_HOLDOUT_COUNTIES:reasons.append("few_unopened_holdout_counties")
            if len(allplots)<MIN_HOLDOUT_PLOTS:reasons.append("few_unopened_holdout_plot_chains")
            if len(common)<MIN_JOINT_CELLS:reasons.append("few_train_VA_WI_common_climate_time_cells")
            if fraction is None or fraction<MIN_COVERAGE:reasons.append("few_holdout_plot_chains_in_train_environment")
            state_results[st]={"source_eligible_for_future_response_design":not reasons,
                               "reasons":reasons,"n_counties":len(counties),
                               "n_unique_plot_chains":len(allplots),
                               "n_source_interval_rows":len(rows),
                               "n_unique_plot_chains_within_VA_WI_train_bins":len(supported),
                               "train_bin_plot_coverage_fraction":fraction}
        result.append({"species_code":sp,"previously_origin_stable_primary":sp in PRIOR_5,
                       "n_train_VA_WI_common_climate_time_cells":len(common),
                       "training_bin_selection_uses_PA_MI":False,
                       "holdouts":state_results,
                       "both_holdout_states_source_eligible":all(z["source_eligible_for_future_response_design"] for z in state_results.values())})
    return {"program":"fia_unopened_PA_MI_external_source_only_common_support_v1",
            "source_species_denominator":len(cfg["species_codes"]),
            "source_species":result,"fixed_primary_five":list(PRIOR_5),
            "n_primary_both_holdout_states_source_eligible":sum(r["previously_origin_stable_primary"] and r["both_holdout_states_source_eligible"] for r in result),
            "n_any_species_both_holdout_states_source_eligible":sum(r["both_holdout_states_source_eligible"] for r in result),
            "outcome_data_opened":False,
            "cross_state_transfer_accuracy_estimated":False,
            "n_independent_biological_effect_tests":0,
            "NEON_access_no_longer_required":True,
            "product_A_M5_unchanged_and_product_B_blocked":True,
            "biological_promotion_authorized":False}


def run(out:Path,train_dir:Path,train_cfg_file:Path,source_cfg_file:Path,fetcher=None,downloader=None)->dict:
    out.mkdir(parents=True,exist_ok=True)
    oldcfg=json.loads(train_cfg_file.read_text())
    params=json.loads(source_cfg_file.read_text())
    joint.verify_config(oldcfg)
    validate_settings(params)
    priorcsv=train_dir/"fia_new_cohort_joint_source_only_county_stable_v2.csv"
    priorreceipt=train_dir/"derived_receipt.json"
    if sha(priorcsv)!=SOURCE_CSV_SHA or sha(priorreceipt)!=SOURCE_RECEIPT_SHA:
        raise ValueError("original prior-response source SHA mismatch")
    train=joint.read_source_only_csv(priorcsv,priorreceipt,oldcfg)
    if len(train)!=89616:
        raise ValueError("fixed original source-only denominator changed")
    metadata={"program":"fia_PA_MI_first_source_only_one_shot_v1",
              "holdout_states":list(STATES),"training_states":list(TRAIN_STATES),
              "no_TREE_DIA_STATUSCD_access":True,"n_original_training_source_rows":len(train),
              "original_train_csv_sha256":SOURCE_CSV_SHA,
              "original_train_receipt_sha256":SOURCE_RECEIPT_SHA,
              "source_status":"initially_unavailable",
              "no_previous_FIA_biological_outcome_reopened":True}
    try:
        index,baseline,noaaqc=fetch_exact_noaa(out,downloader)
        metadata["NOAA"] = noaaqc
        allrows=[]
        for st in STATES:
            row={"state":st,"status":"source_unavailable","source_files":{}}
            metadata.setdefault("holdout_state_receipts",[]).append(row)
            files={}
            for table in ("PLOT","COND","TREE"):
                p,desc=fetch_fia_zip(st,table,out,fetcher=fetcher)
                row["source_files"][table]=desc
                files[table]=(p,desc["csv_member"])
                if sha(p)!=desc["zip_sha256"]:
                    raise ValueError("FIA holdout ZIP bytes modified after source acquisition")
            plots,roots,plotqc=plot_source(*files["PLOT"],st)
            row["plot_source_counts"]=plotqc["counts"]
            row["COND_schema_fields_observed"]=inspect_cond_source_header(*files["COND"])
            data,counts=source_state(st,plots,roots,plotqc["unstable_plot_chains"],*files["TREE"],index,baseline)
            row.update({"status":"source_only_ready",**counts})
            allrows.extend(data)
        if len(allrows)<1 or len({r["state"] for r in allrows})!=len(STATES):
            raise ValueError("at least one fixed holdout state has no source species interval rows")
        seen=set()
        for row in allrows:
            key=(row["species_code"],row["state"],row["interval_id"])
            if key in seen:raise ValueError("duplicate species×state×plot interval")
            seen.add(key)
        outcsv=out/"PA_MI_external_source_only_taxon_plot_intervals.csv"
        with outcsv.open("w",encoding="utf-8",newline="") as fh:
            wr=csv.DictWriter(fh,fieldnames=OUTPUT_COLS,lineterminator="\n")
            wr.writeheader()
            wr.writerows(sorted(allrows,key=lambda r:(int(r["species_code"]),r["state"],
                    r["county_fips"],r["plot_chain_id"],r["interval_id"])))
        report=compare_train_holdout(train,allrows,oldcfg)
        report["status"]="source_only_complete_not_biological_efficacy"
        report["holdout_source_csv_sha256"]=sha(outcsv)
        report["holdout_source_rows"]=len(allrows)
        report["holdout_states_present"]=sorted({r["state"] for r in allrows})
        report["NOAA_derived_county_month_csv_sha256"]=metadata["NOAA"]["derived_sha256"]
        metadata["source_status"]="complete_source_only"
        metadata["holdout_source_rows"]=len(allrows)
        metadata["source_csv_sha256"]=sha(outcsv)
        (out/"PA_MI_external_source_gate_result_v1.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    except Exception as exc:
        metadata["source_status"]="source_unavailable_or_invalid_stop_no_outcome"
        metadata["source_stop_error"]=type(exc).__name__+": "+str(exc)[:260]
        (out/"PA_MI_external_source_only_taxon_plot_intervals.csv").unlink(missing_ok=True)
        report={"program":"fia_unopened_PA_MI_external_source_only_common_support_v1",
                "status":"source_unavailable_or_invalid_stop_no_biological_outcome",
                "source_stop_error_class":type(exc).__name__,
                "holdout_species_support_not_zero_but_unknown":True,
                "n_independent_biological_effect_tests":0,
                "biological_promotion_authorized":False}
        (out/"PA_MI_external_source_gate_result_v1.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    (out/"PA_MI_source_receipt_v1.json").write_text(json.dumps(metadata,sort_keys=True,indent=2)+"\n")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--training-source",required=True,type=Path)
    p.add_argument("--training-config",type=Path,default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    p.add_argument("--holdout-config",type=Path,default=Path("configs/fia_PA_MI_external_source_only_v1.json"))
    a=p.parse_args()
    report=run(a.out,a.training_source,a.training_config,a.holdout_config)
    print("EXTERNAL PA/MI",report["status"],
          "eligible primary 5 in both holdouts",report.get("n_primary_both_holdout_states_source_eligible"),
          "no growth/mortality opened")
    if report["status"]!="source_only_complete_not_biological_efficacy":
        raise SystemExit(2)


if __name__=="__main__":
    main()
