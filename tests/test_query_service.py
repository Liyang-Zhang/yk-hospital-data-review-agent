from yk_review_agent.services.query_service import query_service


BASE_FILTERS = {
    "hospital_id": "中国人民解放军医院301医院",
    "hospital_name": "中国人民解放军医院301医院",
}


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
    result = query_service.run(
        "pgt_total_volume",
        {**BASE_FILTERS, "time_range": "2025年7月15号", "breakdown": "day", "focus": "summary"},
    )
    assert result["table"]["rows"]
    assert result["table"]["rows"][0][0] == "2025-07-15"
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


def test_special_cnv_overview_returns_expected_columns() -> None:
    result = query_service.run(
        "pgta_special_cnv_overview",
        {**BASE_FILTERS, "time_range": "2025年", "breakdown": "overall", "focus": "summary"},
    )
    assert result["table"]["columns"] == [
        "时间",
        "1Mb~4Mb 综合征相关提示",
        "4Mb~10Mb 且≥50%嵌合",
        "≥10Mb 且20%~30%嵌合",
        "拟常染色体区域缺失",
    ]


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
            "time_range": "2025年7月到2025年10月",
            "breakdown": "month",
            "focus": "trend",
            "age_range": "missing",
        },
    )
    assert result["evidence"]["status"] == "ready"
