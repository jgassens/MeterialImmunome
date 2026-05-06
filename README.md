# Metalloimmunome Claim Curation Pilot

A small local app for turning metal–immune papers into structured, adjudicated claim records. The pilot is built around a simple workflow: register papers, define evidence-anchored claim slots, collect paired annotations, lock records, adjudicate disagreements, check quality, and export a grant-ready packet.

![Metalloimmunome Knowledge Pipeline](docs/assets/metalloimmunome_knowledge_pipeline.png)

**Figure.** Evidence sources are converted into study registry entries and evidence-anchored claim slots, independently curated, human-adjudicated, quality-checked, and used to support knowledge graph construction and trust-calibrated material–immune prediction.

## Why this exists

Claim-level curation gets messy quickly in spreadsheets. This app keeps the pilot work organized with stable paper records, deterministic claim IDs, controlled labels, locked annotations, adjudication, QA checks, agreement metrics, and local exports.

The scientific unit here is a conditional claim: material, form, context, comparator, endpoint, direction, and evidence. That is more useful than a flat statement like "metal X causes immune response Y." The app also makes missingness and provenance explicit, so incomplete reporting becomes measurable instead of disappearing into blank cells.

## Scope

This is not the full Metalloimmunome platform. It is a local Streamlit + SQLite curation cockpit for producing auditable pilot records. It does not do PDF ingestion, automatic extraction, hosted deployment, graph storage, or prediction modeling.

## Workflow

The app has six tabs:

- **Papers**: register papers, track metadata, and import paper-registry CSV files.
- **Claim Slots**: define the exact figure, table, or text anchor for each claim.
- **Annotate**: enter one structured annotation for one curator and one claim slot.
- **Adjudicate**: compare locked paired annotations and save the final record.
- **Codebook + QA**: check field definitions, controlled labels, and data-quality flags.
- **Metrics + Export**: review metrics, export CSVs, create the grant packet, and download a SQLite backup.

```text
paper registry -> claim slots -> paired annotations -> locked annotations -> adjudication -> QA/metrics/export
```

## Curation model

The pilot uses two independent AI-assisted curation passes followed by human adjudication.

Original curator annotations are preserved, and adjudicated records are exported when available. Unadjudicated slots fall back to raw annotation records so incomplete pilot work remains visible rather than hidden.

Demo fixtures are seeded on first run so the workflow is visible immediately. They are excluded from grant-facing metrics and exports by default.

## Grant packet

The **Metrics + Export** tab creates a local grant-packet ZIP with:

- `curated_claim_records.csv`
- `paper_registry.csv`
- `claim_slots.csv`
- `pilot_metrics.csv`
- `agreement_report.csv`
- `data_quality_report.csv`
- `data_dictionary.csv`
- `example_claims.csv`
- `proposal_summary.md`
- `README_grant_packet.md`

Demo rows are excluded by default.

The repository does not need to include local SQLite databases or exported packets. Scientific claims should be checked against the exported adjudicated packet, not against demo fixtures or the code alone.

## Run locally

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./run-app
```

Streamlit prints a local URL such as `http://localhost:8501`. Open that URL in a browser. If Streamlit asks for an onboarding email on first launch, pressing Enter with a blank email is fine.

## Development checks

```bash
.venv/bin/python -m pytest
```

GitHub Actions runs `pytest` on pushes and pull requests when enabled for the repository.

## Data handling

- SQLite files live under `data/` and are git-ignored.
- Exported packets are git-ignored.
- No secrets, cloud service, or telemetry are required.
- Do not commit databases, PDFs, exported packets, secrets, or virtual environments.

## Proposal use

This repository can be cited as the software artifact supporting the preliminary curation workflow. Scientific claims should be checked against the exported adjudicated grant packet, not against demo fixtures.
