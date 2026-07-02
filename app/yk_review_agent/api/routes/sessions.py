from fastapi import APIRouter, HTTPException

from yk_review_agent.models.session import SessionCreateRequest, SessionRecord
from yk_review_agent.services.session_store import session_store

router = APIRouter()


@router.post("/sessions", response_model=SessionRecord)
def create_session(payload: SessionCreateRequest) -> SessionRecord:
    return session_store.create_session(payload)


@router.get("/sessions/{session_id}", response_model=SessionRecord)
def get_session(session_id: str) -> SessionRecord:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
