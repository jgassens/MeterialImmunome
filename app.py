from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from curation_pilot import db, exports, metrics  # noqa: E402
from curation_pilot.vocab import (  # noqa: E402
    CLAIM_FIELDS,
    CONFIDENCE_LEVELS,
    CONTEXTS,
    DIRECTIONS,
    ENDPOINT_FAMILIES,
    FULL_TEXT_OPTIONS,
    MATERIAL_FORMS,
    METAL_CLUSTERS,
    MISSINGNESS_OPTIONS,
    PAPER_STATUSES,
    PAPER_TYPES,
    SLOT_STATUSES,
    join_multi,
    split_multi,
)


@st.cache_resource
def get_connection() -> Any:
    db.initialize_database()
    return db.connect()


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def options_with_current(options: list[str], current: str = "", *, blank: bool = True) -> list[str]:
    values = [""] if blank else []
    values.extend(options)
    if current and current not in values:
        values.insert(0 if not blank else 1, current)
    return values


def select_control(
    label: str,
    options: list[str],
    current: str = "",
    *,
    key: str,
    blank: bool = True,
) -> str:
    choices = options_with_current(options, current, blank=blank)
    index = choices.index(current) if current in choices else 0
    return st.selectbox(label, choices, index=index, key=key)


def bool_from_row(row: dict[str, Any], key: str) -> bool:
    return bool(int(row.get(key, 0) or 0))


def dataframe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.fillna("").to_dict("records")


def get_row(frame: pd.DataFrame, key: str, value: str) -> dict[str, Any]:
    if frame.empty or not value:
        return {}
    matched = frame[frame[key] == value]
    if matched.empty:
        return {}
    return matched.iloc[0].fillna("").to_dict()


def render_claim_fields(prefix: str, defaults: dict[str, Any], key_prefix: str) -> dict[str, Any]:
    st.subheader(prefix)
    values: dict[str, Any] = {}

    row1 = st.columns(3)
    with row1[0]:
        values["metal"] = st.text_input(
            "Metal", value=clean(defaults.get("metal", "")), key=f"{key_prefix}_metal"
        )
    with row1[1]:
        values["material_form"] = select_control(
            "Material form",
            MATERIAL_FORMS,
            clean(defaults.get("material_form", "")),
            key=f"{key_prefix}_material_form",
        )
    with row1[2]:
        values["speciation_or_oxidation_state"] = st.text_input(
            "Speciation or oxidation state",
            value=clean(defaults.get("speciation_or_oxidation_state", "")),
            key=f"{key_prefix}_speciation",
        )

    row2 = st.columns(3)
    with row2[0]:
        values["dose"] = st.text_input(
            "Dose", value=clean(defaults.get("dose", "")), key=f"{key_prefix}_dose"
        )
    with row2[1]:
        values["duration"] = st.text_input(
            "Duration",
            value=clean(defaults.get("duration", "")),
            key=f"{key_prefix}_duration",
        )
    with row2[2]:
        values["species"] = st.text_input(
            "Species", value=clean(defaults.get("species", "")), key=f"{key_prefix}_species"
        )

    row3 = st.columns(3)
    with row3[0]:
        values["cell_or_tissue"] = st.text_input(
            "Cell or tissue",
            value=clean(defaults.get("cell_or_tissue", "")),
            key=f"{key_prefix}_cell",
        )
    with row3[1]:
        values["in_vitro_or_in_vivo"] = select_control(
            "Context",
            CONTEXTS,
            clean(defaults.get("in_vitro_or_in_vivo", "")),
            key=f"{key_prefix}_context",
        )
    with row3[2]:
        values["route_or_context"] = st.text_input(
            "Route or context",
            value=clean(defaults.get("route_or_context", "")),
            key=f"{key_prefix}_route",
        )

    row4 = st.columns(3)
    with row4[0]:
        values["stimulation_context"] = st.text_input(
            "Stimulation context",
            value=clean(defaults.get("stimulation_context", "")),
            key=f"{key_prefix}_stim",
        )
    with row4[1]:
        values["comparator"] = st.text_input(
            "Comparator",
            value=clean(defaults.get("comparator", "")),
            key=f"{key_prefix}_comparator",
        )
    with row4[2]:
        values["endpoint_family"] = select_control(
            "Endpoint family",
            ENDPOINT_FAMILIES,
            clean(defaults.get("endpoint_family", "")),
            key=f"{key_prefix}_endpoint_family",
        )

    row5 = st.columns(3)
    with row5[0]:
        values["specific_endpoint"] = st.text_input(
            "Specific endpoint",
            value=clean(defaults.get("specific_endpoint", "")),
            key=f"{key_prefix}_specific_endpoint",
        )
    with row5[1]:
        values["assay"] = st.text_input(
            "Assay", value=clean(defaults.get("assay", "")), key=f"{key_prefix}_assay"
        )
    with row5[2]:
        values["direction"] = select_control(
            "Direction",
            DIRECTIONS,
            clean(defaults.get("direction", "")),
            key=f"{key_prefix}_direction",
        )

    row6 = st.columns(3)
    with row6[0]:
        values["magnitude"] = st.text_input(
            "Magnitude",
            value=clean(defaults.get("magnitude", "")),
            key=f"{key_prefix}_magnitude",
        )
    with row6[1]:
        values["evidence_location"] = st.text_input(
            "Evidence location",
            value=clean(defaults.get("evidence_location", "")),
            key=f"{key_prefix}_evidence_location",
        )
    with row6[2]:
        values["confidence"] = select_control(
            "Confidence",
            CONFIDENCE_LEVELS,
            clean(defaults.get("confidence", "")),
            key=f"{key_prefix}_confidence",
        )

    default_missingness = split_multi(clean(defaults.get("missing_core_fields", "")))
    values["missing_core_fields"] = join_multi(
        st.multiselect(
            "Missing core fields",
            MISSINGNESS_OPTIONS,
            default=[item for item in default_missingness if item in MISSINGNESS_OPTIONS],
            key=f"{key_prefix}_missing",
        )
    )
    values["exact_evidence_excerpt"] = st.text_area(
        "Exact evidence excerpt",
        value=clean(defaults.get("exact_evidence_excerpt", "")),
        key=f"{key_prefix}_excerpt",
        height=90,
    )
    values["curator_notes"] = st.text_area(
        "Curator notes",
        value=clean(defaults.get("curator_notes", "")),
        key=f"{key_prefix}_notes",
        height=80,
    )

    return values


