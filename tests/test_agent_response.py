from yk_review_agent.models.chat import ChatRequest, HostContext
from yk_review_agent.models.session import SessionCreateRequest
from yk_review_agent.services.agent import conversation_agent
from yk_review_agent.services.session_store import session_store

HOSPITAL_ID = "中国人民解放军医院301医院"


def test_structured_business_request_returns_task_and_capability_report() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session",
        )
    )
    request = ChatRequest(
        session_id=session.session_id,
        message=(
            "请帮我统计我们中心从2026年1月1日到2026年5月31日期间，所有PGT项目的数据，"
            "分别展示PGT-A、PGT-SR（含MARECS）、PGT-M的周期数、胚胎数、扩增成功率、NA率、"
            "整倍体率、异常率、嵌合率（仅嵌合）、意外发现率"
        ),
        host_context=HostContext(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session",
        ),
    )

    response = conversation_agent.handle(request, session)

    assert response.structured_answer.answer_mode == "refuse"
    assert response.analysis_task is not None
    assert response.analysis_task.kind == "structured_business_request"
    assert response.capability_report is not None
    assert any(product.product_code == "PGT-A" for product in response.capability_report.products)
    assert any(product.product_code == "PGT-SR" for product in response.capability_report.products)


def test_no_data_response_keeps_answer_mode_and_returns_data_readiness() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-2",
        )
    )
    request = ChatRequest(
        session_id=session.session_id,
        message="2024年 PGT-A 的整倍体率是多少？",
        host_context=HostContext(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-2",
        ),
    )

    response = conversation_agent.handle(request, session)

    assert response.structured_answer.answer_mode == "answer"
    assert response.data_readiness is not None
    assert response.data_readiness.status == "no_data"
    assert response.snapshot_metadata is not None


def test_clarify_response_returns_clarify_payload() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-3",
        )
    )
    request = ChatRequest(
        session_id=session.session_id,
        message="帮我分析一下",
        host_context=HostContext(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-3",
        ),
    )

    response = conversation_agent.handle(request, session)

    assert response.structured_answer.answer_mode == "clarify"
    assert response.clarify_payload is not None
    assert "主指标" in response.clarify_payload.missing_parts


def test_multiturn_followup_chain_preserves_context_and_switches_metric() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-4",
        )
    )
    host_context = HostContext(
        user_id="demo-user",
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
        host_session_id="host-session-4",
    )

    first = conversation_agent.handle(
        ChatRequest(session_id=session.session_id, message="看7月送检量", host_context=host_context),
        session,
    )
    assert first.structured_answer.answer_mode == "answer"
    assert first.structured_answer.metric_ids == ["pgt_total_volume"]
    assert first.route_trace is not None
    assert first.route_trace.filters["time_range"] == "7月"

    second = conversation_agent.handle(
        ChatRequest(session_id=session.session_id, message="那整倍体率呢", host_context=host_context),
        session_store.get_session(session.session_id),
    )
    assert second.structured_answer.answer_mode == "answer"
    assert second.structured_answer.metric_ids == ["pgta_euploid_rate"]
    assert second.route_trace is not None
    assert second.route_trace.filters["time_range"] == "7月"

    third = conversation_agent.handle(
        ChatRequest(session_id=session.session_id, message="那35岁以上呢", host_context=host_context),
        session_store.get_session(session.session_id),
    )
    assert third.structured_answer.answer_mode == "answer"
    assert third.structured_answer.metric_ids == ["pgta_euploid_rate"]
    assert third.route_trace is not None
    assert third.route_trace.filters["age_range"] == "gt:35"
    assert third.route_trace.filters["time_range"] == "7月"

    fourth = conversation_agent.handle(
        ChatRequest(session_id=session.session_id, message="那异常率呢", host_context=host_context),
        session_store.get_session(session.session_id),
    )
    assert fourth.structured_answer.answer_mode == "answer"
    assert fourth.structured_answer.metric_ids == ["pgta_mosaic_abnormal"]
    assert fourth.route_trace is not None
    assert fourth.route_trace.filters["age_range"] == "gt:35"
    assert fourth.route_trace.filters["time_range"] == "7月"


def test_multiturn_explicit_new_metric_overrides_previous_topic() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-5",
        )
    )
    host_context = HostContext(
        user_id="demo-user",
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
        host_session_id="host-session-5",
    )

    first = conversation_agent.handle(
        ChatRequest(session_id=session.session_id, message="看一下 PGT-A 的结果分布", host_context=host_context),
        session,
    )
    assert first.structured_answer.metric_ids == ["pgta_mosaic_abnormal"]

    second = conversation_agent.handle(
        ChatRequest(session_id=session.session_id, message="再看一下质控情况", host_context=host_context),
        session_store.get_session(session.session_id),
    )
    assert second.structured_answer.answer_mode == "answer"
    assert second.structured_answer.metric_ids == ["pgta_quality_overview"]
    assert second.route_trace is not None
    assert second.route_trace.resolved_metric_id == "pgta_quality_overview"


def test_special_cnv_oral_question_returns_special_cnv_result_card() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-special-cnv",
        )
    )
    host_context = HostContext(
        user_id="demo-user",
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
        host_session_id="host-session-special-cnv",
    )

    response = conversation_agent.handle(
        ChatRequest(
            session_id=session.session_id,
            message="想看一下意外发现里面那些1Mb到4Mb综合征相关提示多不多",
            host_context=host_context,
        ),
        session,
    )

    assert response.structured_answer.answer_mode == "answer"
    assert response.structured_answer.metric_ids == ["pgta_special_cnv_overview"]
    assert response.route_trace is not None
    assert response.route_trace.resolved_metric_id == "pgta_special_cnv_overview"
    assert any(card.title == "PGT-A 特殊 CNV 提示总览" for card in response.result_cards)


def test_special_cnv_ambiguous_question_clarifies() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id=HOSPITAL_ID,
            hospital_name="中国人民解放军医院301医院",
            host_session_id="host-session-special-cnv-clarify",
        )
    )
    host_context = HostContext(
        user_id="demo-user",
        hospital_id=HOSPITAL_ID,
        hospital_name="中国人民解放军医院301医院",
        host_session_id="host-session-special-cnv-clarify",
    )

    response = conversation_agent.handle(
        ChatRequest(
            session_id=session.session_id,
            message="4Mb到10Mb且高比例嵌合这类情况帮我汇总一下",
            host_context=host_context,
        ),
        session,
    )

    assert response.structured_answer.answer_mode == "clarify"
    assert response.clarify_payload is not None
    assert "主指标" in response.clarify_payload.missing_parts
