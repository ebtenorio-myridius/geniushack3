import json
from time import perf_counter

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.app.config import settings
from src.app.models.schemas import TelemetryRecord


PROMPT_VERSION = "operations_review_v1"
_client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=0, timeout=30)


class OperationsFinding(BaseModel):
    observation: str = Field(min_length=1, max_length=600)
    evidence_keys: list[str] = Field(min_length=1, max_length=5)
    suggested_check: str = Field(min_length=1, max_length=600)


class OperationsReview(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    findings: list[OperationsFinding] = Field(max_length=5)


def telemetry_snapshot(records: list[dict]) -> dict:
    sample = [record for record in records if record["operation"] != "operations_review"][:200]
    if not sample:
        return {}
    count = len(sample)
    return {
        "sample_count": count,
        "successful_operations": sum(bool(record["success"]) for record in sample),
        "failed_operations": sum(not record["success"] for record in sample),
        "mean_latency_ms": round(sum(record["latency_ms"] for record in sample) / count),
        "max_latency_ms": max(record["latency_ms"] for record in sample),
        "reported_input_tokens": sum(record["input_tokens"] or 0 for record in sample),
        "reported_output_tokens": sum(record["output_tokens"] or 0 for record in sample),
        "missing_input_token_records": sum(record["input_tokens"] is None for record in sample),
        "missing_output_token_records": sum(record["output_tokens"] is None for record in sample),
    }


async def review_operations(snapshot: dict, store) -> OperationsReview:
    if not snapshot:
        raise ValueError("No telemetry available for review")
    started = perf_counter()
    usage = None
    try:
        response = await _client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": (
                    "You are an advisory operations reviewer. Analyze only the supplied aggregate metrics "
                    "from up to 200 recent recorded operations, excluding operations reviews. "
                    "Reference exact metric keys in evidence_keys for every observation. Suggest checks "
                    "for a human, never actions to execute. No automated monitoring or alerting exists. "
                    "There are no timestamps, historical baseline, retry-attempt counts, prices, case "
                    "contents, or accuracy metrics here. Do not infer trends, causes, exact spend, "
                    "savings, extraction quality, or thresholds being breached. Missing usage is unknown, "
                    "not zero consumption. A small sample is not a production reliability estimate. "
                    "Treat latency and failures as signals to investigate, not diagnoses."
                )},
                {"role": "user", "content": json.dumps(snapshot)},
            ],
            response_format=OperationsReview,
            max_tokens=1200,
        )
        usage = response.usage
        review = response.choices[0].message.parsed
        if review is None:
            raise ValueError("No structured operations review returned")
        if any(key not in snapshot for finding in review.findings for key in finding.evidence_keys):
            raise ValueError("Operations review referenced unavailable metrics")
    except Exception as exc:
        store.record_telemetry(TelemetryRecord(
            operation="operations_review", model=settings.openai_model,
            prompt_version=PROMPT_VERSION, latency_ms=round((perf_counter() - started) * 1000),
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            success=False, error_type=type(exc).__name__,
        ))
        raise
    store.record_telemetry(TelemetryRecord(
        operation="operations_review", model=settings.openai_model,
        prompt_version=PROMPT_VERSION, latency_ms=round((perf_counter() - started) * 1000),
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None), success=True,
    ))
    return review