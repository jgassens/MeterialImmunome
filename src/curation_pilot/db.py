"""SQLite persistence for the curation pilot."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from .vocab import CLAIM_FIELDS, join_multi

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "curation.sqlite"

PAPER_COLUMNS = [
    "paper_id",
    "pmid",
    "doi",
    "title",
    "metal_cluster",
    "paper_type",
    "full_text_available",
    "curator",
    "status",
    "demo",
    "source_type",
    "exclude_from_metrics",
    "exclude_from_export_by_default",
]

CLAIM_SLOT_COLUMNS = [
    "claim_id",
    "paper_id",
    "slot_note",
    "slot_status",
    "demo",
    "source_type",
    "exclude_from_metrics",
    "exclude_from_export_by_default",
]

ANNOTATION_COLUMNS = [
    "claim_id",
    "curator",
    *CLAIM_FIELDS,
    "demo",
    "source_type",
    "exclude_from_metrics",
    "exclude_from_export_by_default",
]

ADJUDICATION_COLUMNS = [
    "claim_id",
    "adjudicator",
    *(f"final_{field}" for field in CLAIM_FIELDS),
    "adjudication_notes",
    "demo",
    "source_type",
    "exclude_from_metrics",
    "exclude_from_export_by_default",
]


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection and ensure the data directory exists."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(
    db_path: str | Path = DEFAULT_DB_PATH, *, seed_demo: bool = True
) -> None:
    """Create schema and optionally seed demo fixtures."""
    conn = connect(db_path)
    try:
        create_schema(conn)
        if seed_demo:
            seed_demo_data(conn)
        conn.commit()
    finally:
        conn.close()


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS papers (
            paper_id TEXT PRIMARY KEY,
            pmid TEXT NOT NULL DEFAULT '',
            doi TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            metal_cluster TEXT NOT NULL DEFAULT '',
            paper_type TEXT NOT NULL DEFAULT 'primary study',
            full_text_available TEXT NOT NULL DEFAULT 'yes',
            curator TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'not started',
            demo INTEGER NOT NULL DEFAULT 0,
            source_type TEXT NOT NULL DEFAULT 'manual_curation',
            exclude_from_metrics INTEGER NOT NULL DEFAULT 0,
            exclude_from_export_by_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS claim_slots (
            claim_id TEXT PRIMARY KEY,
            paper_id TEXT NOT NULL,
            slot_note TEXT NOT NULL DEFAULT '',
            slot_status TEXT NOT NULL DEFAULT 'open',
            demo INTEGER NOT NULL DEFAULT 0,
            source_type TEXT NOT NULL DEFAULT 'manual_curation',
            exclude_from_metrics INTEGER NOT NULL DEFAULT 0,
            exclude_from_export_by_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS annotations (
            annotation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            curator TEXT NOT NULL,
            metal TEXT NOT NULL DEFAULT '',
            material_form TEXT NOT NULL DEFAULT '',
            speciation_or_oxidation_state TEXT NOT NULL DEFAULT '',
            dose TEXT NOT NULL DEFAULT '',
            duration TEXT NOT NULL DEFAULT '',
            species TEXT NOT NULL DEFAULT '',
            cell_or_tissue TEXT NOT NULL DEFAULT '',
            in_vitro_or_in_vivo TEXT NOT NULL DEFAULT '',
            route_or_context TEXT NOT NULL DEFAULT '',
            stimulation_context TEXT NOT NULL DEFAULT '',
            comparator TEXT NOT NULL DEFAULT '',
            endpoint_family TEXT NOT NULL DEFAULT '',
            specific_endpoint TEXT NOT NULL DEFAULT '',
            assay TEXT NOT NULL DEFAULT '',
            direction TEXT NOT NULL DEFAULT '',
            magnitude TEXT NOT NULL DEFAULT '',
            evidence_location TEXT NOT NULL DEFAULT '',
            exact_evidence_excerpt TEXT NOT NULL DEFAULT '',
            missing_core_fields TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            curator_notes TEXT NOT NULL DEFAULT '',
            demo INTEGER NOT NULL DEFAULT 0,
            source_type TEXT NOT NULL DEFAULT 'manual_curation',
            exclude_from_metrics INTEGER NOT NULL DEFAULT 0,
            exclude_from_export_by_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claim_slots(claim_id) ON DELETE CASCADE,
            UNIQUE (claim_id, curator)
        );

        CREATE TABLE IF NOT EXISTS adjudications (
            claim_id TEXT PRIMARY KEY,
            adjudicator TEXT NOT NULL,
            final_metal TEXT NOT NULL DEFAULT '',
            final_material_form TEXT NOT NULL DEFAULT '',
            final_speciation_or_oxidation_state TEXT NOT NULL DEFAULT '',
            final_dose TEXT NOT NULL DEFAULT '',
            final_duration TEXT NOT NULL DEFAULT '',
            final_species TEXT NOT NULL DEFAULT '',
            final_cell_or_tissue TEXT NOT NULL DEFAULT '',
            final_in_vitro_or_in_vivo TEXT NOT NULL DEFAULT '',
            final_route_or_context TEXT NOT NULL DEFAULT '',
            final_stimulation_context TEXT NOT NULL DEFAULT '',
            final_comparator TEXT NOT NULL DEFAULT '',
            final_endpoint_family TEXT NOT NULL DEFAULT '',
            final_specific_endpoint TEXT NOT NULL DEFAULT '',
            final_assay TEXT NOT NULL DEFAULT '',
            final_direction TEXT NOT NULL DEFAULT '',
            final_magnitude TEXT NOT NULL DEFAULT '',
            final_evidence_location TEXT NOT NULL DEFAULT '',
            final_exact_evidence_excerpt TEXT NOT NULL DEFAULT '',
            final_missing_core_fields TEXT NOT NULL DEFAULT '',
            final_confidence TEXT NOT NULL DEFAULT '',
            final_curator_notes TEXT NOT NULL DEFAULT '',
            adjudication_notes TEXT NOT NULL DEFAULT '',
            demo INTEGER NOT NULL DEFAULT 0,
            source_type TEXT NOT NULL DEFAULT 'manual_curation',
            exclude_from_metrics INTEGER NOT NULL DEFAULT 0,
            exclude_from_export_by_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claim_slots(claim_id) ON DELETE CASCADE
        );
        """
    )


