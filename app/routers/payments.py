from fastapi import APIRouter, HTTPException, Request

from app.models import PaymentInitRequest, PaymentInitResponse

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentInitResponse)
def initiate_payment(payload: PaymentInitRequest, request: Request) -> PaymentInitResponse:
    retriever = request.app.state.retriever
    gateway = request.app.state.payments

    product = retriever.get_by_id(payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    return gateway.initiate(payload, product)
