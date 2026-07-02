from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    user_id: str
    hospital_id: str
    hospital_name: str | None = None
    host_session_id: str | None = None


class SessionMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LastAnalysisState(BaseModel):
    metric_id: str
    topic: str
    breakdown: str
    time_grain: str
    filters: dict[str, str] = Field(default_factory=dict)
    product_scope: str
    presentation_mode: str = "overview"
    age_range: str | None = None


class SessionContext(BaseModel):
    current_topic: str | None = None
    time_range: str | None = None
    product_scope: str | None = None
    last_result_summary: str | None = None
    applied_filters: dict[str, str] = Field(default_factory=dict)
    last_analysis: LastAnalysisState | None = None


class SessionRecord(BaseModel):
    session_id: str
    user_id: str
    hospital_id: str
    hospital_name: str | None = None
    host_session_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    context: SessionContext = Field(default_factory=SessionContext)
    messages: list[SessionMessage] = Field(default_factory=list)
