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
