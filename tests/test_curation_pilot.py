from __future__ import annotations

import importlib.util
import sqlite3
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from curation_pilot import db, exports, metrics, packet, quality, registry_import, validation


def make_conn(tmp_path: Path, *, seed_demo: bool = True):
    db_path = tmp_path / "curation.sqlite"
    db.initialize_database(db_path, seed_demo=seed_demo)
    return db.connect(db_path)


def test_database_initializes_and_seeds_demo_rows(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    try:
        papers = db.table_df(conn, "papers")
        slots = db.table_df(conn, "claim_slots")
        annotations = db.table_df(conn, "annotations")
        adjudications = db.table_df(conn, "adjudications")

        assert len(papers) == 2
        assert len(slots) == 3
        assert len(annotations) == 5
        assert len(adjudications) == 1
        assert papers["demo"].eq(1).all()
        assert papers["exclude_from_metrics"].eq(1).all()
        assert papers["exclude_from_export_by_default"].eq(1).all()
    finally:
        conn.close()


def test_demo_rows_are_excluded_from_metrics_and_exports_by_default(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    try:
        default_records = exports.claim_records_df(conn)
        default_metrics = metrics.metrics_df(conn)
        demo_records = exports.claim_records_df(conn, include_demo=True)
        demo_metrics = metrics.metrics_df(conn, include_demo=True)

        assert default_records.empty
        assert default_metrics.loc[
            default_metrics["metric"] == "papers_screened", "value"
        ].iloc[0] == 0
        assert len(demo_records) == 4
        assert demo_metrics.loc[
            demo_metrics["metric"] == "paired_claim_slots", "value"
        ].iloc[0] == 2
        assert exports.export_summary(conn) == {
            "exported_records": 0,
            "adjudicated_records": 0,
            "raw_annotation_records": 0,
            "demo_records_in_export": 0,
            "demo_records_excluded": 4,
        }
    finally:
        conn.close()


def test_next_claim_id_is_deterministic_per_paper(tmp_path: Path) -> None:
    conn = make_conn(tmp_path, seed_demo=False)
    try:
        db.upsert_paper(
            conn,
            {
                "paper_id": "P900",
                "title": "Test paper",
                "paper_type": "primary study",
                "full_text_available": "yes",
                "status": "in progress",
            },
        )

        assert db.next_claim_id(conn, "P900") == "P900-C001"

        db.upsert_claim_slot(
            conn,
            {
                "claim_id": "P900-C001",
                "paper_id": "P900",
                "slot_note": "First test slot",
                "slot_status": "open",
            },
        )

        assert db.next_claim_id(conn, "P900") == "P900-C002"
    finally:
        conn.close()


def test_annotation_adjudication_and_export_shape(tmp_path: Path) -> None:
    conn = make_conn(tmp_path, seed_demo=False)
    try:
        db.upsert_paper(
            conn,
            {
                "paper_id": "P001",
                "pmid": "123",
                "title": "Pilot paper",
                "metal_cluster": "aluminum",
                "paper_type": "primary study",
                "full_text_available": "yes",
                "curator": "JG",
                "status": "adjudicated",
            },
        )
        db.upsert_claim_slot(
            conn,
            {
                "claim_id": "P001-C001",
                "paper_id": "P001",
                "slot_note": "Shared slot",
                "slot_status": "open",
            },
        )

        base_annotation = {
            "claim_id": "P001-C001",
            "metal": "Al",
            "material_form": "hydroxide",
            "speciation_or_oxidation_state": "Al(III)",
            "dose": "100 ug/mL",
            "duration": "24 h",
            "species": "mouse",
            "cell_or_tissue": "macrophage",
            "in_vitro_or_in_vivo": "in vitro",
            "route_or_context": "cell culture",
            "stimulation_context": "LPS-primed",
            "comparator": "LPS only",
            "endpoint_family": "inflammasome activation",
            "specific_endpoint": "IL-1 beta secretion",
            "assay": "ELISA",
            "direction": "increased",
            "magnitude": "not reported",
            "evidence_location": "Fig. 2A",
            "exact_evidence_excerpt": "Pilot note",
            "missing_core_fields": "",
            "confidence": "high",
            "curator_notes": "Looks complete.",
        }
        db.upsert_annotation(conn, {**base_annotation, "curator": "JG"})
        db.upsert_annotation(
            conn,
            {
                **base_annotation,
                "curator": "AB",
                "direction": "mixed",
                "confidence": "medium",
            },
        )
        db.save_adjudication(
            conn,
            {
                "claim_id": "P001-C001",
                "adjudicator": "PI",
                **{f"final_{key}": value for key, value in base_annotation.items() if key != "claim_id"},
                "adjudication_notes": "Resolved to increased.",
            },
        )

        records = exports.claim_records_df(conn)
        metric_frame = metrics.metrics_df(conn)

        assert len(records) == 1
        assert records.iloc[0]["record_type"] == "adjudicated"
        assert records.iloc[0]["direction"] == "increased"
        assert "curated_claim_records.csv" not in records.columns
        assert metric_frame.loc[
            metric_frame["metric"] == "agreement_direction", "value"
        ].iloc[0] == 0.0
    finally:
        conn.close()


def test_validation_and_completeness_helpers_flag_missing_core_fields() -> None:
    record = {
        "curator": "JG",
        "valid_claim": "yes",
        "endpoint_family": "inflammasome activation",
        "direction": "increased",
        "confidence": "medium",
        "evidence_location": "Fig. 2A",
        "dose": "",
        "comparator": "LPS only",
        "material_form": "hydroxide",
        "speciation_or_oxidation_state": "",
        "assay": "",
        "specific_endpoint": "",
        "missing_core_fields": "dose missing; speciation missing",
    }

    errors, warnings = validation.validate_claim_record(record)
    complete = validation.completeness_df(record)

    assert errors == []
    assert "assay is blank but `assay unclear` is not selected." in warnings
    assert complete.loc[complete["field"] == "Dose", "status"].iloc[0] == (
        "explicitly missing"
    )
    assert complete.loc[complete["field"] == "Assay", "status"].iloc[0] == (
        "needs review"
    )


def test_schema_upgrade_adds_slice_three_columns_to_existing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "old.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE papers (
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
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    db.initialize_database(db_path, seed_demo=False)
    upgraded = db.connect(db_path)
    try:
        assert "pmcid" in db.existing_columns(upgraded, "papers")
        assert "anchor_location" in db.existing_columns(upgraded, "claim_slots")
        assert "valid_claim" in db.existing_columns(upgraded, "annotations")
        assert "final_valid_claim" in db.existing_columns(upgraded, "adjudications")
    finally:
        upgraded.close()


def test_paper_registry_import_accepts_minimal_and_extended_fields(tmp_path: Path) -> None:
    conn = make_conn(tmp_path, seed_demo=False)
    try:
        csv_text = """paper_id,pmid,title,cluster,first_author,year,journal,metal,material_form,biological_model,endpoint_families,key_endpoints,assays,curation_tier,include_in_v1,notes
P001,12345,Minimal-plus paper,aluminum,Smith,2024,J Immunol,Al,hydroxide,macrophage,inflammasome,IL-1 beta,ELISA,MVP,yes,note
"""
        preview = registry_import.validate_paper_registry_csv(conn, csv_text)
        result = registry_import.import_paper_registry_csv(conn, csv_text)
        papers = db.table_df(conn, "papers")

        assert not preview.has_errors
        assert result.imported_count == 1
        assert papers.loc[papers["paper_id"] == "P001", "metal_cluster"].iloc[0] == "aluminum"
        assert papers.loc[papers["paper_id"] == "P001", "first_author"].iloc[0] == "Smith"
    finally:
        conn.close()


def test_paper_registry_import_blocks_missing_pmid_without_partial_write(tmp_path: Path) -> None:
    conn = make_conn(tmp_path, seed_demo=False)
    try:
        csv_text = """paper_id,pmid,title
P001,12345,Good paper
P002,,Bad paper
"""
        result = registry_import.import_paper_registry_csv(conn, csv_text)
        papers = db.table_df(conn, "papers")

        assert result.has_errors
        assert papers.empty
        assert "PMID is required" in result.issues["message"].str.cat(sep=" ")
    finally:
        conn.close()


def test_paper_registry_import_warns_on_duplicate_pmids(tmp_path: Path) -> None:
    conn = make_conn(tmp_path, seed_demo=False)
    try:
        csv_text = """paper_id,pmid,title
P001,12345,Paper one
P002,12345,Paper two
"""
        preview = registry_import.validate_paper_registry_csv(conn, csv_text)

        assert not preview.has_errors
        assert "duplicate" in preview.issues["message"].str.cat(sep=" ").lower()
    finally:
        conn.close()


def test_reset_demo_data_preserves_manual_rows(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    try:
        db.upsert_paper(
            conn,
            {
                "paper_id": "P777",
                "title": "Manual paper",
                "metal_cluster": "zinc",
                "paper_type": "primary study",
                "full_text_available": "yes",
                "status": "curated",
            },
        )
        db.reset_demo_data(conn)
        papers = db.table_df(conn, "papers")

        assert "P777" in papers["paper_id"].tolist()
        assert len(papers[papers["source_type"] == "demo_fixture"]) == 2
    finally:
        conn.close()


def test_claim_comparison_marks_disagreements(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    try:
        annotations = db.table_df(conn, "annotations")
        slot_annotations = annotations[annotations["claim_id"] == "D001-C002"]
        comparison = metrics.claim_comparison_df(slot_annotations)

        endpoint_row = comparison[comparison["field"] == "endpoint_family"].iloc[0]
        dose_row = comparison[comparison["field"] == "dose_present"].iloc[0]

        assert bool(endpoint_row["disagreement"]) is True
        assert bool(dose_row["disagreement"]) is False
    finally:
        conn.close()


def test_annotation_locking_controls_agreement_and_kappa(tmp_path: Path) -> None:
    conn = make_conn(tmp_path, seed_demo=False)
    try:
        db.upsert_paper(
            conn,
            {
                "paper_id": "P010",
                "pmid": "10",
                "title": "Agreement paper",
                "metal_cluster": "nickel",
                "paper_type": "primary study",
                "full_text_available": "yes",
                "status": "in progress",
            },
        )
        for claim_id, direction in [("P010-C001", "increased"), ("P010-C002", "decreased")]:
            db.upsert_claim_slot(
                conn,
                {
                    "claim_id": claim_id,
                    "paper_id": "P010",
                    "anchor_type": "figure",
                    "anchor_location": "Fig. 1",
                    "slot_status": "open",
                },
            )
            for curator in ["A", "B"]:
                db.upsert_annotation(
                    conn,
                    {
                        "claim_id": claim_id,
                        "curator": curator,
                        "valid_claim": "yes",
                        "endpoint_family": "cytotoxicity",
                        "direction": direction,
                        "material_form": "oxide",
                        "dose": "10 ug/mL",
                        "confidence": "high",
                        "evidence_location": "Fig. 1",
                    },
                )

        annotations = db.table_df(conn, "annotations")
        assert metrics.agreement_summary(annotations)["paired_claim_slots"] == 0

        for claim_id in ["P010-C001", "P010-C002"]:
            for curator in ["A", "B"]:
                db.set_annotation_lock(conn, claim_id, curator, locked=True)

        locked = db.table_df(conn, "annotations")
        summary = metrics.agreement_summary(locked)
        report = metrics.agreement_report_df(locked)

        assert summary["paired_claim_slots"] == 2
        assert summary["agreement_direction"] == 100.0
        assert report.loc[report["field"] == "direction", "cohens_kappa"].iloc[0] == 1.0
    finally:
        conn.close()


def test_quality_report_flags_unanchored_unlocked_and_valid_claim_issues(tmp_path: Path) -> None:
    conn = make_conn(tmp_path, seed_demo=False)
    try:
        db.upsert_paper(
            conn,
            {
                "paper_id": "P020",
                "pmid": "20",
                "title": "QA paper",
                "metal_cluster": "CoCr",
                "paper_type": "primary study",
                "full_text_available": "yes",
                "status": "in progress",
            },
        )
        db.upsert_claim_slot(
            conn,
            {
                "claim_id": "P020-C001",
                "paper_id": "P020",
                "slot_status": "open",
            },
        )
        for curator, valid_claim in [("A", "yes"), ("B", "unsure")]:
            db.upsert_annotation(
                conn,
                {
                    "claim_id": "P020-C001",
                    "curator": curator,
                    "valid_claim": valid_claim,
                    "endpoint_family": "cytotoxicity",
                    "direction": "unclear",
                    "confidence": "low",
                    "evidence_location": "",
                },
            )
            db.set_annotation_lock(conn, "P020-C001", curator, locked=True)

        qa = quality.data_quality_report_df(conn)
        issue_types = set(qa["issue_type"])

        assert "missing_anchor_type" in issue_types
        assert "missing_anchor_location" in issue_types
        assert "paired_locked_unadjudicated" in issue_types
        assert "blank_evidence_location" in issue_types
        assert "valid_claim_unsure" in issue_types
        assert "valid_claim_disagreement" in issue_types
    finally:
        conn.close()


def test_grant_packet_zip_and_backup_outputs(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    try:
        filename, zip_bytes = packet.grant_packet_zip(
            conn,
            include_demo=True,
            now=datetime(2026, 5, 1, 12, 30),
        )
        backup_name, backup_bytes = packet.sqlite_backup_download(
            conn, now=datetime(2026, 5, 1, 12, 30)
        )

        assert filename == "metalloimmunome_pilot_packet_20260501_1230.zip"
        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            names = set(archive.namelist())
            assert {
                "curated_claim_records.csv",
                "paper_registry.csv",
                "claim_slots.csv",
                "pilot_metrics.csv",
                "agreement_report.csv",
                "data_quality_report.csv",
                "data_dictionary.csv",
                "example_claims.csv",
                "proposal_summary.md",
                "README_grant_packet.md",
            }.issubset(names)
            example_claims = archive.read("example_claims.csv").decode("utf-8")
            summary = archive.read("proposal_summary.md").decode("utf-8")
            assert "adjudicated" in example_claims
            assert "Papers screened:" in summary

        assert backup_name == "curation_backup_20260501_1230.sqlite"
        assert backup_bytes.startswith(b"SQLite format 3")
    finally:
        conn.close()


def test_data_dictionary_lists_valid_claim_and_kappa_fields() -> None:
    dictionary = quality.data_dictionary_df()
    fields = set(dictionary["field"])

    assert "valid_claim" in fields
    assert "kappa_fields" in fields


def test_app_imports_without_running_streamlit_main() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("curation_pilot_app", app_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert hasattr(module, "main")
