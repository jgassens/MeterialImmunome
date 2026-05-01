"""Grant-packet and backup exports."""

from __future__ import annotations

import io
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import db, exports, metrics, quality


def timestamp_slug(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d_%H%M")


def _metric(metric_frame: pd.DataFrame, name: str) -> object:
    match = metric_frame[metric_frame["metric"] == name]
    if match.empty:
        return ""
    return match["value"].iloc[0]


def proposal_summary_md(
    conn: sqlite3.Connection, *, include_demo: bool = False
) -> str:
    metric_frame = metrics.metrics_df(conn, include_demo=include_demo)
    return "\n".join(
        [
            "# Metalloimmunome Pilot Summary",
            "",
            f"Papers screened: {_metric(metric_frame, 'papers_screened')}",
            f"Papers curated: {_metric(metric_frame, 'papers_curated')}",
            f"Claim records: {_metric(metric_frame, 'claim_records')}",
            f"Claims per paper: {_metric(metric_frame, 'claims_per_paper')}",
            f"Percent with dose: {_metric(metric_frame, 'percent_with_dose')}",
            f"Percent with comparator: {_metric(metric_frame, 'percent_with_comparator')}",
            f"Endpoint-family raw agreement: {_metric(metric_frame, 'agreement_endpoint_family')}",
            f"Endpoint-family Cohen's kappa: {_metric(metric_frame, 'kappa_endpoint_family')}",
            "",
            "Demo rows are excluded from this summary by default.",
        ]
    )


def grant_packet_readme() -> str:
    return "\n".join(
        [
            "# Grant Packet Contents",
            "",
            "All grant-facing files exclude demo rows by default.",
            "",
            "- `curated_claim_records.csv`: adjudicated records when present, otherwise raw annotations.",
            "- `paper_registry.csv`: paper metadata for the pilot registry.",
            "- `claim_slots.csv`: shared claim slots and evidence anchors.",
            "- `pilot_metrics.csv`: completeness, missingness, agreement, and kappa metrics.",
            "- `agreement_report.csv`: field-level raw agreement and Cohen's kappa.",
            "- `data_quality_report.csv`: QA flags to review before using outputs in the proposal.",
            "- `data_dictionary.csv`: field definitions and controlled vocabularies.",
            "- `example_claims.csv`: a small adjudicated-first sample of claim records.",
            "- `proposal_summary.md`: metrics-derived prose starter for the proposal.",
        ]
    )


def example_claims_df(
    conn: sqlite3.Connection, *, include_demo: bool = False, limit: int = 5
) -> pd.DataFrame:
    records = exports.claim_records_df(conn, include_demo=include_demo)
    if records.empty:
        return records
    priority = records["record_type"].map({"adjudicated": 0}).fillna(1)
    return records.assign(_priority=priority).sort_values(
        ["_priority", "paper_id", "claim_id"]
    ).drop(columns=["_priority"]).head(limit)


def grant_packet_files(
    conn: sqlite3.Connection, *, include_demo: bool = False
) -> dict[str, bytes]:
    _papers, _slots, annotations, _adjudications = exports.filtered_tables_for_metrics(
        conn, include_demo=include_demo
    )
    files = {
        "curated_claim_records.csv": exports.csv_bytes(
            exports.claim_records_df(conn, include_demo=include_demo)
        ),
        "paper_registry.csv": exports.csv_bytes(
            quality.paper_registry_df(conn, include_demo=include_demo)
        ),
        "claim_slots.csv": exports.csv_bytes(
            quality.claim_slots_df(conn, include_demo=include_demo)
        ),
        "pilot_metrics.csv": exports.csv_bytes(
            metrics.metrics_df(conn, include_demo=include_demo)
        ),
        "agreement_report.csv": exports.csv_bytes(
            metrics.agreement_report_df(annotations, locked_only=True)
        ),
        "data_quality_report.csv": exports.csv_bytes(
            quality.data_quality_report_df(conn, include_demo=include_demo)
        ),
        "data_dictionary.csv": exports.csv_bytes(quality.data_dictionary_df()),
        "example_claims.csv": exports.csv_bytes(
            example_claims_df(conn, include_demo=include_demo)
        ),
        "proposal_summary.md": proposal_summary_md(
            conn, include_demo=include_demo
        ).encode("utf-8"),
        "README_grant_packet.md": grant_packet_readme().encode("utf-8"),
    }
    return files


def grant_packet_zip(
    conn: sqlite3.Connection,
    *,
    include_demo: bool = False,
    now: datetime | None = None,
) -> tuple[str, bytes]:
    filename = f"metalloimmunome_pilot_packet_{timestamp_slug(now)}.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in grant_packet_files(conn, include_demo=include_demo).items():
            archive.writestr(path, content)
    return filename, buffer.getvalue()


def sqlite_backup_bytes(conn: sqlite3.Connection) -> bytes:
    database_path = conn.execute("PRAGMA database_list").fetchone()["file"]
    if database_path:
        return Path(database_path).read_bytes()
    buffer = io.BytesIO()
    backup_conn = sqlite3.connect(":memory:")
    try:
        conn.backup(backup_conn)
        for line in backup_conn.iterdump():
            buffer.write((line + "\n").encode("utf-8"))
    finally:
        backup_conn.close()
    return buffer.getvalue()


def sqlite_backup_download(
    conn: sqlite3.Connection, *, now: datetime | None = None
) -> tuple[str, bytes]:
    filename = f"curation_backup_{timestamp_slug(now)}.sqlite"
    return filename, sqlite_backup_bytes(conn)
