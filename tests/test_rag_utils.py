import asyncio
import time


def test_embedding_to_pgvector_str():
    from shared.embedding_generator import embedding_to_pgvector_str

    s = embedding_to_pgvector_str([1.0, 2.5, -3.0])
    assert s == "[1.0,2.5,-3.0]"


def test_normalise_intent_dict_ambiguities_shape():
    from containers.os.clarity_agent.schema_builder import normalise_intent_dict

    out = normalise_intent_dict(
        {
            "intent_id": "create_sales_order",
            "target_doctype": "Sales Order",
            "ambiguities": ["Please provide items"],
            "entities": {"items": None},
        },
        prompt="Create SO",
        erp_type="erpnext",
        session_context=[],
    )

    assert isinstance(out["ambiguities"], list)
    assert isinstance(out["ambiguities"][0], dict)
    assert out["ambiguities"][0]["question"] == "Please provide items"
    assert out["has_ambiguities"] is True
    assert isinstance(out["entities"]["items"], list)


def test_inmemory_ttl_cache_expires():
    from shared.rag_cache import InMemoryTTLCache

    cache = InMemoryTTLCache()

    async def _run():
        await cache.set("k", "v", ttl_s=1)
        assert await cache.get("k") == "v"
        time.sleep(1.2)
        assert await cache.get("k") is None

    asyncio.run(_run())

