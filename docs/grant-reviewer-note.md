# Grant Reviewer Note

This repository contains the **Metalloimmunome Claim Curation Pilot**, a small local Streamlit + SQLite app used to support preliminary claim-level curation for a grant proposal.

It is a curation cockpit, not the full Metalloimmunome platform. It organizes paper registry records, evidence-anchored claim slots, paired curator annotations, annotation locking, human adjudication, QA checks, agreement metrics, and local grant-packet export.

## How to run it

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./run-app
```

Open the local Streamlit URL printed in the terminal. If Streamlit asks for an onboarding email, pressing Enter with a blank email is fine.

## What reviewers should inspect

Reviewers should look at:

- the six-tab workflow in the local app
- controlled field entry in **Annotate**
- evidence anchoring in **Claim Slots**
- disagreement review and final record entry in **Adjudicate**
- QA flags and data dictionary in **Codebook + QA**
- metrics and grant-packet downloads in **Metrics + Export**

The curation model is: **human-adjudicated pilot records generated from two independent AI-assisted extraction passes**.

## What not to infer

Do not infer that this repository is:

- the complete Metalloimmunome platform
- a public hosted web service
- an automated literature-mining system
- a PDF ingestion pipeline
- a RAG or chatbot system
- a graph database
- a prediction model
- the full scientific dataset

The app itself does not automatically extract claims from papers. It structures and preserves curation work so the pilot can produce auditable preliminary outputs.

## Exported grant data

Exported grant data are produced locally from the **Metrics + Export** tab. The public repository may not include local SQLite databases, grant-packet ZIPs, PDFs, or CSV exports.

Proposal-level scientific claims should be checked against the exported adjudicated grant packet, not against demo fixtures or the repository code alone.
