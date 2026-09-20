from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.llm import TaliaAgent
from app.payments import PaymentGateway
from app.rag import CatalogRetriever
from app.routers import chat, payments, whatsapp


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    retriever = CatalogRetriever(settings.catalog_path)
    gateway = PaymentGateway()
    agent = TaliaAgent(retriever=retriever, payments=gateway)

    app.state.retriever = retriever
    app.state.payments = gateway
    app.state.agent = agent

    yield


app = FastAPI(
    title="Talia — Assistante commerciale IA",
    description=(
        "Backend de démonstration : chat web + webhook WhatsApp + RAG catalogue "
        "+ paiement Mobile Money (simulé), propulsé par l'API Claude."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(chat.router)
app.include_router(payments.router)
app.include_router(whatsapp.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "llm_configured": settings.llm_configured,
        "whatsapp_configured": settings.whatsapp_configured,
    }


@app.get("/")
def index():
    return FileResponse("app/static/index.html")
