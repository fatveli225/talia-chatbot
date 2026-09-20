from fastapi import APIRouter, Request

from app.models import ChatMessageIn, ChatMessageOut

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatMessageOut)
def send_message(payload: ChatMessageIn, request: Request) -> ChatMessageOut:
    agent = request.app.state.agent
    return agent.reply(session_id=payload.session_id, user_message=payload.message)
