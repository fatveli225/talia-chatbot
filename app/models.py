from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    name: str
    category: str
    price_fcfa: int
    stock: int
    description: str
    tags: List[str] = Field(default_factory=list)


class ChatMessageIn(BaseModel):
    session_id: str = Field(..., description="Identifiant de conversation (onglet web ou numéro WhatsApp)")
    message: str


class ProductCard(BaseModel):
    id: str
    name: str
    price_fcfa: int
    stock: int
    category: str


class ChatMessageOut(BaseModel):
    reply: str
    products: List[ProductCard] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)


class PaymentProvider(str):
    WAVE = "wave"
    ORANGE_MONEY = "orange_money"
    MTN_MOMO = "mtn_momo"


class PaymentInitRequest(BaseModel):
    session_id: str
    product_id: str
    quantity: int = 1
    provider: Literal["wave", "orange_money", "mtn_momo"]
    phone_number: str


class PaymentInitResponse(BaseModel):
    payment_id: str
    status: Literal["pending", "simulated"]
    provider: str
    amount_fcfa: int
    message: str
    checkout_url: Optional[str] = None
