"""Validation and completeness helpers for curator-facing forms."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .metrics import has_value

MISSINGNESS_BY_FIELD = {
    "dose": "dose missing",
    "comparator": "comparator missing",
    "speciation_or_oxidation_state": "speciation missing",
    "assay": "assay unclear",
    "specific_endpoint": "endpoint unclear",
}

COMPLETENESS_FIELDS = [
    ("dose", "Dose"),
    ("comparator", "Comparator"),
    ("material_form", "Material form"),
    ("speciation_or_oxidation_state", "Speciation or oxidation state"),
    ("assay", "Assay"),
    ("evidence_location", "Evidence location"),
]


def missingness_labels(record: Mapping[str, Any]) -> set[str]:
    value = str(record.get("missing_core_fields", "") or "")
    return {part.strip().lower() for part in value.split(";") if part.strip()}


def completeness_rows(record: Mapping[str, Any]) -> list[dict[str, str]]:
    labels = missingness_labels(record)
    rows: list[dict[str, str]] = []
    for field, label in COMPLETENESS_FIELDS:
        missingness = MISSINGNESS_BY_FIELD.get(field, "")
        present = has_value(record.get(field, ""))
        marked_missing = missingness in labels
        if present:
            status = "present"
        elif marked_missing:
            status = "explicitly missing"
        else:
            status = "needs review"
        rows.append(
            {
                "field": label,
                "status": status,
                "value": str(record.get(field, "") or ""),
                "missingness_label": missingness,
            }
        )
    return rows


def completeness_df(record: Mapping[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        completeness_rows(record),
        columns=["field", "status", "value", "missingness_label"],
    )


def validate_paper(payload: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []
    if not str(payload.get("paper_id", "")).strip():
        errors.append("paper_id is required.")
    if not str(payload.get("title", "")).strip():
        warnings.append("Title is blank; screenshots and exports will be harder to interpret.")
    if not str(payload.get("metal_cluster", "")).strip():
        warnings.append("Metal cluster is blank.")
    if not str(payload.get("curator", "")).strip():
        warnings.append("Curator initials are blank.")
    return errors, warnings


def validate_claim_slot(payload: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []
    if not str(payload.get("claim_id", "")).strip():
        errors.append("claim_id is required.")
    if not str(payload.get("paper_id", "")).strip():
        errors.append("paper_id is required.")
    if not str(payload.get("anchor_type", "")).strip():
        warnings.append("Anchor type is blank.")
    if not str(payload.get("anchor_location", "")).strip():
        warnings.append("Anchor location is blank.")
    if not str(payload.get("slot_note", "")).strip():
        warnings.append("Slot note is blank; use it to identify the shared claim target.")
    return errors, warnings


def validate_claim_record(
    payload: Mapping[str, Any], *, curator_label: str = "Curator"
) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []
    if not str(payload.get("curator", "")).strip() and not str(
        payload.get("adjudicator", "")
    ).strip():
        errors.append(f"{curator_label} is required.")
    valid_claim = str(payload.get("valid_claim", "")).strip()
    if not valid_claim:
        errors.append("Valid claim is required.")
    if valid_claim == "yes":
        for field, label in [
            ("endpoint_family", "Endpoint family"),
            ("direction", "Direction"),
            ("confidence", "Confidence"),
            ("evidence_location", "Evidence location"),
        ]:
            if not str(payload.get(field, "")).strip():
                errors.append(f"{label} is required.")

    labels = missingness_labels(payload)
    if valid_claim == "yes":
        for field, missingness in MISSINGNESS_BY_FIELD.items():
            if not has_value(payload.get(field, "")) and missingness not in labels:
                warnings.append(
                    f"{field} is blank but `{missingness}` is not selected."
                )
    return errors, warnings
