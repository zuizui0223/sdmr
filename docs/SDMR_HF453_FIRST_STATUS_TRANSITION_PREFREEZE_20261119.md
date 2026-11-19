# HF453 first biological status opening: one-forest, predefined 2021→2022 transition and missingness bounds

**Scientific pre-outcome freeze (2026-11-19).** This is a **new, narrowly scoped original-source field-status opening**, distinct from the completed HF453 byte/identity checks and *not* a new independent forest replication. No HF453 \`status\`, \`CP\`, health or death values have been inspected in the authoring of this protocol. Outcomes are unknown and may be null, mixed, unavailable or descriptive positive. No threshold, baseline interval or cohort may be modified after first opening.

## Audited source, independence and scientific target

- Harvard Forest HF453 (v1), EML \`knb-lter-hfr.453.1\`, DOI \`10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193\`.
- Original \`hf453-01-tree-census-2021-2024.csv\`, official MD5 \`c6be7aa99e31ded2041a0aaea07c0205\`, original-source SHA256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, exactly **5,524,386 bytes**.
- Independent archived identity-source reconstruction: [run #44480551817](https://github.com/zuizui0223/sdmr/actions/runs/44480551817), artifact **#14507809147**, archive SHA256 \`db7b67ad79834d40f6e31f7b6f74b585d14b577e2e39f768ee19c0a308c2c82c\`, inner identity JSON SHA256 \`92c2ebe0a5742598cf5e8089ee0b415833d80d57e07693dd9c3e46957ef72158\`. [Machine checkpoint](../evidence/hf453_original_tag_year_identity_recovered_v2.json).
- Original panel: **30,808 unique literal StemTag identities**, exactly **30,808 tag-year rows for each of 2021–2024**, **123,232 original rows**, zero repeated tag-year keys, every tag present in all four annual data years. These are *source row/linkage counts*, **not 30,808 actually observed live stems each year**; a source row can carry \`DN\` or another non-live state.
- Publisher [HF453 original methods and dictionary](https://harvardforest1.fas.harvard.edu/exist/apps/datasets/showData.html?id=HF453): annual July visual census of stems ≥10 cm DBH within **one 35-ha ForestGEO forest plot**. The field protocol states comprehensive observations, but original individual-specific visit dates and missing opportunities are not separately proved by the published rectangular panel. No second forest/biome is being tested.

## Prespecified new field estimand, not a causal process

The primary, frozen target is **2021→2022** original source-coded observed-dead transition for originally documented 2021 \`A/AU\` stems, *conditional on membership in the 30,808-tag published source panel*. The exposed structural-context comparison is prior (2021) \`CP=3,4,5\` (greater light) **minus** \`CP=1,2\` (lower light). These are coarse categories from the published source dictionary, not a causal manipulation, and CP may reflect tree size, species, prior health and site context.

- \`A/AU\` at start: source-coded alive, candidate at risk for that interval. \`DC/DS/DN/NA/blank\` at start are **not** counted as observed-alive start events.
- \`DC/DS\` at following July: source-coded visually observed dead/down or dead/standing, \`Y=1\`. It does not identify exact death date or physiological cause.
- \`A/AU\` at following July: source-coded alive, \`Y=0\`, a *real recorded negative* for this conditional source-code endpoint.
- \`DN\` = dead/not found under the publisher's coding. **Not directly visually established dead for this endpoint**: \`Y=unknown\`. Empty or \`NA\` status are also unknown, never observed zero or death.
- Prior \`CP\` 1 or 2 gives lower-light group; 3, 4 or 5 gives greater-light group; missing CP is **retained as separate unknown-context denominator**, not opportunistically allocated to one group. Wrong/unregistered status/CP code or source key/byte drift is a hard STOP.
- All published tags and years remain in the original observed frame. Eligibility is based only on *start-year observed alive status*, never conditioned on future survival or having an observed next-year outcome. Even a tagged \`DN\` record is not a verified field visit for a living tree.
- The 2022→2023 and 2023→2024 transitions are **secondary, separately reported descriptions**; observations from the same StemTag are dependent. No interval pooling or post-outcome selection is allowed.

For CP-measured originally alive risk events, report exact original counts \`p\` (observed \`DC/DS\`), \`z\` (observed next-year \`A/AU\`), \`m\` (\`DN\` or missing next-year outcomes). Use the already coded exact sharp contrast bounds:

\[
\Delta_{\min}=\frac{p_{\mathrm{more\,light}}}{N_{\mathrm{more\,light}}} - \frac{p_{\mathrm{less\,light}}+m_{\mathrm{less\,light}}}{N_{\mathrm{less\,light}}},
\]
\[
\Delta_{\max}=\frac{p_{\mathrm{more\,light}}+m_{\mathrm{more\,light}}}{N_{\mathrm{more\,light}}}-\frac{p_{\mathrm{less\,light}}}{N_{\mathrm{less\,light}}}.
\]

A sign is called robust only if the **entire identification interval** excludes 0; otherwise \`unresolved\`. These intervals are **not statistical confidence intervals**, do not cover uncertainty outside the published tag frame, do not handle unregistered trees, and do **not identify causal canopy competition**. A source with no at-risk CP-measured events in either group yields \`unavailable\`.

## Execution contract and full-denominator audit

- Exact original source version, three hashes/size metadata, 30,808×4 source-row frame, four source field names, year ordering, primary/secondary intervals, status-code maps and CP thresholds are fixed in [\`configs/hf453_demographic_transition_first_open_v1.json\`](../configs/hf453_demographic_transition_first_open_v1.json).
- The [new analysis script](../scripts/hf453_first_status_transition_v1.py) **refuses to parse source records until the complete 5,524,386 bytes exactly match original SHA-256 and publisher MD5**. Binary original bytes are discarded after a temporary guarded read.
- It accesses **only original \`StemTag\`, \`year\`, \`status\`, \`CP\`** after source integrity; all other 10 source columns are transiently tokenized to respect CSV quoting, not interpreted, retained or exported.
- The original dataset remains a **single forest**, and all 30,808 original tags stay in the annual status-code denominator. Report first-year exclusion counts, CP missingness, known death, known alive and DN/unknown outcome for each interval, plus exact bounded CP association conditional on recorded CP. If any complete-source, ontology or original identity contract fails, STOP; do not change the result denominator after opening.
- Only aggregate JSON is archived. No raw tree row/StemTag/stem coordinate, microdata, fitted regression or fitted p-value is retained. No estimates of species-wide niche drivers, time-to-event hazards, causal death mechanisms or transfer to new forests.
- The [synthetic no-source unit suite](../tests/test_hf453_first_status_transition_v1.py) must PASS first. A separate GitHub workflow will be activated exactly once with a frozen new lock *after* code/config/tests are version-locked.
- Existing M5 71/80 and Structural 30/30 synthetic results, Product-A \`not_promoted\`, blocked Product B, previous FIA 5/5 spatial and 2/5 temporal retrospective outcomes are unaffected. This is **NOT** a way to retroactively promote any of them.

## Decision rubric fixed before results

- New source-coded field transitions can legitimately be tabulated even if the bounded sign is unresolved.
- If the sharp interval includes zero, conclude **no sign identified despite measured annual status**, not absence of a biological effect.
- If the interval has one sign, describe **single-forest observed-status association among CP-measured tagged trees**, **not a universal ecological law or causal density effect**.
- A true process-identification/generalization test still requires independent forests, original sampling-effort/attrition evidence and complete causal process carrier measurements. This source alone cannot meet that gate.

**Provider citation:** Johnson D. (2026), *Annual Tree Health and Mortality Survey of the Harvard Forest CTFS-ForestGEO Plot 2021–2024*, HF453 v1, DOI 10.6073/pasta/0bc6f43d7406c9c01e84a3dd4ed65193.
