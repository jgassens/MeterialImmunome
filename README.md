# Metalloimmunome Claim Curation Pilot

A tiny curation app for producing preliminary data for a metalloimmunome grant.

This is not the Metalloimmunome Platform. It is a structured, local pilot tool whose job is to help curators turn papers into claim-level records, measure completeness and missingness, compare annotators, adjudicate disagreements, and export clean data for the proposal.

The guiding rule is simple:

> No feature gets built unless it directly helps produce the pilot table for the grant.

## Purpose

The app replaces a spreadsheet when a spreadsheet would become messy:

- multiple curators need consistent fields
- controlled dropdowns matter
- missingness needs to be counted
- claim IDs should be automatic
- agreement statistics are needed
- proposal screenshots would help
- clean CSV export is required

The preliminary data are the curated records and metrics. The app is only the tool that gets them there.

## Version 1 Stack

Planned v1 stack:

- **Streamlit** for the interface
- **SQLite** for local storage
- **Pandas** for export and dashboard metrics
- **CSV** for grant-ready data export

No LLMs are planned for v1.

## Minimum Useful Workflow

The smallest useful app should support:

1. Select or register a paper.
2. Enter one material-context-endpoint claim.
3. Choose controlled labels.
4. Mark missing core fields.
5. Save the claim.
6. Review saved claims in a table.
7. Export a clean CSV.
8. View pilot metrics.

If v1 does only that well, it is successful.

## Planned Screens

### Paper Registry

Tracks the papers included in the pilot.

| Field | Example |
| --- | --- |
| `paper_id` | `P001` |
| `pmid` | `18604214` |
| `doi` | optional |
| `title` | paper title |
| `metal_cluster` | aluminum / nickel / CoCr / zinc / other |
| `paper_type` | primary study / review / excluded |
| `full_text_available` | yes / no |
| `curator` | initials |
| `status` | not started / in progress / curated / adjudicated |

### Claim Entry

Each claim is one material-context-endpoint statement.

| Field | Example |
| --- | --- |
| `paper_id` | `P001` |
| `claim_id` | `P001-C003` |
| `metal` | `Al` |
| `material_form` | aluminum hydroxide / alum particle |
| `speciation_or_oxidation_state` | not reported |
| `dose` | `100 ug/mL` |
| `duration` | `24 h` |
| `species` | mouse |
| `cell_or_tissue` | bone-marrow-derived macrophage |
| `in_vitro_or_in_vivo` | in vitro |
| `route_or_context` | cell-culture exposure |
| `stimulation_context` | LPS-primed |
| `comparator` | LPS only |
| `endpoint_family` | inflammasome activation |
| `specific_endpoint` | IL-1 beta secretion |
| `assay` | ELISA |
| `direction` | increased |
| `magnitude` | not reported / fold-change if available |
| `evidence_location` | Fig. 2A |
| `exact_evidence_excerpt` | short copied phrase or paraphrased note |
| `missing_core_fields` | speciation; endotoxin control |
| `confidence` | high / medium / low |
| `curator_notes` | brief note |

### Controlled Vocabulary Manager

The app should use dropdowns or controlled multi-selects wherever values drive metrics or agreement.

| Variable | Allowed values |
| --- | --- |
| `endpoint_family` | inflammasome activation; cytokine induction/skewing; cytotoxicity; other |
| `direction` | increased; decreased; unchanged; mixed; unclear |
| `material_form` | soluble salt; hydroxide; oxide; alloy debris; nanoparticle; MOF; coating; unknown |
| `context` | in vitro; in vivo; ex vivo; clinical tissue |
| `confidence` | high; medium; low |
| `missingness` | dose missing; comparator missing; speciation missing; assay unclear; endpoint unclear; purity/endotoxin not reported |

### Adjudication View

Two curators should be able to annotate the same 15-30 records or papers.

The adjudication view should surface disagreements on:

- endpoint family
- direction
- comparator
- material form
- dose present or absent
- confidence

An adjudicator should select final values while preserving the original curator entries.

### Metrics Dashboard

The dashboard is the grant-facing payoff.

It should report:

| Metric | Why it matters |
| --- | --- |
| number of papers screened | shows scope |
| number of papers curated | shows feasibility |
| number of claim records | shows data density |
| claims per paper | tests whether the paper set is enough |
| percent with dose | tests schema completeness |
| percent with comparator | tests experimental interpretability |
| percent with material form | tests chemistry capture |
| percent with speciation or oxidation state | tests chemistry depth |
| percent with assay | tests endpoint reliability |
| percent with evidence location | tests provenance |
| percent missing endotoxin or purity controls | supports the missingness argument |
| agreement on endpoint family | supports curation reliability |
| agreement on direction | supports curation reliability |

## Grant-Ready Outputs

At the end of the pilot, the app should produce:

1. A CSV of curated claim records.
2. A one-page table of pilot metrics.
3. A screenshot of the curation interface.
4. A screenshot of the missingness and completeness dashboard.
5. A few example claims showing why context matters.
6. A proposal-ready summary sentence.

Example proposal language:

> To test feasibility, we built a lightweight claim-curation interface that allowed curators to register papers, extract context-conditioned metal-immune claims, encode missingness, and export adjudicated records. The pilot was used to curate [N] papers and extract [X] claims, producing the preliminary completeness and agreement statistics reported here.

Example pilot result sentence:

> In a pilot curation of 12 primary studies, the interface produced 54 claim-level records across aluminum, nickel, and cobalt/chromium contexts. Comparator, endpoint, assay, and direction were recoverable in most records, while dose, speciation, and endotoxin/purity reporting were inconsistently available, supporting explicit missingness encoding.

## What Not To Build Now

Do not build these in v1:

- PDF parser
- RAG system
- graph database
- prediction model
- API
- web demo
- LLM chatbot
- automatic figure extraction
- AWS or cloud deployment
- user authentication system
- fancy interface
- batch ingestion for large PDF collections

Those are grant deliverables or future extensions, not preliminary-data needs.

## Future Run Path

Use the local Streamlit app:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens locally in the browser and stores records in `data/curation.sqlite`.

The first run seeds tiny demo fixtures so the workflow is visible immediately. Demo rows are clearly marked and are excluded from metrics and exports by default:

- `demo = true`
- `source_type = demo_fixture`
- `exclude_from_metrics = true`
- `exclude_from_export_by_default = true`

Curators should register real papers, create shared claim slots, enter paired annotations, adjudicate disagreements, and export CSV plus dashboard metrics for the proposal.

## App Workflow

The Streamlit app has five tabs:

- **Papers**: create and update paper registry records.
- **Claim Slots**: create deterministic shared claim IDs such as `P001-C003`.
- **Annotate**: enter one curator annotation per shared claim slot.
- **Adjudicate**: review paired disagreements and save final values.
- **Metrics + Export**: download `curated_claim_records.csv` and `pilot_metrics.csv`.

Exports use adjudicated records when available. If a claim slot has not been adjudicated yet, the export includes raw annotation records instead.

## Acceptance Criteria for v1

Version 1 is done when:

- a curator can register papers
- a curator can enter claim-level records with controlled labels
- missing core fields can be explicitly marked
- records persist in SQLite
- saved claims can be reviewed in the app
- curated claims export as CSV
- the dashboard reports completeness and agreement metrics
- screenshots are suitable for a grant proposal
- no feature distracts from producing the pilot dataset
