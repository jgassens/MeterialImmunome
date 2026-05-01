# AGENTS.md

## Project Identity

This repository is for **Metalloimmunome Claim Curation Pilot**.

It is a tiny grant-preliminary-data app, not a platform. Its purpose is to help human curators turn papers into structured claim records and produce clean pilot metrics for a proposal.

The app succeeds when it helps generate:

- curated claim records
- completeness and missingness statistics
- inter-annotator agreement statistics
- adjudicated records
- proposal-ready screenshots and example claims

The app fails if it delays real curation by becoming a software project for its own sake.

## Non-Negotiable Scope Rule

No feature gets built unless it directly helps produce the pilot table for the grant.

Prefer the smallest useful workflow:

1. Register a paper.
2. Enter a claim.
3. Use controlled labels.
4. Mark missing fields.
5. Save the record.
6. Export clean CSV data.
7. Report pilot metrics.

## Version 1 Stack

Use:

- Streamlit for the interface
- SQLite for local persistence
- Pandas for export and metrics
- CSV as the primary external data format

Do not introduce a heavier stack unless the user explicitly changes the project direction.

## Version 1 Product Boundaries

Build only:

- paper registry
- claim-entry form
- controlled vocabulary fields
- missingness encoding
- saved claims table
- adjudication view
- metrics dashboard
- CSV export

Do not build in v1:

- PDF parser
- RAG system
- graph database
- prediction model
- public API
- web demo
- LLM chatbot
- automatic figure extraction
- cloud deployment
- user authentication
- fancy interface
- batch ingestion of large PDF collections

Those are possible future grant deliverables, not preliminary-data requirements.

## Scientific Priority

Treat human curation and adjudication as the scientific output.

The app is only a structured electronic lab notebook. The important outputs are the records and metrics, especially:

- number of papers screened
- number of papers curated
- number of claim records
- claims per paper
- percent of claims with dose
- percent with comparator
- percent with material form
- percent with speciation or oxidation state
- percent with assay
- percent with evidence location
- percent missing endotoxin or purity controls
- agreement on endpoint family
- agreement on direction

## Data Modeling Rules

Each claim should represent one material-context-endpoint statement.

Preserve explicit missingness. Do not silently collapse unknowns into blanks when a controlled "not reported", "unknown", or missingness label would be more useful for grant metrics.

Use controlled vocabularies wherever practical. Avoid free text for fields that drive agreement or dashboard statistics.

Core controlled fields include:

- endpoint family
- direction
- material form
- context
- confidence
- missingness labels

## Implementation Style

Keep the interface quiet, utilitarian, and fast for repeated curation.

Prefer clear forms, tables, dropdowns, checkboxes, and export buttons over decorative UI. Screenshots should look credible in a grant proposal, but visual polish must not compete with curation speed.

Keep app logic simple and inspectable:

- database setup should be easy to understand
- claim IDs should be deterministic
- exports should be reproducible
- dashboard metrics should be derived from saved records
- adjudication should preserve original curator entries and final values

## Testing Expectations

When adding implementation later, verify at minimum:

- a paper can be registered
- a claim can be saved
- required controlled fields render as controlled inputs
- missingness labels are saved
- claim records can be exported to CSV
- metrics update from saved records
- adjudicated values can be exported or distinguished from raw annotations

Do not claim readiness from UI inspection alone. Use a small seed dataset or manual smoke test that proves the workflow produces grant-ready outputs.

## README Contract

Keep `README.md` aligned with this file. If implementation changes the workflow, update the README so a new curator or coding agent can understand:

- what the pilot app is for
- what is intentionally out of scope
- how to run it
- how to curate records
- how to export grant-ready outputs

