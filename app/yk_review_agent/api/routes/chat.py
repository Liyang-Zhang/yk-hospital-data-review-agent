from fastapi import APIRouter, HTTPException

from yk_review_agent.models.chat import ChatRequest, ChatResponse
from yk_review_agent.services.agent import conversation_agent
from yk_review_agent.services.session_store import session_store

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    session = session_store.get_session(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return conversation_agent.handle(payload, session)