def paper_tab(conn: Any) -> None:
    st.header("Papers")
    papers = db.table_df(conn, "papers")
    paper_ids = ["New paper"] + papers["paper_id"].tolist() if not papers.empty else ["New paper"]
    selected = st.selectbox("Paper", paper_ids, key="paper_select")
    defaults = {} if selected == "New paper" else get_row(papers, "paper_id", selected)

    with st.form("paper_form"):
        cols = st.columns(3)
        with cols[0]:
            paper_id = st.text_input("paper_id", value=clean(defaults.get("paper_id", "")))
        with cols[1]:
            pmid = st.text_input("PMID", value=clean(defaults.get("pmid", "")))
        with cols[2]:
            doi = st.text_input("DOI", value=clean(defaults.get("doi", "")))

        title = st.text_input("Title", value=clean(defaults.get("title", "")))

        cols = st.columns(5)
        with cols[0]:
            metal_cluster = select_control(
                "Metal cluster",
                METAL_CLUSTERS,
                clean(defaults.get("metal_cluster", "")),
                key="paper_metal_cluster",
            )
        with cols[1]:
            paper_type = select_control(
                "Paper type",
                PAPER_TYPES,
                clean(defaults.get("paper_type", "primary study")),
                key="paper_type",
                blank=False,
            )
        with cols[2]:
            full_text_available = select_control(
                "Full text available",
                FULL_TEXT_OPTIONS,
                clean(defaults.get("full_text_available", "yes")),
                key="paper_full_text",
                blank=False,
            )
        with cols[3]:
            curator = st.text_input("Curator", value=clean(defaults.get("curator", "")))
        with cols[4]:
            status = select_control(
                "Status",
                PAPER_STATUSES,
                clean(defaults.get("status", "not started")),
                key="paper_status",
                blank=False,
            )

        submitted = st.form_submit_button("Save paper")
        if submitted:
            if not paper_id.strip():
                st.error("paper_id is required.")
            else:
                db.upsert_paper(
                    conn,
                    {
                        "paper_id": paper_id.strip(),
                        "pmid": pmid,
                        "doi": doi,
                        "title": title,
                        "metal_cluster": metal_cluster,
                        "paper_type": paper_type,
                        "full_text_available": full_text_available,
                        "curator": curator,
                        "status": status,
                        "demo": bool_from_row(defaults, "demo"),
                        "source_type": defaults.get("source_type", "manual_curation")
                        or "manual_curation",
                        "exclude_from_metrics": bool_from_row(defaults, "exclude_from_metrics"),
                        "exclude_from_export_by_default": bool_from_row(
                            defaults, "exclude_from_export_by_default"
                        ),
                    },
                )
                st.success("Paper saved.")
                st.rerun()

    st.dataframe(papers, use_container_width=True, hide_index=True)


