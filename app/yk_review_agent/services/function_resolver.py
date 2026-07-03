from __future__ import annotations

from dataclasses import dataclass

from yk_review_agent.models.intent import ParsedIntent, SUPPORTED_METRIC_IDS
from yk_review_agent.services.metric_catalog import MetricDefinition, ROUTABLE_METRICS


@dataclass(frozen=True)
class FunctionResolution:
    metric_id: str | None
    candidate_metric_ids: list[str]
    reason: str | None = None


class FunctionResolver:
    def resolve(self, *, message: str, parsed: ParsedIntent) -> FunctionResolution:
        candidates: list[str] = []
        text = message.lower()
        explicit_metric_id = parsed.metric_id if parsed.metric_id in SUPPORTED_METRIC_IDS else ""
        first_match_indices: dict[str, int] = {}

        if explicit_metric_id:
            candidates.append(explicit_metric_id)
            first_match_indices[explicit_metric_id] = self._first_match_index(
                message=text,
                metric=self._metric_by_id(explicit_metric_id),
            )

        for metric in ROUTABLE_METRICS:
            score = self._match_score(metric=metric, message=text, parsed=parsed)
            if score > 0:
                candidates.append(metric.metric_id)
                first_match_indices[metric.metric_id] = self._first_match_index(message=text, metric=metric)

        deduped = list(dict.fromkeys(candidates))
        deduped.sort(key=lambda metric_id: (first_match_indices.get(metric_id, 10**6), self._route_priority(metric_id)))
        deduped = self._apply_metric_disambiguation(message=text, candidate_metric_ids=deduped)
        if len(deduped) == 1:
            return FunctionResolution(metric_id=deduped[0], candidate_metric_ids=deduped)
        if deduped:
            return FunctionResolution(
                metric_id=None,
                candidate_metric_ids=deduped,
                reason="当前问题同时命中了多个统计主题，需要先明确主指标。",
            )
        return FunctionResolution(
            metric_id=None,
            candidate_metric_ids=[],
            reason="当前问题还没有命中可执行的单指标主题。",
        )

    def _match_score(self, *, metric: MetricDefinition, message: str, parsed: ParsedIntent) -> int:
        score = 0
        if metric.metric_id == "pgta_cycle_indicator_overview":
            score += self._term_score(message, metric.hard_terms, hard=True)
            score += self._term_score(message, metric.soft_terms, hard=False)
            return score

        if metric.metric_id == "pgta_special_cnv_overview":
            return self._term_score(message, metric.hard_terms, hard=True)

        if metric.metric_id == "pgta_euploid_rate":
            if self._contains_any(message, ("周期无整倍体", "周期整倍体率", "周期整倍体结局", "周期结局")):
                return 0
            score += self._term_score(message, metric.hard_terms, hard=True)
            score += self._term_score(message, metric.soft_terms, hard=False)
            if parsed.breakdown == "age" and score > 0:
                score += 5
            return score

        score += self._term_score(message, metric.hard_terms, hard=True)
        score += self._term_score(message, metric.soft_terms, hard=False)
        return score

    def _contains_any(self, message: str, terms: tuple[str, ...]) -> bool:
        compact_message = self._compact_text(message)
        return any(
            term.lower() in message or self._compact_text(term.lower()) in compact_message
            for term in terms
        )

    def _term_score(self, message: str, terms: tuple[str, ...], *, hard: bool) -> int:
        compact_message = self._compact_text(message)
        matches = [
            term
            for term in terms
            if term.lower() in message or self._compact_text(term.lower()) in compact_message
        ]
        if not matches:
            return 0
        weight = 10 if hard else 3
        return len(matches) * weight

    def _first_match_index(self, *, message: str, metric: MetricDefinition) -> int:
        terms = (*metric.hard_terms, *metric.soft_terms)
        indices = [message.find(term.lower()) for term in terms if term and term.lower() in message]
        return min(indices) if indices else 10**6

    def _compact_text(self, text: str) -> str:
        return "".join(text.split())

    def _route_priority(self, metric_id: str) -> int:
        for metric in ROUTABLE_METRICS:
            if metric.metric_id == metric_id:
                return metric.route_priority
        return 10**6

    def _metric_by_id(self, metric_id: str) -> MetricDefinition | None:
        for metric in ROUTABLE_METRICS:
            if metric.metric_id == metric_id:
                return metric
        return None

    def _apply_metric_disambiguation(
        self, *, message: str, candidate_metric_ids: list[str]
    ) -> list[str]:
        if "pgta_cycle_indicator_overview" in candidate_metric_ids:
            if self._contains_any(
                message,
                (
                    "周期维度",
                    "周期层面",
                    "从周期角度",
                    "按周期看",
                    "整体结局",
                    "周期结局",
                    "周期整倍体结局",
                ),
            ):
                return [
                    metric_id
                    for metric_id in candidate_metric_ids
                    if metric_id == "pgta_cycle_indicator_overview"
                ]
            return [
                metric_id
                for metric_id in candidate_metric_ids
                if metric_id not in {"pgta_euploid_rate", "pgt_total_volume"}
            ]
        if {
            "pgta_special_cnv_overview",
            "pgta_mosaic_abnormal",
        }.issubset(candidate_metric_ids) and (
            self._contains_any(
                message, ("意外发现", "综合征", "拟常染色体", "p22.33", "cnv提示")
            )
            or ("单独" in message and "cnv" in message)
            or "不看整体结果结构" in self._compact_text(message)
        ):
            return [
                metric_id
                for metric_id in candidate_metric_ids
                if metric_id != "pgta_mosaic_abnormal"
            ]
        return candidate_metric_ids


function_resolver = FunctionResolver()
