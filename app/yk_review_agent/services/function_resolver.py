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

        if explicit_metric_id:
            candidates.append(explicit_metric_id)

        for metric in ROUTABLE_METRICS:
            if self._matches(metric=metric, message=text, parsed=parsed):
                candidates.append(metric.metric_id)

        deduped = list(dict.fromkeys(candidates))
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

    def _matches(self, *, metric: MetricDefinition, message: str, parsed: ParsedIntent) -> bool:
        if metric.metric_id == "pgta_age_distribution":
            return parsed.breakdown == "age" or self._contains_any(message, metric.hard_terms)

        if metric.metric_id == "pgta_cycle_indicator_overview":
            return self._contains_any(message, metric.hard_terms)

        if metric.metric_id == "pgta_special_cnv_overview":
            return self._contains_any(message, metric.hard_terms)

        if metric.metric_id == "pgta_euploid_rate":
            if parsed.breakdown == "age":
                return False
            if self._contains_any(message, ("周期无整倍体", "周期整倍体率", "周期结局")):
                return False
            return self._contains_any(message, metric.hard_terms)

        return self._contains_any(message, metric.hard_terms)

    def _contains_any(self, message: str, terms: tuple[str, ...]) -> bool:
        return any(term.lower() in message for term in terms)


function_resolver = FunctionResolver()
