from datetime import datetime

import pytest

from yk_review_agent.services.pgta_detail_dataset import DetailRecord
from yk_review_agent.services.pgta_record_source import get_pgta_record_source
from yk_review_agent.services.pgtsr_record_source import get_pgtsr_record_source
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
    sample_day = get_pgta_record_source().eligible_records[0].created_at.strftime("%Y年%-m月%-d号")
    sample_day_key = get_pgta_record_source().eligible_records[0].created_at.strftime("%Y-%m-%d")
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


def test_pgtsr_volume_returns_expected_shape() -> None:
    result = query_service.run(
        "pgtsr_total_volume",
        {**BASE_FILTERS, "time_range": "当前快照全部时间", "breakdown": "month", "focus": "trend"},
    )

    assert result["table"]["title"].startswith("按月份统计的 PGT-SR")
    assert result["table"]["rows"]


def test_pgtsr_euploid_rate_returns_expected_shape() -> None:
    result = query_service.run(
        "pgtsr_euploid_rate",
        {**BASE_FILTERS, "time_range": "当前快照全部时间", "breakdown": "month", "focus": "trend"},
    )

    assert result["metric_id"] == "pgtsr_euploid_rate"
    assert result["table"]["title"] == "PGT-SR 分月份整倍体率"
    assert result["table"]["rows"]


def test_pgtsr_euploid_rate_supports_age_breakdown() -> None:
    result = query_service.run(
        "pgtsr_euploid_rate",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "age", "focus": "distribution"},
    )

    assert result["metric_id"] == "pgtsr_euploid_rate"
    assert result["table"]["title"] == "PGT-SR 双年龄分层整倍体率"
    assert result["table"]["columns"][:2] == ["年龄对象", "年龄段"]
    assert result["table"]["rows"]


def test_pgtsr_euploid_rate_respects_patient_age_scope_for_breakdown() -> None:
    result = query_service.run(
        "pgtsr_euploid_rate",
        {
            **BASE_FILTERS,
            "time_range": "2025年",
            "breakdown": "age",
            "focus": "distribution",
            "age_scope": "patient",
        },
    )

    assert result["metric_id"] == "pgtsr_euploid_rate"
    assert result["table"]["title"] == "PGT-SR 女方年龄分层整倍体率"
    assert result["chart"]["title"] == "PGT-SR 女方年龄分层整倍体率"
    assert result["table"]["rows"]
    assert all(row[0] == "女方" for row in result["table"]["rows"])


def test_pgtsr_euploid_rate_supports_sr_clinical_type_breakdown() -> None:
    result = query_service.run(
        "pgtsr_euploid_rate",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "sr_clinical_type", "focus": "distribution"},
    )

    assert result["metric_id"] == "pgtsr_euploid_rate"
    assert result["table"]["title"] == "PGT-SR 临床指征分层整倍体率"
    assert result["table"]["columns"][0] == "临床指征"
    assert result["table"]["rows"]
    assert len(result["table"]["rows"]) > 1
    assert all(row[0] != "总体" for row in result["table"]["rows"])
    assert "胚胎层面" in result["summary"]


def test_pgtsr_euploid_rate_supports_translocation_pair_breakdown() -> None:
    result = query_service.run(
        "pgtsr_euploid_rate",
        {
            "time_range": "当前快照全部时间",
            "breakdown": "sr_translocation_pair",
            "focus": "distribution",
            "sr_clinical_type": "平衡易位",
        },
    )

    assert result["metric_id"] == "pgtsr_euploid_rate"
    assert result["table"]["title"] == "PGT-SR 平衡易位类型分层整倍体率"
    assert result["table"]["columns"][0] == "易位类型"
    assert result["table"]["rows"]
    row_labels = [row[0] for row in result["table"]["rows"]]
    assert any(label.startswith("t(") for label in row_labels)
    assert "其他低样本类型" in row_labels


def test_pgtsr_euploid_rate_supports_specific_translocation_pair_filter() -> None:
    result = query_service.run(
        "pgtsr_euploid_rate",
        {
            "time_range": "当前快照全部时间",
            "breakdown": "overall",
            "focus": "summary",
            "sr_clinical_type": "平衡易位",
            "sr_translocation_pair": "t(1;5)",
        },
    )

    assert result["metric_id"] == "pgtsr_euploid_rate"
    assert result["filters"]["sr_translocation_pair"] == "t(1;5)"
    assert result["table"]["title"] == "PGT-SR 整倍体率总览"
    assert "t(1;5)" in result["summary"]


def test_pgtsr_euploid_rate_supports_multiple_sr_type_filters() -> None:
    records = get_pgtsr_record_source().filter_records(hospital_id=BASE_FILTERS["hospital_id"])
    clinical_types = sorted({record.sr_clinical_type for record in records if record.sr_clinical_type})
    assert len(clinical_types) >= 2
    selected_types = clinical_types[:2]

    result = query_service.run(
        "pgtsr_euploid_rate",
        {
            **BASE_FILTERS,
            "time_range": "当前快照全部时间",
            "breakdown": "overall",
            "focus": "summary",
            "sr_clinical_types": "|".join(selected_types),
        },
    )

    assert result["metric_id"] == "pgtsr_euploid_rate"
    assert result["filters"]["sr_clinical_types"] == "|".join(selected_types)
    assert result["evidence"]["status"] == "ready"
    assert result["evidence"]["record_count"] > 0
    assert result["table"]["title"] == "PGT-SR 整倍体率总览"


def test_pgtsr_result_overview_uses_euploid_display_label() -> None:
    result = query_service.run(
        "pgtsr_result_overview",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )

    assert result["table"]["rows"][0][0] == "整倍体"
    assert "整倍体占比" in result["summary"]


def test_pgtsr_next_step_overview_returns_expected_columns() -> None:
    result = query_service.run(
        "pgtsr_next_step_overview",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )

    assert result["table"]["columns"] == [
        "时间",
        "检测周期数",
        "否",
        "是（评估后符合非遗传型构建）",
        "是（评估后符合遗传型构建）",
        "/",
    ]


def test_pgtsr_cycle_indicator_supports_sr_clinical_type_breakdown() -> None:
    result = query_service.run(
        "pgtsr_cycle_indicator_overview",
        {
            **BASE_FILTERS,
            "time_range": "2025年",
            "breakdown": "sr_clinical_type",
            "focus": "distribution",
        },
    )

    assert result["metric_id"] == "pgtsr_cycle_indicator_overview"
    assert result["table"]["columns"][0] == "临床指征"
    assert result["table"]["columns"][2:] == ["周期有整倍体胚胎占比", "周期无整倍体胚胎占比"]
    assert result["table"]["rows"]
    assert all(row[0] != "总体" for row in result["table"]["rows"])
    assert "周期层面" in result["summary"]
