import io

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

import src.app.routers.intake as intake
from src.app.main import app
from src.app.models.schemas import EvidenceCitation, ExtractedChangeRequest, TelemetryRecord
from src.app.services.case_store import CaseStore


def _pdf_bytes(text: str | None = None) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    if text:
        pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _owner_client() -> TestClient:
    client = TestClient(app)
    client.cookies.set("demo_user", "product-owner-1")
    client.cookies.set("demo_role", "product_owner")
    return client


def test_upload_rejects_non_pdf():
    response = _owner_client().post(
        "/intake/upload",
        files={"file": ("notes.txt", b"synthetic text", "text/plain")},
    )

    assert response.status_code == 415
    assert "Only PDF documents are accepted" in response.text


def test_upload_rejects_file_over_size_limit():
    oversized_pdf = b"%PDF-" + b"x" * (10 * 1024 * 1024 + 1)
    response = _owner_client().post(
        "/intake/upload",
        files={"file": ("large.pdf", oversized_pdf, "application/pdf")},
    )

    assert response.status_code == 413
    assert "10 MB upload limit" in response.text


def test_upload_returns_extraction_error_for_textless_pdf():
    response = _owner_client().post(
        "/intake/upload",
        files={"file": ("scanned.pdf", _pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 422
    assert "No extractable text found" in response.text


def test_upload_returns_extraction_error_for_malformed_pdf():
    response = _owner_client().post(
        "/intake/upload",
        files={"file": ("broken.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 422
    assert "not a readable PDF" in response.text


def test_telemetry_page_shows_token_counts_for_each_request(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "telemetry.db"))
    store.record_telemetry(
        TelemetryRecord(
            operation="extraction",
            model="test-model",
            prompt_version="test-prompt",
            latency_ms=125,
            input_tokens=12,
            output_tokens=7,
            success=True,
        )
    )
    monkeypatch.setattr(intake, "case_store", store)

    response = _owner_client().get("/intake/telemetry")

    assert response.status_code == 200
    assert "Prompt tokens" in response.text
    assert "Completion tokens" in response.text
    assert "test-model" in response.text
    assert "12" in response.text
    assert "7" in response.text
    assert "125 ms" in response.text
    assert "Success" in response.text


def test_upload_returns_gateway_error_when_extraction_provider_fails(monkeypatch):
    async def fail_extraction(_text):
        raise RuntimeError("synthetic provider failure")

    monkeypatch.setattr(intake, "draft_extraction", fail_extraction)
    response = _owner_client().post(
        "/intake/upload",
        files={"file": ("request.pdf", _pdf_bytes("Synthetic change request"), "application/pdf")},
    )

    assert response.status_code == 502
    assert "couldn&#39;t produce a valid extraction" in response.text
    assert "synthetic provider failure" not in response.text


def test_operations_review_rejects_non_analysts():
    assert TestClient(app).post("/intake/telemetry/review").status_code == 403
    assert _owner_client().post("/intake/telemetry/review").status_code == 403


def test_operations_review_requires_data_and_same_origin(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "case_store", CaseStore(str(tmp_path / "empty.db")))
    client = TestClient(app)
    client.cookies.set("demo_user", "analyst-1")
    client.cookies.set("demo_role", "analyst")
    assert client.post("/intake/telemetry/review", headers={"Origin": "https://other.example"}).status_code == 403
    response = client.post("/intake/telemetry/review")
    assert response.status_code == 422
    assert "No recorded operations" in response.text


def test_operations_review_renders_evidence_and_controls_provider_errors(monkeypatch, tmp_path):
    from src.app.services.operations_service import OperationsFinding, OperationsReview

    store = CaseStore(str(tmp_path / "operations.db"))
    store.record_telemetry(TelemetryRecord(
        operation="extraction", model="test-model", prompt_version="test",
        latency_ms=125, success=False,
    ))
    monkeypatch.setattr(intake, "case_store", store)
    client = TestClient(app)
    client.cookies.set("demo_user", "analyst-1")
    client.cookies.set("demo_role", "analyst")
    assert "Request AI review" in client.get("/intake/telemetry").text
    assert "Request AI review" not in _owner_client().get("/intake/telemetry").text

    async def review(snapshot, supplied_store):
        assert snapshot["failed_operations"] == 1
        assert supplied_store is store
        return OperationsReview(summary="<script>unsafe()</script>", findings=[OperationsFinding(
            observation="Failure recorded", evidence_keys=["failed_operations"],
            suggested_check="Check provider status",
        )])

    monkeypatch.setattr(intake, "review_operations", review)
    response = client.post("/intake/telemetry/review")
    assert response.status_code == 200
    assert "failed_operations: 1" in response.text
    assert "Check provider status" in response.text
    assert "<script>unsafe()" not in response.text
    assert "&lt;script&gt;" in response.text

    async def fail_review(*_args):
        raise RuntimeError("private provider details")

    monkeypatch.setattr(intake, "review_operations", fail_review)
    response = client.post("/intake/telemetry/review")
    assert response.status_code == 502
    assert "No changes were made" in response.text
    assert "private provider details" not in response.text


def test_upload_retains_source_pages_and_verifiable_extraction(monkeypatch, tmp_path):
    page_text = "Synthetic change request: New product for Payments. A synthetic change request."
    extraction = ExtractedChangeRequest(
        change_title="Synthetic change",
        change_type="new_product",
        business_unit="Payments",
        description="A synthetic change request.",
        extraction_confidence=0.9,
        evidence=[
            EvidenceCitation(field_name="change_title", page_number=1, quote="Synthetic change"),
            EvidenceCitation(field_name="change_type", page_number=1, quote="New product"),
            EvidenceCitation(field_name="business_unit", page_number=1, quote="Payments"),
            EvidenceCitation(field_name="description", page_number=1, quote="A synthetic change request."),
        ],
    )

    received = []

    async def extract(text):
        received.append(text)
        return extraction

    store = CaseStore(str(tmp_path / "intake.db"))
    monkeypatch.setattr(intake, "case_store", store)
    monkeypatch.setattr(intake, "extract_text_by_page_from_pdf", lambda _bytes: [page_text])
    monkeypatch.setattr(intake, "draft_extraction", extract)
    pdf = _pdf_bytes("Synthetic PDF fixture")

    response = _owner_client().post(
        "/intake/upload",
        files={"file": ("request.pdf", pdf, "application/pdf")},
    )

    assert response.status_code == 200
    assert "Page 1" in response.text
    assert received == [f"[SOURCE PAGE 1]\n{page_text}"]
    case = store.list_cases()[0]
    metadata, retained_bytes = store.read_source_document(case.case_id)
    assert metadata["filename"] == "request.pdf"
    assert retained_bytes == pdf
    assert store.list_source_pages(case.case_id)[0]["page_text"] == page_text


def test_upload_rejects_unverifiable_extraction_citation(monkeypatch, tmp_path):
    extraction = ExtractedChangeRequest(
        change_title="Synthetic change",
        change_type="new_product",
        business_unit="Payments",
        description="A synthetic change request.",
        extraction_confidence=0.9,
        evidence=[
            EvidenceCitation(field_name="change_title", page_number=1, quote="not in source"),
            EvidenceCitation(field_name="change_type", page_number=1, quote="New product"),
            EvidenceCitation(field_name="business_unit", page_number=1, quote="Payments"),
            EvidenceCitation(field_name="description", page_number=1, quote="A synthetic change request."),
        ],
    )

    async def extract(_text):
        return extraction

    store = CaseStore(str(tmp_path / "intake.db"))
    monkeypatch.setattr(intake, "case_store", store)
    monkeypatch.setattr(intake, "extract_text_by_page_from_pdf", lambda _bytes: ["New product for Payments. A synthetic change request."])
    monkeypatch.setattr(intake, "draft_extraction", extract)

    response = _owner_client().post(
        "/intake/upload",
        files={"file": ("request.pdf", _pdf_bytes("Synthetic PDF fixture"), "application/pdf")},
    )

    assert response.status_code == 422
    assert "not present on source page" in response.text
    assert store.list_cases() == []


def test_upload_requires_product_owner_role():
    response = TestClient(app).post(
        "/intake/upload",
        files={"file": ("request.pdf", _pdf_bytes("Synthetic change request"), "application/pdf")},
    )

    assert response.status_code == 403