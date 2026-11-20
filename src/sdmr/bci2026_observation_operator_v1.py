"""BCI 2026 Dryad source codebook: tree/status/time operator only.

No BCI original tree rows are retrieved. Source file SHA stage has HTTP401.
Tree identity is (plot, tag), not a stem row or tag without plot.
2025 light exposure is not a pre-outcome predictor for earlier survival.
"""
from dataclasses import dataclass
from datetime import date
import re

PLOTS=frozenset({"10ha","25ha","AVA","Drayton","Pearson","Zetek"})
CENSUSES=(2004,2014,2025)
STATUS=frozenset({"future recruit","alive","missing","dead"})

@dataclass(frozen=True)
class TreeKey:
    plot:str
    tag:str
    def __post_init__(self):
        if self.plot not in PLOTS:
            raise ValueError("unknown_original_BCI_plot")
        if not isinstance(self.tag,str) or not re.fullmatch(r"[0-9]{1,20}",self.tag):
            raise ValueError("BCI_tree_tag_must_be_unmodified_integer_text")
    @property
    def unique_id(self)->str:
        return self.plot+"-"+self.tag

@dataclass(frozen=True)
class Transition:
    status:str
    baseline_alive_at_risk:bool
    author_coded_dead:bool
    strict_observed_dead:bool
    strict_binary_Y:int|None
    future_recruit_is_not_zero:bool
    missing_is_not_observed_dead:bool
    sampling_effort_audited:bool=False
    new_ecological_effect_estimated:bool=False

def classify_tree_transition(*,first_year:int,next_year:int,
                            first_status:str,next_status:str)->Transition:
    """Pure ontology, not evidence of any measured BCI demographic rate.

    BCI original dead includes directly observed AND presumed deaths.
    BCI original missing is unknown state. Future recruit is not baseline zero.
    """
    if (type(first_year) is not int or type(next_year) is not int or
        (first_year,next_year) not in ((2004,2014),(2014,2025))):
        raise ValueError("not_adjacent_source_census_pair")
    if first_status not in STATUS or next_status not in STATUS:
        raise ValueError("unrecognized_original_BCI_status")
    if first_status!="alive":
        return Transition(
            "not_eligible_baseline_alive",False,False,False,None,
            first_status=="future recruit",first_status=="missing")
    if next_status=="alive":
        return Transition("source_coded_next_alive",True,False,False,0,False,False)
    if next_status=="missing":
        return Transition("unknown_not_found",True,False,False,None,False,True)
    if next_status=="dead":
        return Transition(
            "unknown_direct_vs_inferred_death",True,True,False,None,False,False)
    return Transition("ontology_conflict_alive_to_future_recruit_STOP",
                      True,False,False,None,False,False)

def inspect_original_census_visit_date(*,census:int,date_text:str|None)->dict:
    """2004 label was mainly measured 2005: do not assume a 10-year risk."""
    if type(census) is not int or census not in CENSUSES:
        raise ValueError("unregistered_census_label")
    if date_text in (None,"","NA"):
        return {"status":"unobserved_visit_date",
                "visit_year":None,"annual_rate_identified":False}
    if not isinstance(date_text,str) or not re.fullmatch("[0-9]{8}",date_text):
        raise ValueError("invalid_original_visit_date_format")
    try:
        d=date.fromisoformat(
            date_text[:4]+"-"+date_text[4:6]+"-"+date_text[6:])
    except ValueError as ex:
        raise ValueError("invalid_original_visit_date") from ex
    if (census==2004 and d.year not in (2004,2005)) or (
        census in (2014,2025) and d.year!=census):
        raise ValueError("census_label_visit_year_conflict")
    return {"status":"source_coded_visit_date_only","visit_year":d.year,
            "annual_rate_identified":False}

def prior_exposure_admission(*,baseline_year:int,
                            measured_year:int=2025)->dict:
    if type(baseline_year) is not int or baseline_year not in CENSUSES:
        raise ValueError("baseline_census_not_authorized")
    if measured_year!=2025:
        raise ValueError("original_exposure_measured_only_2025")
    return {"status":"2025_exposure_not_prebaseline_mortality_information",
            "admitted_as_baseline_mortality_predictor":False,
            "measured_only_on_recorded_2025_alive":True,
            "causal_exposure_effect_identified":False}
