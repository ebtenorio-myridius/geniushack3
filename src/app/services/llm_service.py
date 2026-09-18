from pathlib import Path
from time import perf_counter

from openai import AsyncOpenAI

from src.app.config import settings
from src.app.models.schemas import ExtractedChangeRequest
from src.app.services.dependencies import case_store
from src.app.models.schemas import TelemetryRecord

_PROMPT_PATH = Path(__file__).resolve().parents[3] / "ai" / "prompts" / "extract_change_request.md"

_client = AsyncOpenAI(api_key=settings.openai_api_key)


def _load_system_prompt() -> str:
    """Read the system prompt from /ai so it stays the single source of
    truth the hackathon judges will actually look at, instead of being
    duplicated/hidden in application code."""
    text = _PROMPT_PATH.read_text()
    start = text.find("```") + 3
    end = text.find("```", start)
    return text[start:end].strip()


async def draft_extraction(raw_text: str) -> ExtractedChangeRequest:
    """Send extracted PDF text to the LLM and get back a structured,
    schema-validated ExtractedChangeRequest.

    Uses OpenAI's structured outputs (`.parse()` + a Pydantic model) rather
    than free-text + manual JSON parsing, so a malformed response raises
    instead of silently corrupting downstream data. This is the one LLM
    call in the current slice — scoring (services/risk_scoring.py) is
    deliberately deterministic, not an LLM call.
    """
    system_prompt = _load_system_prompt()

    # Truncate defensively — swap for a proper chunking/summarization step
    # if you start receiving long multi-page submissions.
    document_text = raw_text[:12000]

    started = perf_counter()
    try:
        response = await _client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": document_text},
            ],
            response_format=ExtractedChangeRequest,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("The model returned no structured extraction")
        usage = response.usage
        case_store.record_telemetry(TelemetryRecord(
            operation="extraction",
            model=settings.openai_model,
            prompt_version=settings.prompt_version,
            latency_ms=round((perf_counter() - started) * 1000),
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            success=True,
        ))
        return parsed
    except Exception as exc:
        case_store.record_telemetry(TelemetryRecord(
            operation="extraction",
            model=settings.openai_model,
            prompt_version=settings.prompt_version,
            latency_ms=round((perf_counter() - started) * 1000),
            success=False,
            error_type=type(exc).__name__,
        ))
        raise
