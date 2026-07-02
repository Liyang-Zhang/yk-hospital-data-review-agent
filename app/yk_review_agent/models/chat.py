from typing import Literal

from pydantic import BaseModel, Field

from yk_review_agent.models.analysis import AnswerMode
from yk_review_agent.models.business_request import ProductCapability


class HostContext(BaseModel):
    user_id: str
    hospital_id: str
    hospital_name: str | None = None
    host_session_id: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)
    host_context: HostContext


class TablePayload(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str | int | float]]
    preview_rows: list[list[str | int | float]] | None = None
    total_rows: int | None = None
    has_more_rows: bool = False


class ChartSeries(BaseModel):
    name: str
    values: list[float]


class ChartPayload(BaseModel):
    title: str
    chart_type: Literal["bar", "line", "pie"] = "bar"
    categories: list[str]
    series: list[ChartSeries]


class ResultCard(BaseModel):
    type: Literal["summary", "table", "chart"]
    title: str
    content: str | None = None
    table: TablePayload | None = None
    chart: ChartPayload | None = None


class StructuredAnswer(BaseModel):
    answer_mode: AnswerMode
    presentation_mode: Literal["overview", "trend", "distribution", "detail_heavy"] = "overview"
    evidence_density: Literal["compact", "dense"] = "compact"
    topic: str
    rationale: str
    applied_filters: dict[str, str]
    metric_ids: list[str]
    warnings: list[str] = Field(default_factory=list)


class ClarifyPayload(BaseModel):
    title: str
    question: str
    missing_parts: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)


class AnalysisTaskStep(BaseModel):
    title: str
    status: Literal["completed", "clarify", "blocked"]
    detail: str | None = None


class AnalysisTask(BaseModel):
    kind: Literal["single_metric", "structured_business_request"]
    title: str
    status: Literal["completed", "clarify", "blocked"]
    steps: list[AnalysisTaskStep] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CapabilityReport(BaseModel):
    title: str
    summary: str
    products: list[ProductCapability] = Field(default_factory=list)


class SnapshotSourceSummary(BaseModel):
    product_code: str
    product_label: str
    data_source: str
    sheet_name: str
    row_count: int
    cycle_count: int
    snapshot_start: str | None = None
    snapshot_end: str | None = None
    semantic_fields: list[str] = Field(default_factory=list)
    execution_status: Literal["executable", "metadata_only"]
    notes: list[str] = Field(default_factory=list)


class SnapshotMetadata(BaseModel):
    mode: Literal["snapshot"] = "snapshot"
    data_source: str
    product_scope: str
    snapshot_start: str
    snapshot_end: str
    hospital_count: int
    registered_products: list[str] = Field(default_factory=list)
    source_summaries: list[SnapshotSourceSummary] = Field(default_factory=list)
    available_context: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DataReadinessReport(BaseModel):
    status: Literal["ready", "no_data", "unsupported"]
    summary: str
    record_count: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RouteTrace(BaseModel):
    raw_message: str
    normalized_message: str
    filters: dict[str, str] = Field(default_factory=dict)
    candidate_metric_ids: list[str] = Field(default_factory=list)
    resolved_metric_id: str | None = None
    answer_mode: AnswerMode
    rationale: str


class ChatResponse(BaseModel):
    assistant_text: str
    structured_answer: StructuredAnswer
    result_cards: list[ResultCard]
    follow_up_suggestions: list[str]
    clarify_payload: ClarifyPayload | None = None
    snapshot_metadata: SnapshotMetadata | None = None
    data_readiness: DataReadinessReport | None = None
    analysis_task: AnalysisTask | None = None
    capability_report: CapabilityReport | None = None
    route_trace: RouteTrace | None = None
    trace_id: str
