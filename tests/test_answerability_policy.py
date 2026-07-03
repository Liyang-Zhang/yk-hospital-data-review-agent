from yk_review_agent.models.intent import ParsedIntent
from yk_review_agent.models.session import SessionContext
from yk_review_agent.services.answerability_policy import answerability_policy
from yk_review_agent.services.intent_parser import intent_parser_service

HOSPITAL_ID = "中国人民解放军医院301医院"
SHANXI_HOSPITAL_ID = "山西省妇幼保健院"


def _evaluate(
    message: str,
    *,
    hospital_id: str = HOSPITAL_ID,
    hospital_name: str | None = None,
    accessible_hospital_ids: list[str] | None = None,
    can_access_all_hospitals: bool = False,
):
    resolved_hospital_name = hospital_name or hospital_id
    parsed = intent_parser_service.parse(
        message=message,
        context=SessionContext(),
        hospital_id=hospital_id,
        hospital_name=resolved_hospital_name,
    )
    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=hospital_id,
        hospital_name=resolved_hospital_name,
        accessible_hospital_ids=accessible_hospital_ids,
        can_access_all_hospitals=can_access_all_hospitals,
    )
    return parsed, plan


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


def test_oral_volume_aliases_route_to_total_volume() -> None:
    message = "301这边2025年PGT-A周期量和胚胎量分别是多少"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert parsed.normalized_message.startswith("中国人民解放军医院301医院")
    assert parsed.time_range == "2025年"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgt_total_volume"


def test_oral_between_age_filter_routes_to_euploid_rate() -> None:
    message = "35 到 37 岁这批患者的PGT-A整倍体率怎么样"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert parsed.age_range == "between:35,37"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_euploid_rate"
    assert plan.filters["age_range"] == "between:35,37"


def test_oral_gte_age_filter_routes_to_euploid_rate() -> None:
    message = "41岁及以上患者这段时间整倍体率情况怎么样"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert parsed.age_range == "gte:41"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_euploid_rate"


def test_missing_age_generic_result_question_clarifies_without_candidates() -> None:
    message = "未填写年龄的这些样本，PGT-A结果怎么样"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id="山西省妇幼保健院",
        hospital_name="山西省妇幼保健院",
    )

    assert parsed.age_range == "missing"
    assert plan.answer_mode == "clarify"
    assert plan.candidate_metric_ids == []
    assert plan.filters["age_range"] == "missing"


def test_cycle_outcome_aliases_do_not_route_to_embryo_euploid_rate() -> None:
    message = "只有 1 个整倍体和大于等于 2 个整倍体的比例分别多少"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_cycle_indicator_overview"


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
    assert plan.candidate_metric_ids == ["pgt_total_volume", "pgta_euploid_rate"]


def test_oral_multi_metric_question_clarifies_with_age_filter_preserved() -> None:
    message = "山西妇幼在25年7月到10月年龄大于35岁的患者送了多少周期，整倍体率如何"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id="山西省妇幼保健院",
        hospital_name="山西省妇幼保健院",
    )

    assert parsed.normalized_message.startswith("山西省妇幼保健院")
    assert parsed.time_range == "2025年7月到2025年10月"
    assert parsed.age_range == "gt:35"
    assert plan.answer_mode == "clarify"
    assert plan.candidate_metric_ids == ["pgt_total_volume", "pgta_euploid_rate"]


def test_oral_special_cnv_question_answers() -> None:
    message = "想看一下意外发现里面那些1Mb到4Mb综合征相关提示多不多"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_special_cnv_overview"


def test_special_cnv_smoke_route_stays_on_special_cnv() -> None:
    message = "想单独看一下 CNV 提示，不看整体结果结构"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_special_cnv_overview"


def test_special_cnv_and_result_overview_conflict_clarifies() -> None:
    message = "4Mb到10Mb且高比例嵌合这类情况帮我汇总一下"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "clarify"
    assert plan.candidate_metric_ids == ["pgta_special_cnv_overview", "pgta_mosaic_abnormal"]


def test_explicit_other_hospital_without_permission_refuses() -> None:
    message = "301这边2025年PGT-A周期量和胚胎量分别是多少"
    parsed, plan = _evaluate(
        message,
        hospital_id=SHANXI_HOSPITAL_ID,
        hospital_name=SHANXI_HOSPITAL_ID,
    )

    assert parsed.requested_hospital_id == HOSPITAL_ID
    assert plan.answer_mode == "refuse"
    assert plan.metric_family is None
    assert SHANXI_HOSPITAL_ID in plan.rationale
    assert HOSPITAL_ID in plan.rationale


def test_explicit_current_hospital_stays_answerable() -> None:
    message = "山西妇幼2025年PGT-A周期量和胚胎量分别是多少"
    parsed, plan = _evaluate(
        message,
        hospital_id=SHANXI_HOSPITAL_ID,
        hospital_name=SHANXI_HOSPITAL_ID,
    )

    assert parsed.requested_hospital_id == SHANXI_HOSPITAL_ID
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgt_total_volume"
    assert plan.filters["hospital_id"] == SHANXI_HOSPITAL_ID


def test_no_explicit_hospital_defaults_to_host_hospital() -> None:
    message = "2025年PGT-A周期量和胚胎量分别是多少"
    parsed, plan = _evaluate(
        message,
        hospital_id=SHANXI_HOSPITAL_ID,
        hospital_name=SHANXI_HOSPITAL_ID,
    )

    assert parsed.requested_hospital_id is None
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgt_total_volume"
    assert plan.filters["hospital_id"] == SHANXI_HOSPITAL_ID


def test_accessible_hospital_ids_can_grant_cross_hospital_access() -> None:
    message = "301这边2025年PGT-A周期量和胚胎量分别是多少"
    parsed, plan = _evaluate(
        message,
        hospital_id=SHANXI_HOSPITAL_ID,
        hospital_name=SHANXI_HOSPITAL_ID,
        accessible_hospital_ids=[SHANXI_HOSPITAL_ID, HOSPITAL_ID],
    )

    assert parsed.requested_hospital_id == HOSPITAL_ID
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgt_total_volume"
    assert plan.filters["hospital_id"] == HOSPITAL_ID


def test_can_access_all_hospitals_allows_known_explicit_hospital() -> None:
    message = "301这边2025年PGT-A周期量和胚胎量分别是多少"
    parsed, plan = _evaluate(
        message,
        hospital_id=SHANXI_HOSPITAL_ID,
        hospital_name=SHANXI_HOSPITAL_ID,
        can_access_all_hospitals=True,
    )

    assert parsed.requested_hospital_id == HOSPITAL_ID
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgt_total_volume"
    assert plan.filters["hospital_id"] == HOSPITAL_ID


def test_unknown_explicit_hospital_refuses_as_dataset_missing() -> None:
    message = "火星医院2025年PGT-A周期量和胚胎量分别是多少"
    parsed, plan = _evaluate(
        message,
        hospital_id=SHANXI_HOSPITAL_ID,
        hospital_name=SHANXI_HOSPITAL_ID,
        can_access_all_hospitals=True,
    )

    assert parsed.requested_hospital_id == "火星医院"
    assert plan.answer_mode == "refuse"
    assert plan.metric_family is None
    assert "当前可访问的数据集不包含" in plan.rationale


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