def query_df(
    conn: sqlite3.Connection, query: str, params: tuple[Any, ...] | list[Any] = ()
) -> pd.DataFrame:
    return pd.read_sql_query(query, conn, params=params)


def table_df(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    allowed = {"papers", "claim_slots", "annotations", "adjudications"}
    if table not in allowed:
        raise ValueError(f"Unsupported table: {table}")
    return query_df(conn, f"SELECT * FROM {table} ORDER BY created_at, rowid")


def _bool_int(value: Any) -> int:
    return 1 if bool(value) else 0


def _normalize_payload(columns: list[str], payload: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for column in columns:
        value = payload.get(column, "")
        if column in {"demo", "exclude_from_metrics", "exclude_from_export_by_default"}:
            value = _bool_int(value)
        if column == "missing_core_fields" or column == "final_missing_core_fields":
            value = join_multi(value)
        row[column] = value
    return row


def _upsert(
    conn: sqlite3.Connection,
    table: str,
    key_columns: list[str],
    columns: list[str],
    payload: Mapping[str, Any],
) -> None:
    row = _normalize_payload(columns, payload)
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    update_columns = [column for column in columns if column not in key_columns]
    update_sql = ", ".join(f"{column}=excluded.{column}" for column in update_columns)
    sql = f"""
        INSERT INTO {table} ({column_sql})
        VALUES ({placeholders})
        ON CONFLICT ({", ".join(key_columns)}) DO UPDATE SET
            {update_sql},
            updated_at=CURRENT_TIMESTAMP
    """
    conn.execute(sql, [row[column] for column in columns])
    conn.commit()


def upsert_paper(conn: sqlite3.Connection, payload: Mapping[str, Any]) -> None:
    _upsert(conn, "papers", ["paper_id"], PAPER_COLUMNS, payload)


def upsert_claim_slot(conn: sqlite3.Connection, payload: Mapping[str, Any]) -> None:
    _upsert(conn, "claim_slots", ["claim_id"], CLAIM_SLOT_COLUMNS, payload)


def upsert_annotation(conn: sqlite3.Connection, payload: Mapping[str, Any]) -> None:
    _upsert(conn, "annotations", ["claim_id", "curator"], ANNOTATION_COLUMNS, payload)


def save_adjudication(conn: sqlite3.Connection, payload: Mapping[str, Any]) -> None:
    _upsert(conn, "adjudications", ["claim_id"], ADJUDICATION_COLUMNS, payload)
    conn.execute(
        """
        UPDATE claim_slots
        SET slot_status = 'adjudicated', updated_at = CURRENT_TIMESTAMP
        WHERE claim_id = ?
        """,
        (payload["claim_id"],),
    )
    conn.commit()


def next_claim_id(conn: sqlite3.Connection, paper_id: str) -> str:
    """Return the next deterministic shared claim ID for a paper."""
    rows = conn.execute(
        "SELECT claim_id FROM claim_slots WHERE paper_id = ?", (paper_id,)
    ).fetchall()
    max_number = 0
    pattern = re.compile(rf"^{re.escape(paper_id)}-C(\d+)$")
    for row in rows:
        match = pattern.match(row["claim_id"])
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f"{paper_id}-C{max_number + 1:03d}"


def seed_demo_data(conn: sqlite3.Connection) -> None:
    """Seed tiny demo fixtures once for first-run screenshots and tests."""
    existing = conn.execute(
        "SELECT COUNT(*) AS count FROM papers WHERE source_type = 'demo_fixture'"
    ).fetchone()["count"]
    if existing:
        return

    demo_flags = {
        "demo": True,
        "source_type": "demo_fixture",
        "exclude_from_metrics": True,
        "exclude_from_export_by_default": True,
    }

    upsert_paper(
        conn,
        {
            "paper_id": "D001",
            "pmid": "demo-001",
            "doi": "",
            "title": "Demo fixture paper: aluminum adjuvant macrophage response",
            "metal_cluster": "aluminum",
            "paper_type": "primary study",
            "full_text_available": "yes",
            "curator": "JG",
            "status": "adjudicated",
            **demo_flags,
        },
    )
    upsert_paper(
        conn,
        {
            "paper_id": "D002",
            "pmid": "demo-002",
            "doi": "",
            "title": "Demo fixture paper: uncertain nickel cytotoxicity record",
            "metal_cluster": "nickel",
            "paper_type": "primary study",
            "full_text_available": "yes",
            "curator": "AB",
            "status": "in progress",
            **demo_flags,
        },
    )

    for slot in [
        {
            "claim_id": "D001-C001",
            "paper_id": "D001",
            "slot_note": "Complete high-confidence cytokine claim.",
            "slot_status": "open",
        },
        {
            "claim_id": "D001-C002",
            "paper_id": "D001",
            "slot_note": "Paired annotation with missing dose/speciation and disagreement.",
            "slot_status": "adjudicated",
        },
        {
            "claim_id": "D002-C001",
            "paper_id": "D002",
            "slot_note": "Uncertain slot used to exercise invalid/low-confidence handling.",
            "slot_status": "uncertain",
        },
    ]:
        upsert_claim_slot(conn, {**slot, **demo_flags})

    base_complete = {
        "claim_id": "D001-C001",
        "metal": "Al",
        "material_form": "hydroxide",
        "speciation_or_oxidation_state": "Al(III)",
        "dose": "100 ug/mL",
        "duration": "24 h",
        "species": "mouse",
        "cell_or_tissue": "bone-marrow-derived macrophage",
        "in_vitro_or_in_vivo": "in vitro",
        "route_or_context": "cell-culture exposure",
        "stimulation_context": "LPS-primed",
        "comparator": "LPS only",
        "endpoint_family": "cytokine induction/skewing",
        "specific_endpoint": "IL-1 beta secretion",
        "assay": "ELISA",
        "direction": "increased",
        "magnitude": "demo fold-change",
        "evidence_location": "Fig. demo 1A",
        "exact_evidence_excerpt": "Demo fixture excerpt; not evidence.",
        "missing_core_fields": "",
        "confidence": "high",
        "curator_notes": "Complete demo annotation.",
        **demo_flags,
    }
    upsert_annotation(conn, {**base_complete, "curator": "JG"})
    upsert_annotation(conn, {**base_complete, "curator": "AB"})

    disagreement_a = {
        "claim_id": "D001-C002",
        "curator": "JG",
        "metal": "Al",
        "material_form": "hydroxide",
        "speciation_or_oxidation_state": "not reported",
        "dose": "",
        "duration": "24 h",
        "species": "mouse",
        "cell_or_tissue": "macrophage",
        "in_vitro_or_in_vivo": "in vitro",
        "route_or_context": "cell-culture exposure",
        "stimulation_context": "LPS-primed",
        "comparator": "vehicle",
        "endpoint_family": "inflammasome activation",
        "specific_endpoint": "IL-1 beta secretion",
        "assay": "ELISA",
        "direction": "increased",
        "magnitude": "not reported",
        "evidence_location": "Fig. demo 2A",
        "exact_evidence_excerpt": "Demo fixture excerpt; not evidence.",
        "missing_core_fields": ["dose missing", "speciation missing"],
        "confidence": "medium",
        "curator_notes": "Dose and speciation are missing.",
        **demo_flags,
    }
    disagreement_b = {
        **disagreement_a,
        "curator": "AB",
        "comparator": "LPS only",
        "endpoint_family": "cytokine induction/skewing",
        "direction": "mixed",
        "confidence": "low",
        "curator_notes": "Comparator is ambiguous in demo fixture.",
    }
    upsert_annotation(conn, disagreement_a)
    upsert_annotation(conn, disagreement_b)

    uncertain = {
        "claim_id": "D002-C001",
        "curator": "JG",
        "metal": "Ni",
        "material_form": "unknown",
        "speciation_or_oxidation_state": "not reported",
        "dose": "",
        "duration": "",
        "species": "",
        "cell_or_tissue": "cell line not reported",
        "in_vitro_or_in_vivo": "in vitro",
        "route_or_context": "unclear exposure context",
        "stimulation_context": "",
        "comparator": "",
        "endpoint_family": "cytotoxicity",
        "specific_endpoint": "viability",
        "assay": "",
        "direction": "unclear",
        "magnitude": "",
        "evidence_location": "text not located",
        "exact_evidence_excerpt": "Demo fixture uncertain slot; not evidence.",
        "missing_core_fields": [
            "dose missing",
            "comparator missing",
            "speciation missing",
            "assay unclear",
            "purity/endotoxin not reported",
        ],
        "confidence": "low",
        "curator_notes": "Uncertain demo slot.",
        **demo_flags,
    }
    upsert_annotation(conn, uncertain)

    save_adjudication(
        conn,
        {
            "claim_id": "D001-C002",
            "adjudicator": "PI",
            "final_metal": "Al",
            "final_material_form": "hydroxide",
            "final_speciation_or_oxidation_state": "not reported",
            "final_dose": "",
            "final_duration": "24 h",
            "final_species": "mouse",
            "final_cell_or_tissue": "macrophage",
            "final_in_vitro_or_in_vivo": "in vitro",
            "final_route_or_context": "cell-culture exposure",
            "final_stimulation_context": "LPS-primed",
            "final_comparator": "LPS only",
            "final_endpoint_family": "inflammasome activation",
            "final_specific_endpoint": "IL-1 beta secretion",
            "final_assay": "ELISA",
            "final_direction": "increased",
            "final_magnitude": "not reported",
            "final_evidence_location": "Fig. demo 2A",
            "final_exact_evidence_excerpt": "Demo fixture excerpt; not evidence.",
            "final_missing_core_fields": ["dose missing", "speciation missing"],
            "final_confidence": "medium",
            "final_curator_notes": "Adjudicated demo fixture.",
            "adjudication_notes": "Final value selected from paired demo annotations.",
            **demo_flags,
        },
    )

