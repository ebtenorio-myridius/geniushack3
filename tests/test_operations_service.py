import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.app.services import operations_service


def test_snapshot_bounds_sample_preserves_missing_usage_and_excludes_reviews():
    record = dict(operation="extraction", success=True, latency_ms=120,
                  input_tokens=None, output_tokens=5, private_text="must not be sent")
    snapshot = operations_service.telemetry_snapshot([
        dict(record, operation="operations_review"), *[record] * 201,
    ])
    assert snapshot["sample_count"] == 200
    assert snapshot["missing_input_token_records"] == 200
    assert snapshot["reported_output_tokens"] == 1000
    assert "private_text" not in snapshot
    assert operations_service.telemetry_snapshot([]) == {}


@pytest.mark.parametrize("outcome", ["success", "unknown_metric", "empty", "provider_error"])
def test_review_validates_evidence_and_records_own_usage(monkeypatch, outcome):
    review = operations_service.OperationsReview(summary="Human review needed", findings=[
        operations_service.OperationsFinding(
            observation="One failed operation", evidence_keys=[
                "invented_metric" if outcome == "unknown_metric" else "failed_operations"
            ], suggested_check="Inspect provider status manually",
        ),
    ])
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=None if outcome == "empty" else review))],
        usage=SimpleNamespace(prompt_tokens=30, completion_tokens=15),
    )
    parse = AsyncMock(return_value=response)
    if outcome == "provider_error":
        parse.side_effect = RuntimeError("provider failed")
    monkeypatch.setattr(operations_service, "_client", SimpleNamespace(
        beta=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=parse)))
    ))
    store = Mock()
    if outcome == "success":
        assert asyncio.run(operations_service.review_operations({"failed_operations": 1}, store)) == review
        assert json.loads(parse.call_args.kwargs["messages"][1]["content"]) == {"failed_operations": 1}
    else:
        with pytest.raises((ValueError, RuntimeError)):
            asyncio.run(operations_service.review_operations({"failed_operations": 1}, store))
    store.record_telemetry.assert_called_once()
    record = store.record_telemetry.call_args.args[0]
    assert record.operation == "operations_review"
    assert record.success == (outcome == "success")
    assert record.input_tokens == (None if outcome == "provider_error" else 30)