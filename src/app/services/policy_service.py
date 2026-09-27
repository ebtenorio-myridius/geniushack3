"""Policy evidence retrieval.

Two retrieval paths, both returning the same PolicyEvidence shape so
callers and templates don't need to know which one ran:

1. Semantic (primary): if ai/policy_index.json exists (built offline by
   tools/embed_policies.py) and OPENAI_API_KEY is configured, embed the
   change request's own text and return the policy chunks with the
   highest cosine similarity. This is real retrieval over the governed
   policy corpus in /docs/policies — not a category lookup table — and is
   the "modelled, governed data layer" the brief asks for at this corpus
   size. It does not need a vector database: with a few dozen short
   policy chunks, an in-memory cosine-similarity scan is fast and exact.
   The migration path for a larger corpus is to swap _load_index()/
   _cosine_similarity() for a call to pgvector, Azure AI Search, or
   similar — the PolicyEvidence contract on the way out doesn't change.

2. Rule-based (fallback): a deterministic keyword/category match, used
   when the semantic index or API key isn't available — e.g. in CI, where
   no OPENAI_API_KEY secret is configured and tests must stay
   network-free and deterministic, or during a provider outage like the
   one documented in ops/monitoring.md. This mirrors the "fail loudly,
   then keep the workflow moving" philosophy already used in
   llm_service.py's extraction call.

`retrieval_method` on every returned item records which path produced it,
and `similarity_score` is populated for semantic matches — both exist so
an analyst or an examiner can see why a given policy was surfaced, per the
brief's "every rating traceable to its inputs and reasoning" requirement.

Known trade-off: the OpenAI call below is synchronous inside an async
FastAPI route (see routers/intake.py), which briefly blocks the event
loop. That's an acceptable trade at hackathon/demo request volume; a
production version should move this to a thread executor or an async
client, matching the pattern already used in llm_service.py.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from time import perf_counter

from openai import OpenAI

from src.app.config import settings
from src.app.models.schemas import ExtractedChangeRequest, PolicyEvidence, TelemetryRecord
from src.app.services.dependencies import case_store

_INDEX_PATH = Path(__file__).resolve().parents[3] / "ai" / "policy_index.json"
_EMBEDDING_MODEL = "text-embedding-3-small"
_TOP_K = 3
# Below this cosine similarity, treat it as "no relevant policy found"
# rather than force a low-quality match into the record.
_MIN_SIMILARITY = 0.15

_index_cache: dict | None = None


def _load_index() -> dict | None:
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    if not _INDEX_PATH.exists():
        return None
    _index_cache = json.loads(_INDEX_PATH.read_text())
    return _index_cache


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _request_query_text(request: ExtractedChangeRequest) -> str:
    parts = [
        f"Change type: {request.change_type.value}",
        f"Description: {request.description}",
    ]
    if request.geographies_involved:
        parts.append(f"Geographies: {', '.join(request.geographies_involved)}")
    if request.customer_segments_involved:
        parts.append(f"Customer segments: {', '.join(request.customer_segments_involved)}")
    if request.vendor_involved:
        parts.append(f"Vendor involved: {request.vendor_name or 'unnamed vendor'}")
    if request.products_involved:
        parts.append(f"Products: {', '.join(request.products_involved)}")
    if request.stated_risk_factors:
        parts.append(f"Stated risk factors: {', '.join(request.stated_risk_factors)}")
    return "\n".join(parts)


def _semantic_policy_evidence(request: ExtractedChangeRequest) -> list[PolicyEvidence] | None:
    """Returns None to mean "could not run semantic retrieval, caller
    should fall back" — distinct from returning [], which means "ran fine,
    nothing was relevant enough"."""
    index = _load_index()
    if not index or not settings.openai_api_key:
        return None

    started = perf_counter()
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=index.get("model", _EMBEDDING_MODEL),
            input=[_request_query_text(request)],
        )
        query_vector = response.data[0].embedding
    except Exception as exc:
        case_store.record_telemetry(TelemetryRecord(
            operation="policy_retrieval",
            model=_EMBEDDING_MODEL,
            prompt_version="policy_index_v1",
            latency_ms=round((perf_counter() - started) * 1000),
            success=False,
            error_type=type(exc).__name__,
        ))
        return None

    scored = [
        (_cosine_similarity(query_vector, chunk["embedding"]), chunk)
        for chunk in index["chunks"]
    ]
    scored = [pair for pair in scored if pair[0] >= _MIN_SIMILARITY]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    evidence = [
        PolicyEvidence(
            policy_id=chunk["policy_id"],
            title=chunk["title"],
            section=chunk["section"],
            excerpt=chunk["excerpt"],
            relevance=f"Semantic match (cosine similarity {score:.2f}) to the submitted change.",
            source_path=chunk["source_path"],
            similarity_score=round(score, 4),
            retrieval_method="semantic",
        )
        for score, chunk in scored[:_TOP_K]
    ]

    case_store.record_telemetry(TelemetryRecord(
        operation="policy_retrieval",
        model=_EMBEDDING_MODEL,
        prompt_version="policy_index_v1",
        latency_ms=round((perf_counter() - started) * 1000),
        success=True,
    ))
    return evidence


# --- Deterministic fallback -------------------------------------------------
# Used when the semantic index or API key isn't available. Keeps the app
# functional and keeps the test suite network-free and deterministic.

_FALLBACK_POLICIES = {
    "customer-risk": PolicyEvidence(
        policy_id="customer-risk-v1",
        title="Synthetic customer and geography risk guidance",
        section="Customer and geography exposure",
        excerpt="Assess customer segments, geography footprint, and cross-border exposure before launch.",
        relevance="Category rule match (semantic retrieval unavailable).",
        source_path="docs/policies/customer-risk.md",
        retrieval_method="rule_fallback",
    ),
    "third-party-risk": PolicyEvidence(
        policy_id="third-party-risk-v1",
        title="Synthetic third-party risk guidance",
        section="Vendor oversight",
        excerpt="Vendor involvement requires due diligence, monitoring, and documented accountability.",
        relevance="Category rule match (semantic retrieval unavailable).",
        source_path="docs/policies/third-party-risk.md",
        retrieval_method="rule_fallback",
    ),
    "product-risk": PolicyEvidence(
        policy_id="product-risk-v1",
        title="Synthetic product change risk guidance",
        section="New products and channels",
        excerpt="New products and channels require documented risk analysis before approval.",
        relevance="Category rule match (semantic retrieval unavailable).",
        source_path="docs/policies/product-risk.md",
        retrieval_method="rule_fallback",
    ),
}


def _rule_based_policy_evidence(request: ExtractedChangeRequest) -> list[PolicyEvidence]:
    evidence = []
    if request.change_type.value in {"new_product", "feature_change", "process_change"} or request.products_involved:
        evidence.append(_FALLBACK_POLICIES["product-risk"])
    if request.geographies_involved or request.customer_segments_involved:
        evidence.append(_FALLBACK_POLICIES["customer-risk"])
    if request.vendor_involved:
        evidence.append(_FALLBACK_POLICIES["third-party-risk"])
    return evidence


def find_policy_evidence(request: ExtractedChangeRequest) -> list[PolicyEvidence]:
    semantic_result = _semantic_policy_evidence(request)
    if semantic_result is not None:
        return semantic_result
    return _rule_based_policy_evidence(request)
