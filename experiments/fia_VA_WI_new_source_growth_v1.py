"""Two-phase new-FIA-source VA/WI growth comparison; original v4 is closed.

A: open only county/date/identity/forest metadata; persist SHA of each fresh
FIA PLOT/COND/TREE ZIP and test the full five-primary-taxon 5-fold source
gate BEFORE reading TREE.DIA/STATUSCD.
B: read outcomes from the SAME verified local ZIP bytes, conditional on
surviving linked trees; fit the frozen stationary vs WI-specific climate
association contrast. This is post-prior-outcome exploratory, NOT independent
biological replication or physiology.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

import fia_climate_tree_source_gate_v3 as gate
import fia_climate_density_growth_v1 as growth_reader
import fia_joint_source_only_v1 as source_only
import fia_VA_WI_county_source_folds_v1 as pre
import fia_shared_vs_regional_growth_core_v1 as model

STATES = ("VA", "WI")
SPECIES = tuple(gate.SPECIES)
PRIMARY = model.SPECIES
NOAA_CSV_SHA256 = "623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8"
PROGRAM = "fia_VA_WI_new_source_two_phase_conditional_growth_v1"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_contract(cfg: dict) -> None:
    required = {
        "study": PROGRAM,
        "states": list(STATES),
        "taxa_denominator": list(SPECIES),
        "primary_five_species": list(PRIMARY),
        "geographic_folds": 5,
        "county_split": "first4bytes_sha256_county_FIPS_mod5",
        "models": list(model.MODELS),
        "endpoint": "log_diameter_growth_per_year_conditional_linked_live_to_live",
        "min_practical_shared_and_region_rmse_gain_percent": 1.0,
        "n_bootstrap": 399,
        "NOAA_snapshot": "20261006",
        "NOAA_csv_sha256": NOAA_CSV_SHA256,
        "min_outcome_train_pairs_per_state": model.MIN_TRAIN_TREE_PAIRS_PER_STATE,
        "min_outcome_test_pairs_per_state": model.MIN_TEST_TREE_PAIRS_PER_STATE,
        "min_outcome_train_counties_per_state": model.MIN_TRAIN_COUNTIES,
        "min_outcome_test_counties_per_state": model.MIN_TEST_COUNTIES,
        "min_outcome_test_unique_plot_chains_per_state": model.MIN_TEST_PLOTS,
        "source_only_gate_requires_all_primary_25_folds": True,
        "no_RI_tree_outcomes_opened": True,
        "historical_v4_cannot_be_reinterpreted": True,
        "new_source_version_not_independent_individual_sample": True,
        "scientific_status": "postpriorFIAoutcome_exploratory_noncausal_development",
    }
    for k,v in required.items():
        if cfg.get(k) != v:
            raise ValueError("frozen scientific contract mismatch: " + k)
    if cfg.get("no_automatic_rerun_after_failure") is not True:
        raise ValueError("missing one-shot execution contract")


def no_outcome_source_phase(outdir: Path, climate: dict, county_baseline: dict,
                            support_cfg: dict, *, fetcher=None) -> tuple[dict,dict,list[dict]]:
    outdir.mkdir(parents=True,exist_ok=True)
    sources = []
    paths = {}
    src_rows = []
    for state in STATES:
        record = {"state": state, "status": "source_unavailable",
                  "TREE_DIA_STATUSCD_unread": True}
        sources.append(record)
        files = {}
        paths[state] = files
        try:
            for table in ("PLOT","COND","TREE"):
                info, filepath = gate.fetch_zip(state,table,outdir,fetcher=fetcher)
                record[table.lower()+"_source"] = info
                if info["status"]!="ready":
                    raise ValueError(state+" "+table+" source unavailable "+str(info.get("error")))
                files[table] = (filepath, info["member"])
            # PLOT/COND are source context and do not read TREE response.
            plots, counts = gate.read_plots(*files["PLOT"],state,climate)
            record["plot_climate"] = counts
            _, cond_count = gate.read_conds(*files["COND"])
            record["prior_forest_source_context"] = cond_count
            plot_meta = source_only.read_plots_identity(*files["PLOT"],state)
            prior_ids = {old for old,county,exposure in plots.values()}
            species, counts_tree = source_only.read_tree_species_only(*files["TREE"],prior_ids)
            record["prior_visit_tree_species_identity"] = counts_tree
            observed = source_only.assemble_source_rows(
                 state,plots,plot_meta,species,county_baseline)
            record["n_source_taxon_plot_intervals"] = len(observed)
            record["status"]="source_only_ready"
            src_rows.extend(observed)
        except Exception as e:
            record["status"]="source_stop"
            record["reason"]=f"{type(e).__name__}: {str(e)[:350]}"
    if len(sources)!=2 or any(x["status"]!="source_only_ready" for x in sources):
        info = {"program": PROGRAM, "status":"source_stop_no_tree_response_opened",
                "sources":sources,"n_source_states_ready":sum(x["status"]=="source_only_ready" for x in sources),
                "TREE_DIA_STATUSCD_unread":True,"biological_promotion_authorized":False}
        (outdir/"source_phase_receipt.json").write_text(json.dumps(info,indent=2,sort_keys=True)+"\n")
        return info, paths, []

    # Uniform complete plot-chain exclusion, NEVER chosen by observed response
    # or climate. Preserve both pre-QC and post-QC source denominators.
    counties=defaultdict(set)
    for row in src_rows:
        counties[(row["state"],row["plot_chain_id"])].add(row["county_fips"])
    unstable={k for k,v in counties.items() if len(v)>1}
    original=list(src_rows)
    src_rows=[r for r in original if (r["state"],r["plot_chain_id"]) not in unstable]
    removed=[r for r in original if (r["state"],r["plot_chain_id"]) in unstable]
    if not src_rows:
        raise ValueError("no source rows after fixed county-stability rule")
    seen=set()
    for row in src_rows:
        key=(row["species_code"],row["state"],row["interval_id"])
        if key in seen:
            raise ValueError("duplicate pre-response source taxon-state-plot interval")
        seen.add(key)
    # Source plot eligibility before any tree responses.
    source_gate=pre.evaluate(src_rows,support_cfg)
    complete=source_gate["source_ready_primary_taxon_fold_cells"]==25
    source_file=outdir/"new_source_only_taxon_plot_intervals.csv"
    with source_file.open("w",newline="",encoding="utf-8") as f:
        cols=sorted(source_only.COLUMNS)
        writer=csv.DictWriter(f,fieldnames=cols,lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(src_rows,key=lambda r:
             (int(r["species_code"]),r["state"],r["county_fips"],
              r["plot_chain_id"],r["interval_id"])))
    (outdir/"source_county_folds_pre_response.json").write_text(
        json.dumps(source_gate,sort_keys=True,indent=2)+"\n")
    receipt={"program":PROGRAM,
             "status":"source_ready_before_tree_response" if complete
                      else "source_insufficient_no_tree_response_opened",
             "sources":sources,"n_source_states_ready":2,
             "source_rows_before_county_QC":len(original),
             "source_rows_after_county_QC":len(src_rows),
             "excluded_county_unstable_plot_chains":len(unstable),
             "excluded_county_unstable_source_rows":len(removed),
             "counties_unstable_plot_chain_sha256":
                 sorted(hashlib.sha256((a+"|"+b).encode()).hexdigest() for a,b in unstable),
             "source_only_csv_sha256":sha(source_file),
             "source_county_folds_pre_response_sha256":sha(outdir/"source_county_folds_pre_response.json"),
             "no_TREE_DIA_or_STATUSCD_read":True,
             "complete_primary_25_source_folds_before_response":complete,
             "n_primary_source_eligible_folds":source_gate["source_ready_primary_taxon_fold_cells"],
             "new_upstream_ZIP_version_not_independent_raw_tree_sample":True,
             "old_FIA_v4_response_untouched":True,
             "biological_promotion_authorized":False}
    (outdir/"source_phase_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return receipt, paths, src_rows


def biological_outcome_phase(receipt: dict, paths: dict, source_rows: list[dict],
                             climate: dict, support_cfg: dict, outdir: Path) -> dict:
    if receipt.get("status")!="source_ready_before_tree_response":
        return {"status":"not_opened_source_gate_failed",
                "n_primary_complete":0,"biological_promotion_authorized":False}
    # No network call occurs between the frozen receipt barrier and opening.
    for row in receipt["sources"]:
        state=row["state"]
        for table in ("PLOT","COND","TREE"):
            filename, member=paths[state][table]
            if sha(filename)!=row[table.lower()+"_source"]["sha256"]:
                raise ValueError("FIA raw source changed after SHA receipt before outcome opening")
    baseline=growth_reader.baseline_climate(climate)
    frames=[]
    reports=[]
    for state in STATES:
        files=paths[state]
        plots, qc_plot=gate.read_plots(*files["PLOT"],state,climate)
        dates=growth_reader.read_plot_aux(*files["PLOT"],plots)
        conditions=growth_reader.read_conditions(*files["COND"])
        df,qc=growth_reader.tree_outcomes(*files["TREE"],plots,dates,conditions,baseline,state)
        frames.append(df)
        reports.append({"state":state,"status":"conditional_survivor_response_opened",
                        "n_growth_pairs_selected_before_source_QC":len(df),
                        "growth_source_QC":qc})
    combined=pd.concat(frames,ignore_index=True)
    keys={(r["species_code"],r["state"],r["interval_id"]) for r in source_rows}
    original_rows=len(combined)
    joined=combined.apply(lambda x:(str(x.sp),str(x.state),str(x["plot"])) in keys,axis=1)
    clean=combined.loc[joined].reset_index(drop=True)
    # Differences are expected only from the source-only county-unstable
    # chain exclusion. Never call a tree death/missing occurrence zero growth.
    excluded=original_rows-len(clean)
    # The selected derived growth input is archived as a rerunnable numeric
    # input: no raw tree CN, no precise plot coordinates, no full FIA ZIP.
    selected=clean.loc[clean.sp.isin(PRIMARY)].reset_index(drop=True)
    deriv=model.attach_source_to_growth(selected,source_rows)
    columns=["sp","state","plot","county","year_centered","interval",
             "ln_dia10","age60","ba100","tanom3","panom200","growth",
             "plot_chain_sha256","county_fold"]
    derived_file=outdir/"primary_five_conditional_growth_inputs_v1.csv"
    deriv.loc[:,columns].to_csv(derived_file,index=False,float_format="%.16g")
    response=model.evaluate(clean,source_rows,support_cfg)
    response["primary_five_conditional_growth_inputs_csv_sha256"]=sha(derived_file)
    response["primary_five_conditional_growth_inputs_rows"]=len(deriv)
    response["raw_TREE_zip_not_archived"]=True
    response.update({
        "first_open_state":receipt["status"],
        "source_phase_receipt_sha256":sha(outdir/"source_phase_receipt.json"),
        "source_county_folds_pre_response_sha256":sha(outdir/"source_county_folds_pre_response.json"),
        "n_growth_pairs_before_prior_source_join":original_rows,
        "n_growth_pairs_after_prior_source_join":len(clean),
        "n_growth_pairs_missing_prior_source_identity":excluded,
        "state_growth_data_qc":reports,
        "no_RI_biological_outcomes_opened":True,
        "not_independent_replication_of_prior_v4":True,
        "status_transition_rates_not_estimated":True,
        "product_B_remains_blocked":True})
    return response


def run(outdir: Path, noaa_csv: Path, noaa_receipt: Path,
        support_config: Path, science_config: Path, *, fetcher=None) -> dict:
    outdir.mkdir(parents=True,exist_ok=True)
    contract=json.loads(science_config.read_text(encoding="utf-8"))
    verify_contract(contract)
    support=json.loads(support_config.read_text(encoding="utf-8"))
    gate_source=importlib.util.spec_from_file_location("source_only_gate_helper",
                          Path(__file__).parent/"fia_joint_support_gate_v1.py")
    # Verify unmodified source schema and original 13-taxonomy/3-state
    # design, even though the new response is VA/WI only.
    import fia_joint_support_gate_v1 as common
    common.verify_config(support)
    original=json.loads(noaa_receipt.read_bytes())
    if (original.get("study")!="fia_noaa_county_climate_pre_response_v1" or
        original.get("snapshot")!="20261006" or
        original.get("climate_csv_rows")!=43890 or
        sha(noaa_csv)!=NOAA_CSV_SHA256 or
        sha(noaa_csv)!=original.get("climate_csv_sha256")):
        raise ValueError("independent frozen NOAA snapshot invalid")
    climate=gate.load_climate(noaa_csv)
    climate_baseline=source_only.baselines(climate)
    with tempfile.TemporaryDirectory(prefix="sdmr_VA_WI_source_then_growth_") as tmp:
        source, paths, rows=no_outcome_source_phase(Path(tmp),climate,climate_baseline,
                                                    support,fetcher=fetcher)
        for name in ("source_phase_receipt.json","source_county_folds_pre_response.json",
                     "new_source_only_taxon_plot_intervals.csv"):
            file=Path(tmp)/name
            if file.exists():
                (outdir/name).write_bytes(file.read_bytes())
        if source["status"]!="source_ready_before_tree_response":
            result={"program":PROGRAM, "status":source["status"],
                    "n_primary_complete":0,
                    "no_biological_outcomes_opened":True,
                    "biological_promotion_authorized":False}
        else:
            try:
                result=biological_outcome_phase(source,paths,rows,climate,support,Path(tmp))
                derived=Path(tmp)/"primary_five_conditional_growth_inputs_v1.csv"
                if derived.exists():
                    (outdir/derived.name).write_bytes(derived.read_bytes())
                result["status"]="postsource_exploratory_growth_opened"
                # Archive (with hashed plot references) model-design data so
                # numeric rechecks need not rely on mutable upstream ZIP bytes.
            except Exception as exc:
                result={"program":PROGRAM,"status":"response_opened_but_analysis_failed_closed",
                        "failure":f"{type(exc).__name__}: {str(exc)[:320]}",
                        "n_primary_complete":0,
                        "do_not_promote_partial_response_results":True,
                        "biological_promotion_authorized":False}
        (outdir/"VA_WI_growth_result_v1.json").write_text(
            json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(result["status"],"complete primary taxa",result.get("n_primary_complete"))
        return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",type=Path,required=True)
    p.add_argument("--noaa-csv",type=Path,default=Path("results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv"))
    p.add_argument("--noaa-receipt",type=Path,default=Path("results/fia_noaa_county_climate_v1/source_receipt.json"))
    p.add_argument("--support-config",type=Path,default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    p.add_argument("--science-config",type=Path,default=Path("configs/fia_VA_WI_shared_regional_growth_v1.json"))
    args=p.parse_args()
    result=run(args.outdir,args.noaa_csv,args.noaa_receipt,args.support_config,args.science_config)
    if result.get("status") not in ("postsource_exploratory_growth_opened",):
        raise SystemExit(2)


if __name__=="__main__":
    main()
