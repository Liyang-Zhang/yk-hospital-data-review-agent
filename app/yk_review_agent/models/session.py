from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


HospitalScopeMode = Literal["single", "all"]


class SessionCreateRequest(BaseModel):
    user_id: str
    hospital_id: str
    hospital_name: str | None = None
    host_session_id: str | None = None
    product_scope: str = "PGT-A"
    hospital_scope_mode: HospitalScopeMode = "single"
    accessible_hospital_ids: list[str] | None = None
    can_access_all_hospitals: bool = False


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
    hospital_scope_mode: HospitalScopeMode = "single"
    last_result_summary: str | None = None
    applied_filters: dict[str, str] = Field(default_factory=dict)
    last_analysis: LastAnalysisState | None = None


class SessionOverview(BaseModel):
    hospital_name: str
    product_scope: str = "PGT-A"
    hospital_scope_mode: HospitalScopeMode = "single"
    snapshot_start: str
    snapshot_end: str
    embryo_count: int = 0
    cycle_count: int = 0
    summary: str


class SessionRecord(BaseModel):
    session_id: str
    user_id: str
    hospital_id: str
    hospital_name: str | None = None
    hospital_scope_mode: HospitalScopeMode = "single"
    accessible_hospital_ids: list[str] | None = None
    can_access_all_hospitals: bool = False
    host_session_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    overview: SessionOverview | None = None
    context: SessionContext = Field(default_factory=SessionContext)
    messages: list[SessionMessage] = Field(default_factory=list)
