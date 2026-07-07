from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from yk_review_agent.models.session import SessionContext, SessionCreateRequest, SessionMessage, SessionRecord
from yk_review_agent.services.snapshot_service import snapshot_service


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(self, payload: SessionCreateRequest) -> SessionRecord:
        session_id = str(uuid4())
        hospital_name = payload.hospital_name or payload.hospital_id
        record = SessionRecord(
            session_id=session_id,
            user_id=payload.user_id,
            hospital_id=payload.hospital_id,
            hospital_name="全部医院" if payload.hospital_scope_mode == "all" else hospital_name,
            hospital_scope_mode=payload.hospital_scope_mode,
            accessible_hospital_ids=payload.accessible_hospital_ids,
            can_access_all_hospitals=payload.can_access_all_hospitals,
            host_session_id=payload.host_session_id,
            overview=snapshot_service.build_session_overview(
                payload.hospital_id,
                hospital_name,
                product_scope=payload.product_scope,
                hospital_scope_mode=payload.hospital_scope_mode,
            ),
            context=SessionContext(product_scope=payload.product_scope, hospital_scope_mode=payload.hospital_scope_mode),
        )
        self._sessions[session_id] = record
        return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def append_message(self, session_id: str, message: SessionMessage) -> SessionRecord:
        record = self._sessions[session_id]
        record.messages.append(message)
        record.updated_at = datetime.utcnow()
        return record

    def update_session(self, record: SessionRecord) -> SessionRecord:
        record.updated_at = datetime.utcnow()
        self._sessions[record.session_id] = record
        return record


session_store = InMemorySessionStore()
