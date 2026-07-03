from pydantic import BaseModel, Field

from yk_review_agent.models.business_request import RequestedBusinessMetric


SUPPORTED_METRIC_IDS = {
    "pgt_total_volume",
    "pgta_euploid_rate",
    "pgta_age_distribution",
    "pgta_quality_overview",
    "pgta_mosaic_abnormal",
    "pgta_cycle_indicator_overview",
    "pgta_special_cnv_overview",
}


class FollowUpResolution(BaseModel):
    mode: str = "none"
    inherited_fields: list[str] = Field(default_factory=list)
    summary: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None


class ParsedIntent(BaseModel):
    request_kind: str = Field(
        default="single_metric",
        description="请求类型，可选 single_metric / structured_business_request。",
    )
    topic: str = Field(description="当前问题归一化后的主题名称。")
    metric_id: str = Field(
        default="",
        description="受控指标ID。仅允许 pgt_total_volume, pgta_euploid_rate, pgta_age_distribution, pgta_quality_overview, pgta_mosaic_abnormal, pgta_cycle_indicator_overview, pgta_special_cnv_overview。",
    )
    time_range: str = Field(
        default="当前快照全部时间",
        description="原问题中的时间范围表达，例如 2025年7月、2025年Q3、2025年7月15日。",
    )
    age_range: str | None = Field(
        default=None,
        description="年龄筛选范围，例如 lt:35、between:35,37、gt:35、gte:41、missing。",
    )
    product_scope: str = Field(
        default="PGT-A",
        description="当前产品范围。第一版只允许 PGT-A。",
    )
    breakdown: str = Field(
        default="overall",
        description="输出拆分维度，可选 overall/month/quarter/day/age/result/qc。",
    )
    focus: str = Field(
        default="summary",
        description="当前分析关注点，例如 trend/rate/distribution/summary。",
    )
    candidate_metric_ids: list[str] = Field(
        default_factory=list,
        description="候选指标族列表，用于后续 answerability policy 判断是否需要澄清。",
    )
    requested_products: list[str] = Field(default_factory=list)
    requested_metrics: list[RequestedBusinessMetric] = Field(default_factory=list)
    includes_marecs: bool = False
    has_explicit_time_range: bool = False
    has_explicit_product_scope: bool = False
    has_explicit_age_range: bool = False
    has_explicit_hospital_scope: bool = False
    requested_hospital_id: str | None = None
    normalized_message: str = Field(default="")
    follow_up_resolution: FollowUpResolution = Field(default_factory=FollowUpResolution)
    applied_filters: dict[str, str] = Field(default_factory=dict)
    unsupported_reason: str | None = Field(
        default=None,
        description="如果当前问题超出第一版范围，给出拒答原因；如果支持则为 null。",
    )
