from __future__ import annotations

from pathlib import Path

import pytest

from yk_review_agent.core.config import settings
from yk_review_agent.models.chat import ChatRequest, HostContext
from yk_review_agent.models.session import SessionCreateRequest
from yk_review_agent.services.agent import conversation_agent
from yk_review_agent.services.pgta_detail_dataset import get_pgta_dataset
from yk_review_agent.services.product_snapshot_registry import get_snapshot_registry
from yk_review_agent.services.query_service import query_service
from yk_review_agent.services.question_normalizer import question_normalizer
from yk_review_agent.services.session_store import session_store


ORACLE_SNAPSHOT = Path("tests/fixtures/snapshots/pgta-shanxi-oracle.xlsx").resolve()
HOSPITAL_ID = "山西省妇幼保健院"
BASE_FILTERS = {
    "hospital_id": HOSPITAL_ID,
    "hospital_name": HOSPITAL_ID,
}


@pytest.fixture()
def use_pgta_oracle_snapshot() -> None:
    original_pgta_file = settings.pgta_detail_file
    settings.pgta_detail_file = str(ORACLE_SNAPSHOT)
    get_pgta_dataset.cache_clear()
    get_snapshot_registry.cache_clear()
    question_normalizer._hospital_alias_map = None
    yield
    settings.pgta_detail_file = original_pgta_file
    get_pgta_dataset.cache_clear()
    get_snapshot_registry.cache_clear()
    question_normalizer._hospital_alias_map = None


def test_pgta_volume_matches_oracle_for_2025(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgt_total_volume",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"] == [["总体", 954, 2681, "2.81"]]


