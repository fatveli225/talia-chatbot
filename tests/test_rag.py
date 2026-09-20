from app.config import get_settings
from app.rag import CatalogRetriever


def _retriever() -> CatalogRetriever:
    settings = get_settings()
    return CatalogRetriever(settings.catalog_path)


def test_catalog_loads():
    retriever = _retriever()
    assert len(retriever.products) > 0


def test_search_returns_relevant_product():
    retriever = _retriever()
    results = retriever.search("panneau solaire")
    assert len(results) > 0
    assert any("solaire" in p.name.lower() for p in results)


def test_search_irrelevant_query_returns_nothing():
    retriever = _retriever()
    results = retriever.search("bonjour comment ça va")
    assert results == []


def test_get_by_id():
    retriever = _retriever()
    product = retriever.get_by_id("P001")
    assert product is not None
    assert "Disjoncteur" in product.name

    assert retriever.get_by_id("INEXISTANT") is None
