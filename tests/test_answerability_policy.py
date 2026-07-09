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
    context_product_scope: str | None = None,
    hospital_scope_mode: str = "single",
    accessible_hospital_ids: list[str] | None = None,
    can_access_all_hospitals: bool = False,
):
    resolved_hospital_name = hospital_name or hospital_id
    parsed = intent_parser_service.parse(
        message=message,
        context=SessionContext(product_scope=context_product_scope),
        hospital_id=hospital_id,
        hospital_name=resolved_hospital_name,
    )
    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=hospital_id,
        hospital_name=resolved_hospital_name,
        hospital_scope_mode=hospital_scope_mode,
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
    parsed = _parse("按年龄分层看整倍体率")
    plan = answerability_policy.evaluate(
        message="按年龄分层看整倍体率",
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert parsed.breakdown == "age"
    assert parsed.metric_id == "pgta_euploid_rate"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_euploid_rate"


def test_cycle_outcome_by_age_routes_to_cycle_metric_with_age_breakdown() -> None:
    message = "按年龄分层，从周期维度去看下整体结局"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id="山西省妇幼保健院",
        hospital_name="山西省妇幼保健院",
    )

    assert parsed.breakdown == "age"
    assert parsed.metric_id == "pgta_cycle_indicator_overview"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_cycle_indicator_overview"
    assert plan.candidate_metric_ids == ["pgta_cycle_indicator_overview"]


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


def test_quarterly_volume_trend_answers() -> None:
    message = "按季度看一下 PGT-A 的送检趋势"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id="山西省妇幼保健院",
        hospital_name="山西省妇幼保健院",
    )

    assert parsed.breakdown == "quarter"
    assert parsed.focus == "trend"
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


def test_cycle_angle_question_routes_to_cycle_indicator_overview() -> None:
    message = "从周期角度分析无整倍体胚胎率"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_cycle_indicator_overview"


def test_explicit_cycle_outcome_question_does_not_clarify() -> None:
    message = "看一下 PGT-A 的周期整倍体结局"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_cycle_indicator_overview"


