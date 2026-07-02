from yk_review_agent.models.session import LastAnalysisState, SessionContext
from yk_review_agent.services.answerability_policy import answerability_policy
from yk_review_agent.services.intent_parser import intent_parser_service

HOSPITAL_ID = "中国人民解放军医院301医院"


def test_followup_inherits_metric_for_breakdown_only_question() -> None:
    context = SessionContext(
        current_topic="PGT-A 整倍体率",
        time_range="2025年7月",
        product_scope="PGT-A",
        last_result_summary="已返回 2025年7月的 PGT-A 整倍体率。",
        last_analysis=LastAnalysisState(
            metric_id="pgta_euploid_rate",
            topic="PGT-A 整倍体率",
            breakdown="month",
            time_grain="month",
            filters={"time_range": "2025年7月", "hospital_id": HOSPITAL_ID, "breakdown": "month"},
            product_scope="PGT-A",
            presentation_mode="trend",
        ),
    )
    parsed = intent_parser_service.parse(
        message="按季度看呢",
        context=context,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert parsed.metric_id == "pgta_euploid_rate"
    assert parsed.breakdown == "quarter"
    assert parsed.time_range == "2025年7月"
    assert "metric_id" in parsed.follow_up_resolution.inherited_fields
    assert "time_range" in parsed.follow_up_resolution.inherited_fields
    plan = answerability_policy.evaluate(
        message="按季度看呢",
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "answer"


def test_followup_inherits_time_for_metric_switch_question() -> None:
    parsed = intent_parser_service.parse(
        message="那整倍体率呢",
        context=SessionContext(
            current_topic="PGT-A 送检量",
            time_range="2025年7月",
            product_scope="PGT-A",
            last_result_summary="已返回 2025年7月的 PGT-A 送检量。",
            last_analysis=LastAnalysisState(
                metric_id="pgt_total_volume",
                topic="PGT-A 送检量",
                breakdown="month",
                time_grain="month",
                filters={"time_range": "2025年7月", "hospital_id": HOSPITAL_ID, "breakdown": "month"},
                product_scope="PGT-A",
                presentation_mode="trend",
            ),
        ),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert parsed.time_range == "2025年7月"
    assert "time_range" in parsed.follow_up_resolution.inherited_fields
    plan = answerability_policy.evaluate(
        message="那整倍体率呢",
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_euploid_rate"


def test_followup_inherits_metric_for_age_filter_followup() -> None:
    parsed = intent_parser_service.parse(
        message="那35岁以上呢",
        context=SessionContext(
            current_topic="PGT-A 整倍体率",
            time_range="2025年7月到2025年10月",
            product_scope="PGT-A",
            last_result_summary="已返回 2025年7月到2025年10月的 PGT-A 整倍体率。",
            last_analysis=LastAnalysisState(
                metric_id="pgta_euploid_rate",
                topic="PGT-A 整倍体率",
                breakdown="month",
                time_grain="month",
                filters={"time_range": "2025年7月到2025年10月", "hospital_id": HOSPITAL_ID, "breakdown": "month"},
                product_scope="PGT-A",
                presentation_mode="trend",
            ),
        ),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert parsed.metric_id == "pgta_euploid_rate"
    assert parsed.age_range == "gt:35"
    assert "metric_id" in parsed.follow_up_resolution.inherited_fields
    plan = answerability_policy.evaluate(
        message="那35岁以上呢",
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "answer"
    assert plan.metric_family == "pgta_euploid_rate"


def test_followup_without_actionable_metric_clarifies() -> None:
    parsed = intent_parser_service.parse(
        message="那呢",
        context=SessionContext(
            current_topic="PGT-A 送检量",
            time_range="2025年7月",
            product_scope="PGT-A",
            last_result_summary="已返回 2025年7月的 PGT-A 送检量。",
            last_analysis=LastAnalysisState(
                metric_id="pgt_total_volume",
                topic="PGT-A 送检量",
                breakdown="month",
                time_grain="month",
                filters={"time_range": "2025年7月", "hospital_id": HOSPITAL_ID, "breakdown": "month"},
                product_scope="PGT-A",
                presentation_mode="trend",
            ),
        ),
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )

    assert parsed.follow_up_resolution.needs_clarification is True
    plan = answerability_policy.evaluate(
        message="那呢",
        parsed=parsed,
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
    )
    assert plan.answer_mode == "clarify"
    assert plan.clarification_question is not None
