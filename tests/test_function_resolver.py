from yk_review_agent.models.intent import ParsedIntent
from yk_review_agent.services.function_resolver import function_resolver


def _parsed(*, breakdown: str = "overall", focus: str = "summary") -> ParsedIntent:
    return ParsedIntent(
        topic="测试",
        time_range="2025年",
        product_scope="PGT-A",
        breakdown=breakdown,
        focus=focus,
        normalized_message="",
    )


def test_cycle_outcome_has_priority_over_euploid_rate() -> None:
    resolution = function_resolver.resolve(
        message="看一下周期无整倍体率和周期整倍体结局",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_cycle_indicator_overview"
    assert resolution.candidate_metric_ids == ["pgta_cycle_indicator_overview"]


def test_special_cnv_has_priority_over_result_overview() -> None:
    resolution = function_resolver.resolve(
        message="看一下提示CNV和特殊 CNV 提示情况",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_special_cnv_overview"


def test_multi_topic_question_returns_multiple_candidates() -> None:
    resolution = function_resolver.resolve(
        message="看一下送检量和整倍体率",
        parsed=_parsed(),
    )

    assert resolution.metric_id is None
    assert resolution.candidate_metric_ids == ["pgta_euploid_rate", "pgt_total_volume"]


def test_age_breakdown_routes_to_age_distribution() -> None:
    resolution = function_resolver.resolve(
        message="换成年龄分层",
        parsed=_parsed(breakdown="age"),
    )

    assert resolution.metric_id == "pgta_age_distribution"
