from datetime import datetime

import pytest

from yk_review_agent.services.pgta_detail_dataset import DetailRecord, get_pgta_dataset
from yk_review_agent.services.query_service import (
    _is_incidental_mosaic_cnv,
    _is_pseudoautosomal_deletion,
    _is_syndrome_micro_cnv,
    query_service,
)


BASE_FILTERS = {
    "hospital_id": "中国人民解放军医院301医院",
    "hospital_name": "中国人民解放军医院301医院",
}

pytestmark = pytest.mark.integration


def test_month_breakdown_returns_expected_shape() -> None:
    result = query_service.run(
        "pgta_euploid_rate",
        {**BASE_FILTERS, "time_range": "当前快照全部时间", "breakdown": "month", "focus": "trend"},
    )
    assert result["table"]["title"] == "PGT-A 分月份整倍体率"
    assert result["table"]["rows"]


def test_quarter_breakdown_returns_expected_shape() -> None:
    result = query_service.run(
        "pgt_total_volume",
        {**BASE_FILTERS, "time_range": "当前快照全部时间", "breakdown": "quarter", "focus": "trend"},
    )
    assert result["table"]["title"] == "按季度统计的 PGT-A 送检量"
    assert result["table"]["rows"]


def test_day_filter_is_applied() -> None:
    sample_day = get_pgta_dataset().eligible_records[0].created_at.strftime("%Y年%-m月%-d号")
    sample_day_key = get_pgta_dataset().eligible_records[0].created_at.strftime("%Y-%m-%d")
    result = query_service.run(
        "pgt_total_volume",
        {**BASE_FILTERS, "time_range": sample_day, "breakdown": "day", "focus": "summary"},
    )
    assert result["table"]["rows"]
    assert result["table"]["rows"][0][0] == sample_day_key
    assert result["evidence"]["status"] == "ready"


def test_result_overview_contains_incidental_and_aneuploid_metrics() -> None:
    result = query_service.run(
        "pgta_mosaic_abnormal",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )
    labels = [row[0] for row in result["table"]["rows"]]
    assert "意外发现胚胎数" in labels
    assert "异倍体胚胎数" in labels


def test_cycle_indicator_overview_uses_month_rows() -> None:
    result = query_service.run(
        "pgta_cycle_indicator_overview",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "month", "focus": "trend"},
    )
    assert result["table"]["title"] == "PGT-A 周期结局总览"
    assert result["table"]["rows"]
    assert str(result["table"]["rows"][0][0]).startswith("2025-")


def test_cycle_indicator_overview_supports_age_breakdown() -> None:
    result = query_service.run(
        "pgta_cycle_indicator_overview",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "age", "focus": "distribution"},
    )

    assert result["metric_id"] == "pgta_cycle_indicator_overview"
    assert result["table"]["columns"][0] == "年龄段"
    assert result["table"]["rows"]


def test_legacy_age_distribution_metric_aliases_to_euploid_age_breakdown() -> None:
    result = query_service.run(
        "pgta_age_distribution",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "age", "focus": "distribution"},
    )

    assert result["metric_id"] == "pgta_euploid_rate"
    assert result["table"]["title"] == "PGT-A 年龄分层整倍体率"


def test_special_cnv_overview_returns_expected_columns() -> None:
    result = query_service.run(
        "pgta_special_cnv_overview",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["columns"] == [
        "时间",
        "1Mb~4Mb 综合征相关提示",
        "4Mb~10Mb 且≥50%嵌合且综合征相关",
        "≥10Mb 且20%~30%嵌合",
        "拟常染色体区域缺失",
    ]


def test_special_cnv_rules_only_count_incidental_records() -> None:
    base = dict(
        created_at=datetime(2025, 1, 1),
        month_bucket="2025-01",
        cycle_id="cycle-1",
        task_name="cycle-1",
        sample_name="sample-1",
        sample_type="胚胎",
        hospital_name="test",
        hospital_code="test",
        product_name="PGT-A",
        description_cn="未见异常",
        description_en="",
        qc_conclusion="",
        ldpgta_qc_conclusion="",
        age=None,
        age_label="",
        mapd=None,
        bincv=None,
        cnvpq=None,
        cnv_type="",
        upd_arms="",
        result_detail="该区域包含已知综合征",
        aneuploidy_label="",
    )
    incidental = DetailRecord(
        **base,
        sample_id="sample-1",
        ldpgta_cnv_type="dup(1)(q21.1)(~1.20Mb); del(X)(p22.33)(~2.80Mb); del(4)(q26)(~12.00Mb,~25%)",
        incidental_label="有",
    )
    non_incidental = DetailRecord(
        **base,
        sample_id="sample-2",
        ldpgta_cnv_type="dup(1)(q21.1)(~1.20Mb); del(X)(p22.33)(~2.80Mb); del(4)(q26)(~12.00Mb,~25%)",
        incidental_label="无",
    )
    assert _is_syndrome_micro_cnv(incidental, 1, 4)
    assert _is_pseudoautosomal_deletion(incidental)
    assert _is_incidental_mosaic_cnv(incidental, 10, None, 20, 30, require_syndrome=False)
    assert not _is_syndrome_micro_cnv(non_incidental, 1, 4)
    assert not _is_pseudoautosomal_deletion(non_incidental)
    assert not _is_incidental_mosaic_cnv(non_incidental, 10, None, 20, 30, require_syndrome=False)


def test_special_cnv_rules_do_not_depend_on_result_label() -> None:
    item = DetailRecord(
        created_at=datetime(2025, 1, 1),
        month_bucket="2025-01",
        cycle_id="cycle-1",
        task_name="cycle-1",
        sample_id="sample-1",
        sample_name="sample-1",
        sample_type="胚胎",
        hospital_name="test",
        hospital_code="test",
        product_name="PGT-A",
        description_cn="未见异常",
        description_en="",
        qc_conclusion="",
        ldpgta_qc_conclusion="",
        age=None,
        age_label="",
        mapd=None,
        bincv=None,
        cnvpq=None,
        cnv_type="",
        upd_arms="",
        ldpgta_cnv_type="del(9)(p24.3p23)(~9.80Mb,~54%)",
        result_detail="该区域包含已知综合征",
        incidental_label="有",
        aneuploidy_label="",
    )
    assert _is_incidental_mosaic_cnv(item, 4, 10, 50, 100, require_syndrome=True)


def test_age_range_filter_is_applied_to_volume_metric() -> None:
    all_result = query_service.run(
        "pgt_total_volume",
        {**BASE_FILTERS, "time_range": "2025年7月到2025年10月", "breakdown": "overall", "focus": "summary"},
    )
    age_filtered_result = query_service.run(
        "pgt_total_volume",
        {
            **BASE_FILTERS,
            "time_range": "2025年7月到2025年10月",
            "breakdown": "overall",
            "focus": "summary",
            "age_range": "gt:35",
        },
    )
    assert all_result["evidence"]["record_count"] >= age_filtered_result["evidence"]["record_count"]


def test_age_range_filter_is_applied_to_euploid_metric() -> None:
    result = query_service.run(
        "pgta_euploid_rate",
        {
            **BASE_FILTERS,
            "time_range": "2025年",
            "breakdown": "month",
            "focus": "trend",
            "age_range": "missing",
        },
    )
    assert result["evidence"]["status"] == "ready"
