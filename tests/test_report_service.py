from yk_review_agent.services.report_service import report_service


def test_single_point_chart_is_omitted_for_answer_cards() -> None:
    result = {
        "summary": "当前只有一个月的数据。",
        "table": {
            "title": "按月份统计的 PGT-A 胚胎数",
            "columns": ["月份", "胚胎数"],
            "rows": [["2025-07", 342]],
        },
        "chart": {
            "title": "PGT-A 月度胚胎数",
            "chart_type": "bar",
            "categories": ["2025-07"],
            "series": [{"name": "胚胎数", "values": [342]}],
        },
    }

    presentation = report_service.build_cards("pgt_total_volume", result)

    assert presentation.presentation_mode == "trend"
    assert [card.type for card in presentation.result_cards] == ["summary", "table"]


def test_multi_point_chart_is_retained_for_answer_cards() -> None:
    result = {
        "summary": "当前有多个时间点的数据。",
        "table": {
            "title": "按日期统计的 PGT-A 胚胎数",
            "columns": ["日期", "胚胎数"],
            "rows": [["2025-07-03", 68], ["2025-07-04", 5]],
        },
        "chart": {
            "title": "PGT-A 日期胚胎数",
            "chart_type": "bar",
            "categories": ["2025-07-03", "2025-07-04"],
            "series": [{"name": "胚胎数", "values": [68, 5]}],
        },
    }

    presentation = report_service.build_cards("pgt_total_volume", result)

    assert presentation.presentation_mode == "trend"
    assert [card.type for card in presentation.result_cards] == ["summary", "table", "chart"]


def test_trend_table_uses_preview_rows() -> None:
    rows = [[f"2025-07-{day:02d}", day] for day in range(1, 11)]
    result = {
        "summary": "按天趋势数据。",
        "table": {
            "title": "按日期统计的 PGT-A 胚胎数",
            "columns": ["日期", "胚胎数"],
            "rows": rows,
        },
        "chart": {
            "title": "PGT-A 日期胚胎数",
            "chart_type": "bar",
            "categories": [row[0] for row in rows],
            "series": [{"name": "胚胎数", "values": [row[1] for row in rows]}],
        },
    }

    presentation = report_service.build_cards("pgt_total_volume", result)
    table_card = next(card for card in presentation.result_cards if card.type == "table")

    assert table_card.table.total_rows == 10
    assert table_card.table.has_more_rows is True
    assert len(table_card.table.preview_rows or []) == 6
