import io

from pypdf import PdfReader


class PdfExtractionError(Exception):
    """Raised when a PDF has no extractable text (e.g. a scanned image)."""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Pull plain text out of an uploaded PDF.

    This is the deterministic first step before anything touches the LLM —
    keeping it separate makes it independently unit-testable (see
    tests/test_pdf_extraction.py) and means a bad PDF fails fast with a
    clear error rather than producing a confusing LLM response.

    Note: this only handles text-layer PDFs. A scanned/image-only PDF will
    raise PdfExtractionError — for that case, swap in a vision-model call
    (send page images to GPT-4o-class model) or an OCR step upstream.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages_text).strip()

    if not text:
        raise PdfExtractionError(
            "No extractable text found. This may be a scanned/image-only PDF — "
            "consider an OCR or vision-model fallback."
        )

    return text
