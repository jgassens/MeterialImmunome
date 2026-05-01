"""Grant-facing metrics for the curation pilot."""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd

from .exports import claim_records_df, filtered_tables_for_metrics
from .vocab import AGREEMENT_FIELDS

MISSING_VALUES = {"", "not reported", "unknown", "unclear", "n/a", "na", "none"}


def normalize_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def has_value(value: Any) -> bool:
    return normalize_value(value) not in MISSING_VALUES


def dose_present(row: pd.Series | dict[str, Any]) -> bool:
    missing = normalize_value(row.get("missing_core_fields", ""))
    if "dose missing" in missing:
        return False
    return has_value(row.get("dose", ""))


def field_percent(frame: pd.DataFrame, field: str) -> float:
    if frame.empty:
        return 0.0
    present = frame[field].apply(has_value)
    if field == "dose":
        present = frame.apply(dose_present, axis=1)
    return round(float(present.mean() * 100), 1)


def missingness_percent(frame: pd.DataFrame, label: str) -> float:
    if frame.empty:
        return 0.0
    missing = frame["missing_core_fields"].fillna("").str.lower().str.contains(label)
    return round(float(missing.mean() * 100), 1)


def agreement_summary(annotations: pd.DataFrame) -> dict[str, float | int]:
    if annotations.empty:
        return {f"agreement_{field}": 0.0 for field in AGREEMENT_FIELDS} | {
            "paired_claim_slots": 0
        }

    paired_groups = []
    for _claim_id, group in annotations.groupby("claim_id"):
        if group["curator"].nunique() >= 2:
            paired_groups.append(group)

    denominator = len(paired_groups)
    summary: dict[str, float | int] = {"paired_claim_slots": denominator}
    for field in AGREEMENT_FIELDS:
        agreeing = 0
        for group in paired_groups:
            if field == "dose_present":
                values = {dose_present(row) for _, row in group.iterrows()}
            else:
                values = {normalize_value(value) for value in group[field].tolist()}
            if len(values) == 1:
                agreeing += 1
        summary[f"agreement_{field}"] = (
            round((agreeing / denominator) * 100, 1) if denominator else 0.0
        )
    return summary


def metrics_df(conn: sqlite3.Connection, *, include_demo: bool = False) -> pd.DataFrame:
    papers, slots, annotations, _adjudications = filtered_tables_for_metrics(
        conn, include_demo=include_demo
    )
    records = claim_records_df(conn, include_demo=include_demo)
    agreements = agreement_summary(annotations)

    paper_count = len(papers)
    curated_papers = int(papers["status"].isin(["curated", "adjudicated"]).sum()) if not papers.empty else 0
    claim_count = len(records)
    claims_per_paper = round(claim_count / paper_count, 2) if paper_count else 0.0

    rows = [
        ("papers_screened", paper_count, "Count of included paper registry rows."),
        ("papers_curated", curated_papers, "Papers marked curated or adjudicated."),
        ("shared_claim_slots", len(slots), "Shared material-context-endpoint slots."),
        ("claim_records", claim_count, "Exportable adjudicated or raw annotation records."),
        ("claims_per_paper", claims_per_paper, "Exportable records divided by papers screened."),
        ("percent_with_dose", field_percent(records, "dose"), "Records with dose present."),
        (
            "percent_with_comparator",
            field_percent(records, "comparator"),
            "Records with comparator present.",
        ),
        (
            "percent_with_material_form",
            field_percent(records, "material_form"),
            "Records with material form present.",
        ),
        (
            "percent_with_speciation_or_oxidation_state",
            field_percent(records, "speciation_or_oxidation_state"),
            "Records with speciation or oxidation state present.",
        ),
        ("percent_with_assay", field_percent(records, "assay"), "Records with assay present."),
        (
            "percent_with_evidence_location",
            field_percent(records, "evidence_location"),
            "Records with evidence location present.",
        ),
        (
            "percent_missing_purity_or_endotoxin_controls",
            missingness_percent(records, "purity/endotoxin not reported"),
            "Records explicitly missing purity or endotoxin reporting.",
        ),
        (
            "paired_claim_slots",
            agreements["paired_claim_slots"],
            "Claim slots annotated by at least two curators.",
        ),
        (
            "agreement_endpoint_family",
            agreements["agreement_endpoint_family"],
            "Exact agreement on endpoint family across paired annotations.",
        ),
        (
            "agreement_direction",
            agreements["agreement_direction"],
            "Exact agreement on direction across paired annotations.",
        ),
        (
            "agreement_comparator",
            agreements["agreement_comparator"],
            "Exact agreement on comparator across paired annotations.",
        ),
        (
            "agreement_material_form",
            agreements["agreement_material_form"],
            "Exact agreement on material form across paired annotations.",
        ),
        (
            "agreement_dose_present",
            agreements["agreement_dose_present"],
            "Agreement on whether dose is present.",
        ),
        (
            "agreement_confidence",
            agreements["agreement_confidence"],
            "Exact agreement on confidence.",
        ),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "description"])


def disagreements_df(
    conn: sqlite3.Connection, *, include_demo: bool = False
) -> pd.DataFrame:
    _papers, slots, annotations, _adjudications = filtered_tables_for_metrics(
        conn, include_demo=include_demo
    )
    if annotations.empty:
        return pd.DataFrame(columns=["claim_id", "paper_id", "field", "values"])

    slot_lookup = slots.set_index("claim_id").to_dict("index") if not slots.empty else {}
    rows: list[dict[str, str]] = []
    for claim_id, group in annotations.groupby("claim_id"):
        if group["curator"].nunique() < 2:
            continue
        for field in AGREEMENT_FIELDS:
            if field == "dose_present":
                values_by_curator = {
                    row["curator"]: "present" if dose_present(row) else "absent"
                    for _, row in group.iterrows()
                }
            else:
                values_by_curator = {
                    row["curator"]: str(row[field]).strip() for _, row in group.iterrows()
                }
            normalized = {normalize_value(value) for value in values_by_curator.values()}
            if len(normalized) > 1:
                rows.append(
                    {
                        "claim_id": claim_id,
                        "paper_id": str(slot_lookup.get(claim_id, {}).get("paper_id", "")),
                        "field": field,
                        "values": "; ".join(
                            f"{curator}: {value}"
                            for curator, value in sorted(values_by_curator.items())
                        ),
                    }
                )
    return pd.DataFrame(rows, columns=["claim_id", "paper_id", "field", "values"])

