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

from curation_pilot import (  # noqa: E402
    db,
    exports,
    metrics,
    packet,
    quality,
    registry_import,
    validation,
)
from curation_pilot.vocab import (  # noqa: E402
    ANCHOR_TYPES,
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
    VALID_CLAIM_OPTIONS,
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
    disabled: bool = False,
) -> str:
    choices = options_with_current(options, current, blank=blank)
    index = choices.index(current) if current in choices else 0
    return st.selectbox(label, choices, index=index, key=key, disabled=disabled)


def bool_from_row(row: dict[str, Any], key: str) -> bool:
    return bool(int(row.get(key, 0) or 0))


def dataframe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.fillna("").to_dict("records")


def flash(level: str, message: str) -> None:
    st.session_state.setdefault("flash_messages", []).append((level, message))


def render_flash() -> None:
    messages = st.session_state.pop("flash_messages", [])
    for level, message in messages:
        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        elif level == "error":
            st.error(message)
        else:
            st.info(message)


def render_validation_feedback(errors: list[str], warnings: list[str]) -> None:
    for error in errors:
        st.error(error)
    for warning in warnings:
        st.warning(warning)


def flash_validation_feedback(
    success_message: str, warnings: list[str] | None = None
) -> None:
    flash("success", success_message)
    for warning in warnings or []:
        flash("warning", warning)


def get_row(frame: pd.DataFrame, key: str, value: str) -> dict[str, Any]:
    if frame.empty or not value:
        return {}
    matched = frame[frame[key] == value]
    if matched.empty:
        return {}
    return matched.iloc[0].fillna("").to_dict()


