"""Paper-registry CSV validation and import."""

from __future__ import annotations

import io
import sqlite3
from dataclasses import dataclass
from typing import Any

import pandas as pd

from . import db
from .vocab import PAPER_IMPORT_COLUMNS


@dataclass
class ImportPreview:
    records: pd.DataFrame
    issues: pd.DataFrame
    has_errors: bool
    imported_count: int = 0


def _issue(
    rows: list[dict[str, str]],
    severity: str,
    row_number: str,
    field: str,
    message: str,
) -> None:
    rows.append(
        {
            "severity": severity,
            "row_number": row_number,
            "field": field,
            "message": message,
        }
    )


def _normalize_column(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _read_csv(content: str | bytes) -> pd.DataFrame:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    return pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def validate_paper_registry_csv(
    conn: sqlite3.Connection, content: str | bytes
) -> ImportPreview:
    issues: list[dict[str, str]] = []
    try:
        raw = _read_csv(content)
    except Exception as exc:  # pragma: no cover - pandas error wording varies
        _issue(issues, "error", "file", "csv", f"Could not parse CSV: {exc}")
        return _preview([], issues)

    original_columns = [_normalize_column(column) for column in raw.columns]
    raw.columns = original_columns
    accepted = set(PAPER_IMPORT_COLUMNS)
    unknown = [column for column in raw.columns if column not in accepted]
    for column in unknown:
        _issue(issues, "warning", "file", column, "Unknown column will be ignored.")

    if "paper_id" not in raw.columns:
        _issue(issues, "error", "file", "paper_id", "CSV must include paper_id.")
    if "pmid" not in raw.columns:
        _issue(issues, "error", "file", "pmid", "CSV must include pmid.")

    for column in PAPER_IMPORT_COLUMNS:
        if column not in raw.columns:
            raw[column] = ""

    if "metal_cluster" in raw.columns and "cluster" in raw.columns:
        raw["metal_cluster"] = raw["metal_cluster"].where(
            raw["metal_cluster"].astype(str).str.strip() != "",
            raw["cluster"],
        )
        raw["cluster"] = raw["cluster"].where(
            raw["cluster"].astype(str).str.strip() != "",
            raw["metal_cluster"],
        )

    records: list[dict[str, Any]] = []
    for index, row in raw.iterrows():
        row_number = str(index + 2)
        record = {column: str(row.get(column, "") or "").strip() for column in PAPER_IMPORT_COLUMNS}
        record.setdefault("paper_type", "primary study")
        record.setdefault("full_text_available", "yes")
        record.setdefault("status", "not started")
        if not record["paper_type"]:
            record["paper_type"] = "primary study"
        if not record["full_text_available"]:
            record["full_text_available"] = "yes"
        if not record["status"]:
            record["status"] = "not started"

        if not record["paper_id"]:
            _issue(issues, "error", row_number, "paper_id", "paper_id is required.")
        is_demo = _boolish(str(row.get("demo", "")))
        if not is_demo and not record["pmid"]:
            _issue(
                issues,
                "error",
                row_number,
                "pmid",
                "PMID is required for non-demo imported papers.",
            )
        record.update(
            {
                "demo": is_demo,
                "source_type": "imported_registry",
                "exclude_from_metrics": False,
                "exclude_from_export_by_default": False,
            }
        )
        records.append(record)

    records_df = pd.DataFrame(records, columns=db.PAPER_COLUMNS)
    _add_duplicate_pmid_warnings(conn, records_df, issues)
    return _preview(records_df, issues)


def _add_duplicate_pmid_warnings(
    conn: sqlite3.Connection, records: pd.DataFrame, issues: list[dict[str, str]]
) -> None:
    if records.empty or "pmid" not in records:
        return

    nonblank = records[records["pmid"].astype(str).str.strip() != ""]
    for pmid, group in nonblank.groupby("pmid"):
        if len(group["paper_id"].unique()) > 1:
            _issue(
                issues,
                "warning",
                "upload",
                "pmid",
                f"Duplicate PMID {pmid} appears under multiple uploaded paper IDs.",
            )

    existing = db.table_df(conn, "papers")
    if existing.empty:
        return
    existing_pmids = existing[existing["pmid"].astype(str).str.strip() != ""]
    for record in nonblank.to_dict("records"):
        matches = existing_pmids[
            (existing_pmids["pmid"] == record["pmid"])
            & (existing_pmids["paper_id"] != record["paper_id"])
        ]
        if not matches.empty:
            _issue(
                issues,
                "warning",
                "upload",
                "pmid",
                f"Duplicate PMID {record['pmid']} already exists under another paper ID.",
            )


def _preview(records: pd.DataFrame | list[Any], issues: list[dict[str, str]]) -> ImportPreview:
    records_df = (
        records
        if isinstance(records, pd.DataFrame)
        else pd.DataFrame(records, columns=db.PAPER_COLUMNS)
    )
    issues_df = pd.DataFrame(
        issues,
        columns=["severity", "row_number", "field", "message"],
    )
    has_errors = bool(not issues_df.empty and (issues_df["severity"] == "error").any())
    return ImportPreview(records_df, issues_df, has_errors)


def import_paper_registry_csv(
    conn: sqlite3.Connection, content: str | bytes
) -> ImportPreview:
    preview = validate_paper_registry_csv(conn, content)
    if preview.has_errors:
        return preview

    try:
        conn.commit()
        conn.execute("BEGIN")
        for record in preview.records.to_dict("records"):
            db.upsert_paper(conn, record, commit=False)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    preview.imported_count = len(preview.records)
    return preview
