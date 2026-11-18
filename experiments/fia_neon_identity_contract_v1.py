"""NEON 2026 NORMALIZED source-only tagged-individual identity audit.

Consumes only *explicitly projected identity/sampling columns* from THREE
future NEON tables; NEVER accepts growth, death/status, diameter or coordinates.
For RELEASE-2026 mappingandtagging has NO eventID. Multi-stem tempStemID and
TEMP individualID may NOT identify the same stem across census years.
This module is fixture tested only until authorized NEON row-level access.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import datetime as dt
from typing import Any

ALLOWED_TABLE_FIELDS = {
    "perplotperyear": {"site","plotID","eventID","surveyYear",
                       "samplingImpractical","totalSampledAreaTrees"},
    "mappingandtagging": {"site","plotID","individualID","date","taxonID"},
    "apparentindividual": {"site","plotID","eventID","individualID","tempStemID"},
}
MIN_GAP_YEARS = 4
SITES = ("HARV","SCBI")
FIA_CODES = ("129","316","802","833","837")
BLOCKED_RESULT = "source_only_tagged_individual_candidates_not_demographic_effect"


def _fields(rows: list[dict], table: str) -> None:
    if table not in ALLOWED_TABLE_FIELDS:
        raise ValueError("unknown NEON source table type")
    allow = ALLOWED_TABLE_FIELDS[table]
    for row in rows:
        if not isinstance(row, dict) or set(row) != allow:
            raise ValueError("NEON 2026 normalized source column mismatch: "+table)
        if row["site"] not in SITES:
            raise ValueError("site outside the fixed independent two-site pilot")


def _year(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("invalid NEON survey year")
    try:
        y = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid NEON survey year") from exc
    if str(value).strip() != str(y) or not 2010 <= y <= 2030:
        raise ValueError("invalid NEON survey year")
    return y


def latest_mapping(rows: list[dict]) -> tuple[dict,Counter]:
    """2026 mapping table is static; select latest correction by DATE, not eventID."""
    records={}
    flags=Counter()
    for row in rows:
        key=(row["site"],row["plotID"],row["individualID"])
        if not all(isinstance(v,str) and v.strip() for v in key):
            flags["invalid_static_tag_identity"]+=1;continue
        if key[2].upper().startswith("TEMP"):
            flags["temporary_ID_not_longitudinal"]+=1;continue
        try:
            date=dt.date.fromisoformat(row["date"][:10])
        except (ValueError,TypeError,AttributeError):
            flags["invalid_mapping_correction_date"]+=1;continue
        taxon=str(row["taxonID"] or "").strip()
        if not taxon:
            flags["missing_taxonomic_assignment"]+=1;continue
        if key in records:
            flags["historical_mapping_correction_rows"]+=1
            other=records[key]
            if date==other[0] and taxon!=other[1]:
                flags["conflicting_same_day_taxonomic_update"]+=1
                records[key]=(date,None)
                continue
            if date <= other[0]:
                continue
        records[key]=(date,taxon)
    return {k:v[1] for k,v in records.items() if v[1]}, flags


def audit_identity_source(plot_events: list[dict], mapping: list[dict],
                          woody_events: list[dict]) -> dict:
    """Do not read or join any biological value. A repeat ID is only a CANDIDATE."""
    _fields(plot_events,"perplotperyear")
    _fields(mapping,"mappingandtagging")
    _fields(woody_events,"apparentindividual")
    flags=Counter()
    plot_index={}
    for row in plot_events:
        key=(row["site"],row["plotID"],row["eventID"])
        if not all(isinstance(v,str) and v.strip() for v in key):
            raise ValueError("invalid NEON perplot event identity")
        if key in plot_index:
            raise ValueError("duplicate NEON plotID x eventID, cannot invent survey area")
        y=_year(row["surveyYear"])
        try:
            area=float(row["totalSampledAreaTrees"])
        except (TypeError,ValueError):
            area=float("nan")
        import math
        effort=(row["samplingImpractical"]=="ok" and math.isfinite(area) and area>0)
        if not effort:
            flags["plot_event_without_complete_tree_sampled_area_or_effort"]+=1
        plot_index[key]={"year":y,"tree_area_valid":effort}
    static,corrections=latest_mapping(mapping)
    flags.update(corrections)
    seen_raw=set()
    by_individual=defaultdict(lambda: defaultdict(list))
    raw_ids_by_plot=defaultdict(set)
    for row in woody_events:
        site,plot,event,ind=(row.get(k) for k in ("site","plotID","eventID","individualID"))
        stem=str(row["tempStemID"] or "").strip()
        if not all(isinstance(v,str) and v for v in (site,plot,event,ind)) or not stem:
            flags["missing_apparentindividual_identity"]+=1;continue
        rawkey=(site,event,ind,stem)
        if rawkey in seen_raw:
            raise ValueError("duplicate NEON eventID x individualID x tempStemID")
        seen_raw.add(rawkey)
        if ind.upper().startswith("TEMP"):
            flags["TEMP_ID_event_rows_not_longitudinal"]+=1;continue
        if (site,plot,event) not in plot_index:
            flags["apparentindividual_event_has_no_perplotperyear_design"]+=1;continue
        if not plot_index[(site,plot,event)]["tree_area_valid"]:
            flags["individual_event_area_or_effort_invalid"]+=1;continue
        if (site,plot,ind) not in static:
            flags["no_current_static_mapping_for_individual"]+=1;continue
        by_individual[(site,plot,ind)][event].append(stem)
        raw_ids_by_plot[(site,ind)].add(plot)
    candidate_counts=Counter()
    by_site=Counter()
    distinct_plots=defaultdict(set)
    taxon_ids=defaultdict(set)
    for (site,plot,ind),by_event in by_individual.items():
        if len(raw_ids_by_plot[(site,ind)])>1:
            flags["same_individualID_appears_in_multiple_plots"]+=1
            continue
        events=[]
        if any(len(stems)!=1 or stems[0]!="1" for stems in by_event.values()):
            flags["multi_stem_or_nonstable_tempStemID"]+=1
            continue
        for event in by_event:
            y=plot_index[(site,plot,event)]["year"]
            events.append((y,event))
        years={x[0] for x in events}
        if len(years)<2:
            flags["single_year_tag_identity_only"]+=1;continue
        if max(years)-min(years)<MIN_GAP_YEARS:
            flags["repeat_ID_time_span_under_four_years"]+=1;continue
        candidate_counts[site]+=1
        by_site[site]+=1
        distinct_plots[site].add(plot)
        taxon_ids[site].add(static[(site,plot,ind)])
    return {
        "program":"sdmr_NEON_2026_source_only_normalized_individual_linkage_v1",
        "status": BLOCKED_RESULT,
        "fixed_pilot_sites":list(SITES),
        "n_input_plot_events":len(plot_events),
        "n_input_mapping_static_records":len(mapping),
        "n_input_apparentindividual_identity_records":len(woody_events),
        "n_valid_plot_event_records":sum(x["tree_area_valid"] for x in plot_index.values()),
        "n_unique_corrected_non_TEMP_static_tagIDs":len(static),
        "n_source_identity_candidates_with_4_years_or_longer":sum(candidate_counts.values()),
        "n_candidate_IDs_by_site":{s:by_site[s] for s in SITES},
        "n_plots_with_candidate_IDs_by_site":{s:len(distinct_plots[s]) for s in SITES},
        "n_unverified_NEON_taxonIDs_by_site":{s:len(taxon_ids[s]) for s in SITES},
        "failure_and_exclusion_counts":dict(sorted(flags.items())),
        "FIA_codes_await_NEON_source_taxon_crosswalk":list(FIA_CODES),
        "NEON_taxonIDs_obfuscated_where_species_of_concern":True,
        "RELEASE_2026_mappingandtagging_eventID_absent":True,
        "tempStemID_not_year_stable_for_multi_stem":True,
        "TEMP_individualIDs_not_tag_repeats":True,
        "survey_years_do_not_guarantee_individual_survival":True,
        "verified_same_tree_growth_or_death_status":None,
        "raw_tree_diameter_status_values_evaluated":False,
        "biological_outcome_estimated":False,
        "independent_efficacy_or_competition_mechanism_confirmed":False,
        "prior_FIA_and_Product_A_M5_unchanged_Product_B_blocked":True,
    }
