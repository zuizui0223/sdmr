"""Exact environmental-opportunity mechanism for geographic limiting-axis switches.

Given a STATIONARY, HYPOTHETICAL fitness penalty in both regions,
  -log(fitness) = w_T * |(T - T_opt)/sigma_T|**p
                + w_W * |(W - W_opt)/sigma_W|**p,
this computes equal-area EXPECTED component penalties over predeclared source
rectangles, not real limiting factors or fitted biological parameters.

For regional mean standardized losses A_T, A_W, temperature is the larger
component iff w_T/w_W > A_W/A_T.  If two regions have distinct thresholds,
there is an analytic interval of INVARIANT w_T/w_W giving a driver switch.

No focal occurrence, sentinel effort or collection outcome is ever consulted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EXPECTED_SOURCE_SHA256 = "42747f07c030a09134a08703bf20e60a73fe661468c2047ccc1c1fd7628b85aa"
REGION_PAIRS = {
    "Quercus robur": ("quercus_DE_central", "quercus_SE_south"),
    "Pinus sylvestris": ("pinus_ES_central", "pinus_FI_central"),
}
REQUIRED = ("region", "cell_id", "temperature", "moisture")
ILLUSTRATION = {"temperature_optimum_c": 9.0, "precipitation_optimum_mm": 900.0,
                "thermal_scale_c": 3.0, "precipitation_scale_mm": 250.0,
                "relative_thermal_weight": 1.0}
# Equal-weight ranges are a post-source SENSITIVITY GRID, not a prior distribution.
GRID_T = tuple(5.0 + 0.5 * i for i in range(17))  # 5...13 C
GRID_W = tuple(700.0 + 50.0 * i for i in range(9))  # 700...1100 mm


def validate_availability(frame: pd.DataFrame) -> pd.DataFrame:
    """Require the full fixed rectangle panel; discard every response column."""
    missing = sorted(set(REQUIRED) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing environmental source columns: {missing}")
    df = frame.loc[:, REQUIRED].copy()
    df["region"] = df.region.astype(str)
    df["cell_id"] = df.cell_id.astype(str)
    expected = {r for pair in REGION_PAIRS.values() for r in pair}
    if set(df.region) != expected:
        raise ValueError("Fixed four-region environmental denominator is incomplete or changed")
    if df.duplicated(["region", "cell_id"]).any():
        raise ValueError("Duplicate regional equal-area climate cell")
    for v in ("temperature", "moisture"):
        df[v] = pd.to_numeric(df[v], errors="coerce")
        if not np.isfinite(df[v].to_numpy(float)).all():
            raise ValueError(f"Nonfinite climate field: {v}")
    if not all(int(g.shape[0]) >= 2 for _, g in df.groupby("region")):
        raise ValueError("Each available region must have at least two cells")
    return df.sort_values(["region", "cell_id"], kind="mergesort").reset_index(drop=True)


def component_losses(region: pd.DataFrame, *, t_opt: float, w_opt: float,
                     t_scale: float, w_scale: float, power: int) -> tuple[float, float]:
    if not np.isfinite([t_opt, w_opt, t_scale, w_scale]).all() or t_scale <= 0 or w_scale <= 0:
        raise ValueError("Finite optima and strictly positive scales required")
    if power not in (1, 2):
        raise ValueError("Only absolute and quadratic stationary penalties are declared")
    t = float(np.mean(np.abs((region.temperature.to_numpy(float) - t_opt) / t_scale) ** power))
    w = float(np.mean(np.abs((region.moisture.to_numpy(float) - w_opt) / w_scale) ** power))
    return t, w


def threshold_for_thermal_dominance(t_loss: float, w_loss: float) -> float:
    if t_loss < 0 or w_loss < 0:
        raise ValueError("Losses must be nonnegative")
    return float(w_loss / t_loss) if t_loss > 0 else float("inf")


def evaluate_pair(a: pd.DataFrame, b: pd.DataFrame, *, params: dict, power: int) -> dict[str, Any]:
    t0, w0 = params["temperature_optimum_c"], params["precipitation_optimum_mm"]
    st, sw = params["thermal_scale_c"], params["precipitation_scale_mm"]
    ratio = float(params["relative_thermal_weight"])
    if ratio <= 0 or not np.isfinite(ratio):
        raise ValueError("Relative thermal weight must be positive and finite")
    av = []
    for g in (a, b):
        temp, moisture = component_losses(g, t_opt=t0, w_opt=w0,
                                          t_scale=st, w_scale=sw, power=power)
        gap = ratio * temp - moisture
        av.append({"thermal_mean_penalty":temp, "moisture_mean_penalty":moisture,
                   "thermal_minus_moisture":float(gap),
                   "critical_thermal_to_moisture_weight":threshold_for_thermal_dominance(temp, moisture),
                   "dominant_hypothetical_penalty":("thermal" if gap > 1e-12 else
                                                    "moisture" if gap < -1e-12 else "tie")})
    l, h = sorted(x["critical_thermal_to_moisture_weight"] for x in av)
    inter = bool(np.isfinite(l) and np.isfinite(h) and h-l > 1e-12)
    t_a = (float(a.temperature.min()),float(a.temperature.max()))
    t_b = (float(b.temperature.min()),float(b.temperature.max()))
    width = max(0.0, min(t_a[1],t_b[1])-max(t_a[0],t_b[0]))
    return {"penalty_power":power, "regions":av,
            "switch_possible_for_fixed_identical_response_weights":inter,
            "critical_weight_open_interval":([float(l),float(h)] if inter else None),
            "fixed_weight_within_switch_interval":bool(inter and l < ratio < h),
            "fixed_weight_observed_opportunity_reversal":bool(av[0]["thermal_minus_moisture"] *
                                                             av[1]["thermal_minus_moisture"] < -1e-12),
            "raw_temperature_overlap_c":width}


def study(frame: pd.DataFrame, *, source_sha256: str) -> dict[str, Any]:
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("Environmental source bytes do not match archived first-open receipt")
    df = validate_availability(frame)
    results = []
    for taxon, (a_name, b_name) in REGION_PAIRS.items():
        a = df.loc[df.region == a_name]
        b = df.loc[df.region == b_name]
        curves = {}
        for power,label in ((2,"quadratic"),(1,"absolute")):
            e = evaluate_pair(a,b,params=ILLUSTRATION,power=power)
            n_cross = 0
            for t0 in GRID_T:
                for w0 in GRID_W:
                    p = dict(ILLUSTRATION, temperature_optimum_c=t0,
                             precipitation_optimum_mm=w0)
                    temp_a,water_a=component_losses(a,t_opt=t0,w_opt=w0,t_scale=p["thermal_scale_c"],
                                                    w_scale=p["precipitation_scale_mm"],power=power)
                    temp_b,water_b=component_losses(b,t_opt=t0,w_opt=w0,t_scale=p["thermal_scale_c"],
                                                    w_scale=p["precipitation_scale_mm"],power=power)
                    if (temp_a-water_a)*(temp_b-water_b) < -1e-12:
                        n_cross += 1
            e["sensitivity_grid"] = {"temperature_optima_c":list(GRID_T),
                                     "precipitation_optima_mm":list(GRID_W),
                                     "n_grid_points":len(GRID_T)*len(GRID_W),
                                     "n_driver_reversals_under_fixed_weight":n_cross,
                                     "fraction_grid_points_driver_reversal_not_probability":
                                     n_cross/(len(GRID_T)*len(GRID_W))}
            curves[label] = e
        results.append({"taxon_label_for_climate_source_only":taxon,
                        "regions":[a_name,b_name],"climate_cell_counts":[len(a),len(b)],
                        "fixed_hypothetical_response":curves})
    return {"analysis":"stationary_niche_constraint_switch_geometry_v1",
            "source_sha256":source_sha256,"n_equal_area_climate_cells":len(df),
            "hypothetical_fitness_parameters_not_species_measured":ILLUSTRATION,
            "response_function":"loss = weight_T * abs((T-Topt)/Tscale)^p + weight_W * abs((P-Popt)/Pscale)^p",
            "same_response_in_both_regions":True,"uses_occurrence_or_effort_columns":False,
            "environmental_source": "CHELSA v2.1 BIO1 and BIO12, 1981-2010; four predeclared source rectangles",
            "limits": ["Hypothetical optima, scales, weights and penalty shapes are not measured plant traits",
                       "Equal-area geographic rectangles are not validated taxon accessible M",
                       "A regional mean penalty is not actual physiological limitation or realized niche adaptation",
                       "The sensitivity grid is post-source and does not represent a prior or ecological frequency",
                       "No claim that observed plants have different realized or fundamental niches",
                       "Disjoint temperature support prevents a within-shared-support empirical response comparison"],
            "results":results}


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    raw=args.source.read_bytes()
    receipt=study(pd.read_csv(args.source),source_sha256=hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    for r in receipt["results"]:
        print(r["taxon_label_for_climate_source_only"],r["regions"])
        for model_name,z in r["fixed_hypothetical_response"].items():
            print("  ",model_name,z["critical_weight_open_interval"],
                  z["fixed_weight_observed_opportunity_reversal"],
                  z["sensitivity_grid"]["n_driver_reversals_under_fixed_weight"],"/",
                  z["sensitivity_grid"]["n_grid_points"])


if __name__ == "__main__":
    main()
