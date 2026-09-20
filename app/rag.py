"""
Moteur RAG (Retrieval-Augmented Generation) pour Talia.

Approche volontairement légère : pas de base vectorielle externe (Pinecone,
Chroma...) pour rester facile à faire tourner en local ou en démo, mais une
vraie étape de récupération sémantique via TF-IDF + similarité cosinus,
plutôt que d'injecter tout le catalogue dans le prompt à chaque message.

Pour un passage en production avec un catalogue de plusieurs milliers de
produits, remplacer `CatalogRetriever` par une implémentation basée sur des
embeddings (Voyage AI, OpenAI embeddings...) et une base vectorielle
(Chroma, pgvector, Pinecone). L'interface (`search`) resterait identique.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import Product


class CatalogRetriever:
    """Charge le catalogue produit et retrouve les articles pertinents pour une requête."""

    def __init__(self, catalog_path: Path):
        self.catalog_path = catalog_path
        self.products: List[Product] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._load()

    def _load(self) -> None:
        raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        self.products = [Product(**item) for item in raw]

        corpus = [self._document_text(p) for p in self.products]
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
        )
        self._matrix = self._vectorizer.fit_transform(corpus)

    @staticmethod
    def _document_text(product: Product) -> str:
        return " ".join(
            [
                product.name,
                product.category,
                product.description,
                " ".join(product.tags),
            ]
        )

    def search(self, query: str, top_k: int = 4) -> List[Product]:
        """Retourne les `top_k` produits les plus pertinents pour la requête."""
        if not query.strip():
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()

        ranked = sorted(
            zip(self.products, scores), key=lambda pair: pair[1], reverse=True
        )
        # On ne garde que les résultats avec un minimum de pertinence pour
        # éviter de renvoyer des produits sans rapport quand la requête est
        # hors-catalogue (ex: "bonjour").
        return [product for product, score in ranked[:top_k] if score > 0.03]

    def get_by_id(self, product_id: str) -> Product | None:
        return next((p for p in self.products if p.id == product_id), None)

    def all_categories(self) -> List[str]:
        return sorted({p.category for p in self.products})