def render_claim_fields(
    prefix: str,
    defaults: dict[str, Any],
    key_prefix: str,
    *,
    disabled: bool = False,
) -> dict[str, Any]:
    st.subheader(prefix)
    values: dict[str, Any] = {}

    values["valid_claim"] = select_control(
        "Valid claim",
        VALID_CLAIM_OPTIONS,
        clean(defaults.get("valid_claim", "")),
        key=f"{key_prefix}_valid_claim",
        disabled=disabled,
    )

    row1 = st.columns(3)
    with row1[0]:
        values["metal"] = st.text_input(
            "Metal",
            value=clean(defaults.get("metal", "")),
            key=f"{key_prefix}_metal",
            disabled=disabled,
        )
    with row1[1]:
        values["material_form"] = select_control(
            "Material form",
            MATERIAL_FORMS,
            clean(defaults.get("material_form", "")),
            key=f"{key_prefix}_material_form",
            disabled=disabled,
        )
    with row1[2]:
        values["speciation_or_oxidation_state"] = st.text_input(
            "Speciation or oxidation state",
            value=clean(defaults.get("speciation_or_oxidation_state", "")),
            key=f"{key_prefix}_speciation",
            disabled=disabled,
        )

    row2 = st.columns(3)
    with row2[0]:
        values["dose"] = st.text_input(
            "Dose",
            value=clean(defaults.get("dose", "")),
            key=f"{key_prefix}_dose",
            disabled=disabled,
        )
    with row2[1]:
        values["duration"] = st.text_input(
            "Duration",
            value=clean(defaults.get("duration", "")),
            key=f"{key_prefix}_duration",
            disabled=disabled,
        )
    with row2[2]:
        values["species"] = st.text_input(
            "Species",
            value=clean(defaults.get("species", "")),
            key=f"{key_prefix}_species",
            disabled=disabled,
        )

    row3 = st.columns(3)
    with row3[0]:
        values["cell_or_tissue"] = st.text_input(
            "Cell or tissue",
            value=clean(defaults.get("cell_or_tissue", "")),
            key=f"{key_prefix}_cell",
            disabled=disabled,
        )
    with row3[1]:
        values["in_vitro_or_in_vivo"] = select_control(
            "Context",
            CONTEXTS,
            clean(defaults.get("in_vitro_or_in_vivo", "")),
            key=f"{key_prefix}_context",
            disabled=disabled,
        )
    with row3[2]:
        values["route_or_context"] = st.text_input(
            "Route or context",
            value=clean(defaults.get("route_or_context", "")),
            key=f"{key_prefix}_route",
            disabled=disabled,
        )

    row4 = st.columns(3)
    with row4[0]:
        values["stimulation_context"] = st.text_input(
            "Stimulation context",
            value=clean(defaults.get("stimulation_context", "")),
            key=f"{key_prefix}_stim",
            disabled=disabled,
        )
    with row4[1]:
        values["comparator"] = st.text_input(
            "Comparator",
            value=clean(defaults.get("comparator", "")),
            key=f"{key_prefix}_comparator",
            disabled=disabled,
        )
    with row4[2]:
        values["endpoint_family"] = select_control(
            "Endpoint family",
            ENDPOINT_FAMILIES,
            clean(defaults.get("endpoint_family", "")),
            key=f"{key_prefix}_endpoint_family",
            disabled=disabled,
        )

    row5 = st.columns(3)
    with row5[0]:
        values["specific_endpoint"] = st.text_input(
            "Specific endpoint",
            value=clean(defaults.get("specific_endpoint", "")),
            key=f"{key_prefix}_specific_endpoint",
            disabled=disabled,
        )
    with row5[1]:
        values["assay"] = st.text_input(
            "Assay",
            value=clean(defaults.get("assay", "")),
            key=f"{key_prefix}_assay",
            disabled=disabled,
        )
    with row5[2]:
        values["direction"] = select_control(
            "Direction",
            DIRECTIONS,
            clean(defaults.get("direction", "")),
            key=f"{key_prefix}_direction",
            disabled=disabled,
        )

    row6 = st.columns(3)
    with row6[0]:
        values["magnitude"] = st.text_input(
            "Magnitude",
            value=clean(defaults.get("magnitude", "")),
            key=f"{key_prefix}_magnitude",
            disabled=disabled,
        )
    with row6[1]:
        values["evidence_location"] = st.text_input(
            "Evidence location",
            value=clean(defaults.get("evidence_location", "")),
            key=f"{key_prefix}_evidence_location",
            disabled=disabled,
        )
    with row6[2]:
        values["confidence"] = select_control(
            "Confidence",
            CONFIDENCE_LEVELS,
            clean(defaults.get("confidence", "")),
            key=f"{key_prefix}_confidence",
            disabled=disabled,
        )

    default_missingness = split_multi(clean(defaults.get("missing_core_fields", "")))
    values["missing_core_fields"] = join_multi(
        st.multiselect(
            "Missing core fields",
            MISSINGNESS_OPTIONS,
            default=[item for item in default_missingness if item in MISSINGNESS_OPTIONS],
            key=f"{key_prefix}_missing",
            disabled=disabled,
        )
    )
    values["exact_evidence_excerpt"] = st.text_area(
        "Exact evidence excerpt",
        value=clean(defaults.get("exact_evidence_excerpt", "")),
        key=f"{key_prefix}_excerpt",
        height=90,
        disabled=disabled,
    )
    values["curator_notes"] = st.text_area(
        "Curator notes",
        value=clean(defaults.get("curator_notes", "")),
        key=f"{key_prefix}_notes",
        height=80,
        disabled=disabled,
    )

    return values


def render_completeness_panel(record: dict[str, Any]) -> None:
    st.caption("Completeness check")
    st.dataframe(
        validation.completeness_df(record),
        use_container_width=True,
        hide_index=True,
    )


