"""
Passerelle de paiement Mobile Money.

⚠️ SIMULATION : ce module ne débite aucun compte réel. Il génère une réponse
crédible (identifiant de transaction, statut, lien de paiement fictif) pour
permettre de démontrer le parcours complet client → produit → paiement.

Pour passer en production, implémenter les méthodes `create_payment` de
chaque provider avec les vraies API :
  - Wave     : https://docs.wave.com/business
  - Orange Money : https://developer.orange.com/apis/om-webpay
  - MTN MoMo : https://momodeveloper.mtn.com

Chaque provider suit la même interface (`PaymentProviderBase`), donc changer
de simulation à réel ne touche que ce fichier.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.models import PaymentInitRequest, PaymentInitResponse, Product


class PaymentProviderBase(ABC):
    name: str

    @abstractmethod
    def create_payment(self, request: PaymentInitRequest, amount_fcfa: int) -> PaymentInitResponse:
        ...


class WaveProvider(PaymentProviderBase):
    name = "wave"

    def create_payment(self, request: PaymentInitRequest, amount_fcfa: int) -> PaymentInitResponse:
        # TODO (prod): POST https://api.wave.com/v1/checkout/sessions
        payment_id = f"wave_{uuid.uuid4().hex[:10]}"
        return PaymentInitResponse(
            payment_id=payment_id,
            status="simulated",
            provider=self.name,
            amount_fcfa=amount_fcfa,
            message=f"Lien de paiement Wave envoyé au {request.phone_number} (simulation).",
            checkout_url=f"https://pay.wave.com/simulate/{payment_id}",
        )


class OrangeMoneyProvider(PaymentProviderBase):
    name = "orange_money"

    def create_payment(self, request: PaymentInitRequest, amount_fcfa: int) -> PaymentInitResponse:
        # TODO (prod): POST https://api.orange.com/orange-money-webpay/{country}/v1/webpayment
        payment_id = f"om_{uuid.uuid4().hex[:10]}"
        return PaymentInitResponse(
            payment_id=payment_id,
            status="simulated",
            provider=self.name,
            amount_fcfa=amount_fcfa,
            message=f"Demande de paiement Orange Money envoyée au {request.phone_number} (simulation).",
            checkout_url=f"https://webpayment.orange.com/simulate/{payment_id}",
        )


class MTNMoMoProvider(PaymentProviderBase):
    name = "mtn_momo"

    def create_payment(self, request: PaymentInitRequest, amount_fcfa: int) -> PaymentInitResponse:
        # TODO (prod): POST https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay
        payment_id = f"momo_{uuid.uuid4().hex[:10]}"
        return PaymentInitResponse(
            payment_id=payment_id,
            status="simulated",
            provider=self.name,
            amount_fcfa=amount_fcfa,
            message=f"Requête MTN MoMo envoyée au {request.phone_number} (simulation).",
            checkout_url=None,
        )


class PaymentGateway:
    """Point d'entrée unique qui route vers le bon provider Mobile Money."""

    def __init__(self):
        self._providers: dict[str, PaymentProviderBase] = {
            "wave": WaveProvider(),
            "orange_money": OrangeMoneyProvider(),
            "mtn_momo": MTNMoMoProvider(),
        }

    def initiate(self, request: PaymentInitRequest, product: Product) -> PaymentInitResponse:
        provider = self._providers[request.provider]
        amount = product.price_fcfa * request.quantity
        return provider.create_payment(request, amount)