def claim_slots_tab(conn: Any) -> None:
    st.header("Claim Slots")
    papers = db.table_df(conn, "papers")
    slots = db.table_df(conn, "claim_slots")

    if papers.empty:
        st.warning("Add a paper before creating claim slots.")
        return

    paper_id = st.selectbox("Paper", papers["paper_id"].tolist(), key="slot_paper")
    slot_ids = ["New claim slot"] + slots[slots["paper_id"] == paper_id]["claim_id"].tolist()
    selected_slot = st.selectbox("Claim slot", slot_ids, key="slot_select")
    defaults = {} if selected_slot == "New claim slot" else get_row(slots, "claim_id", selected_slot)
    default_claim_id = defaults.get("claim_id") or db.next_claim_id(conn, paper_id)

    with st.form("slot_form"):
        claim_id = st.text_input("claim_id", value=clean(default_claim_id))
        slot_note = st.text_area("Slot note", value=clean(defaults.get("slot_note", "")), height=100)
        slot_status = select_control(
            "Slot status",
            SLOT_STATUSES,
            clean(defaults.get("slot_status", "open")),
            key="slot_status",
            blank=False,
        )
        submitted = st.form_submit_button("Save claim slot")
        if submitted:
            if not claim_id.strip():
                st.error("claim_id is required.")
            else:
                paper_row = get_row(papers, "paper_id", paper_id)
                db.upsert_claim_slot(
                    conn,
                    {
                        "claim_id": claim_id.strip(),
                        "paper_id": paper_id,
                        "slot_note": slot_note,
                        "slot_status": slot_status,
                        "demo": bool_from_row(defaults, "demo"),
                        "source_type": defaults.get("source_type", "manual_curation")
                        or "manual_curation",
                        "exclude_from_metrics": bool_from_row(defaults, "exclude_from_metrics")
                        or bool_from_row(paper_row, "exclude_from_metrics"),
                        "exclude_from_export_by_default": bool_from_row(
                            defaults, "exclude_from_export_by_default"
                        )
                        or bool_from_row(paper_row, "exclude_from_export_by_default"),
                    },
                )
                st.success("Claim slot saved.")
                st.rerun()

    st.dataframe(slots, use_container_width=True, hide_index=True)


def annotate_tab(conn: Any) -> None:
    st.header("Annotate")
    slots = db.table_df(conn, "claim_slots")
    annotations = db.table_df(conn, "annotations")

    if slots.empty:
        st.warning("Create a claim slot before annotating.")
        return

    claim_id = st.selectbox("Claim slot", slots["claim_id"].tolist(), key="annotate_slot")
    slot_row = get_row(slots, "claim_id", claim_id)
    existing_for_slot = annotations[annotations["claim_id"] == claim_id]
    annotation_choices = ["New annotation"] + existing_for_slot["curator"].tolist()
    selected_annotation = st.selectbox("Annotation", annotation_choices, key="annotation_select")
    defaults = (
        {}
        if selected_annotation == "New annotation"
        else get_row(existing_for_slot, "curator", selected_annotation)
    )

    with st.form("annotation_form"):
        curator = st.text_input("Curator", value=clean(defaults.get("curator", "")))
        claim_values = render_claim_fields("Claim record", defaults, "annotation")
        submitted = st.form_submit_button("Save annotation")
        if submitted:
            if not curator.strip():
                st.error("Curator is required.")
            else:
                db.upsert_annotation(
                    conn,
                    {
                        "claim_id": claim_id,
                        "curator": curator.strip(),
                        **claim_values,
                        "demo": bool_from_row(slot_row, "demo"),
                        "source_type": slot_row.get("source_type", "manual_curation")
                        or "manual_curation",
                        "exclude_from_metrics": bool_from_row(
                            slot_row, "exclude_from_metrics"
                        ),
                        "exclude_from_export_by_default": bool_from_row(
                            slot_row, "exclude_from_export_by_default"
                        ),
                    },
                )
                st.success("Annotation saved.")
                st.rerun()

    st.dataframe(existing_for_slot, use_container_width=True, hide_index=True)


