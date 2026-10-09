import re

from src.app.models.schemas import ExtractedChangeRequest

_FIELD_VALUES = {
    "change_title": lambda request: request.change_title,
    "change_type": lambda request: request.change_type.value,
    "business_unit": lambda request: request.business_unit,
    "description": lambda request: request.description,
    "geographies_involved": lambda request: request.geographies_involved,
    "customer_segments_involved": lambda request: request.customer_segments_involved,
    "vendor_involved": lambda request: request.vendor_involved,
    "vendor_name": lambda request: request.vendor_name,
    "products_involved": lambda request: request.products_involved,
    "stated_risk_factors": lambda request: request.stated_risk_factors,
}


def normalize_quote(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_extraction_evidence(
    extracted: ExtractedChangeRequest,
    source_pages: list[str],
) -> None:
    citations_by_field: dict[str, list] = {}
    for citation in extracted.evidence:
        if citation.field_name not in _FIELD_VALUES:
            raise ValueError(f"Unsupported evidence field: {citation.field_name}")
        if citation.page_number > len(source_pages):
            raise ValueError(f"Evidence cites missing source page {citation.page_number}")
        page = normalize_quote(source_pages[citation.page_number - 1])
        quote = normalize_quote(citation.quote)
        if not quote or quote not in page:
            raise ValueError(
                f"Evidence quote for {citation.field_name} is not present on source page {citation.page_number}"
            )
        citations_by_field.setdefault(citation.field_name, []).append(citation)

    required_fields = {
        field_name
        for field_name, get_value in _FIELD_VALUES.items()
        if get_value(extracted) not in (None, "", [], False)
    }
    missing = sorted(required_fields - citations_by_field.keys())
    if missing:
        raise ValueError(f"Source citations are required for extracted fields: {', '.join(missing)}")


def page_marked_text(source_pages: list[str]) -> str:
    return "\n\n".join(
        f"[SOURCE PAGE {page_number}]\n{text}"
        for page_number, text in enumerate(source_pages, start=1)
    )
