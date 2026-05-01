from __future__ import annotations

import importlib.util
from pathlib import Path

from curation_pilot import db, exports, metrics


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


def test_app_imports_without_running_streamlit_main() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("curation_pilot_app", app_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert hasattr(module, "main")