def adjudicate_tab(conn: Any) -> None:
    st.header("Adjudicate")
    slots = db.table_df(conn, "claim_slots")
    annotations = db.table_df(conn, "annotations")
    adjudications = db.table_df(conn, "adjudications")

    if slots.empty:
        st.warning("Create a claim slot before adjudicating.")
        return

    include_demo = st.checkbox("Include demo fixtures", value=True, key="adjudicate_demo")
    disagreements = metrics.disagreements_df(conn, include_demo=include_demo)
    st.dataframe(disagreements, use_container_width=True, hide_index=True)

    claim_id = st.selectbox("Claim slot", slots["claim_id"].tolist(), key="adjudicate_slot")
    slot_row = get_row(slots, "claim_id", claim_id)
    slot_annotations = annotations[annotations["claim_id"] == claim_id]
    st.dataframe(slot_annotations, use_container_width=True, hide_index=True)

    existing = get_row(adjudications, "claim_id", claim_id)
    if existing:
        defaults = {
            field: existing.get(f"final_{field}", "")
            for field in CLAIM_FIELDS
        }
    elif not slot_annotations.empty:
        defaults = slot_annotations.iloc[0].fillna("").to_dict()
    else:
        defaults = {}

    with st.form("adjudication_form"):
        adjudicator = st.text_input(
            "Adjudicator", value=clean(existing.get("adjudicator", ""))
        )
        final_values = render_claim_fields("Final record", defaults, "adjudication")
        adjudication_notes = st.text_area(
            "Adjudication notes",
            value=clean(existing.get("adjudication_notes", "")),
            height=90,
        )
        submitted = st.form_submit_button("Save adjudication")
        if submitted:
            if not adjudicator.strip():
                st.error("Adjudicator is required.")
            else:
                payload = {
                    "claim_id": claim_id,
                    "adjudicator": adjudicator.strip(),
                    "adjudication_notes": adjudication_notes,
                    "demo": bool_from_row(slot_row, "demo"),
                    "source_type": slot_row.get("source_type", "manual_curation")
                    or "manual_curation",
                    "exclude_from_metrics": bool_from_row(slot_row, "exclude_from_metrics"),
                    "exclude_from_export_by_default": bool_from_row(
                        slot_row, "exclude_from_export_by_default"
                    ),
                }
                payload.update({f"final_{field}": value for field, value in final_values.items()})
                db.save_adjudication(conn, payload)
                st.success("Adjudication saved.")
                st.rerun()


def metrics_export_tab(conn: Any) -> None:
    st.header("Metrics + Export")
    include_demo = st.checkbox("Include demo fixtures", value=False, key="export_demo")
    metric_frame = metrics.metrics_df(conn, include_demo=include_demo)
    records = exports.claim_records_df(conn, include_demo=include_demo)

    metric_lookup = dict(zip(metric_frame["metric"], metric_frame["value"], strict=False))
    cols = st.columns(4)
    cols[0].metric("Papers screened", metric_lookup.get("papers_screened", 0))
    cols[1].metric("Papers curated", metric_lookup.get("papers_curated", 0))
    cols[2].metric("Claim records", metric_lookup.get("claim_records", 0))
    cols[3].metric("Endpoint agreement", f"{metric_lookup.get('agreement_endpoint_family', 0)}%")

    st.subheader("Pilot metrics")
    st.dataframe(metric_frame, use_container_width=True, hide_index=True)
    st.download_button(
        "Download pilot_metrics.csv",
        data=exports.csv_bytes(metric_frame),
        file_name="pilot_metrics.csv",
        mime="text/csv",
    )

    st.subheader("Curated claim records")
    st.dataframe(records, use_container_width=True, hide_index=True)
    st.download_button(
        "Download curated_claim_records.csv",
        data=exports.csv_bytes(records),
        file_name="curated_claim_records.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(
        page_title="Metalloimmunome Claim Curation Pilot",
        layout="wide",
    )
    st.title("Metalloimmunome Claim Curation Pilot")
    conn = get_connection()

    tabs = st.tabs(["Papers", "Claim Slots", "Annotate", "Adjudicate", "Metrics + Export"])
    with tabs[0]:
        paper_tab(conn)
    with tabs[1]:
        claim_slots_tab(conn)
    with tabs[2]:
        annotate_tab(conn)
    with tabs[3]:
        adjudicate_tab(conn)
    with tabs[4]:
        metrics_export_tab(conn)


if __name__ == "__main__":
    main()

