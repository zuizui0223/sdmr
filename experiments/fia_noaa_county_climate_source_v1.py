"""FIA county climate preflight: fixed NOAA nClimDiv county monthly source.

Never opens tree growth, survival or plot-level locations. NOAA county FIPS must not
be confused with *different* nClimDiv state-series identification codes.
The resulting 1991-2025 Apr-Sep monthly temperature and rainfall data are
pre-response ecological exposures, not a fitted effect of climate on growth.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

COLUMNS = ("fips_county", "year", "month", "temperature_c", "precipitation_mm")


def verify_contract(c: dict) -> None:
    if c.get("study") != "fia_noaa_county_climate_pre_response_v1":
        raise ValueError("unrecognized study")
    if c.get("states_fips") != {"RI": "44", "VA": "51", "WI": "55"}:
        raise ValueError("county FIPS states differ from predeclared geographic panel")
    if c.get("snapshot") != "20261006" or c.get("source_variables") != {
        "temperature": {"file": "climdiv-tmpccy-v1.0.0-20261006", "element": "02", "source_units": "degree_fahrenheit"},
        "precipitation": {"file": "climdiv-pcpncy-v1.0.0-20261006", "element": "01", "source_units": "inches_per_month"},
    }:
        raise ValueError("NOAA source snapshot or variable definitions changed")
    if (c.get("year_start"), c.get("year_end"), c.get("baseline_start"), c.get("baseline_end")) != (1991, 2025, 1991, 2020):
        raise ValueError("year/baseline cohort changed")
    if c.get("growing_season_months") != [4,5,6,7,8,9]:
        raise ValueError("growing-season month universe changed")
    if not 40_000_000 <= int(c.get("maximum_single_source_bytes", 0)) <= 100_000_000:
        raise ValueError("archive limit invalid")
    if c.get("claim_level") != "county_level_temperature_precipitation_metadata_only_not_tree_growth_or_causal_niche":
        raise ValueError("unfrozen claim boundary")


def parse_climdiv_county(data: bytes, variable: str, conf: dict):
    """Read NOAA first token FIPS5 + variable element2 + YYYY4; then 12 months.

    Reject missing/suspect values instead of zero-imputing, preserve full
    denominator for all declared months/years/counties.  The county first two
    chars are conventional FIPS codes (44/51/55), *not* NOAA state series IDs.
    """
    vars_ = conf["source_variables"]
    expected_el = vars_[variable]["element"]
    statecodes = set(conf["states_fips"].values())
    months = set(conf["growing_season_months"])
    values = {}
    problems = Counter()
    found_years = defaultdict(set)
    try:
        stream = io.StringIO(data.decode("ascii"))
    except UnicodeDecodeError as exc:
        raise ValueError("non-ASCII NOAA county file") from exc
    n_matching_records = 0
    for line in stream:
        words = line.split()
        if not words:
            continue
        key = words[0]
        if len(key) != 11 or not key.isdigit() or len(words) != 13:
            raise ValueError("malformed NOAA county fixed-width record")
        fips, element, yeartext = key[:5], key[5:7], key[7:]
        if element != expected_el:
            raise ValueError("unexpected element code in "+variable)
        year = int(yeartext)
        if fips[:2] not in statecodes or not conf["year_start"] <= year <= conf["year_end"]:
            continue
        n_matching_records += 1
        if fips[2:] == "000":
            raise ValueError("state total row mistaken for county FIPS")
        county_year = (fips, year)
        if county_year in found_years[fips]:
            raise ValueError("duplicate county/year in NOAA source")
        found_years[fips].add(county_year)
        for month in months:
            try:
                v = float(words[month])
            except ValueError as exc:
                raise ValueError("non numeric NOAA county climate data") from exc
            valid = math.isfinite(v) and v not in (-9.99, -99.99, -999.9, -9999.0)
            if variable == "precipitation":
                valid = valid and 0 <= v <= 1000  # monthly inches, too large is suspicious
                transformed = v * 25.4
            else:
                valid = valid and -80 < v < 145  # NOAA air temperature degrees F
                transformed = (v-32)*5/9
            if not valid:
                problems["missing_or_invalid_"+variable] += 1
                continue
            vkey = (fips, year, month)
            if vkey in values:
                raise ValueError("duplicate county/month in NOAA source")
            values[vkey] = round(transformed, 6)
    return values, {"n_matching_county_year_records": n_matching_records,
                    "n_distinct_counties": len(found_years),
                    "n_invalid_month_values": sum(problems.values()),
                    "invalid_reasons": dict(sorted(problems.items()))}


def merge_validate_temperature_rainfall(t, p, config):
    """Full paired months only, no input source outcomes, no missing→zero."""
    joined = sorted(set(t) & set(p))
    month_population = set(t) | set(p)
    n_unpaired = len(month_population)-len(joined)
    baseline = defaultdict(list)
    for fips,y,m in joined:
        if config["baseline_start"] <= y <= config["baseline_end"]:
            baseline[fips].append((y,m))
    no_baseline = sorted(fips for fips, dates in baseline.items() if len(dates) < 25*6)
    eligible_counties = {fips for fips, dates in baseline.items() if len(dates) >= 25*6}
    by_state = {}
    for state, prefix in config["states_fips"].items():
        counties = {f for f in eligible_counties if f[:2] == prefix}
        if len(counties) < config["minimum_complete_counties"][state]:
            raise RuntimeError(f"{state}: county climate support below independent gate: {len(counties)}")
        count = sum(1 for f,y,m in joined if f in counties)
        by_state[state] = {"n_counties_baseline_complete_25years":len(counties),
                           "n_joined_growing_months":count,"n_county_years_equivalent":count/6}
    rows = [(f,year,month,t[(f,year,month)],p[(f,year,month)])
            for f,year,month in joined if f in eligible_counties]
    return rows, {"n_unpaired_variable_months":n_unpaired,
                  "n_counties_with_incomplete_baseline":len(no_baseline),
                  "n_complete_counties_total":len(eligible_counties),
                  "states":by_state}


def normalize_interval_exposure(rows: list[tuple], fips: str,
                                from_year: int, from_month: int,
                                to_year: int, to_month: int):
    """Whole Apr–Sep months strictly BETWEEN two field measurements.

    Does NOT include either boundary measurement month; a full 6-month season
    is the minimum, and all calendar Apr–Sep months between are required.
    Returns no effect estimate and no extrapolation outside 1991-2025.
    """
    if not (1 <= from_month <= 12 and 1 <= to_month <= 12):
        return None
    a, b = 12*from_year+from_month, 12*to_year+to_month
    if b <= a or b-a > 12*21:
        return None
    lookup = {(ff, yy, mm): (tc, pr) for ff, yy, mm, tc, pr in rows}
    candidates = [(year,month) for year in range(from_year, to_year+1) for month in (4,5,6,7,8,9)
                  if a < 12*year+month < b]
    if len(candidates) < 6 or any((fips,year,month) not in lookup for year,month in candidates):
        return None
    vals = [lookup[(fips,y,m)] for y,m in candidates]
    return {"months":len(vals), "temperature_c_mean":sum(q[0] for q in vals)/len(vals),
            "precipitation_mm_per_six_months":sum(q[1] for q in vals)*6/len(vals),
            "fips_county":fips,
            "measurement_start_excluded":f"{from_year:04d}-{from_month:02d}",
            "measurement_end_excluded":f"{to_year:04d}-{to_month:02d}"}


def _download(url, max_size, fetcher=None):
    if fetcher is not None:
        data = fetcher(url)
    else:
        with urlopen(Request(url,headers={"User-Agent":"sdmr-nclimdiv-county-v1/1"}),timeout=80) as r:
            data = r.read(max_size+1)
    if not isinstance(data,bytes) or len(data)>max_size or not data:
        raise ValueError("NOAA source unavailable or over fixed download cap")
    return data


def run(config_path: Path, output_dir: Path, *, fetcher=None):
    conf = json.loads(config_path.read_bytes())
    verify_contract(conf)
    output_dir.mkdir(parents=True,exist_ok=True)
    samples = {}
    sources = {}
    for variable,meta in conf["source_variables"].items():
        url = conf["archive_base"].rstrip("/")+"/"+meta["file"]
        data = _download(url,conf["maximum_single_source_bytes"],fetcher=fetcher)
        value, stats = parse_climdiv_county(data,variable,conf)
        sources[variable] = {"url":url,"source_sha256":hashlib.sha256(data).hexdigest(),
                             "bytes":len(data),**stats}
        samples[variable] = value
    rows, coverage = merge_validate_temperature_rainfall(samples["temperature"],samples["precipitation"],conf)
    climate_csv = output_dir / "noaa_county_growing_months_1991_2025.csv"
    with climate_csv.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.writer(handle,lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow(row)
    receipt={"study":conf["study"],"no_tree_or_growth_data_opened":True,
             "fips_codes_are_US_state_county_not_NCEI_ordinal_state_codes":True,
             "snapshot":conf["snapshot"],"source_info":sources,"coverage":coverage,
             "climate_csv_sha256":hashlib.sha256(climate_csv.read_bytes()).hexdigest(),
             "climate_csv_rows":len(rows),
             "downstream_plots_require_county_fips_and_pinned_measyear_measmon":True,
             "no_climate_growth_interaction_or_causal_process_identified":True}
    report_path=output_dir/"source_receipt.json"
    report_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("NOAA snapshot:",receipt["snapshot"],"paired growing months",len(rows),
          "county coverage",{k:v["n_counties_baseline_complete_25years"] for k,v in coverage["states"].items()})
    return receipt


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config",type=Path,default=Path("configs/fia_noaa_county_climate_source_v1.json"))
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    run(args.config,args.out)


if __name__ == "__main__":
    main()
