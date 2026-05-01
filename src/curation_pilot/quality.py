"""Codebook and data-quality reporting for the pilot workflow."""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd

from . import db, exports, metrics, validation
from .vocab import (
    AGREEMENT_FIELDS,
    ANCHOR_TYPES,
    CONFIDENCE_LEVELS,
    CONTEXTS,
    DIRECTIONS,
    ENDPOINT_FAMILIES,
    KAPPA_FIELDS,
    MATERIAL_FORMS,
    MISSINGNESS_OPTIONS,
    PAPER_IMPORT_COLUMNS,
    VALID_CLAIM_OPTIONS,
)


def _issue(
    rows: list[dict[str, str]],
    severity: str,
    issue_type: str,
    table: str,
    record_id: str,
    message: str,
) -> None:
    rows.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "table": table,
            "record_id": record_id,
            "message": message,
        }
    )


def data_dictionary_df() -> pd.DataFrame:
    rows = [
        (
            "paper registry",
            "paper_id",
            "Stable local paper identifier such as P001.",
            "",
            "yes",
        ),
        ("paper registry", "pmid", "PubMed identifier for real imported papers.", "", "yes"),
        ("paper registry", "include_in_v1", "Marks the 12-paper MVP set.", "yes; no", "no"),
        (
            "claim slot",
            "anchor_type",
            "Shared evidence anchor type for paired annotation.",
            "; ".join(ANCHOR_TYPES),
            "yes",
        ),
        (
            "claim slot",
            "anchor_location",
            "Shared location such as Fig. 2A or Results paragraph 3.",
            "",
            "yes",
        ),
        (
            "annotation",
            "valid_claim",
            "Curator judgment that the shared slot is a valid claim.",
            "; ".join(VALID_CLAIM_OPTIONS),
            "yes",
        ),
        (
            "annotation",
            "locked",
            "Locked annotations are eligible for agreement, kappa, QA, and adjudication.",
            "0; 1",
            "yes",
        ),
        (
            "annotation",
            "endpoint_family",
            "Controlled endpoint family.",
            "; ".join(ENDPOINT_FAMILIES),
            "yes when valid_claim = yes",
        ),
        (
            "annotation",
            "direction",
            "Controlled direction of the claim.",
            "; ".join(DIRECTIONS),
            "yes when valid_claim = yes",
        ),
        (
            "annotation",
            "material_form",
            "Controlled material form.",
            "; ".join(MATERIAL_FORMS),
            "no",
        ),
        (
            "annotation",
            "in_vitro_or_in_vivo",
            "Controlled biological context.",
            "; ".join(CONTEXTS),
            "no",
        ),
        (
            "annotation",
            "confidence",
            "Curator confidence in the structured claim.",
            "; ".join(CONFIDENCE_LEVELS),
            "yes when valid_claim = yes",
        ),
        (
            "annotation",
            "missing_core_fields",
            "Explicit missingness labels.",
            "; ".join(MISSINGNESS_OPTIONS),
            "no",
        ),
        (
            "metrics",
            "agreement_fields",
            "Fields used for raw agreement.",
            "; ".join(AGREEMENT_FIELDS),
            "n/a",
        ),
        (
            "metrics",
            "kappa_fields",
            "Fields used for Cohen's kappa.",
            "; ".join(KAPPA_FIELDS),
            "n/a",
        ),
        (
            "export",
            "demo exclusion",
            "Grant-facing outputs exclude demo rows by default.",
            "demo = 0",
            "yes",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=["section", "field", "description", "allowed_values", "required"],
    )


def _filtered_tables(
    conn: sqlite3.Connection, include_demo: bool
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return exports.filtered_tables_for_metrics(conn, include_demo=include_demo)


def data_quality_report_df(
    conn: sqlite3.Connection, *, include_demo: bool = False
) -> pd.DataFrame:
    papers, slots, annotations, adjudications = _filtered_tables(conn, include_demo)
    records = exports.claim_records_df(conn, include_demo=include_demo)
    rows: list[dict[str, str]] = []

    if include_demo:
        demo_count = int((records["demo"] == 1).sum()) if not records.empty else 0
        if demo_count:
            _issue(
                rows,
                "warning",
                "demo_rows_included",
                "exports",
                "grant-facing outputs",
                f"{demo_count} demo records are included in this report.",
            )

    for paper in papers.to_dict("records"):
        paper_id = str(paper.get("paper_id", ""))
        for field in ["paper_id", "title", "metal_cluster", "paper_type", "status"]:
            if not str(paper.get(field, "") or "").strip():
                _issue(
                    rows,
                    "error",
                    "missing_required_paper_field",
                    "papers",
                    paper_id,
                    f"Paper is missing required field `{field}`.",
                )
        if not int(paper.get("demo", 0) or 0) and not str(paper.get("pmid", "") or "").strip():
            _issue(
                rows,
                "error",
                "missing_pmid",
                "papers",
                paper_id,
                "Real paper is missing PMID.",
            )

    if not papers.empty and "pmid" in papers.columns:
        pmid_counts = papers[papers["pmid"].astype(str).str.strip() != ""].groupby("pmid")
        for pmid, group in pmid_counts:
            if len(group) > 1:
                _issue(
                    rows,
                    "warning",
                    "duplicate_pmid",
                    "papers",
                    str(pmid),
                    "PMID appears under multiple paper IDs: "
                    + ", ".join(group["paper_id"].astype(str).tolist()),
                )

    annotation_counts = (
        annotations.groupby("claim_id")["curator"].nunique().to_dict()
        if not annotations.empty
        else {}
    )
    locked_counts = (
        annotations[annotations["locked"].astype(int) == 1]
        .groupby("claim_id")["curator"]
        .nunique()
        .to_dict()
        if not annotations.empty and "locked" in annotations.columns
        else {}
    )
    adjudicated_ids = set(adjudications["claim_id"].tolist()) if not adjudications.empty else set()

    for slot in slots.to_dict("records"):
        claim_id = str(slot.get("claim_id", ""))
        if not str(slot.get("anchor_type", "") or "").strip():
            _issue(
                rows,
                "warning",
                "missing_anchor_type",
                "claim_slots",
                claim_id,
                "Claim slot is missing anchor_type.",
            )
        if not str(slot.get("anchor_location", "") or "").strip():
            _issue(
                rows,
                "warning",
                "missing_anchor_location",
                "claim_slots",
                claim_id,
                "Claim slot is missing anchor_location.",
            )
        annotator_count = int(annotation_counts.get(claim_id, 0))
        locked_count = int(locked_counts.get(claim_id, 0))
        if annotator_count < 2:
            _issue(
                rows,
                "warning",
                "unpaired_claim_slot",
                "claim_slots",
                claim_id,
                "Claim slot has fewer than two curator annotations.",
            )
        elif locked_count < 2:
            _issue(
                rows,
                "warning",
                "paired_but_unlocked",
                "annotations",
                claim_id,
                "Claim slot is paired but fewer than two annotations are locked.",
            )
        elif claim_id not in adjudicated_ids:
            _issue(
                rows,
                "warning",
                "paired_locked_unadjudicated",
                "claim_slots",
                claim_id,
                "Claim slot has paired locked annotations but no adjudication.",
            )

    for record in records.to_dict("records"):
        record_id = f"{record.get('paper_id', '')}/{record.get('claim_id', '')}"
        if not metrics.has_value(record.get("evidence_location", "")):
            _issue(
                rows,
                "error",
                "blank_evidence_location",
                "claim_records",
                record_id,
                "Record has blank evidence_location.",
            )
        if str(record.get("valid_claim", "")).strip() == "unsure":
            _issue(
                rows,
                "warning",
                "valid_claim_unsure",
                "claim_records",
                record_id,
                "Record has valid_claim = unsure.",
            )
        for complete in validation.completeness_rows(record):
            if complete["status"] == "needs review" and complete["missingness_label"]:
                _issue(
                    rows,
                    "warning",
                    "missingness_label_absent",
                    "claim_records",
                    record_id,
                    f"{complete['field']} is blank or not reported without "
                    f"`{complete['missingness_label']}`.",
                )

    for claim_id, group in metrics.paired_annotation_groups(annotations, locked_only=True):
        values = {str(value).strip() for value in group["valid_claim"].tolist()}
        if len(values) > 1:
            _issue(
                rows,
                "warning",
                "valid_claim_disagreement",
                "annotations",
                str(claim_id),
                "Locked paired annotations disagree on valid_claim.",
            )

    for adjudication in adjudications.to_dict("records"):
        claim_id = str(adjudication.get("claim_id", ""))
        final_valid = str(adjudication.get("final_valid_claim", "") or "").strip()
        if final_valid == "no" and (
            str(adjudication.get("final_endpoint_family", "") or "").strip()
            or str(adjudication.get("final_direction", "") or "").strip()
        ):
            _issue(
                rows,
                "warning",
                "invalid_final_has_claim_fields",
                "adjudications",
                claim_id,
                "Final valid_claim = no but endpoint or direction is populated.",
            )
        if str(adjudication.get("final_confidence", "") or "").strip() == "low":
            _issue(
                rows,
                "warning",
                "low_confidence_final",
                "adjudications",
                claim_id,
                "Final adjudicated record has low confidence.",
            )

    return pd.DataFrame(
        rows,
        columns=["severity", "issue_type", "table", "record_id", "message"],
    )


def paper_registry_df(conn: sqlite3.Connection, *, include_demo: bool = False) -> pd.DataFrame:
    papers = db.table_df(conn, "papers")
    if papers.empty or include_demo:
        return papers
    return papers[(papers["demo"] == 0) & (papers["exclude_from_export_by_default"] == 0)].copy()


def claim_slots_df(conn: sqlite3.Connection, *, include_demo: bool = False) -> pd.DataFrame:
    slots = db.table_df(conn, "claim_slots")
    if slots.empty or include_demo:
        return slots
    return slots[(slots["demo"] == 0) & (slots["exclude_from_export_by_default"] == 0)].copy()


def import_template_columns() -> list[str]:
    return PAPER_IMPORT_COLUMNS
