from dataclasses import dataclass

from yk_review_agent.models.chat import ChartPayload, ChartSeries, ResultCard, TablePayload
from yk_review_agent.services.metric_catalog import get_metric


@dataclass(frozen=True)
class AnswerPresentation:
    result_cards: list[ResultCard]
    presentation_mode: str
    evidence_density: str


class ReportService:
    def build_cards(self, metric_id: str, result: dict) -> AnswerPresentation:
        metric = get_metric(metric_id)
        card_order = metric.default_card_types if metric else ("summary", "table", "chart")
        cards: list[ResultCard] = []
        presentation_mode = self._presentation_mode(metric_id, result)
        evidence_density = self._evidence_density(result)

        for card_type in card_order:
            if card_type == "summary":
                cards.append(ResultCard(type="summary", title="分析结论", content=result["summary"]))
            elif card_type == "table":
                table = result.get("table")
                if table:
                    preview_rows = self._preview_rows(presentation_mode, table["rows"])
                    cards.append(
                        ResultCard(
                            type="table",
                            title=table["title"],
                            table=TablePayload(
                                title=table["title"],
                                columns=table["columns"],
                                rows=table["rows"],
                                preview_rows=preview_rows,
                                total_rows=len(table["rows"]),
                                has_more_rows=len(preview_rows) < len(table["rows"]),
                            ),
                        )
                    )
            elif card_type == "chart":
                chart = result.get("chart")
                if chart and self._should_render_chart(metric_id, chart):
                    cards.append(
                        ResultCard(
                            type="chart",
                            title=chart["title"],
                            chart=ChartPayload(
                                title=chart["title"],
                                chart_type=metric.default_chart_type or chart["chart_type"],
                                categories=chart["categories"],
                                series=[
                                    ChartSeries(name=series["name"], values=series["values"])
                                    for series in chart["series"]
                                ],
                            ),
                        )
                    )
        return AnswerPresentation(
            result_cards=cards,
            presentation_mode=presentation_mode,
            evidence_density=evidence_density,
        )

    def build_state_cards(self, *, title: str, content: str) -> AnswerPresentation:
        return AnswerPresentation(
            result_cards=[ResultCard(type="summary", title=title, content=content)],
            presentation_mode="overview",
            evidence_density="compact",
        )

    def _should_render_chart(self, metric_id: str, chart: dict) -> bool:
        metric = get_metric(metric_id)
        if not metric or not metric.default_chart_type:
            return False

        categories = chart.get("categories", [])
        if not isinstance(categories, list) or len(categories) < metric.min_chart_points:
            return False

        series = chart.get("series", [])
        if not isinstance(series, list) or not series:
            return False

        return True

    def _presentation_mode(self, metric_id: str, result: dict) -> str:
        metric = get_metric(metric_id)
        row_count = len(result.get("table", {}).get("rows", []))
        chart_goal = metric.chart_goal if metric else None

        if chart_goal == "trend":
            return "trend"
        if chart_goal in {"distribution", "comparison"}:
            return "distribution"
        if row_count > 8:
            return "detail_heavy"
        return "overview"

    def _evidence_density(self, result: dict) -> str:
        row_count = len(result.get("table", {}).get("rows", []))
        return "dense" if row_count > 8 else "compact"

    def _preview_rows(self, presentation_mode: str, rows: list[list[str | int | float]]) -> list[list[str | int | float]]:
        if presentation_mode == "trend":
            limit = 6
        elif presentation_mode == "detail_heavy":
            limit = 8
        else:
            limit = len(rows)
        return rows[:limit]


report_service = ReportService()
