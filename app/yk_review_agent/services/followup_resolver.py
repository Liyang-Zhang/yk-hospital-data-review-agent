from __future__ import annotations

from yk_review_agent.models.intent import FollowUpResolution, ParsedIntent
from yk_review_agent.models.session import SessionContext


FOLLOW_UP_CUES = ("那", "再", "换成", "改成", "继续", "然后", "呢")
AGE_ONLY_PATTERNS = ("按年龄分层", "换成年龄分层", "那35岁以上呢", "那35-37岁呢", "那未填写年龄呢")
UNDERSPECIFIED_FOLLOW_UPS = ("那呢", "然后呢", "继续", "继续看", "再看看", "再看呢")


class FollowUpResolver:
    def resolve(self, *, message: str, parsed: ParsedIntent, context: SessionContext) -> ParsedIntent:
        if context.last_analysis is None:
            return parsed

        updated = parsed.model_copy(deep=True)
        inherited_fields: list[str] = []
        resolution_mode = "none"
        message_text = message.strip()

        if not updated.has_explicit_time_range and context.time_range:
            updated.time_range = context.time_range
            inherited_fields.append("time_range")
            resolution_mode = "inherit_context"

        if self._is_underspecified_follow_up(message_text) and not any(
            [
                updated.metric_id,
                updated.candidate_metric_ids,
                updated.breakdown != "overall",
                updated.has_explicit_age_range,
                updated.has_explicit_time_range,
            ]
        ):
            updated.follow_up_resolution = FollowUpResolution(
                mode="clarify_follow_up",
                inherited_fields=sorted(set(inherited_fields)),
                summary="当前追问缺少足够的指标信息，不能安全继承。",
                needs_clarification=True,
                clarification_question="请补充这次想继续看的指标，例如整倍体率、送检量、质控情况或结果分布。",
            )
            return updated

        if (
            not updated.has_explicit_age_range
            and context.last_analysis
            and context.last_analysis.age_range
            and updated.breakdown != "age"
            and updated.metric_id != "pgta_age_distribution"
        ):
            if self._looks_like_follow_up(message_text):
                updated.age_range = context.last_analysis.age_range
                updated.has_explicit_age_range = True
                inherited_fields.append("age_range")
                resolution_mode = "inherit_context"

        if (
            not updated.metric_id
            and not updated.candidate_metric_ids
            and updated.breakdown != "overall"
            and updated.breakdown != "age"
            and self._looks_like_follow_up(message_text)
        ):
            updated.metric_id = context.last_analysis.metric_id
            updated.candidate_metric_ids = [context.last_analysis.metric_id]
            updated.topic = context.last_analysis.topic
            updated.product_scope = context.last_analysis.product_scope
            inherited_fields.extend(["metric_id", "product_scope"])
            resolution_mode = "rewrite_metric" if updated.breakdown == "overall" else "rewrite_breakdown"

        if updated.metric_id and not updated.product_scope:
            updated.product_scope = context.last_analysis.product_scope
            inherited_fields.append("product_scope")
            resolution_mode = resolution_mode or "inherit_context"

        if updated.breakdown != "overall" and updated.metric_id == context.last_analysis.metric_id:
            resolution_mode = "rewrite_breakdown"

        if updated.has_explicit_age_range and not updated.metric_id and self._looks_like_follow_up(message_text):
            updated.metric_id = context.last_analysis.metric_id
            updated.candidate_metric_ids = [context.last_analysis.metric_id]
            updated.topic = context.last_analysis.topic
            updated.product_scope = context.last_analysis.product_scope
            inherited_fields.extend(["metric_id", "product_scope"])
            resolution_mode = "rewrite_filter"

        if inherited_fields:
            updated.follow_up_resolution = FollowUpResolution(
                mode=resolution_mode,
                inherited_fields=sorted(set(inherited_fields)),
                summary=f"已继承当前会话中的 {'、'.join(sorted(set(inherited_fields)))}。",
            )

        return updated

    def _looks_like_follow_up(self, message: str) -> bool:
        if any(message.startswith(cue) for cue in FOLLOW_UP_CUES):
            return True
        if any(cue in message for cue in ("按月看呢", "按季度看呢", "按天看呢", *AGE_ONLY_PATTERNS)):
            return True
        return False

    def _is_underspecified_follow_up(self, message: str) -> bool:
        normalized = message.strip()
        return normalized in UNDERSPECIFIED_FOLLOW_UPS


follow_up_resolver = FollowUpResolver()