def test_pgta_volume_matches_oracle_for_jul_to_oct(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgt_total_volume",
        {**BASE_FILTERS, "time_range": "2025年7月到2025年10月", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"] == [["总体", 328, 926, "2.82"]]


def test_pgta_euploid_rate_matches_oracle_for_2025(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_euploid_rate",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"] == [["总体", 2681, 1359, "50.7%"]]


def test_pgta_euploid_rate_matches_oracle_for_jul_to_oct(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_euploid_rate",
        {**BASE_FILTERS, "time_range": "2025年7月到2025年10月", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"] == [["总体", 926, 471, "50.9%"]]


def test_pgta_euploid_rate_matches_oracle_for_gt_35(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_euploid_rate",
        {
            **BASE_FILTERS,
            "time_range": "2025年7月到2025年10月",
            "breakdown": "overall",
            "focus": "summary",
            "age_range": "gt:35",
        },
    )
    assert result["table"]["rows"] == [["总体", 585, 255, "43.6%"]]


def test_pgta_euploid_rate_matches_oracle_for_35_to_37_bucket(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_euploid_rate",
        {
            **BASE_FILTERS,
            "time_range": "2025年7月到2025年10月",
            "breakdown": "overall",
            "focus": "summary",
            "age_range": "between:35,37",
        },
    )
    assert result["table"]["rows"] == [["总体", 345, 179, "51.9%"]]


def test_pgta_age_distribution_matches_oracle(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_age_distribution",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "age", "focus": "distribution"},
    )
    assert result["table"]["rows"] == [
        ["＜35岁", 323, 1040, 642, "61.7%"],
        ["35-38岁", 341, 990, 524, "52.9%"],
        ["＞38岁", 288, 649, 193, "29.7%"],
        ["未填写", 2, 2, 0, "0.0%"],
    ]


def test_pgta_quality_overview_matches_oracle(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_quality_overview",
        {**BASE_FILTERS, "time_range": "2025年7月到2025年10月", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"][:8] == [
        ["检测周期数", 328],
        ["检测胚胎数", 926],
        ["平均囊胚数", "2.82"],
        ["检测成功率", "98.6%"],
        ["NA胚胎数", 13],
        ["PASS样本数", 823],
        ["INFO样本数", 90],
        ["FAIL样本数", 13],
    ]


def test_pgta_cycle_indicator_overview_matches_oracle(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_cycle_indicator_overview",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"] == [["总体", 954, "69.6%", "30.4%", "8.2%", "28.9%", "40.7%"]]


def test_pgta_mosaic_abnormal_matches_oracle_for_jul_to_oct(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_mosaic_abnormal",
        {**BASE_FILTERS, "time_range": "2025年7月到2025年10月", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"] == [
        ["整倍体胚胎数", 471, "50.9%"],
        ["仅嵌合胚胎数", 120, "13.0%"],
        ["异常胚胎数", 322, "34.8%"],
        ["异倍体胚胎数", 10, "1.1%"],
        ["意外发现胚胎数", 36, "3.9%"],
    ]


def test_pgta_mosaic_abnormal_matches_oracle_for_2025_incidental_rate(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_mosaic_abnormal",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["rows"] == [
        ["整倍体胚胎数", 1359, "50.7%"],
        ["仅嵌合胚胎数", 334, "12.5%"],
        ["异常胚胎数", 964, "36.0%"],
        ["异倍体胚胎数", 55, "2.1%"],
        ["意外发现胚胎数", 120, "4.5%"],
    ]


def test_pgta_result_distribution_matches_oracle_for_jul_to_oct(use_pgta_oracle_snapshot: None) -> None:
    result = query_service.run(
        "pgta_mosaic_abnormal",
        {**BASE_FILTERS, "time_range": "2025年7月到2025年10月", "breakdown": "result", "focus": "distribution"},
    )
    assert result["table"]["rows"] == [
        ["未见异常", 471, "50.9%"],
        ["嵌合异常", 120, "13.0%"],
        ["异常", 322, "34.8%"],
        ["质控不合格", 13, "1.4%"],
    ]


def test_route_trace_matches_oracle_question_for_jul_to_oct_euploid_rate(use_pgta_oracle_snapshot: None) -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="oracle-user",
            hospital_id=HOSPITAL_ID,
            hospital_name=HOSPITAL_ID,
            host_session_id="oracle-host-1",
        )
    )
    response = conversation_agent.handle(
        ChatRequest(
            session_id=session.session_id,
            message="统计下 2025 年 7 月到 10 月的整倍体率情况",
            host_context=HostContext(
                user_id="oracle-user",
                hospital_id=HOSPITAL_ID,
                hospital_name=HOSPITAL_ID,
                host_session_id="oracle-host-1",
            ),
        ),
        session,
    )
    assert response.route_trace is not None
    assert response.route_trace.normalized_message == "统计下 2025年7月到2025年10月的整倍体率情况"
    assert response.route_trace.resolved_metric_id == "pgta_euploid_rate"
    assert response.route_trace.filters["hospital_id"] == HOSPITAL_ID
    assert response.route_trace.filters["time_range"] == "2025年7月到2025年10月"
    assert response.route_trace.answer_mode == "answer"
    assert response.result_cards[0].content == "当前快照下，PGT-A 共检测 926 个胚胎，其中整倍体 471 个，整倍体率为 50.9%。"


def test_route_trace_matches_oracle_question_for_gt_35(use_pgta_oracle_snapshot: None) -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="oracle-user",
            hospital_id=HOSPITAL_ID,
            hospital_name=HOSPITAL_ID,
            host_session_id="oracle-host-2",
        )
    )
    response = conversation_agent.handle(
        ChatRequest(
            session_id=session.session_id,
            message="想看下高龄患者这边的整倍体率，大于 35 岁这一组",
            host_context=HostContext(
                user_id="oracle-user",
                hospital_id=HOSPITAL_ID,
                hospital_name=HOSPITAL_ID,
                host_session_id="oracle-host-2",
            ),
        ),
        session,
    )
    assert response.route_trace is not None
    assert response.route_trace.resolved_metric_id == "pgta_euploid_rate"
    assert response.route_trace.filters["age_range"] == "gt:35"
    assert response.route_trace.answer_mode == "answer"
    assert response.result_cards[0].content == "当前快照下，PGT-A 共检测 1639 个胚胎，其中整倍体 717 个，整倍体率为 43.7%。"
