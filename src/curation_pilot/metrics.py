"""Grant-facing metrics for the curation pilot."""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from .exports import claim_records_df, filtered_tables_for_metrics
from .vocab import AGREEMENT_FIELDS, KAPPA_FIELDS

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


def field_value(row: pd.Series | dict[str, Any], field: str) -> str:
    if field == "dose_present":
        return "present" if dose_present(row) else "absent"
    return normalize_value(row.get(field, ""))


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


def locked_annotations(annotations: pd.DataFrame, *, locked_only: bool = True) -> pd.DataFrame:
    if annotations.empty or not locked_only or "locked" not in annotations.columns:
        return annotations
    return annotations[annotations["locked"].astype(int) == 1].copy()


def paired_annotation_groups(
    annotations: pd.DataFrame, *, locked_only: bool = True
) -> list[tuple[str, pd.DataFrame]]:
    scoped = locked_annotations(annotations, locked_only=locked_only)
    groups: list[tuple[str, pd.DataFrame]] = []
    if scoped.empty:
        return groups
    for claim_id, group in scoped.groupby("claim_id"):
        if group["curator"].nunique() >= 2:
            groups.append((str(claim_id), group.sort_values("curator")))
    return groups


def agreement_summary(
    annotations: pd.DataFrame, *, locked_only: bool = True
) -> dict[str, float | int | None]:
    if annotations.empty:
        return {f"agreement_{field}": 0.0 for field in AGREEMENT_FIELDS} | {
            "paired_claim_slots": 0
        } | {
            f"kappa_{field}": None for field in KAPPA_FIELDS
        }

    paired_groups = paired_annotation_groups(annotations, locked_only=locked_only)
    denominator = len(paired_groups)
    summary: dict[str, float | int | None] = {"paired_claim_slots": denominator}
    for field in AGREEMENT_FIELDS:
        agreeing = 0
        for _claim_id, group in paired_groups:
            values = {field_value(row, field) for _, row in group.iterrows()}
            if len(values) == 1:
                agreeing += 1
        summary[f"agreement_{field}"] = (
            round((agreeing / denominator) * 100, 1) if denominator else 0.0
        )
    report = agreement_report_df(annotations, locked_only=locked_only)
    for field in KAPPA_FIELDS:
        matching = report[report["field"] == field]
        summary[f"kappa_{field}"] = (
            matching["cohens_kappa"].iloc[0] if not matching.empty else None
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
        (
            "kappa_valid_claim",
            agreements["kappa_valid_claim"],
            "Cohen's kappa for valid_claim across paired locked annotations.",
        ),
        (
            "kappa_endpoint_family",
            agreements["kappa_endpoint_family"],
            "Cohen's kappa for endpoint family across paired locked annotations.",
        ),
        (
            "kappa_direction",
            agreements["kappa_direction"],
            "Cohen's kappa for direction across paired locked annotations.",
        ),
        (
            "kappa_material_form",
            agreements["kappa_material_form"],
            "Cohen's kappa for material form across paired locked annotations.",
        ),
        (
            "kappa_confidence",
            agreements["kappa_confidence"],
            "Cohen's kappa for confidence across paired locked annotations.",
        ),
        (
            "kappa_dose_present",
            agreements["kappa_dose_present"],
            "Cohen's kappa for dose-present status across paired locked annotations.",
        ),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "description"])


def disagreements_df(
    conn: sqlite3.Connection, *, include_demo: bool = False, locked_only: bool = True
) -> pd.DataFrame:
    _papers, slots, annotations, _adjudications = filtered_tables_for_metrics(
        conn, include_demo=include_demo
    )
    if annotations.empty:
        return pd.DataFrame(columns=["claim_id", "paper_id", "field", "values"])

    slot_lookup = slots.set_index("claim_id").to_dict("index") if not slots.empty else {}
    rows: list[dict[str, str]] = []
    for claim_id, group in paired_annotation_groups(annotations, locked_only=locked_only):
        for field in AGREEMENT_FIELDS:
            values_by_curator = {
                row["curator"]: field_value(row, field)
                for _, row in group.iterrows()
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


def agreement_report_df(
    annotations: pd.DataFrame, *, locked_only: bool = True
) -> pd.DataFrame:
    groups = paired_annotation_groups(annotations, locked_only=locked_only)
    rows: list[dict[str, object]] = []
    for field in AGREEMENT_FIELDS:
        pairs: list[tuple[str, str]] = []
        for _claim_id, group in groups:
            values = [field_value(row, field) for _, row in group.head(2).iterrows()]
            if len(values) == 2:
                pairs.append((values[0], values[1]))
        paired_count = len(pairs)
        agreeing = sum(1 for left, right in pairs if left == right)
        raw_agreement = round((agreeing / paired_count) * 100, 1) if paired_count else 0.0
        kappa = None
        if field in KAPPA_FIELDS and paired_count:
            left_values = [left for left, _right in pairs]
            right_values = [right for _left, right in pairs]
            observed_labels = set(left_values) | set(right_values)
            if len(observed_labels) >= 2:
                score = cohen_kappa_score(left_values, right_values)
                if pd.notna(score):
                    kappa = round(float(score), 3)
        rows.append(
            {
                "field": field,
                "paired_claim_slots": paired_count,
                "raw_agreement_percent": raw_agreement,
                "cohens_kappa": kappa,
                "kappa_included": field in KAPPA_FIELDS,
                "locked_only": locked_only,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "field",
            "paired_claim_slots",
            "raw_agreement_percent",
            "cohens_kappa",
            "kappa_included",
            "locked_only",
        ],
    )


def claim_comparison_df(annotations: pd.DataFrame) -> pd.DataFrame:
    """Compare paired curator values for one claim slot."""
    columns = ["field", "disagreement"]
    if annotations.empty:
        return pd.DataFrame(columns=columns)

    curators = sorted(str(curator) for curator in annotations["curator"].unique())
    rows: list[dict[str, str | bool]] = []
    fields = [
        "valid_claim",
        "endpoint_family",
        "direction",
        "comparator",
        "material_form",
        "dose_present",
        "confidence",
        "assay",
        "evidence_location",
    ]
    for field in fields:
        row: dict[str, str | bool] = {"field": field}
        normalized_values = set()
        for curator in curators:
            curator_rows = annotations[annotations["curator"] == curator]
            if curator_rows.empty:
                value = ""
            else:
                value = field_value(curator_rows.iloc[0], field)
            row[curator] = value
            normalized_values.add(normalize_value(value))
        row["disagreement"] = len(normalized_values) > 1
        rows.append(row)
    return pd.DataFrame(rows, columns=["field", *curators, "disagreement"])
