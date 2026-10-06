#!/usr/bin/env python3
"""Build all four MEE submission figures from frozen M5 definitions/results."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_METRICS=ROOT/"results"/"sdmr_v6_prospective_kt_v2_metrics.json"

def load_metrics(path:Path)->dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("program")!="sdmr-v6-prospective-known-truth-v2":
        raise ValueError("wrong M5 metrics program")
    if data.get("passed") is not True:
        raise ValueError("canonical M5 endpoint is not PASS")
    if data.get("prospective_seed_min")!=74001 or data.get("prospective_seed_max")!=74020:
        raise ValueError("prospective seed denominator changed")
    return data

def _box(ax,xy,w,h,text,fontsize=10):
    x,y=xy
    p=FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02",linewidth=1.2,fill=False)
    ax.add_patch(p)
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fontsize,wrap=True)
    return p

def _arrow(ax,a,b):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=14,linewidth=1.1))

def figure1_states(out:Path)->None:
    fig,ax=plt.subplots(figsize=(9.2,5.4))
    ax.set_xlim(0,10); ax.set_ylim(0,6); ax.axis("off")
    _box(ax,(0.3,4.55),2.25,0.8,"Declared predictor\nsystem",11)
    _box(ax,(3.05,4.55),2.4,0.8,"Full-system\ninformation gate",11)
    _box(ax,(6.0,4.55),3.25,0.8,"Matched full vs process-free\nreconstruction routes",11)
    _arrow(ax,(2.55,4.95),(3.05,4.95)); _arrow(ax,(5.45,4.95),(6.0,4.95))
    _box(ax,(0.55,2.0),1.55,0.85,"Replaceable")
    _box(ax,(2.4,2.0),1.55,0.85,"Contributory")
    _box(ax,(4.25,2.0),1.55,0.85,"Required")
    _box(ax,(6.1,2.0),1.55,0.85,"Unresolved")
    _box(ax,(7.95,2.0),1.55,0.85,"Unavailable")
    ax.text(5.0,3.45,"Five process-information states",ha="center",fontsize=12)
    ax.text(1.325,1.5,"adequate process-free\nroute remains",ha="center",va="top",fontsize=8.5)
    ax.text(3.175,1.5,"removal worsens\nall adequate routes",ha="center",va="top",fontsize=8.5)
    ax.text(5.025,1.5,"all process-free\nroutes inadequate",ha="center",va="top",fontsize=8.5)
    ax.text(6.875,1.5,"incomplete, ambiguous\nor nonseparable",ha="center",va="top",fontsize=8.5)
    ax.text(8.725,1.5,"full system itself\nnot informative",ha="center",va="top",fontsize=8.5)
    ax.text(5.0,0.45,"Inference is allowed to abstain rather than convert missing information into a sharp process claim.",ha="center",fontsize=10)
    fig.tight_layout()
    fig.savefig(out,format="svg")
    plt.close(fig)

def figure2_worlds(out:Path)->None:
    worlds=[
      ("unique_process","distinct information","informative"),
      ("redundant_representation","alternative carriers","informative"),
      ("shared_carrier","one carrier, >1 process","informative"),
      ("null_correlated","correlation without membership","informative"),
      ("interaction","non-additive signal","informative"),
      ("observation_confounded","effort confounding","report-only"),
      ("omitted_driver","driver absent from system","null"),
      ("geographic_shift","proxy reverses in transfer","informative"),
    ]
    fig,ax=plt.subplots(figsize=(9.4,5.2))
    ax.axis("off")
    cell_text=[[w.replace("_"," "),challenge,role] for w,challenge,role in worlds]
    table=ax.table(
      cellText=cell_text,
      colLabels=["Known-truth world","Inferential challenge","Authorization role"],
      cellLoc="left",colLoc="left",loc="center",
      colWidths=[0.33,0.43,0.24],
    )
    table.auto_set_font_size(False); table.set_fontsize(9.5); table.scale(1,1.55)
    ax.set_title("Eight prospective known-truth worlds",fontsize=13,pad=14)
    fig.tight_layout()
    fig.savefig(out,format="svg")
    plt.close(fig)

def figure3_denominator(data:dict,out:Path)->None:
    counts=data["counts"]; metrics=data["metrics"]
    labels=["Positive\ntargets","Replaceable\ntargets","Unresolved\ntargets","Unavailable\ntargets","Structural\nrefusal"]
    den=[int(counts[k]) for k in ("positive","replaceable","unresolved","unavailable","structural_refusal")]
    adverse=[
      int(round(den[0]*(1-float(metrics["positive_recovery"])))),
      int(round(den[1]*float(metrics["false_positive_rate"]))),
      int(round(den[2]*float(metrics["overresolution_rate"]))),
      int(round(den[3]*float(metrics["unavailable_sharp_rate"]))),
      int(round(den[4]*float(metrics["structural_refusal_violation_rate"]))),
    ]
    correct=[d-a for d,a in zip(den,adverse)]
    fig,ax=plt.subplots(figsize=(8.4,4.8))
    x=list(range(len(labels)))
    ax.bar(x,correct,label="Recovered / correctly preserved")
    ax.bar(x,adverse,bottom=correct,label="Missed / violated")
    ax.set_xticks(x,labels); ax.set_ylabel("Prospective process-state cells")
    ax.set_title("Prospective denominator and outcomes")
    ymax=max(den)
    for i,(d,a) in enumerate(zip(den,adverse)):
        label="71/80 recovered" if i==0 else f"{a}/{d} violations"
        ax.text(i,d+ymax*0.018,label,ha="center",va="bottom",fontsize=9)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out,format="svg")
    plt.close(fig)

def figure4_authorization(data:dict,out:Path)->None:
    rates=data["informative_control_authorization_rates"]
    names=list(rates)
    values=[float(rates[n]) for n in names]
    names.extend(["omitted_driver","observation_confounded\n(report-only)"])
    values.extend([
      float(data["metrics"]["w7_authorization_rate"]),
      float(data["metrics"]["report_only_world_authorization_rate"]),
    ])
    fig,ax=plt.subplots(figsize=(9.2,4.8))
    x=list(range(len(names)))
    ax.bar(x,values); ax.set_ylim(0,1.08)
    ax.set_xticks(x,[n.replace("_","\n") for n in names])
    ax.set_ylabel("Full-system authorization rate")
    ax.set_title("Full-system authorization separates informative and missing-driver worlds")
    for i,v in enumerate(values):
        ax.text(i,min(1.045,v+0.025),f"{int(round(v*20))}/20",ha="center",va="bottom",fontsize=9)
    fig.tight_layout()
    fig.savefig(out,format="svg")
    plt.close(fig)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--metrics",type=Path,default=DEFAULT_METRICS)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args()
    data=load_metrics(a.metrics)
    a.output_dir.mkdir(parents=True,exist_ok=True)
    figure1_states(a.output_dir/"figure1_process_information_states.svg")
    figure2_worlds(a.output_dir/"figure2_known_truth_worlds.svg")
    figure3_denominator(data,a.output_dir/"figure3_prospective_denominator.svg")
    figure4_authorization(data,a.output_dir/"figure4_world_authorization.svg")
    print(a.output_dir)

if __name__=="__main__":
    main()
