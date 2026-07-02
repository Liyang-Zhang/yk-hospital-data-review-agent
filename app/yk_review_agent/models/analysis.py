from typing import Literal

from pydantic import BaseModel, Field


AnswerMode = Literal["answer", "clarify", "refuse"]


class AnalysisPlan(BaseModel):
    product_scope: str
    metric_family: str | None = None
    breakdown: str = "overall"
    time_grain: str = "overall"
    filters: dict[str, str] = Field(default_factory=dict)
    answer_mode: AnswerMode
    rationale: str
    candidate_metric_ids: list[str] = Field(default_factory=list)
    normalized_message: str = ""
    clarification_question: str | None = None
    clarify_missing: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
