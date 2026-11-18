"""FIA plot/condition source audit for a NEW three-state growth-response cohort.

No TREE results are read. Current DataMart bytes are never substituted for the
original frozen TREE archives used by historical SDMR PR #284 demographic results.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zipfile import ZipFile, BadZipFile

BASE = "https://apps.fs.usda.gov/fia/datamart/CSV/"
STATES = ("RI", "VA", "WI")
TABLES = ("PLOT", "COND")
MAX_ZIP_BYTES = 320_000_000
MAX_UNCOMPRESSED_BYTES = 3_500_000_000


def _year(value):
    try:
        n = int(str(value).strip())
        if 1850 <= n <= 2027:
            return n
    except (ValueError, TypeError):
        pass
    return None


def _age(value):
    try:
        n = int(str(value).strip())
        return n if 0 <= n <= 500 else None
    except (ValueError, TypeError):
        return None


def _fetch(state, table, folder, fetcher=None):
    if state not in STATES or table not in TABLES:
        raise ValueError("invalid predeclared state/table")
    url = BASE + state + "_" + table + ".zip"
    dst = folder / (state + "_" + table + ".zip")
    digest = hashlib.sha256()
    out = {"state": state, "table": table, "source_url": url, "status": "unavailable"}
    try:
        src = (io.BytesIO(fetcher(state, table)) if fetcher else
               urlopen(Request(url, headers={"User-Agent": "sdmr-independent-fia-plot-cond-source-v1"}), timeout=90))
        with src, dst.open("wb") as f:
            size = 0
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > MAX_ZIP_BYTES:
                    raise ValueError("zip_above_declared_cap")
                f.write(block)
                digest.update(block)
        with ZipFile(dst) as z:
            selected = [i for i in z.infolist() if not i.is_dir() and
                        i.filename.upper().endswith((state + "_" + table + ".CSV"))]
            if len(selected) != 1:
                raise ValueError("missing_or_ambiguous_table_member")
            if selected[0].file_size > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("csv_uncompressed_cap")
            out.update({"status": "ready", "zip_sha256": digest.hexdigest(),
                        "zip_bytes": size, "csv_member": selected[0].filename,
                        "csv_uncompressed_bytes": selected[0].file_size})
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, BadZipFile) as e:
        out.update({"status": "unavailable", "reason": type(e).__name__ + ": " + str(e)[:160]})
        dst.unlink(missing_ok=True)
    return out, dst


def _plot_reader(zippath, member, db):
    db.execute("CREATE TABLE plot (cn TEXT PRIMARY KEY, prev TEXT, invyr INTEGER, measyear INTEGER, mearmon INTEGER, status TEXT)")
    count = 0
    bad = Counter()
    nonidentical = 0
    months = 0
    with ZipFile(zippath) as z, z.open(member) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        required = {"CN", "INVYR", "MEASYEAR"}
        names = set(reader.fieldnames or [])
        if required - names:
            raise ValueError("PLOT missing " + str(sorted(required - names)))
        buf = []
        for row in reader:
            count += 1
            cn = str(row.get("CN") or "").strip()
            invyr = _year(row.get("INVYR"))
            measyear = _year(row.get("MEASYEAR"))
            month_raw = str(row.get("MEASMON") or "").strip()
            month = int(month_raw) if month_raw.isdigit() and 1 <= int(month_raw) <= 12 else None
            if not cn:
                bad["missing_cn"] += 1
                continue
            if invyr is None:
                bad["missing_or_invalid_invyr"] += 1
            if measyear is None:
                bad["missing_or_invalid_measyear"] += 1
            if invyr is not None and measyear is not None and invyr != measyear:
                nonidentical += 1
            if month is not None and measyear is not None:
                months += 1
            buf.append((cn, str(row.get("PREV_PLT_CN") or "").strip(), invyr, measyear, month,
                        str(row.get("PLOT_STATUS_CD") or "").strip()))
            if len(buf) >= 3000:
                db.executemany("INSERT INTO plot VALUES (?,?,?,?,?,?)", buf)
                buf = []
        if buf:
            db.executemany("INSERT INTO plot VALUES (?,?,?,?,?,?)", buf)
    db.commit()
    pairs = db.execute("""SELECT COUNT(*),
             SUM(CASE WHEN c.measyear > p.measyear THEN 1 ELSE 0 END),
             SUM(CASE WHEN c.measyear > p.measyear AND c.invyr > p.invyr
                      AND (c.measyear-p.measyear)!=(c.invyr-p.invyr) THEN 1 ELSE 0 END)
             FROM plot c JOIN plot p ON c.prev=p.cn WHERE c.prev!=''""").fetchone()
    return {"n_source_plots": count, "plot_columns": sorted(names),
            "n_with_valid_measyear_and_month": months,
            "n_invyr_measyear_disagree": nonidentical,
            "plot_year_qc": dict(bad),
            "n_internal_previous_plot_links": pairs[0],
            "n_forward_measyear_links": pairs[1] or 0,
            "n_forward_links_with_interval_disagreement": pairs[2] or 0,
            "no_tree_response_accessed": True}


def _cond_reader(zippath, member, db):
    cols = ["PLT_CN", "CONDID", "STDAGE", "STDORGCD", "COND_STATUS_CD",
            "CONDPROP_UNADJ", "FORTYPCD", "STDSZCD", "DSTRBCD1"]
    counts = Counter()
    seen = set()
    with ZipFile(zippath) as z, z.open(member) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        names = set(reader.fieldnames or [])
        required = {"PLT_CN", "CONDID", "STDAGE", "STDORGCD", "COND_STATUS_CD"}
        if required - names:
            raise ValueError("COND missing " + str(sorted(required - names)))
        for row in reader:
            counts["source_conditions"] += 1
            plt = str(row.get("PLT_CN") or "").strip()
            cond = str(row.get("CONDID") or "").strip()
            if not plt or not cond:
                counts["invalid_keys"] += 1
                continue
            if (plt, cond) in seen:
                raise ValueError("duplicate condition key")
            seen.add((plt, cond))
            exists = db.execute("SELECT 1 FROM plot WHERE cn=?", (plt,)).fetchone() is not None
            if not exists:
                counts["condition_without_plot"] += 1
                continue
            counts["condition_with_plot"] += 1
            if str(row.get("COND_STATUS_CD") or "").strip() != "1":
                continue
            counts["forest_condition_with_plot"] += 1
            if _age(row.get("STDAGE")) is not None:
                counts["forest_age_valid"] += 1
            origin = str(row.get("STDORGCD") or "").strip()
            if origin == "0":
                counts["forest_natural_origin"] += 1
            elif origin == "1":
                counts["forest_artificial_origin"] += 1
            else:
                counts["forest_origin_unknown"] += 1
            if str(row.get("CONDPROP_UNADJ") or "").strip() == "1":
                counts["forest_full_condition_prop_exact_1"] += 1
            if str(row.get("FORTYPCD") or "").strip():
                counts["forest_type_recorded"] += 1
            if str(row.get("STDSZCD") or "").strip():
                counts["stand_size_recorded"] += 1
            if str(row.get("DSTRBCD1") or "").strip():
                counts["disturbance_code_recorded"] += 1
    return {"condition_columns": sorted(names), "condition_qc": dict(counts),
            "no_tree_response_accessed": True}


def run(states=STATES, fetcher=None):
    if tuple(states) != STATES:
        raise ValueError("state panel must be RI VA WI; no switching after outcome inspection")
    records = []
    for state in states:
        with tempfile.TemporaryDirectory(prefix="sdmr_fia_plot_" + state) as tmp:
            folder = Path(tmp)
            pmeta, pfile = _fetch(state, "PLOT", folder, fetcher=fetcher)
            cmeta, cfile = _fetch(state, "COND", folder, fetcher=fetcher)
            audit = {"state": state, "plot": pmeta, "cond": cmeta,
                     "status": "unavailable", "matched_tree_growth_available": False}
            if pmeta["status"] == "ready" and cmeta["status"] == "ready":
                db = sqlite3.connect(folder / "index.sqlite")
                try:
                    audit["plot_validation"] = _plot_reader(pfile, pmeta["csv_member"], db)
                    audit["condition_validation"] = _cond_reader(cfile, cmeta["csv_member"], db)
                    audit["status"] = "source_linked_metadata_ready"
                except (ValueError, sqlite3.Error, OSError, UnicodeError) as e:
                    audit["reason"] = type(e).__name__ + ": " + str(e)[:200]
                finally:
                    db.close()
            records.append(audit)
    return {"study": "fia_plot_condition_independent_source_gate_v1",
            "states": records, "n_states_complete": sum(s["status"] == "source_linked_metadata_ready" for s in records),
            "historical_fia_tree_source_frozen_and_unmodified": True,
            "first_measurement_growth_or_survival_refitted": False,
            "biological_claim": "none; metadata source-coverage only"}


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    for x in result["states"]:
        ps = x.get("plot_validation", {})
        cs = x.get("condition_validation", {}).get("condition_qc", {})
        print(x["state"], x["status"], "PLOT", ps.get("n_source_plots"),
              "MEASYEAR_DISAGREE", ps.get("n_invyr_measyear_disagree"),
              "FOREST_AGE", cs.get("forest_age_valid"), "NATURAL", cs.get("forest_natural_origin"))
    if result["n_states_complete"] != 3:
        print("SOURCE HOLD - incomplete fixed three-state panel")


if __name__ == "__main__":
    main()
