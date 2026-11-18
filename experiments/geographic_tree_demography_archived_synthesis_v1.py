"""Post-result, outcome-aware descriptive synthesis of source-verified FIA trees.

Uses ONLY the archived, immutable 13-species × RI/VA/WI aggregate; no
reopening source samples, no fresh tuning, no causal/climatic interpretation.
The signal of interest is between-region heterogeneity of size-stratified
live-to-live diameter growth, checked separately against observed status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ARCHIVE_SHA256 = "57259fe905a610e311934b6cbc3a54143677629d2a87df7e7ee6bbe7cc64d414"
ARCHIVED_ACTION_RUN = 39244950162
ARCHIVED_ARTIFACT_ID = 12183086705
STATES = ("RI", "VA", "WI")
EXPECTED_CODES = ("68", "129", "261", "316", "318", "371", "531", "541", "743", "762", "802", "833", "837")
BANDS = ("1-<5", "5-<10", "10-<20", "20+")
STATE_PAIRS = (("RI", "VA"), ("RI", "WI"), ("VA", "WI"))


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def _direction(value: float) -> str:
    return "higher" if value > 0 else ("lower" if value < 0 else "tie")


def validate(data: dict) -> tuple[dict[str, dict[str, dict]], dict[str, dict]]:
    """Fail closed on missing states, altered cohort, inconsistent denominators."""
    if data.get("analysis") != "fia_three_state_named_taxa_first_observed_demography_v1":
        raise ValueError("not the frozen first FIA measured-response schema")
    if data.get("n_predeclared_taxa") != 13 or data.get("no_claim_about_niche_evolution_or_constraint_switch") is not True:
        raise ValueError("cohort/claim-ceiling altered")
    if data.get("sources", {}).get("original_source_zip_sha_by_state") != {
        "RI": "222098c72977840e512822734bef551a37c5021dde489157f9e408f482d1cc02",
        "VA": "6c79b569ca6e2c99d51946a23236b305842a730bd491e75ba31e9ecc408df36b",
        "WI": "18c55e9d0568879ce4a88b7763af9b86743a2d47945671d41d020bec4b4e3274",
    }:
        raise ValueError("FIA TREE raw ZIP provenance changed")
    summaries = data.get("state_summaries", [])
    if [x.get("state") for x in summaries] != list(STATES):
        raise ValueError("three-state panel not intact/order differs")
    rows: dict[str, dict[str, dict]] = {}
    names: dict[str, str] = {}
    for state_group in summaries:
        state = state_group["state"]
        entry: dict[str, dict] = {}
        for row in state_group.get("taxa", []):
            code = str(row["spcd"])
            if code in entry:
                raise ValueError("duplicate species in a state")
            if code not in EXPECTED_CODES:
                raise ValueError("non-nominated species in a state")
            current_name = row["official_scientific_name"]
            if code in names and current_name != names[code]:
                raise ValueError("state-specific taxon-name mismatch")
            names[code] = current_name
            entry[code] = row
            for key in ("n_valid_forward_links", "n_prior_live_linked", "n_observed_live_to_live",
                        "n_observed_live_to_dead", "n_removed_excluded", "n_not_tallied_excluded",
                        "n_other_unknown_status_excluded", "n_growth_pairs_with_diameter",
                        "n_growth_pairs_matching_diameter_height_code"):
                v = row[key]
                if type(v) is not int or v < 0:
                    raise ValueError(f"invalid link denominator {state}/{code}/{key}")
            linked = row["n_observed_live_to_live"] + row["n_observed_live_to_dead"]
            live_tot = linked + row["n_removed_excluded"] + row["n_not_tallied_excluded"] + row["n_other_unknown_status_excluded"]
            if live_tot != row["n_prior_live_linked"]:
                raise ValueError(f"status decomposition inconsistent for {state}/{code}")
            if not row["n_prior_live_linked"] <= row["n_valid_forward_links"]:
                raise ValueError("prior-live exceeds forward matched links")
            if not (row["n_growth_pairs_matching_diameter_height_code"] <= row["n_growth_pairs_with_diameter"] <= row["n_observed_live_to_live"]):
                raise ValueError("growth/height-code numerator exceeds eligible links")
            frac = row["mortality_fraction_among_live_to_live_or_dead_links"]
            if linked == 0 or not _close(float(frac), row["n_observed_live_to_dead"] / linked):
                raise ValueError("invalid observed linked dead fraction")
            band_table = row["size_band_growth_log_means"]
            if set(band_table) != set(BANDS):
                raise ValueError("size-band definitions/order altered")
            if sum(band_table[b]["n"] for b in BANDS) != row["n_growth_pairs_with_diameter"]:
                raise ValueError("size-band growth denominator inconsistent")
            for band in BANDS:
                n, mean = band_table[band]["n"], band_table[band]["mean_annual_log_diameter_change"]
                if type(n) is not int or n < 0 or (mean is None) != (n == 0):
                    raise ValueError("size-band empty/missing mismatch")
                if mean is not None and not math.isfinite(mean):
                    raise ValueError("nonfinite growth mean")
        if set(entry) != set(EXPECTED_CODES):
            raise ValueError(f"missing selected species for state {state}")
        rows[state] = entry
    std = data.get("size_standardized", {})
    if std.get("min_growth_pairs_per_band_per_state") != 30:
        raise ValueError("size-standardization threshold changed")
    std_by_taxon: dict[str, dict] = {}
    for record in std.get("taxa", []):
        code = str(record["spcd"])
        if code in std_by_taxon or code not in EXPECTED_CODES:
            raise ValueError("size-standardized cohort altered")
        expected = [band for band in BANDS if all(rows[s][code]["size_band_growth_log_means"][band]["n"] >= 30 for s in STATES)]
        if record["eligible_size_bands"] != expected or record["n_shared_size_bands"] != len(expected):
            raise ValueError("selected common size bands changed")
        by_state = record["observed_size_standardized_mean_log_diameter_change_by_state"]
        weights = {band: sum(rows[s][code]["size_band_growth_log_means"][band]["n"] for s in STATES) for band in expected}
        denom = sum(weights.values())
        for state in STATES:
            expected_val = (
                sum(weights[band] * rows[state][code]["size_band_growth_log_means"][band]["mean_annual_log_diameter_change"] for band in expected) / denom
                if denom else None
            )
            received = by_state[state]
            if (received is None) != (expected_val is None) or (received is not None and not _close(received, expected_val)):
                raise ValueError("archived standardized growth disagrees with raw size bins")
        std_by_taxon[code] = record
    if set(std_by_taxon) != set(EXPECTED_CODES):
        raise ValueError("size-standardized output is missing taxa")
    return rows, std_by_taxon


def synthesize(data: dict, *, archived_sha256: str) -> dict:
    if archived_sha256 != ARCHIVE_SHA256:
        raise ValueError("source aggregate digest differs from the verified corrected archived artifact")
    by_state, by_std = validate(data)
    species = []
    for code in EXPECTED_CODES:
        row = by_std[code]
        growth = row["observed_size_standardized_mean_log_diameter_change_by_state"]
        death = {st: by_state[st][code]["mortality_fraction_among_live_to_live_or_dead_links"] for st in STATES}
        n_shared = row["n_shared_size_bands"]
        growth_pairs = {st: by_state[st][code]["n_growth_pairs_with_diameter"] for st in STATES}
        record = {"code": code, "species": by_state["RI"][code]["official_scientific_name"],
                  "n_shared_size_bands": n_shared, "shared_size_bands": row["eligible_size_bands"],
                  "growth_pairs_by_state": growth_pairs, "size_standardized_log_growth_per_year": growth,
                  "observed_linked_dead_fraction_not_annual_hazard": death}
        if n_shared:
            record["growth_direction_in_RI_VA_WI_order"] = (
                "strict_increase" if growth["RI"] < growth["VA"] < growth["WI"] else
                "strict_decrease" if growth["RI"] > growth["VA"] > growth["WI"] else "mixed_or_tied"
            )
        else:
            record["growth_direction_in_RI_VA_WI_order"] = "not_estimable_common_size_band"
        # A direct within-band sign audit guards against a reversal caused by
        # standardization weights or broad initial-diameter composition.
        differences = {}
        for band in row["eligible_size_bands"]:
            ri_mean = by_state["RI"][code]["size_band_growth_log_means"][band]["mean_annual_log_diameter_change"]
            wi_mean = by_state["WI"][code]["size_band_growth_log_means"][band]["mean_annual_log_diameter_change"]
            differences[band] = wi_mean - ri_mean
        record["common_size_band_WI_minus_RI_log_growth_per_year"] = differences
        record["n_common_bands_WI_growth_higher"] = sum(v > 0 for v in differences.values())
        record["all_common_bands_WI_growth_higher"] = (
            all(v > 0 for v in differences.values()) if differences else None
        )
        species.append(record)

    state_support = {}
    for st in STATES:
        rows = list(by_state[st].values())
        n_live = sum(x["n_observed_live_to_live"] for x in rows)
        n_dead = sum(x["n_observed_live_to_dead"] for x in rows)
        state_support[st] = {
            "growth_pairs": sum(x["n_growth_pairs_with_diameter"] for x in rows),
            "prior_live_forward_linked": sum(x["n_prior_live_linked"] for x in rows),
            "observed_live_to_live": n_live,
            "observed_live_to_dead": n_dead,
            "not_currently_tallied_excluded": sum(x["n_not_tallied_excluded"] for x in rows),
            "observed_linked_dead_fraction_pooled_not_design_weighted": n_dead/(n_live+n_dead),
        }

    comparisons = []
    for a, b in STATE_PAIRS:
        eligible = [r for r in species if r["n_shared_size_bands"] > 0]
        growth = [r["size_standardized_log_growth_per_year"][b] - r["size_standardized_log_growth_per_year"][a] for r in eligible]
        deaths = [r["observed_linked_dead_fraction_not_annual_hazard"][b] - r["observed_linked_dead_fraction_not_annual_hazard"][a] for r in eligible]
        all_deaths = [r["observed_linked_dead_fraction_not_annual_hazard"][b] - r["observed_linked_dead_fraction_not_annual_hazard"][a] for r in species]
        per_count = []
        for min_bands in (1, 2, 3):
            keep = [r for r in eligible if r["n_shared_size_bands"] >= min_bands]
            d = [r["size_standardized_log_growth_per_year"][b]-r["size_standardized_log_growth_per_year"][a] for r in keep]
            per_count.append({"minimum_shared_size_bands": min_bands, "taxa": len(keep),
                              "growth_higher_in_second_state": sum(v > 0 for v in d),
                              "growth_lower_in_second_state": sum(v < 0 for v in d),
                              "growth_tied": sum(v == 0 for v in d)})
        comparisons.append({"first_state": a, "second_state": b,
                            "n_taxa_with_common_size_growth": len(eligible),
                            "n_taxa_without_common_size_growth": len(species)-len(eligible),
                            "higher_growth_in_second_state": sum(v > 0 for v in growth),
                            "lower_growth_in_second_state": sum(v < 0 for v in growth),
                            "median_within_species_log_growth_difference_per_year": median(growth),
                            "n_taxa_observed_dead_fraction_higher_in_second_of_all_13": sum(v > 0 for v in all_deaths),
                            "n_taxa_observed_dead_fraction_lower_in_second_of_all_13": sum(v < 0 for v in all_deaths),
                            "among_growth_comparable_taxa": {
                               "higher_growth_and_higher_linked_dead_fraction": sum(g>0 and d>0 for g, d in zip(growth, deaths)),
                               "higher_growth_and_lower_linked_dead_fraction": sum(g>0 and d<0 for g, d in zip(growth, deaths)),
                               "lower_growth_and_higher_linked_dead_fraction": sum(g<0 and d>0 for g, d in zip(growth, deaths)),
                               "lower_growth_and_lower_linked_dead_fraction": sum(g<0 and d<0 for g, d in zip(growth, deaths)),
                            }, "shared_size_band_sensitivity": per_count})
    stable = [r for r in species if r["n_shared_size_bands"] > 0]
    return {
        "analysis": "fia_archived_regional_growth_status_synthesis_v1",
        "status": "post_outcome_descriptive_no_confirmatory_promotion",
        "provenance": {"source_github_actions_run": ARCHIVED_ACTION_RUN,
                       "source_artifact_id": ARCHIVED_ARTIFACT_ID, "source_json_sha256": archived_sha256,
                       "reference": "evidence/geographic_tree_demography_first_response_v1/aggregate.json"},
        "n_pre_response_frozen_species": len(species),
        "n_species_with_shared_size_bins": len(stable),
        "n_species_with_2plus_shared_size_bins": sum(r["n_shared_size_bands"] >= 2 for r in species),
        "n_species_with_2plus_bands_all_WI_above_RI": sum(
            r["n_shared_size_bands"] >= 2 and r["all_common_bands_WI_growth_higher"] is True for r in species
        ),
        "species_with_2plus_bands_all_WI_above_RI": [
            r["species"] for r in species
            if r["n_shared_size_bands"] >= 2 and r["all_common_bands_WI_growth_higher"] is True
        ],
        "n_total_common_size_bands_across_species": sum(r["n_shared_size_bands"] for r in species),
        "n_common_size_bands_WI_growth_higher": sum(r["n_common_bands_WI_growth_higher"] for r in species),
        "n_states": len(STATES),
        "species": species,
        "states": state_support,
        "state_pair_descriptive_comparisons": comparisons,
        "strict_increasing_growth_ri_va_wi_species": [r["species"] for r in stable if r["growth_direction_in_RI_VA_WI_order"] == "strict_increase"],
        "strict_decreasing_growth_ri_va_wi_species": [r["species"] for r in stable if r["growth_direction_in_RI_VA_WI_order"] == "strict_decrease"],
        "interpretation": "Within-species regionally heterogeneous observed live-tree diameter increments persist for the common available initial-diameter bands; linked death fractions do not form a common matching pattern. The data do NOT attribute the heterogeneity to climate, niche evolution, fitness optima, or physiological limits.",
        "inferential_boundary": [
           "Species/state counts are not independent tree-level replicates; no p-values or taxon-level generalization claimed.",
           "Size-band-standardized means retain only trees observed live twice; survival selection bias is unresolved.",
           "Diameter bands are broad and shared between states only when each band has >=30 pairs; four species cannot be compared.",
           "Death fraction is conditional on observed prior-live links and lacks equal inventory intervals, plot weights or true hazard model.",
           "No exact exposure/climate, plot design, management or demographic state-space model is available from this aggregate.",
           "This post-outcome analysis is retrospective; it does not reopen historical SDMR Product A/B or M5 endpoints."
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("evidence/geographic_tree_demography_first_response_v1/aggregate.json"))
    parser.add_argument("--output", type=Path, default=Path("results/fia_archived_regional_growth_status_synthesis_v1.json"))
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    output = synthesize(json.loads(source_bytes), archived_sha256=hashlib.sha256(source_bytes).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(f"Source verified: {output['n_pre_response_frozen_species']} taxa / {output['n_states']} states; common-size eligibility {output['n_species_with_shared_size_bins']} taxa")
    print("Direction RI<VA<WI:", len(output["strict_increasing_growth_ri_va_wi_species"]))


if __name__ == "__main__":
    main()
