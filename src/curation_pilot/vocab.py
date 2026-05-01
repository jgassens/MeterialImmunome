"""Controlled vocabularies and shared schema constants."""

PAPER_TYPES = ["primary study", "review", "excluded"]
PAPER_STATUSES = ["not started", "in progress", "curated", "adjudicated"]
FULL_TEXT_OPTIONS = ["yes", "no"]
METAL_CLUSTERS = ["aluminum", "nickel", "CoCr", "zinc", "other"]

SLOT_STATUSES = ["open", "uncertain", "invalid", "adjudicated"]
ANCHOR_TYPES = [
    "figure",
    "table",
    "results paragraph",
    "methods paragraph",
    "supplement",
    "other",
]

ENDPOINT_FAMILIES = [
    "inflammasome activation",
    "cytokine induction/skewing",
    "cytotoxicity",
    "other",
]
DIRECTIONS = ["increased", "decreased", "unchanged", "mixed", "unclear"]
MATERIAL_FORMS = [
    "soluble salt",
    "hydroxide",
    "oxide",
    "alloy debris",
    "nanoparticle",
    "MOF",
    "coating",
    "unknown",
]
CONTEXTS = ["in vitro", "in vivo", "ex vivo", "clinical tissue"]
CONFIDENCE_LEVELS = ["high", "medium", "low"]
VALID_CLAIM_OPTIONS = ["yes", "no", "unsure"]
MISSINGNESS_OPTIONS = [
    "none apparent",
    "dose missing",
    "comparator missing",
    "speciation missing",
    "assay unclear",
    "endpoint unclear",
    "purity/endotoxin not reported",
]

CLAIM_FIELDS = [
    "valid_claim",
    "metal",
    "material_form",
    "speciation_or_oxidation_state",
    "dose",
    "duration",
    "species",
    "cell_or_tissue",
    "in_vitro_or_in_vivo",
    "route_or_context",
    "stimulation_context",
    "comparator",
    "endpoint_family",
    "specific_endpoint",
    "assay",
    "direction",
    "magnitude",
    "evidence_location",
    "exact_evidence_excerpt",
    "missing_core_fields",
    "confidence",
    "curator_notes",
]

EXPORT_COLUMNS = [
    "record_type",
    "paper_id",
    "claim_id",
    "curator_or_adjudicator",
    *CLAIM_FIELDS,
    "demo",
    "source_type",
]

AGREEMENT_FIELDS = [
    "valid_claim",
    "endpoint_family",
    "direction",
    "comparator",
    "material_form",
    "dose_present",
    "confidence",
]

KAPPA_FIELDS = [
    "valid_claim",
    "endpoint_family",
    "direction",
    "material_form",
    "confidence",
    "dose_present",
]

PAPER_IMPORT_COLUMNS = [
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "first_author",
    "year",
    "journal",
    "cluster",
    "metal_cluster",
    "metal",
    "material_form",
    "biological_model",
    "endpoint_families",
    "key_endpoints",
    "assays",
    "curation_tier",
    "include_in_v1",
    "notes",
    "paper_type",
    "full_text_available",
    "curator",
    "status",
]


def split_multi(value: str | None) -> list[str]:
    """Split a stored semicolon-delimited multi-select value."""
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def join_multi(values: list[str] | tuple[str, ...] | str | None) -> str:
    """Store multi-select values in a stable semicolon-delimited form."""
    if values is None:
        return ""
    if isinstance(values, str):
        return values.strip()
    return "; ".join(str(value).strip() for value in values if str(value).strip())
