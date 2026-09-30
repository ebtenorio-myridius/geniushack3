import io

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

import src.app.routers.intake as intake
from src.app.main import app


def _pdf_bytes(text: str | None = None) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    if text:
        pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_upload_rejects_non_pdf():
    response = TestClient(app).post(
        "/intake/upload",
        files={"file": ("notes.txt", b"synthetic text", "text/plain")},
    )

    assert response.status_code == 415
    assert "Only PDF documents are accepted" in response.text


def test_upload_rejects_file_over_size_limit():
    oversized_pdf = b"%PDF-" + b"x" * (10 * 1024 * 1024 + 1)
    response = TestClient(app).post(
        "/intake/upload",
        files={"file": ("large.pdf", oversized_pdf, "application/pdf")},
    )

    assert response.status_code == 413
    assert "10 MB upload limit" in response.text


def test_upload_returns_extraction_error_for_textless_pdf():
    response = TestClient(app).post(
        "/intake/upload",
        files={"file": ("scanned.pdf", _pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 422
    assert "No extractable text found" in response.text


def test_upload_returns_extraction_error_for_malformed_pdf():
    response = TestClient(app).post(
        "/intake/upload",
        files={"file": ("broken.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 422
    assert "not a readable PDF" in response.text


def test_upload_returns_gateway_error_when_extraction_provider_fails(monkeypatch):
    async def fail_extraction(_text):
        raise RuntimeError("synthetic provider failure")

    monkeypatch.setattr(intake, "draft_extraction", fail_extraction)
    response = TestClient(app).post(
        "/intake/upload",
        files={"file": ("request.pdf", _pdf_bytes("Synthetic change request"), "application/pdf")},
    )

    assert response.status_code == 502
    assert "couldn&#39;t produce a valid extraction" in response.text
    assert "synthetic provider failure" not in response.text