def test_ambiguous_euploid_object_clarifies() -> None:
    message = "看一下无整倍体率"
    parsed = _parse(message)

    plan = answerability_policy.evaluate(
        message=message,
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert plan.answer_mode == "clarify"
    assert plan.clarify_missing == ["统计对象"]
    assert plan.candidate_metric_ids == ["pgta_euploid_rate", "pgta_cycle_indicator_overview"]


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
    assert any("PGT-SR（含 MARECS） 当前可支撑" in line for line in plan.warnings)


def test_pgtsr_volume_answers() -> None:
    message = "2025年 PGT-SR 送检量"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_total_volume"


def test_pgtsr_euploid_rate_answers() -> None:
    message = "2025年 PGT-SR 整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.metric_id == "pgtsr_euploid_rate"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"


def test_pgtsr_generic_age_filter_clarifies_age_scope() -> None:
    message = "2025年 PGT-SR >35岁患者整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.age_range == "gt:35"
    assert parsed.age_scope is None
    assert plan.answer_mode == "clarify"
    assert plan.clarify_missing == ["年龄对象"]


def test_pgtsr_patient_age_filter_answers() -> None:
    message = "2025年 PGT-SR 女方年龄>35岁整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.age_range == "gt:35"
    assert parsed.age_scope == "patient"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.filters["patient_age_range"] == "gt:35"


def test_pgtsr_female_age_breakdown_answers_as_patient_scope() -> None:
    message = "按女性年龄分层统计胚胎整倍体率"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "age"
    assert parsed.age_scope == "patient"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.filters["age_scope"] == "patient"


def test_pgtsr_age_breakdown_answers() -> None:
    message = "按年龄分层看一下 PGT-SR 整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "age"
    assert parsed.metric_id == "pgtsr_euploid_rate"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"


def test_pgtsr_next_step_answers() -> None:
    message = "看一下 PGT-SR 是否进入下一步易位筛查"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_next_step_overview"


def test_pgtsr_cycle_indicator_by_clinical_type_answers() -> None:
    message = "罗氏易位、平衡易位、倒位等不同 SR 患者的周期整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_clinical_type"
    assert parsed.sr_clinical_type is None
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_cycle_indicator_overview"
    assert "sr_clinical_type" not in plan.filters


def test_pgtsr_sr_type_embryo_euploid_answers() -> None:
    message = "罗氏易位、平衡易位、倒位等不同 SR 患者的胚胎整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_clinical_type"
    assert parsed.sr_clinical_type is None
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert "sr_clinical_type" not in plan.filters


def test_pgtsr_multiple_sr_types_keep_filter_when_not_asking_breakdown() -> None:
    message = "罗氏易位、平衡易位患者的胚胎整倍体率"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "overall"
    assert parsed.sr_clinical_types == ["平衡易位", "罗氏易位"]
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.breakdown == "sr_clinical_type"
    assert plan.filters["breakdown"] == "sr_clinical_type"
    assert plan.filters["sr_clinical_types"] == "平衡易位|罗氏易位"


def test_pgtsr_indication_alias_embryo_euploid_answers() -> None:
    message = "按适应症看一下 PGT-SR 整倍体胚胎占比"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_clinical_type"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"


def test_pgtsr_embryo_euploid_by_clinical_type_answers() -> None:
    message = "按临床指征看一下 PGT-SR 胚胎整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_clinical_type"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"


def test_pgtsr_translocation_pair_euploid_answers() -> None:
    message = "t(1;5) 的 PGT-SR 胚胎整倍体率是多少"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.metric_id == "pgtsr_euploid_rate"
    assert parsed.sr_translocation_pair == "t(1;5)"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.filters["sr_clinical_type"] == "平衡易位"
    assert plan.filters["sr_translocation_pair"] == "t(1;5)"


def test_pgtsr_translocation_pair_breakdown_answers() -> None:
    message = "按平衡易位类型看 PGT-SR 胚胎整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_translocation_pair"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.filters["sr_clinical_type"] == "平衡易位"


def test_pgtsr_balanced_translocation_different_types_answers() -> None:
    message = "平衡易位不同类型得胚胎整倍体率统计"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_translocation_pair"
    assert parsed.sr_translocation_pair is None
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.filters["sr_clinical_type"] == "平衡易位"


def test_pgtsr_translocation_pair_example_breakdown_answers_without_pair_filter() -> None:
    message = "按t(1;5)这类染色体对做总览分组"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_translocation_pair"
    assert parsed.sr_translocation_pair is None
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert "sr_translocation_pair" not in plan.filters
    assert plan.filters["sr_clinical_type"] == "平衡易位"


def test_pgtsr_specific_translocation_pair_type_answers_without_breakdown() -> None:
    message = "平衡易位中t(1;5)类型得胚胎整倍体率"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "overall"
    assert parsed.sr_translocation_pair == "t(1;5)"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.filters["sr_clinical_type"] == "平衡易位"
    assert plan.filters["sr_translocation_pair"] == "t(1;5)"


def test_pgtsr_this_kind_of_translocation_pair_answers_as_specific_filter() -> None:
    message = "平衡易位中t(1;5)这类平衡易位的胚胎整倍体率"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "overall"
    assert parsed.sr_translocation_pair == "t(1;5)"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"
    assert plan.filters["sr_clinical_type"] == "平衡易位"
    assert plan.filters["sr_translocation_pair"] == "t(1;5)"


def test_pgtsr_translocation_pair_with_month_refuses() -> None:
    message = "按月看一下 t(1;5) 的 PGT-SR 整倍体率变化"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.sr_translocation_pair == "t(1;5)"
    assert parsed.breakdown == "month"
    assert plan.answer_mode == "refuse"
    assert "暂不支持" in plan.rationale


def test_non_pgtsr_translocation_pair_refuses() -> None:
    message = "看一下 PGT-A 里 t(1;5) 的整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-A"
    assert parsed.sr_translocation_pair == "t(1;5)"
    assert plan.answer_mode == "refuse"
    assert "仅支持 PGT-SR" in plan.rationale


def test_pgtsr_embryo_euploid_situation_answers_without_clarify() -> None:
    message = "看一下 PGT-SR 的胚胎整倍体情况"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.metric_id == "pgtsr_euploid_rate"
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgtsr_euploid_rate"


def test_pgtsr_clinical_type_euploid_without_object_clarifies() -> None:
    message = "按临床指征看一下 PGT-SR 整倍体率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert parsed.breakdown == "sr_clinical_type"
    assert plan.answer_mode == "clarify"
    assert plan.clarify_missing == ["统计对象"]
    assert plan.candidate_metric_ids == ["pgtsr_euploid_rate", "pgtsr_cycle_indicator_overview"]
    assert plan.clarification_question == "这次你想看胚胎层面的整倍体率，还是周期层面的整倍体结局？"
    assert "按临床指征看一下 PGT-SR 胚胎整倍体率" in plan.suggestions
    assert "按临床指征看一下 PGT-SR 周期结局" in plan.suggestions


def test_pgtsr_workspace_broad_embryo_question_clarifies_with_pgtsr_only_suggestions() -> None:
    message = "25年7月的胚胎整体情况"
    parsed, plan = _evaluate(message, context_product_scope="PGT-SR")

    assert parsed.product_scope == "PGT-SR"
    assert parsed.time_range == "2025年7月"
    assert plan.answer_mode == "clarify"
    assert plan.clarify_missing == ["主指标"]
    assert plan.clarification_question == "请先明确你想看的 PGT-SR 指标，例如送检量、胚胎整倍体率、质控情况、结果分布或周期结局。"
    assert plan.suggestions
    assert all("PGT-A" not in suggestion for suggestion in plan.suggestions)
    assert "看一下 PGT-SR 结果分布" in plan.suggestions
    assert "看一下 PGT-SR 的胚胎整倍体率" in plan.suggestions


def test_pgtsr_marecs_stage2_refuses() -> None:
    message = "看一下 PGT-SR MaReCs 第二阶段不携带率"
    parsed, plan = _evaluate(message)

    assert parsed.product_scope == "PGT-SR"
    assert plan.answer_mode == "refuse"
    assert "MaReCs 第二阶段" in plan.rationale


def test_all_hospitals_scope_answers_without_hospital_filter() -> None:
    parsed, plan = _evaluate(
        "2025年 PGT-SR 送检量",
        hospital_id="__ALL_HOSPITALS__",
        hospital_name="全部医院",
        hospital_scope_mode="all",
        can_access_all_hospitals=True,
    )

    assert parsed.product_scope == "PGT-SR"
    assert plan.answer_mode == "answer"
    assert plan.filters["hospital_scope_mode"] == "all"
    assert "hospital_id" not in plan.filters


def test_all_hospitals_scope_requires_permission() -> None:
    _, plan = _evaluate(
        "2025年 PGT-A 送检量",
        hospital_id="__ALL_HOSPITALS__",
        hospital_name="全部医院",
        hospital_scope_mode="all",
        can_access_all_hospitals=False,
    )

    assert plan.answer_mode == "refuse"
    assert "全部医院的数据权限" in plan.rationale
