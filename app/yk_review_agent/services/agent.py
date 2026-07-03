from __future__ import annotations

from uuid import uuid4

from yk_review_agent.models.analysis import AnalysisPlan
from yk_review_agent.models.business_request import StructuredBusinessRequest
from yk_review_agent.models.chat import (
    AnalysisTask,
    AnalysisTaskStep,
    CapabilityReport,
    ClarifyPayload,
    ChatRequest,
    ChatResponse,
    RouteTrace,
    SnapshotMetadata,
    StructuredAnswer,
)
from yk_review_agent.models.session import LastAnalysisState, SessionContext, SessionMessage, SessionRecord
from yk_review_agent.services.answerability_policy import answerability_policy
from yk_review_agent.services.business_request_service import business_request_service
from yk_review_agent.services.intent_parser import intent_parser_service
from yk_review_agent.services.pgta_detail_dataset import get_pgta_dataset
from yk_review_agent.services.query_service import query_service
from yk_review_agent.services.report_service import report_service
from yk_review_agent.services.session_store import session_store
from yk_review_agent.services.snapshot_service import snapshot_service


class ConversationAgent:
    """Controlled PGT-A orchestrator for the V0.1 product baseline."""

    def handle(self, request: ChatRequest, session: SessionRecord) -> ChatResponse:
        session_store.append_message(
            request.session_id, SessionMessage(role="user", content=request.message)
        )

        parsed = intent_parser_service.parse(
            message=request.message,
            context=session.context,
            hospital_id=request.host_context.hospital_id or session.hospital_id,
            hospital_name=request.host_context.hospital_name or session.hospital_name,
        )
        plan = answerability_policy.evaluate(
            message=request.message,
            parsed=parsed,
            hospital_id=request.host_context.hospital_id or session.hospital_id,
            hospital_name=request.host_context.hospital_name or session.hospital_name,
            accessible_hospital_ids=request.host_context.accessible_hospital_ids,
            can_access_all_hospitals=request.host_context.can_access_all_hospitals,
        )
        snapshot_metadata = snapshot_service.get_snapshot_metadata()
        if plan.answer_mode != "answer":
            return self._non_answer_response(
                request,
                session,
                parsed,
                parsed.request_kind,
                parsed.topic,
                plan,
                snapshot_metadata,
                parsed.metric_id or (parsed.candidate_metric_ids[0] if parsed.candidate_metric_ids else None),
            )

        query_result = query_service.run(plan.metric_family or "", plan.filters)
        presentation = report_service.build_cards(plan.metric_family or "", query_result)
        data_readiness = snapshot_service.build_data_readiness(plan.metric_family, plan.filters)
        snapshot_start, snapshot_end = get_pgta_dataset().stat_month_range
        hospital_name = request.host_context.hospital_name or session.hospital_name or session.hospital_id
        assistant_text = (
            f"当前医院 {hospital_name}：{query_result['summary']} 数据范围来自当前业务整理的 PGT-A 快照，"
            f"统计月份覆盖 {snapshot_start} 至 {snapshot_end}。"
        )
        session.context = SessionContext(
            current_topic=parsed.topic,
            time_range=parsed.time_range,
            product_scope=plan.product_scope,
            last_result_summary=assistant_text,
            applied_filters=plan.filters,
            last_analysis=LastAnalysisState(
                metric_id=plan.metric_family or "",
                topic=parsed.topic,
                breakdown=plan.breakdown,
                time_grain=plan.time_grain,
                filters=plan.filters,
                product_scope=plan.product_scope,
                presentation_mode=presentation.presentation_mode,
                age_range=plan.filters.get("age_range"),
            ),
        )
        session_store.append_message(
            request.session_id, SessionMessage(role="assistant", content=assistant_text)
        )
        session_store.update_session(session)

        return ChatResponse(
            assistant_text=assistant_text,
            structured_answer=StructuredAnswer(
                answer_mode="answer",
                presentation_mode=presentation.presentation_mode,
                evidence_density=presentation.evidence_density,
                topic=parsed.topic,
                rationale=plan.rationale,
                applied_filters=plan.filters,
                metric_ids=[plan.metric_family] if plan.metric_family else [],
                warnings=plan.warnings,
            ),
            result_cards=presentation.result_cards,
            follow_up_suggestions=plan.suggestions or self._follow_ups(plan.metric_family or ""),
            clarify_payload=None,
            snapshot_metadata=snapshot_metadata,
            data_readiness=data_readiness,
            analysis_task=self._build_analysis_task(
                request_kind=parsed.request_kind,
                topic=parsed.topic,
                plan=plan,
                executed_metric=plan.metric_family,
            ),
            capability_report=self._build_capability_report(parsed),
            route_trace=self._build_route_trace(
                message=request.message,
                plan=plan,
                parsed=parsed,
            ),
            trace_id=str(uuid4()),
        )

    def _non_answer_response(
        self,
        request: ChatRequest,
        session: SessionRecord,
        parsed,
        request_kind: str,
        topic: str,
        plan: AnalysisPlan,
        snapshot_metadata: SnapshotMetadata,
        metric_id: str | None,
    ) -> ChatResponse:
        assistant_text = (
            plan.clarification_question
            if plan.answer_mode == "clarify" and plan.clarification_question
            else plan.rationale
        )
        session.context = SessionContext(
            current_topic=topic,
            time_range=plan.filters.get("time_range"),
            product_scope=plan.product_scope,
            last_result_summary=assistant_text,
            applied_filters=plan.filters,
            last_analysis=session.context.last_analysis,
        )
        session_store.append_message(
            request.session_id, SessionMessage(role="assistant", content=assistant_text)
        )
        session_store.update_session(session)
        card_title = "需要澄清" if plan.answer_mode == "clarify" else "当前不支持"
        presentation = report_service.build_state_cards(title=card_title, content=assistant_text)
        data_readiness = snapshot_service.build_data_readiness(metric_id, plan.filters)
        return ChatResponse(
            assistant_text=assistant_text,
            structured_answer=StructuredAnswer(
                answer_mode=plan.answer_mode,
                presentation_mode=presentation.presentation_mode,
                evidence_density=presentation.evidence_density,
                topic=topic,
                rationale=plan.rationale,
                applied_filters=plan.filters,
                metric_ids=[],
                warnings=plan.warnings or ["当前快照模式已接入多产品文件，但真实执行主链路仍只支持 PGT-A 统计问题。"],
            ),
            result_cards=presentation.result_cards,
            follow_up_suggestions=plan.suggestions,
            clarify_payload=self._build_clarify_payload(plan),
            snapshot_metadata=snapshot_metadata,
            data_readiness=data_readiness,
            analysis_task=self._build_analysis_task(
                request_kind=request_kind,
                topic=topic,
                plan=plan,
                executed_metric=None,
            ),
            capability_report=self._build_capability_report(parsed=None, topic=topic, plan=plan, message=request.message),
            route_trace=self._build_route_trace(
                message=request.message,
                plan=plan,
                parsed=parsed,
            ),
            trace_id=str(uuid4()),
        )

    def _build_clarify_payload(self, plan: AnalysisPlan) -> ClarifyPayload | None:
        if plan.answer_mode != "clarify" or not plan.clarification_question:
            return None
        options = list(plan.suggestions)
        if "年龄范围" in plan.clarify_missing:
            options.extend(["<35岁", "35-37岁", ">35岁", "41岁及以上", "未填写年龄"])
        clarify_type = "general"
        if "主指标" in plan.clarify_missing or "指标集合" in plan.clarify_missing:
            clarify_type = "multiple_metrics" if len(plan.candidate_metric_ids) > 1 else "missing_metric"
        elif "统计对象" in plan.clarify_missing:
            clarify_type = "ambiguous_object"
        elif any(item in plan.clarify_missing for item in ("时间范围", "年龄范围", "产品范围")):
            clarify_type = "missing_filter"
        return ClarifyPayload(
            clarify_type=clarify_type,
            title="请补充关键信息",
            question=plan.clarification_question,
            missing_parts=plan.clarify_missing,
            options=list(dict.fromkeys(options)),
        )

    def _build_analysis_task(
        self,
        request_kind: str,
        topic: str,
        plan: AnalysisPlan,
        executed_metric: str | None,
    ) -> AnalysisTask:
        kind = "structured_business_request" if request_kind == "structured_business_request" else "single_metric"
        if kind == "structured_business_request":
            steps = [
                AnalysisTaskStep(
                    title="识别业务统计任务单",
                    status="completed",
                    detail=f"已识别主题：{topic}",
                ),
                AnalysisTaskStep(
                    title="校验关键范围信息",
                    status="completed" if plan.answer_mode != "clarify" else "clarify",
                    detail=plan.clarification_question if plan.answer_mode == "clarify" else "已具备产品范围、时间范围和指标集合。",
                ),
                AnalysisTaskStep(
                    title="评估当前版本执行能力",
                    status="blocked" if plan.answer_mode == "refuse" else "completed",
                    detail=plan.rationale,
                ),
            ]
            status = "clarify" if plan.answer_mode == "clarify" else "blocked" if plan.answer_mode == "refuse" else "completed"
            return AnalysisTask(
                kind=kind,
                title="结构化业务统计任务",
                status=status,
                steps=steps,
                notes=plan.warnings,
            )

        steps = [
            AnalysisTaskStep(
                title="识别问题意图",
                status="completed",
                detail=f"主题：{topic}",
            ),
            AnalysisTaskStep(
                title="校验产品与数据边界",
                status="completed" if plan.answer_mode == "answer" else "clarify" if plan.answer_mode == "clarify" else "blocked",
                detail=plan.rationale,
            ),
        ]
        if plan.answer_mode == "answer":
            steps.append(
                AnalysisTaskStep(
                    title="执行受控统计分析",
                    status="completed",
                    detail=f"已执行指标：{executed_metric or '当前指标'}",
                )
            )
        status = "completed" if plan.answer_mode == "answer" else "clarify" if plan.answer_mode == "clarify" else "blocked"
        return AnalysisTask(
            kind=kind,
            title="单指标统计分析",
            status=status,
            steps=steps,
            notes=plan.warnings,
        )

    def _build_capability_report(
        self,
        parsed=None,
        topic: str | None = None,
        plan: AnalysisPlan | None = None,
        message: str | None = None,
    ) -> CapabilityReport | None:
        request = None
        if parsed is not None and getattr(parsed, "request_kind", "") == "structured_business_request":
            request = StructuredBusinessRequest(
                request_kind="structured_business_request",
                requested_products=parsed.requested_products,
                requested_metrics=parsed.requested_metrics,
                includes_marecs=parsed.includes_marecs,
            )
        elif message:
            parsed_request = business_request_service.parse(message)
            if parsed_request.request_kind == "structured_business_request":
                request = parsed_request

        if request is None:
            return None

        matrix = business_request_service.build_capability_matrix(request)
        if not matrix.products:
            return None
        summary = (
            "当前已将请求拆为按产品、按指标的能力检查结果。"
            if plan is None or plan.answer_mode != "clarify"
            else "当前已识别为结构化业务统计请求，但还需要先补全关键范围信息。"
        )
        return CapabilityReport(
            title="能力矩阵",
            summary=summary,
            products=matrix.products,
        )

    def _follow_ups(self, metric_id: str) -> list[str]:
        if metric_id == "pgta_euploid_rate":
            return [
                "按年龄分层看一下 PGT-A 整倍体率",
                "再看一下 PGT-A 的质控情况",
                "补充 PGT-A 的嵌合与异常结构",
            ]
        if metric_id == "pgta_quality_overview":
            return [
                "看一下 PGT-A 的结果分布",
                "看一下 PGT-A 的周期整倍体结局",
                "按月看一下 PGT-A 整倍体率变化",
            ]
        if metric_id == "pgta_mosaic_abnormal":
            return [
                "看一下 PGT-A 的周期整倍体结局",
                "看一下 PGT-A 的特殊 CNV 提示情况",
                "再看一下 PGT-A 的质控情况",
            ]
        return [
            "看一下当前快照下的 PGT-A 送检量",
            "看一下 PGT-A 的整倍体率",
            "按年龄分层看一下 PGT-A 整倍体率",
            "再看一下 PGT-A 的质控情况",
        ]

    def _build_route_trace(
        self,
        *,
        message: str,
        plan: AnalysisPlan,
        parsed,
    ) -> RouteTrace:
        filters = dict(plan.filters)
        candidate_metric_ids = plan.candidate_metric_ids
        resolved_metric_id = plan.metric_family
        normalized_message = plan.normalized_message or (getattr(parsed, "normalized_message", "") if parsed is not None else message)
        if parsed is not None:
            candidate_metric_ids = parsed.candidate_metric_ids or ([parsed.metric_id] if parsed.metric_id else [])
            resolved_metric_id = plan.metric_family or parsed.metric_id or None
        return RouteTrace(
            raw_message=message,
            normalized_message=normalized_message,
            filters=filters,
            candidate_metric_ids=candidate_metric_ids,
            resolved_metric_id=resolved_metric_id,
            answer_mode=plan.answer_mode,
            rationale=plan.rationale,
        )


conversation_agent = ConversationAgent()
