"""
Cœur conversationnel de Talia.

Talia est un agent Claude avec deux outils (tool use / function calling) :
  - `search_catalog` : recherche RAG dans le catalogue produit (voir rag.py)
  - `initiate_payment` : déclenche un paiement Mobile Money simulé (voir payments.py)

Le même agent est utilisé par l'interface web (routers/chat.py) et par le
webhook WhatsApp (routers/whatsapp.py) : la logique métier ne dépend jamais
du canal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import anthropic

from app.config import get_settings
from app.models import ChatMessageOut, PaymentInitRequest, ProductCard
from app.payments import PaymentGateway
from app.rag import CatalogRetriever

MAX_TOOL_ITERATIONS = 4

TOOLS = [
    {
        "name": "search_catalog",
        "description": (
            "Recherche des produits dans le catalogue à partir d'une requête en "
            "langage naturel (ex: 'panneau solaire', 'quelque chose pour protéger "
            "mon tableau électrique'). Retourne les produits les plus pertinents "
            "avec prix, stock et description. À utiliser dès que le client mentionne "
            "un besoin, un type de produit, ou demande un prix."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Requête de recherche"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "initiate_payment",
        "description": (
            "Déclenche une demande de paiement Mobile Money pour un produit choisi "
            "par le client. À utiliser uniquement après confirmation explicite du "
            "client sur le produit, la quantité et le moyen de paiement souhaité."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "quantity": {"type": "integer", "minimum": 1},
                "provider": {
                    "type": "string",
                    "enum": ["wave", "orange_money", "mtn_momo"],
                },
                "phone_number": {
                    "type": "string",
                    "description": "Numéro de téléphone du client pour le paiement",
                },
            },
            "required": ["product_id", "quantity", "provider", "phone_number"],
        },
    },
]


def _system_prompt() -> str:
    settings = get_settings()
    return f"""Tu es Talia, l'assistante commerciale IA de {settings.business_name}, \
{settings.business_description}.

Ton rôle : accueillir les clients (sur le web ou WhatsApp), comprendre leur besoin, \
leur recommander les bons produits du catalogue, répondre à leurs questions techniques \
de base, et les accompagner jusqu'au paiement Mobile Money.

Règles importantes :
- Tu ne parles JAMAIS d'un produit ou d'un prix sans l'avoir d'abord recherché avec \
l'outil `search_catalog`. N'invente jamais un produit, un prix ou une disponibilité.
- Si le catalogue ne contient rien de pertinent, dis-le honnêtement et propose une \
alternative ou de contacter un conseiller humain.
- Sois chaleureuse, directe et efficace — le ton d'un bon vendeur de quartier, pas \
d'un robot. Des phrases courtes. Pas de jargon inutile.
- Avant de déclencher un paiement avec `initiate_payment`, récapitule toujours le \
produit, la quantité, le prix total et le moyen de paiement, et attends la confirmation \
explicite du client.
- Les prix sont en Francs CFA (FCFA).
- Réponds dans la langue du client (français par défaut).
"""


@dataclass
class ConversationState:
    history: List[dict] = field(default_factory=list)


class TaliaAgent:
    def __init__(self, retriever: CatalogRetriever, payments: PaymentGateway):
        self.retriever = retriever
        self.payments = payments
        self.settings = get_settings()
        self.client = (
            anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
            if self.settings.llm_configured
            else None
        )
        self._sessions: Dict[str, ConversationState] = {}

    def _get_session(self, session_id: str) -> ConversationState:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationState()
        return self._sessions[session_id]

    def _run_tool(self, name: str, tool_input: dict, session_id: str) -> tuple[str, List[ProductCard]]:
        """Exécute un outil et retourne (résultat texte pour Claude, produits trouvés)."""
        if name == "search_catalog":
            results = self.retriever.search(tool_input.get("query", ""))
            if not results:
                return "Aucun produit correspondant trouvé dans le catalogue.", []
            cards = [
                ProductCard(
                    id=p.id, name=p.name, price_fcfa=p.price_fcfa,
                    stock=p.stock, category=p.category,
                )
                for p in results
            ]
            lines = [
                f"- [{p.id}] {p.name} — {p.price_fcfa:,} FCFA — stock: {p.stock} — {p.description}".replace(",", " ")
                for p in results
            ]
            return "\n".join(lines), cards

        if name == "initiate_payment":
            request = PaymentInitRequest(
                session_id=session_id,
                product_id=tool_input["product_id"],
                quantity=int(tool_input.get("quantity", 1)),
                provider=tool_input["provider"],
                phone_number=tool_input["phone_number"],
            )
            product = self.retriever.get_by_id(request.product_id)
            if product is None:
                return f"Produit {request.product_id} introuvable.", []
            response = self.payments.initiate(request, product)
            return (
                f"Paiement initié: {response.status} — {response.message} "
                f"(réf: {response.payment_id})"
            ), []

        return f"Outil inconnu: {name}", []

    def reply(self, session_id: str, user_message: str) -> ChatMessageOut:
        if self.client is None:
            return ChatMessageOut(
                reply=(
                    "⚠️ Aucune clé ANTHROPIC_API_KEY n'est configurée côté serveur. "
                    "Ajoute-la dans ton fichier .env pour activer Talia (voir README)."
                ),
            )

        state = self._get_session(session_id)
        state.history.append({"role": "user", "content": user_message})

        all_products: List[ProductCard] = []
        final_text = ""

        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.client.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=1024,
                system=_system_prompt(),
                tools=TOOLS,
                messages=state.history,
            )

            # On réinjecte les blocs de contenu de la réponse tels quels dans
            # l'historique : le SDK Anthropic sait les sérialiser directement
            # pour le prochain appel (pattern recommandé pour le tool use).
            state.history.append({"role": "assistant", "content": response.content})

            text_blocks = [b.text for b in response.content if b.type == "text"]
            final_text = "\n".join(text_blocks) if text_blocks else final_text

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_text, products = self._run_tool(
                    block.name, block.input, session_id
                )
                all_products.extend(products)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    }
                )
            state.history.append({"role": "user", "content": tool_results})

        # Dédoublonne les produits (le même produit peut ressortir de plusieurs recherches)
        seen = set()
        unique_products = []
        for p in all_products:
            if p.id not in seen:
                seen.add(p.id)
                unique_products.append(p)

        return ChatMessageOut(
            reply=final_text or "Désolée, je n'ai pas de réponse à te proposer pour l'instant.",
            products=unique_products,
        )
