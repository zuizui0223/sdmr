#!/usr/bin/env python3
"""Independent, post-outcome case-level audit; no model fitting or parameter tuning.

Reads only sealed GitHub Actions case/artifact ZIPs and the declared aggregate.
Checks source SHA-256 receipts, fixed denominators, states, and independently
recomputes the population-reference vs consensus confusion matrices.
The ODO reference is NOT causal generating-process truth.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, zipfile
from collections import Counter
from pathlib import Path

STATES={"replaceable","contributory","required","unresolved","unavailable"}
POS={"contributory","required"}
SHARP={"replaceable","contributory","required"}
SPLITS=("random_cell","spatial")
LEARNERS=("shallow3_hgb","standardized_isotropic_l2")


def verify_and_derive(artifacts:Path, aggregate_zip:Path, output:Path):
    output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(aggregate_zip) as z:
        assert z.testzip() is None
        d=json.loads(z.read("aggregate.json"))
    assert d["schema"]=="sdmr.matched_known_truth_split.aggregate.v1"
    assert d["original_v5_promotion"]=="failed_closed"
    assert d["declared_fit_count"]==2016
    receipts={(int(r["seed"]),r["world"]):r for r in d["source_receipts"]}
    assert len(receipts)==24
    cases=[]
    for path in sorted(artifacts.glob("matched*.zip")):
        if path==aggregate_zip: continue
        with zipfile.ZipFile(path) as z:
            if set(z.namelist())!={"case.json","finite_frozen_before_oracle.json"}:continue
            assert z.testzip() is None
            cb=z.read("case.json")
            fb=z.read("finite_frozen_before_oracle.json")
        case=json.loads(cb)
        k=(int(case["seed"]),case["world"])
        assert k in receipts,(path,k)
        rec=receipts[k]
        assert hashlib.sha256(cb).hexdigest()==rec["case_sha256"],k
        assert hashlib.sha256(fb).hexdigest()==rec["finite_receipt_sha256"],k
        assert case["finite_receipt_sha256"]==rec["finite_receipt_sha256"]
        assert case["prospective"] is True and case["original_v5_promotion"]=="failed_closed"
        assert case["M5_original_evidence_changed"] is False
        finite=json.loads(fb)
        assert finite["prospective"] is True
        assert finite["status"]=="finite_frozen_before_reference_opening"
        assert finite["reference_truth_read_by_learner"] is False
        assert (int(finite["seed"]),finite["world"])==k
        assert set(case["oracle"])==set(case["consensus"]["spatial"])
        assert set(case["oracle"])==set(case["consensus"]["random_cell"])
        assert len(case["oracle"])==6
        assert set(case["authorization"])==set(SPLITS)
        for mode in SPLITS:
            assert set(case["per_learner_authorization"][mode])==set(LEARNERS)
            assert set(case["per_learner_states"][mode])==set(LEARNERS)
            for proc in case["oracle"]:
                assert case["oracle"][proc] in STATES
                assert case["consensus"][mode][proc] in STATES
                a=case["per_learner_states"][mode][LEARNERS[0]][proc]
                b=case["per_learner_states"][mode][LEARNERS[1]][proc]
                expected=("unavailable" if "unavailable" in (a,b) else a if a==b and a in SHARP else "unresolved")
                assert expected==case["consensus"][mode][proc],(k,mode,proc,a,b,expected)
        assert case["authorization"][mode] is not None
        cases.append(case)
    assert len(cases)==24, len(cases)
    assert len({(x["seed"],x["world"]) for x in cases})==24
    assert set(receipts)=={(int(x["seed"]),x["world"]) for x in cases}
    assert {int(c["seed"]) for c in cases}=={91001,91002,91003}
    assert len({c["world"] for c in cases})==8
    cells=[]
    for c in cases:
        for mode in SPLITS:
            for proc,oracle in c["oracle"].items():
                con=c["consensus"][mode][proc]
                cells.append({"seed":c["seed"],"world":c["world"],"process":proc,
                    "split":mode,"oracle_state":oracle,
                    "hgb_state":c["per_learner_states"][mode]["shallow3_hgb"][proc],
                    "standardized_L2_state":c["per_learner_states"][mode]["standardized_isotropic_l2"][proc],
                    "joint_state":con,"joint_authorized":int(c["authorization"][mode]),
                    "HGB_authorized":int(c["per_learner_authorization"][mode]["shallow3_hgb"]),
                    "standardized_L2_authorized":int(c["per_learner_authorization"][mode]["standardized_isotropic_l2"]),
                    "oracle_positive":int(oracle in POS),"consensus_positive":int(con in POS),
                    "joint_positive_recovered":int(oracle in POS and con in POS),
                    "overresolution":int(oracle=="unresolved" and con in SHARP),
                    "false_positive_on_replaceable":int(oracle=="replaceable" and con in POS)})
    assert len(cells)==288
    oracle_counts=Counter(c["oracle_state"] for c in cells if c["split"]=="random_cell")
    assert oracle_counts=={"replaceable":105,"contributory":12,"unresolved":9,"unavailable":18}
    independent={}
    for mode in SPLITS:
        z=[x for x in cells if x["split"]==mode]
        counts=Counter(x["joint_state"] for x in z)
        joint=sum(c["authorization"][mode] for c in cases)
        pos=sum(x["joint_positive_recovered"] for x in z)
        over=sum(x["overresolution"] for x in z)
        false=sum(x["false_positive_on_replaceable"] for x in z)
        assert joint==d["summary"][mode]["joint_authorized"]["numerator"]
        assert pos==d["summary"][mode]["positive_recovery"]["numerator"]
        assert over==d["summary"][mode]["overresolution_on_unresolved"]["numerator"]
        assert false==d["summary"][mode]["false_positive_on_replaceable"]["numerator"]
        assert dict(counts)=={k:v for k,v in d["summary"][mode]["state_counts"].items() if v}
        independent[mode]={"joint_authorized":joint,"sharp":sum(counts[s] for s in SHARP),
            "positive_recovery":pos,"oracle_positive_denominator":12,
            "false_positive_on_replaceable":false,"oracle_replaceable_denominator":105,
            "overresolution_on_unresolved":over,"oracle_unresolved_denominator":9,
            "sharp_on_unavailable":sum(x["oracle_state"]=="unavailable" and x["joint_state"] in SHARP for x in z),
            "oracle_unavailable_denominator":18,"counts":dict(counts)}
    pair=[]
    for c in sorted(cases,key=lambda x:(x["world"],x["seed"])):
        pair.append({"world":c["world"],"seed":c["seed"],
          "random_sharp":sum(x in SHARP for x in c["consensus"]["random_cell"].values()),
          "spatial_sharp":sum(x in SHARP for x in c["consensus"]["spatial"].values())})
    assert sum(x["random_sharp"]-x["spatial_sharp"] for x in pair)==18
    assert all(x["random_sharp"]>=x["spatial_sharp"] for x in pair)
    out={"schema":"sdmr.matched_kt.independent_receipt_and_crosswalk_audit.v1",
        "source_workflow_run":38192262406,"source_aggregate_artifact_id":11722575098,
        "source_aggregate_zip_sha256":hashlib.sha256(aggregate_zip.read_bytes()).hexdigest(),
        "checked_case_zips":24,"checked_process_split_cells":288,
        "oracle_reference":"observational-distribution information state approximation; NOT biological generating-cause labels",
        "summary":independent,"paired_cases":pair,
        "status":"verified_from_all_24_individual_case_SHA256_receipts"}
    with open(output/"crosswalk_288_cells.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(cells[0]));w.writeheader();w.writerows(sorted(cells,key=lambda x:(x["world"],x["seed"],x["process"],x["split"])))
    (output/"independent_audit_summary.json").write_text(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"summary":independent},ensure_ascii=False,indent=2))
    return out

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--artifacts",type=Path,default=Path("/mnt/data"))
    ap.add_argument("--aggregate",type=Path,default=Path("/mnt/data/SDMR_Matched_KT_Prospective_24cases_2026-10-12.zip"))
    ap.add_argument("--output",type=Path,default=Path("/mnt/data/sdmr_matched_kt_v1_audit"))
    a=ap.parse_args();verify_and_derive(a.artifacts,a.aggregate,a.output)