def styled_comparison(frame: pd.DataFrame) -> Any:
    if frame.empty:
        return frame

    def style_row(row: pd.Series) -> list[str]:
        color = "background-color: #fff3cd" if bool(row.get("disagreement")) else ""
        return [color] * len(row)

    return frame.style.apply(style_row, axis=1)


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
            pmcid = st.text_input("PMCID", value=clean(defaults.get("pmcid", "")))

        cols = st.columns(3)
        with cols[0]:
            doi = st.text_input("DOI", value=clean(defaults.get("doi", "")))
        with cols[1]:
            first_author = st.text_input(
                "First author", value=clean(defaults.get("first_author", ""))
            )
        with cols[2]:
            year = st.text_input("Year", value=clean(defaults.get("year", "")))

        title = st.text_input("Title", value=clean(defaults.get("title", "")))
        journal = st.text_input("Journal", value=clean(defaults.get("journal", "")))

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

        with st.expander("Extended registry metadata"):
            cols = st.columns(3)
            with cols[0]:
                cluster = st.text_input("Cluster", value=clean(defaults.get("cluster", "")))
            with cols[1]:
                metal = st.text_input("Metal", value=clean(defaults.get("metal", "")))
            with cols[2]:
                registry_material_form = st.text_input(
                    "Registry material form",
                    value=clean(defaults.get("material_form", "")),
                )
            biological_model = st.text_input(
                "Biological model", value=clean(defaults.get("biological_model", ""))
            )
            endpoint_families = st.text_input(
                "Endpoint families", value=clean(defaults.get("endpoint_families", ""))
            )
            key_endpoints = st.text_input(
                "Key endpoints", value=clean(defaults.get("key_endpoints", ""))
            )
            assays = st.text_input("Assays", value=clean(defaults.get("assays", "")))
            cols = st.columns(2)
            with cols[0]:
                curation_tier = st.text_input(
                    "Curation tier", value=clean(defaults.get("curation_tier", ""))
                )
            with cols[1]:
                include_in_v1 = st.text_input(
                    "Include in v1", value=clean(defaults.get("include_in_v1", ""))
                )
            notes = st.text_area("Registry notes", value=clean(defaults.get("notes", "")))

        submitted = st.form_submit_button("Save paper")
        if submitted:
            payload = {
                "paper_id": paper_id.strip(),
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": doi,
                "title": title,
                "first_author": first_author,
                "year": year,
                "journal": journal,
                "cluster": cluster,
                "metal_cluster": metal_cluster,
                "metal": metal,
                "material_form": registry_material_form,
                "biological_model": biological_model,
                "endpoint_families": endpoint_families,
                "key_endpoints": key_endpoints,
                "assays": assays,
                "curation_tier": curation_tier,
                "include_in_v1": include_in_v1,
                "notes": notes,
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
            }
            errors, warnings = validation.validate_paper(payload)
            if errors:
                render_validation_feedback(errors, warnings)
            else:
                db.upsert_paper(conn, payload)
                flash_validation_feedback("Paper saved.", warnings)
                st.rerun()

    with st.expander("Import paper registry CSV"):
        uploaded = st.file_uploader("Paper registry CSV", type=["csv"], key="paper_import")
        if uploaded is not None:
            content = uploaded.getvalue()
            preview = registry_import.validate_paper_registry_csv(conn, content)
            st.subheader("Import validation")
            st.dataframe(preview.issues, use_container_width=True, hide_index=True)
            st.subheader("Import preview")
            st.dataframe(preview.records, use_container_width=True, hide_index=True)
            if preview.has_errors:
                st.error("Fix blocking import errors before saving.")
            elif st.button("Import paper registry"):
                result = registry_import.import_paper_registry_csv(conn, content)
                flash(
                    "success",
                    f"Imported {result.imported_count} paper registry rows.",
                )
                for issue in result.issues.to_dict("records"):
                    if issue["severity"] == "warning":
                        flash("warning", issue["message"])
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
        cols = st.columns(3)
        with cols[0]:
            anchor_type = select_control(
                "Anchor type",
                ANCHOR_TYPES,
                clean(defaults.get("anchor_type", "")),
                key="slot_anchor_type",
            )
        with cols[1]:
            anchor_location = st.text_input(
                "Anchor location", value=clean(defaults.get("anchor_location", ""))
            )
        with cols[2]:
            anchor_note = st.text_input(
                "Anchor note", value=clean(defaults.get("anchor_note", ""))
            )
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
            paper_row = get_row(papers, "paper_id", paper_id)
            payload = {
                "claim_id": claim_id.strip(),
                "paper_id": paper_id,
                "anchor_type": anchor_type,
                "anchor_location": anchor_location,
                "anchor_note": anchor_note,
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
            }
            errors, warnings = validation.validate_claim_slot(payload)
            if errors:
                render_validation_feedback(errors, warnings)
            else:
                db.upsert_claim_slot(conn, payload)
                flash_validation_feedback("Claim slot saved.", warnings)
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
    locked = bool_from_row(defaults, "locked")
    if selected_annotation != "New annotation":
        status = "locked" if locked else "unlocked"
        st.info(f"Selected annotation is {status}.")
        lock_cols = st.columns(2)
        with lock_cols[0]:
            if not locked and st.button("Lock selected annotation"):
                db.set_annotation_lock(conn, claim_id, selected_annotation, locked=True)
                flash("success", "Annotation locked.")
                st.rerun()
        with lock_cols[1]:
            if locked and st.button("Unlock selected annotation"):
                db.set_annotation_lock(conn, claim_id, selected_annotation, locked=False)
                flash("warning", "Annotation unlocked for editing.")
                st.rerun()

    with st.form("annotation_form"):
        curator = st.text_input(
            "Curator",
            value=clean(defaults.get("curator", "")),
            disabled=locked,
        )
        claim_values = render_claim_fields(
            "Claim record", defaults, "annotation", disabled=locked
        )
        render_completeness_panel(claim_values)
        submitted = st.form_submit_button("Save annotation", disabled=locked)
        if submitted:
            payload = {
                "claim_id": claim_id,
                "curator": curator.strip(),
                **claim_values,
                "demo": bool_from_row(slot_row, "demo"),
                "source_type": slot_row.get("source_type", "manual_curation")
                or "manual_curation",
                "exclude_from_metrics": bool_from_row(slot_row, "exclude_from_metrics"),
                "exclude_from_export_by_default": bool_from_row(
                    slot_row, "exclude_from_export_by_default"
                ),
            }
            errors, warnings = validation.validate_claim_record(payload)
            if errors:
                render_validation_feedback(errors, warnings)
            else:
                db.upsert_annotation(conn, payload)
                flash_validation_feedback("Annotation saved.", warnings)
                st.rerun()

    if not existing_for_slot.empty:
        st.subheader("Current annotations for this slot")
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
    locked_count = (
        slot_annotations[slot_annotations["locked"].astype(int) == 1]["curator"].nunique()
        if not slot_annotations.empty and "locked" in slot_annotations.columns
        else 0
    )
    comparison = metrics.claim_comparison_df(slot_annotations)
    st.subheader("Curator comparison")
    st.dataframe(styled_comparison(comparison), use_container_width=True, hide_index=True)
    st.subheader("Raw annotations for this slot")
    st.dataframe(slot_annotations, use_container_width=True, hide_index=True)

    existing = get_row(adjudications, "claim_id", claim_id)
    eligible_for_adjudication = locked_count >= 2 or bool(existing)
    if not eligible_for_adjudication:
        st.warning("Adjudication is enabled after at least two curator annotations are locked.")
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
        render_completeness_panel(final_values)
        adjudication_notes = st.text_area(
            "Adjudication notes",
            value=clean(existing.get("adjudication_notes", "")),
            height=90,
        )
        submitted = st.form_submit_button(
            "Save adjudication", disabled=not eligible_for_adjudication
        )
        if submitted:
            validation_payload = {
                "adjudicator": adjudicator.strip(),
                **final_values,
            }
            errors, warnings = validation.validate_claim_record(
                validation_payload, curator_label="Adjudicator"
            )
            if errors:
                render_validation_feedback(errors, warnings)
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
                flash_validation_feedback("Adjudication saved.", warnings)
                st.rerun()


