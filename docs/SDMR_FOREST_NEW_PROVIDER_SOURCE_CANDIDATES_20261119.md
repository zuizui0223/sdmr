# New independent forest provider candidates: original status and sampling frame, no response opening

**Source research status (updated 2026-11-19): public codebook discovery plus a successful HF453 original-byte checksum audit.** The HF453 first provider stream was SHA-256/MD5 checked and discarded, without decoding any original tree response rows/status observations; no forest survival/growth or ecological mechanism effect has been estimated. The prior five-source retrospective/source-only gate and all 80 synthetic KT cases remain unchanged.

## A. BCI / Smithsonian, 2026 Dryad revised release

Source: [Wright, Dryad DOI 10.5061/dryad.1g1jwsvc3](https://datadryad.org/dataset/doi:10.5061/dryad.1g1jwsvc3). Published **2026-03-17**, revised **2026-08-31** (two different versions, never silently mixed). The author-public codebook advertises exactly five current file names: `Key_sp6.txt`, `mainfile.txt`, `Plot_UTM_coordinates.txt`, `README.md`, `stemfile.txt`. Original file hashes and publisher version ID remain **unretrieved** and must be frozen from original provider before source opening. Direct original README download attempt by web tool returned HTTP403; do not treat that as evidence of biological absence or bypass provider access controls.

**Design information only:** six BCI plots, three census labels **2004, 2014, 2025**, 58 hectares in total, 34,367 original recorded measurements, 15,562 tagged trees and 222 species per author metadata. This is **one tropical-island location**, NOT six independent biomes. The source `mainfile` is tree-level and records `plot, tag, census, unique.id, status`; a tag can repeat across plots so the individual key is `plot + tag`. In the multi-stem table each tree receives one tag; a stem should **not** be longitudinally identified across censuses. Original date fields, potentially differing measurement periods, must be audited before annualizing growth.

Source-status semantics from the author-public README:
- `future recruit`: did not yet meet entry threshold, **not an observed absence**.
- `alive`: recorded alive.
- `missing`: previously alive but not found, **death is not demonstrated** by that category alone.
- `dead`: original author's mixed class, including found dead and certain inferred deaths after repeated missing census; **not uniformly an observed death**. Any strict observed-mortality denominator needs the original individual code/census provenance.
- `dbh` absent when missing, dead or future-recruit and for some otherwise alive records; missing numeric diameter must not be imputed to zero.

**Provisional scientific role:** stress-test long-term identity, entry/recruitment, presumed-dead versus observed-dead and completeness of source opportunities. It cannot alone demonstrate cross-biome portability or a causal forest structural coefficient.

## B. Harvard Forest, HF453 2026 field-health series

Source: [Harvard Forest HF453](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF453), DOI [10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193](https://doi.org/10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193), original `hf453-01`, published 2026 under CC0. The author reports an **annual July census 2021–2024 of all stems ≥10 cm DBH in one 35-ha Harvard Forest ForestGEO plot**, linked to CTFS/ForestGEO stem tags, canopy position, percentage intact/live crown and tree health/damage factors.

Published codebook:
- `A`: observed alive with no recorded visible health issue.
- `AU`: alive with at least one health issue.
- `DC`: dead/down; `DS`: dead/standing.
- `DN`: coded dead/not found, not direct visual confirmation of a fallen or standing dead individual. Keep separate in a strict known-observed-death sensitivity.
- `CP` canopy position and `PercCI/PercCL` original crown/foliage measures could be prior predictors in an appropriately frozen `t → t+1` mortality or health transition, but should NOT be read as independent causal causes of later death without adjustment for time, health/state, plot, treatment and detection.

**Provisional scientific role:** independent *original measurement protocol* to test whether repeated survey status, prior health and visible/unfound mortality can be represented without collapsing absence/missingness. This is also **one forest**; its 35-ha survey is not 35 independent ecosystem replicates.

## Reusable contract now implemented — codebook only

`src/sdmr/forest_longitudinal_status_v1.py` and `tests/test_forest_longitudinal_status_v1.py` pin the two public codebooks as separate namespaces:

1. Disallow invented cross-source aliases, `missing → death`, `future recruit → zero/absence` or `BCI stemID → stable across censuses`.
2. Distinguish author-reported inferred deaths from visual dead statuses.
3. Refuse reversed or undeclared census labels.
4. Explicitly state that classification of synthetic status pairs is **not** a population mortality rate, actual time-at-risk or consent to open biological data.

The tests use *synthetic labels only*. No Dryad or HF453 raw response values are fetched.

## Next source admission, before any organism data are opened

The strict sequence is:

- Obtain original public file metadata/version, exact download archive SHA/checksums and original source license (without biological data inspection).
- Freeze original sample-unit identity, site/plot/census calendar, status-code interpretation, source sampling/effort method and a source version.
- Specify *separate* response-free burned pilot versus outcome heldout, exact original tree-level cohort/censoring/entry rules, at-risk denominator and spatial blocks without looking at outcome values.
- Make an explicitly **within-study diagnostic** target if all independent geographic units lie within one forest/island; don't describe a 6-plot or 35-ha sample as a global forest test.
- Only after passing the sampling opportunity source gate and new design freeze may separately authorized biological outcome access be considered.

**Access/availability boundary:** BCI Dryad 2026 original ZIP and file checksums remain unverified. HF453 original **byte identity** has now passed an independent source-only checksum step (see terminal appendix below), but tree-row identity, sampling opportunity and status/risk-set correctness have **not** been audited. Both studies remain unavailable for new biological process identification. The five previously archived forest study/source audit decisions remain separate and are not updated by these candidates.


## 2026-11-19 historical provider-check metadata (before first original-byte opening)

The Harvard Forest public HF453 catalog links the **specific original filename**
`hf453-01-tree-census-2021-2024.csv` at
`https://harvardforest1.fas.harvard.edu/data/p45/hf453/hf453-01-tree-census-2021-2024.csv`.
Its **publisher-generated preview** reports 123,232 rows × 14 columns and
**MD5 `c6be7aa99e31ded2041a0aaea07c0205`**. These are *publisher
metadata* only; this repository has **not** fetched the original CSV, hashed
its bytes, parsed any biological outcome rows or accepted the preview as a
new study outcome. The precise source URL redirected to a host not accessible
through the available retrieval route.

The independent `sdmr.forest_original_receipt_v1.audit_original_source_bytes`
further enforces a prospective file SHA-256 match, optional publisher MD5
match, immutable publisher-version string, and separation of original-source
from analysis-artifact digests. It **never** authorizes biological result
opening and cannot reconstruct publisher authenticity from a user-supplied
path alone. A matching file hash must be followed by the separate
original sampling/effort and process-carrier gate.

Public source references: [HF453 dataset and use policy](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF453);
[official HF453 file preview/checksum](https://harvardforest1.fas.harvard.edu/data/plots/hf453-01.pdf).


## 2026-11-19 HF453 first original-byte terminal — source-only verified, no biological effect

One and only lock-triggered [Actions run #44475206249](https://github.com/zuizui0223/sdmr/actions/runs/44475206249) at source commit `a14cc8362a971aff66e7d49c003eb37de108d190` **SUCCESS**. The official Harvard original CSV HTTPS stream resolved to the allowed publisher host; the complete **5,524,386 bytes** matched pre-recorded publisher MD5 `c6be7aa99e31ded2041a0aaea07c0205`, with new full-byte SHA-256 `0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74`. Original CSV bytes were **not archived or parsed**; job artifact #14506116223 stores only the preflight and match JSONs. ZIP SHA-256 `b7934bb8bbe351f90fb95de871b8c959061d4256f8bdfd7e4624206592755a96`; full [source checkpoint](../evidence/hf453_publisher_original_bytes_first_open_v1.json).

The exact source-only methods are in [the original-byte preregistered contract](SDMR_HF453_ORIGINAL_BYTE_ONESHOT_V1.md); the *post-source, pre-response* [HF453 risk-set protocol](SDMR_HF453_RISKSET_PREFREEZE_V1.md) declares original tag, July occasion, living start states, visually dead `DC/DS`, unresolved `DN`, and missingness-robust canopy comparison. These are **not** field estimates. No actual tree status rows, sample-level response counts or mortality models have been inspected, and a single Harvard forest remains **one forest**, not independent ecosystem replication.
