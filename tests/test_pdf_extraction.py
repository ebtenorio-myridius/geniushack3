import io

import pytest
from reportlab.pdfgen import canvas

from src.app.services.pdf_extraction import PdfExtractionError, extract_text_from_pdf


def _make_pdf_bytes(text: str | None) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    if text:
        c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buffer.getvalue()


def test_extracts_text_from_a_normal_pdf():
    pdf_bytes = _make_pdf_bytes("New product launch: instant P2P transfers, EU rollout.")
    text = extract_text_from_pdf(pdf_bytes)
    assert "instant P2P transfers" in text


def test_raises_on_pdf_with_no_extractable_text():
    pdf_bytes = _make_pdf_bytes(None)
    with pytest.raises(PdfExtractionError):
        extract_text_from_pdf(pdf_bytes)