def metrics_export_tab(conn: Any) -> None:
    st.header("Metrics + Export")
    include_demo = st.checkbox("Include demo fixtures", value=False, key="export_demo")
    metric_frame = metrics.metrics_df(conn, include_demo=include_demo)
    records = exports.claim_records_df(conn, include_demo=include_demo)
    export_summary = exports.export_summary(conn, include_demo=include_demo)

    metric_lookup = dict(zip(metric_frame["metric"], metric_frame["value"], strict=False))
    cols = st.columns(4)
    cols[0].metric("Papers screened", metric_lookup.get("papers_screened", 0))
    cols[1].metric("Papers curated", metric_lookup.get("papers_curated", 0))
    cols[2].metric("Claim records", metric_lookup.get("claim_records", 0))
    cols[3].metric("Endpoint agreement", f"{metric_lookup.get('agreement_endpoint_family', 0)}%")

    st.subheader("Export sanity checks")
    summary_cols = st.columns(5)
    summary_cols[0].metric("Exported records", export_summary["exported_records"])
    summary_cols[1].metric("Adjudicated", export_summary["adjudicated_records"])
    summary_cols[2].metric("Raw annotations", export_summary["raw_annotation_records"])
    summary_cols[3].metric("Demo in export", export_summary["demo_records_in_export"])
    summary_cols[4].metric("Demo excluded", export_summary["demo_records_excluded"])

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

    st.subheader("Grant packet")
    packet_name, packet_bytes = packet.grant_packet_zip(conn, include_demo=include_demo)
    st.download_button(
        f"Download {packet_name}",
        data=packet_bytes,
        file_name=packet_name,
        mime="application/zip",
    )

    backup_name, backup_bytes = packet.sqlite_backup_download(conn)
    st.download_button(
        f"Download {backup_name}",
        data=backup_bytes,
        file_name=backup_name,
        mime="application/vnd.sqlite3",
    )

    with st.expander("Demo utility"):
        st.caption("Resets only rows marked as demo fixtures. Manual curation data is left alone.")
        if st.button("Reset demo fixtures"):
            db.reset_demo_data(conn)
            flash("success", "Demo fixtures reset.")
            st.rerun()


