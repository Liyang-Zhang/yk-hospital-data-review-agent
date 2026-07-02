from yk_review_agent.models.intent import ParsedIntent
from yk_review_agent.models.session import SessionContext
from yk_review_agent.services.answerability_policy import answerability_policy
from yk_review_agent.services.intent_parser import intent_parser_service

HOSPITAL_ID = "中国人民解放军医院301医院"


def _parse(message: str) -> ParsedIntent:
    return intent_parser_service.parse(
        message=message,
        context=SessionContext(),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )


def test_weather_refuses() -> None:
    plan = answerability_policy.evaluate(
        message="天气如何",
        parsed=_parse("天气如何"),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "refuse"


def test_ambiguous_analysis_clarifies() -> None:
    plan = answerability_policy.evaluate(
        message="帮我分析一下",
        parsed=_parse("帮我分析一下"),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "clarify"
    assert plan.clarification_question is not None


def test_daily_volume_answers() -> None:
    plan = answerability_policy.evaluate(
        message="按天的维度去统计下的送检量",
        parsed=_parse("按天的维度去统计下的送检量"),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgt_total_volume"
    assert plan.breakdown == "day"


def test_qc_euploid_conflict_refuses() -> None:
    plan = answerability_policy.evaluate(
        message="按质控维度看整倍体率",
        parsed=_parse("按质控维度看整倍体率"),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "refuse"


def test_age_rate_answers() -> None:
    plan = answerability_policy.evaluate(
        message="按年龄分层看整倍体率",
        parsed=_parse("按年龄分层看整倍体率"),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_age_distribution"


def test_short_year_trend_maps_to_monthly_euploid_rate() -> None:
    message = "25年PGT-A整倍体率与时间趋势"
    parsed = _parse(message)
    assert parsed.time_range == "2025年"
    assert parsed.breakdown == "month"

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_euploid_rate"


def test_normalized_hospital_year_and_age_filter_are_parsed() -> None:
    parsed = _parse("山西妇幼在25年7月到10月>35岁患者的整倍体率")
    assert parsed.normalized_message.startswith("山西省妇幼保健院")
    assert parsed.time_range == "2025年7月到2025年10月"
    assert parsed.age_range == "gt:35"
    plan = answerability_policy.evaluate(
        message="山西妇幼在25年7月到10月>35岁患者的整倍体率",
        parsed=parsed,
        hospital_id="山西省妇幼保健院",
        hospital_name="山西省妇幼保健院",
    )
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_euploid_rate"


def test_multi_topic_question_clarifies_instead_of_picking_first_metric() -> None:
    message = "看一下送检量和整倍体率"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "clarify"
    assert plan.candidate_metric_ids == ["pgta_euploid_rate", "pgt_total_volume"]


def test_structured_business_request_without_scope_clarifies() -> None:
    message = "统计下PGT家系周期数、胚胎数、扩增成功率、NA率、整倍体率、异常率、嵌合率（仅嵌合）、意外发现率等数据"
    parsed = _parse(message)
    assert parsed.request_kind == "structured_business_request"
    assert parsed.has_explicit_product_scope is False
    assert parsed.has_explicit_time_range is False

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "clarify"
    assert "关键范围信息" in plan.rationale
    assert plan.clarification_question is not None


def test_structured_business_request_is_detected_and_refused_with_matrix() -> None:
    message = (
        "请帮我统计我们中心从2026年1月1日到2026年5月31日期间，所有PGT项目的数据，"
        "分别展示PGT-A SR(含marecs)PGT-M,包括PGT家系周期数、胚胎数、扩增成功率、NA率、"
        "整倍体率、异常率、嵌合率（仅嵌合）、意外发现率等"
    )
    parsed = _parse(message)
    assert parsed.request_kind == "structured_business_request"
    assert "PGT-A" in parsed.requested_products
    assert "PGT-SR" in parsed.requested_products
    assert "PGT-M" in parsed.requested_products
    assert parsed.has_explicit_product_scope is True
    assert parsed.has_explicit_time_range is True

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "refuse"
    assert "结构化业务统计任务单" in plan.rationale
    assert any("PGT-A 当前可支撑" in line for line in plan.warnings)
    assert any("PGT-SR（含 MARECS） 当前不支撑" in line for line in plan.warnings)
