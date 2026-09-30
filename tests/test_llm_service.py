import asyncio
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from src.app.models.schemas import ExtractedChangeRequest
from src.app.services import llm_service


def _connection_error():
    return APIConnectionError(
        message="synthetic connection failure",
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )


def _timeout_error():
    return APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )


def _rate_limit_error():
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return RateLimitError(
        message="synthetic rate limit",
        response=httpx.Response(429, request=request),
        body=None,
    )


def _response():
    extracted = ExtractedChangeRequest(
        change_title="Synthetic change",
        change_type="feature_change",
        business_unit="Consumer Banking",
        description="Synthetic test request.",
        extraction_confidence=0.9,
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=extracted))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


class _FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def parse(self, **_kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _install_fake_client(monkeypatch, outcomes):
    completions = _FakeCompletions(outcomes)
    client = SimpleNamespace(beta=SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    monkeypatch.setattr(llm_service, "_client", client)
    monkeypatch.setattr(llm_service, "_load_system_prompt", lambda: "synthetic prompt")
    telemetry = []
    monkeypatch.setattr(llm_service.case_store, "record_telemetry", telemetry.append)
    return completions, telemetry


@pytest.mark.parametrize(
    "transient_error",
    [_connection_error, _timeout_error, _rate_limit_error],
)
def test_draft_extraction_retries_transient_provider_error(monkeypatch, transient_error):
    completions, telemetry = _install_fake_client(
        monkeypatch,
        [transient_error(), _response()],
    )

    extracted = asyncio.run(llm_service.draft_extraction("synthetic source"))

    assert extracted.change_title == "Synthetic change"
    assert completions.calls == 2
    assert len(telemetry) == 1
    assert telemetry[0].success is True


def test_draft_extraction_does_not_retry_non_transient_error(monkeypatch):
    completions, telemetry = _install_fake_client(
        monkeypatch,
        [ValueError("invalid structured output")],
    )

    with pytest.raises(ValueError, match="invalid structured output"):
        asyncio.run(llm_service.draft_extraction("synthetic source"))

    assert completions.calls == 1
    assert len(telemetry) == 1
    assert telemetry[0].success is False
    assert telemetry[0].error_type == "ValueError"


def test_draft_extraction_records_failure_after_retry_limit(monkeypatch):
    completions, telemetry = _install_fake_client(
        monkeypatch,
        [_connection_error(), _connection_error(), _connection_error()],
    )

    with pytest.raises(APIConnectionError):
        asyncio.run(llm_service.draft_extraction("synthetic source"))

    assert completions.calls == llm_service._MAX_EXTRACTION_ATTEMPTS
    assert len(telemetry) == 1
    assert telemetry[0].success is False
    assert telemetry[0].error_type == "APIConnectionError"