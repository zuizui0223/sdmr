# Hubbard Brook EDI: open independent forest source schema prefreeze (2026-11-21)

**No Hubbard Brook original tree records opened.** This is one independent physical forest *source candidate* beyond Harvard and SCBI, not an achieved biological transfer validation or source-verified tree mortality result.

## Why this candidate

The [Hubbard Brook data catalog](https://hubbardbrook.org/data-catalog/) states all its EDI archived datasets are **open access under CC BY**. Compared with BCI Dryad 2026 v5 original HTTP401 and SCBI's separate official master/collaboration approval requirements, this is a promising independently hosted source of original ecological measurements. However, an open data catalog does not by itself prove individual-tree identities, complete positive survey effort, direct mortality observation, original tree status ontology or a useable SDMR environmental carrier. Those require a *separate original-file and sampling-opportunity audit*.

The [Hubbard Brook Forest Analytics reference](https://hubbardbrook.org/hubbard-brook-forest-analytics/) and EDI catalog give these three **fixed published data package versions**:

| Source watershed | Pinned EDI package ID | Published DOI | Coverage in catalog |
| --- | --- | --- | --- |
| Watershed 1 | \`knb-lter-hbr.446.1\` | \`10.6073/pasta/3d0031ea82d308f81ab26000a106b264\` | 1996–2021 |
| Watershed 5 | \`knb-lter-hbr.447.1\` | \`10.6073/pasta/f50f9bab4936632b49cf93f56750394c\` | 1982–2019 |
| Watershed 6 | \`knb-lter-hbr.448.1\` | \`10.6073/pasta/1aa4c3ad4c98ed151decc9ea7fa76694\` | 1965–2022 |

These three watersheds are nested in **one Hubbard Brook Experimental Forest**. They are distinct watershed treatment/spatial histories, **not three independently sampled forests or biomes**. Any future environmental or disturbance mechanism comparison must account for watershed histories and the event dates.

## Exactly one metadata-only gate, frozen before data opening

- Only read the three fixed EDI **Ecological Metadata Language (EML) records**, using \`https://pasta.lternet.edu/package/metadata/eml/knb-lter-hbr/<package_sequence>/1\` with the exact fixed sequence 446,447,448.
- Verify EML root's \`packageId\`, original XML bytes SHA-256 and length, and extract **source data entity names, attribute field names and rights metadata**. No original tabular file bytes, tree tags, status values, detections, absences, plot coordinates or biological outcomes are accessed.
- Report candidate attribute names for ID/stem tagging, survey year/date, diameter and status; **a column name does not establish complete sampling opportunity or direct mortality**. Even a metadata status field cannot be assumed equivalent to HF453 \`DC/DS\` or BCI source \`dead\`.
- If the provider rejects EML fetch, an EML file is an HTML access notice, package identity changes, or source schema is missing, output explicit **metadata STOP**. Do not substitute a newer version, open a package of aggregated species counts, or interpret 403 as ecological absence.
- Only nonidentifying EML schema/rights and metadata hash are archived. No original response, training or test dataset is created.
- A real independent forest-process test remains **blocked** until original entity file bytes are SHA verified, actual tree/grain linkage and measured zero/unknown states are audited, original watershed and spatial/temporal holdout groups are defined, and new response targets frozen before biological values are opened.

Pre-frozen [source package contract](../configs/hubbardbrook_edi_tree_source_metadata_v1.json), [metadata-only reader](../scripts/hubbardbrook_edi_eml_source_metadata_v1.py) and [no-source synthetic tests](../tests/test_hubbardbrook_edi_eml_source_metadata_v1.py).

## Methodological limit

The ultimate scientific question is whether independently observed forest records can carry physically coherent ecological process information beyond predictive performance and observation artifact. Hubbard Brook could contribute a separately sampled **forest** relative to Harvard, but it would not independently verify the *same prior canopy CP variable* without original directly comparable measurements; forest inventory may support another structural or temporal estimand only after source audit.

Original M5 71/80, Structural 30/30 and 0/50 synthetic KT, Harvard source association/score disagreement, Product-A \`not_promoted\`, and Product B \`blocked\` remain unchanged. BCI access 401 and SCBI master approval hold are distinct provider issues, not evidence against SDMR.
