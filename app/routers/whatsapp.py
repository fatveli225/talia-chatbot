"""
Webhook WhatsApp Cloud API (Meta).

Configuration côté Meta (App Meta for Developers > WhatsApp > Configuration) :
  - Callback URL : https://<ton-domaine-public>/webhook/whatsapp
  - Verify token : la valeur de WHATSAPP_VERIFY_TOKEN dans ton .env
  - Champs d'abonnement (webhook fields) : "messages"

En local, expose ton serveur avec un tunnel (ex: `ngrok http 8000`) pour
obtenir une URL publique HTTPS que Meta peut appeler.

Doc officielle : https://developers.facebook.com/docs/whatsapp/cloud-api
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Query, Request, Response

from app.config import get_settings

logger = logging.getLogger("talia.whatsapp")

router = APIRouter(prefix="/webhook/whatsapp", tags=["whatsapp"])


@router.get("")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """Étape de vérification exigée par Meta lors de la configuration du webhook."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("")
async def receive_message(request: Request):
    """Reçoit les événements entrants (messages, statuts...) de WhatsApp."""
    payload = await request.json()
    agent = request.app.state.agent
    settings = get_settings()

    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        messages = change.get("messages", [])
    except (KeyError, IndexError):
        # Statuts de livraison, accusés de lecture, etc. — rien à faire.
        return {"status": "ignored"}

    for message in messages:
        if message.get("type") != "text":
            continue
        from_number = message["from"]
        text = message["text"]["body"]

        result = agent.reply(session_id=f"whatsapp:{from_number}", user_message=text)
        await _send_whatsapp_message(settings, to=from_number, body=result.reply)

    return {"status": "ok"}


async def _send_whatsapp_message(settings, to: str, body: str) -> None:
    if not settings.whatsapp_configured:
        logger.warning(
            "WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID absents : "
            "message non envoyé (mode démo). Réponse Talia : %s", body,
        )
        return

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}"
        f"/{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, headers=headers, json=data)
        if response.status_code >= 400:
            logger.error("Échec envoi WhatsApp: %s %s", response.status_code, response.text)