def codebook_qa_tab(conn: Any) -> None:
    st.header("Codebook + QA")
    include_demo = st.checkbox("Include demo fixtures", value=False, key="qa_demo")
    qa_frame = quality.data_quality_report_df(conn, include_demo=include_demo)
    codebook = quality.data_dictionary_df()

    st.subheader("QA summary")
    if qa_frame.empty:
        st.success("No QA flags for the selected export scope.")
    else:
        cols = st.columns(3)
        cols[0].metric("QA flags", len(qa_frame))
        cols[1].metric("Errors", int((qa_frame["severity"] == "error").sum()))
        cols[2].metric("Warnings", int((qa_frame["severity"] == "warning").sum()))
        st.dataframe(qa_frame, use_container_width=True, hide_index=True)
        st.download_button(
            "Download data_quality_report.csv",
            data=exports.csv_bytes(qa_frame),
            file_name="data_quality_report.csv",
            mime="text/csv",
        )

    st.subheader("Data dictionary")
    st.dataframe(codebook, use_container_width=True, hide_index=True)
    st.download_button(
        "Download data_dictionary.csv",
        data=exports.csv_bytes(codebook),
        file_name="data_dictionary.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(
        page_title="Metalloimmunome Claim Curation Pilot",
        layout="wide",
    )
    st.title("Metalloimmunome Claim Curation Pilot")
    render_flash()
    conn = get_connection()

    tabs = st.tabs(
        [
            "Papers",
            "Claim Slots",
            "Annotate",
            "Adjudicate",
            "Codebook + QA",
            "Metrics + Export",
        ]
    )
    with tabs[0]:
        paper_tab(conn)
    with tabs[1]:
        claim_slots_tab(conn)
    with tabs[2]:
        annotate_tab(conn)
    with tabs[3]:
        adjudicate_tab(conn)
    with tabs[4]:
        codebook_qa_tab(conn)
    with tabs[5]:
        metrics_export_tab(conn)


if __name__ == "__main__":
    main()
