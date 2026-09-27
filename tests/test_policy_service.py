import json

from src.app.models.schemas import ExtractedChangeRequest
from src.app.services import policy_service


def _request(**overrides):
    values = dict(
        change_title="Synthetic change",
        change_type="feature_change",
        business_unit="Consumer Banking",
        description="Synthetic change.",
        extraction_confidence=0.9,
    )
    values.update(overrides)
    return ExtractedChangeRequest(**values)


def test_policy_evidence_is_targeted_and_cited():
    """No ai/policy_index.json is committed for this to find in a fresh
    checkout/CI run, so this exercises the deterministic rule-based
    fallback — the same behavior the app has always had."""
    evidence = policy_service.find_policy_evidence(
        _request(
            change_type="vendor_onboarding",
            geographies_involved=["United States"],
            vendor_involved=True,
        )
    )
    policy_ids = {item.policy_id for item in evidence}
    assert policy_ids == {"customer-risk-v1", "third-party-risk-v1"}
    assert all(item.source_path.startswith("docs/policies/") for item in evidence)
    assert all(item.section and item.excerpt and item.relevance for item in evidence)
    assert all(item.retrieval_method == "rule_fallback" for item in evidence)


def test_policy_evidence_is_empty_for_unclassified_change():
    evidence = policy_service.find_policy_evidence(_request(change_type="other"))
    assert evidence == []


def test_semantic_retrieval_ranks_by_cosine_similarity(monkeypatch, tmp_path):
    """Exercises the real ranking logic (not the fallback) without making a
    network call, by injecting a tiny fake index and a stub embeddings
    client. Proves the similarity math and top-k selection work, since the
    live end-to-end path can only be verified with a real OPENAI_API_KEY
    (see tools/embed_policies.py and evals/ for that live check)."""
    fake_index = {
        "model": "text-embedding-3-small",
        "chunks": [
            {
                "policy_id": "customer-risk-v1",
                "title": "Synthetic customer and geography risk guidance",
                "section": "Geographic footprint",
                "excerpt": "Cross-border exposure and country risk.",
                "source_path": "docs/policies/customer-risk.md",
                "embedding": [1.0, 0.0, 0.0],
            },
            {
                "policy_id": "third-party-risk-v1",
                "title": "Synthetic third-party risk guidance",
                "section": "Vendor due diligence",
                "excerpt": "Vendor financial-crime controls and ownership.",
                "source_path": "docs/policies/third-party-risk.md",
                "embedding": [0.0, 1.0, 0.0],
            },
        ],
    }
    index_path = tmp_path / "policy_index.json"
    index_path.write_text(json.dumps(fake_index))
    monkeypatch.setattr(policy_service, "_INDEX_PATH", index_path)
    monkeypatch.setattr(policy_service, "_index_cache", None)
    monkeypatch.setattr(policy_service.settings, "openai_api_key", "test-key")

    # Route telemetry to a throwaway store so this test never touches the
    # developer's real risk_workbench.db.
    from src.app.services.case_store import CaseStore
    monkeypatch.setattr(policy_service, "case_store", CaseStore(str(tmp_path / "telemetry.db")))

    class _FakeEmbeddingItem:
        def __init__(self, embedding):
            self.embedding = embedding

    class _FakeEmbeddingResponse:
        def __init__(self, embedding):
            self.data = [_FakeEmbeddingItem(embedding)]

    class _FakeClient:
        def __init__(self, api_key=None):
            pass

        class embeddings:
            @staticmethod
            def create(model, input):
                # Deliberately closest to the vendor-risk chunk.
                return _FakeEmbeddingResponse([0.0, 0.9, 0.1])

    monkeypatch.setattr(policy_service, "OpenAI", _FakeClient)

    evidence = policy_service.find_policy_evidence(
        _request(vendor_involved=True, vendor_name="Acme Vendor")
    )

    assert evidence[0].policy_id == "third-party-risk-v1"
    assert evidence[0].retrieval_method == "semantic"
    assert evidence[0].similarity_score > 0.9


def test_semantic_retrieval_falls_back_below_similarity_floor(monkeypatch, tmp_path):
    """A query that doesn't resemble any indexed chunk should return no
    evidence rather than force a low-quality match."""
    fake_index = {
        "model": "text-embedding-3-small",
        "chunks": [
            {
                "policy_id": "customer-risk-v1",
                "title": "Synthetic customer and geography risk guidance",
                "section": "Geographic footprint",
                "excerpt": "Cross-border exposure and country risk.",
                "source_path": "docs/policies/customer-risk.md",
                "embedding": [1.0, 0.0, 0.0],
            },
        ],
    }
    index_path = tmp_path / "policy_index.json"
    index_path.write_text(json.dumps(fake_index))
    monkeypatch.setattr(policy_service, "_INDEX_PATH", index_path)
    monkeypatch.setattr(policy_service, "_index_cache", None)
    monkeypatch.setattr(policy_service.settings, "openai_api_key", "test-key")

    from src.app.services.case_store import CaseStore
    monkeypatch.setattr(policy_service, "case_store", CaseStore(str(tmp_path / "telemetry.db")))

    class _FakeEmbeddingItem:
        def __init__(self, embedding):
            self.embedding = embedding

    class _FakeEmbeddingResponse:
        def __init__(self, embedding):
            self.data = [_FakeEmbeddingItem(embedding)]

    class _FakeClient:
        def __init__(self, api_key=None):
            pass

        class embeddings:
            @staticmethod
            def create(model, input):
                # Orthogonal to the only indexed chunk -> similarity ~0.
                return _FakeEmbeddingResponse([0.0, 1.0, 0.0])

    monkeypatch.setattr(policy_service, "OpenAI", _FakeClient)

    evidence = policy_service.find_policy_evidence(_request())
    assert evidence == []
