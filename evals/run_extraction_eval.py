"""Run the paid, live extraction evaluation explicitly when desired."""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app.services.llm_service import draft_extraction
from src.app.services.risk_scoring import score_change_request


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "data" / "synthetic_cases.json"
RESULTS_DIR = ROOT / "evals" / "results"


def _field_accuracy(actual, expected) -> tuple[int, int]:
    correct = 0
    total = 0
    for field, expected_value in expected.items():
        if field == "extraction_confidence":
            continue
        total += 1
        actual_value = getattr(actual, field)
        if hasattr(actual_value, "value"):
            actual_value = actual_value.value
        if isinstance(actual_value, str) and isinstance(expected_value, str):
            matches = actual_value.strip().casefold() == expected_value.strip().casefold()
        elif isinstance(actual_value, list) and isinstance(expected_value, list):
            matches = sorted(str(item).strip().casefold() for item in actual_value) == sorted(str(item).strip().casefold() for item in expected_value)
        else:
            matches = actual_value == expected_value
        if matches:
            correct += 1
    return correct, total


async def run():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        started = time.perf_counter()
        try:
            actual = None
            last_error = None
            for _ in range(3):
                try:
                    actual = await draft_extraction(case["source_text"])
                    break
                except Exception as exc:
                    last_error = exc
                    if type(exc).__name__ not in {"APIConnectionError", "APITimeoutError", "RateLimitError"}:
                        raise
            if actual is None:
                raise last_error
            correct, total = _field_accuracy(actual, case["expected_extraction"])
            assessment = score_change_request(actual)
            results.append({"case_id": case["case_id"], "success": True, "correct_fields": correct, "total_fields": total, "field_accuracy": round(correct / total, 3), "risk_level": assessment.risk_level.value, "expected_risk_level": case["expected_risk_level"], "risk_agreement": assessment.risk_level.value == case["expected_risk_level"], "latency_ms": round((time.perf_counter() - started) * 1000), "actual": actual.model_dump(mode="json")})
        except Exception as exc:
            results.append({"case_id": case["case_id"], "success": False, "error_type": type(exc).__name__, "latency_ms": round((time.perf_counter() - started) * 1000)})
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    successful = [item for item in results if item["success"]]
    total_fields = sum(item.get("total_fields", 0) for item in successful)
    correct_fields = sum(item.get("correct_fields", 0) for item in successful)
    output = {"case_count": len(cases), "successful_cases": len(successful), "field_accuracy": round(correct_fields / total_fields, 3) if total_fields else 0, "risk_agreement": round(sum(item.get("risk_agreement", False) for item in successful) / len(successful), 3) if successful else 0, "results": results}
    (RESULTS_DIR / "latest.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"case_count": output["case_count"], "successful_cases": output["successful_cases"], "field_accuracy": output["field_accuracy"], "risk_agreement": output["risk_agreement"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(run())