"""CSV-ready exports for claim records."""

from __future__ import annotations

import sqlite3

import pandas as pd

from . import db
from .vocab import CLAIM_FIELDS, EXPORT_COLUMNS


def _filter_table(frame: pd.DataFrame, include_demo: bool, flag: str) -> pd.DataFrame:
    if frame.empty or include_demo:
        return frame.copy()
    return frame[(frame["demo"] == 0) & (frame[flag] == 0)].copy()


def _load_filtered_tables(
    conn: sqlite3.Connection, include_demo: bool, flag: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    papers = _filter_table(db.table_df(conn, "papers"), include_demo, flag)
    slots = _filter_table(db.table_df(conn, "claim_slots"), include_demo, flag)
    annotations = _filter_table(db.table_df(conn, "annotations"), include_demo, flag)
    adjudications = _filter_table(db.table_df(conn, "adjudications"), include_demo, flag)

    if not papers.empty:
        slots = slots[slots["paper_id"].isin(papers["paper_id"])]
    else:
        slots = slots.iloc[0:0]

    if not slots.empty:
        annotations = annotations[annotations["claim_id"].isin(slots["claim_id"])]
        adjudications = adjudications[adjudications["claim_id"].isin(slots["claim_id"])]
    else:
        annotations = annotations.iloc[0:0]
        adjudications = adjudications.iloc[0:0]

    return papers, slots, annotations, adjudications


def claim_records_df(conn: sqlite3.Connection, *, include_demo: bool = False) -> pd.DataFrame:
    """Return adjudicated records when present and raw annotations otherwise."""
    _papers, slots, annotations, adjudications = _load_filtered_tables(
        conn, include_demo, "exclude_from_export_by_default"
    )
    records: list[dict[str, object]] = []
    adjudicated_claim_ids = set(adjudications["claim_id"].tolist())

    slot_lookup = slots.set_index("claim_id").to_dict("index") if not slots.empty else {}

    for row in adjudications.to_dict("records"):
        claim_id = row["claim_id"]
        slot = slot_lookup.get(claim_id, {})
        record = {
            "record_type": "adjudicated",
            "paper_id": slot.get("paper_id", ""),
            "claim_id": claim_id,
            "curator_or_adjudicator": row.get("adjudicator", ""),
            "demo": int(row.get("demo", 0) or slot.get("demo", 0)),
            "source_type": row.get("source_type", ""),
        }
        for field in CLAIM_FIELDS:
            record[field] = row.get(f"final_{field}", "")
        records.append(record)

    raw_annotations = annotations[~annotations["claim_id"].isin(adjudicated_claim_ids)]
    for row in raw_annotations.to_dict("records"):
        claim_id = row["claim_id"]
        slot = slot_lookup.get(claim_id, {})
        record = {
            "record_type": "raw_annotation",
            "paper_id": slot.get("paper_id", ""),
            "claim_id": claim_id,
            "curator_or_adjudicator": row.get("curator", ""),
            "demo": int(row.get("demo", 0) or slot.get("demo", 0)),
            "source_type": row.get("source_type", ""),
        }
        for field in CLAIM_FIELDS:
            record[field] = row.get(field, "")
        records.append(record)

    return pd.DataFrame(records, columns=EXPORT_COLUMNS)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Encode a DataFrame as UTF-8 CSV bytes for Streamlit downloads."""
    return frame.to_csv(index=False).encode("utf-8")


def export_summary(conn: sqlite3.Connection, *, include_demo: bool = False) -> dict[str, int]:
    """Return sanity-check counts for the currently selected export scope."""
    records = claim_records_df(conn, include_demo=include_demo)
    all_records = claim_records_df(conn, include_demo=True)
    if records.empty:
        adjudicated = 0
        raw = 0
        demo_in_export = 0
    else:
        adjudicated = int((records["record_type"] == "adjudicated").sum())
        raw = int((records["record_type"] == "raw_annotation").sum())
        demo_in_export = int((records["demo"] == 1).sum())
    return {
        "exported_records": len(records),
        "adjudicated_records": adjudicated,
        "raw_annotation_records": raw,
        "demo_records_in_export": demo_in_export,
        "demo_records_excluded": max(len(all_records) - len(records), 0)
        if not include_demo
        else 0,
    }


def filtered_tables_for_metrics(
    conn: sqlite3.Connection, *, include_demo: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return _load_filtered_tables(conn, include_demo, "exclude_from_metrics")
