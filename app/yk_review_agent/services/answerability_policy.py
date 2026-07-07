from __future__ import annotations

import re

from yk_review_agent.models.analysis import AnalysisPlan
from yk_review_agent.models.business_request import StructuredBusinessRequest
from yk_review_agent.models.intent import ParsedIntent
from yk_review_agent.services.business_request_service import business_request_service
from yk_review_agent.services.function_resolver import function_resolver
from yk_review_agent.services.metric_catalog import (
    CLARIFY_PROMPTS,
    REFUSE_SUGGESTIONS,
    SUPPORTED_DOMAIN_TERMS,
    active_data_capabilities,
    get_metric,
)
from yk_review_agent.services.pgta_record_source import get_pgta_record_source
from yk_review_agent.services.pgtsr_record_source import get_pgtsr_record_source

AMBIGUOUS_EUPLOID_OBJECT_TERMS = (
    "无整倍体率",
    "整倍体结局",
)


class AnswerabilityPolicy:
    def evaluate(
        self,
        *,
        message: str,
        parsed: ParsedIntent,
        hospital_id: str,
        hospital_name: str | None,
        hospital_scope_mode: str = "single",
        accessible_hospital_ids: list[str] | None = None,
        can_access_all_hospitals: bool = False,
    ) -> AnalysisPlan:
        target_hospital_id = parsed.requested_hospital_id or (hospital_id if hospital_scope_mode == "single" else None)
        product_scope = parsed.product_scope or "PGT-A"
        filters = {
            "time_range": parsed.time_range,
            "hospital_scope_mode": hospital_scope_mode,
            **({"hospital_id": target_hospital_id, "hospital_name": target_hospital_id} if target_hospital_id else {}),
            "breakdown": parsed.breakdown,
            "focus": parsed.focus,
            **(
                {"patient_age_range": parsed.age_range}
                if parsed.age_range and parsed.age_scope == "patient"
                else {"spouse_age_range": parsed.age_range}
                if parsed.age_range and parsed.age_scope == "spouse"
                else {"age_range": parsed.age_range}
                if parsed.age_range
                else {}
            ),
            **({"sr_clinical_type": parsed.sr_clinical_type} if parsed.sr_clinical_type else {}),
        }
        time_grain = self._infer_time_grain(parsed.time_range, parsed.breakdown)
        resolution = function_resolver.resolve(message=parsed.normalized_message or message, parsed=parsed)
        if hospital_access_plan := self._evaluate_hospital_access(
            parsed=parsed,
            filters=filters,
            time_grain=time_grain,
            host_hospital_id=hospital_id,
            host_hospital_name=hospital_name or hospital_id,
            hospital_scope_mode=hospital_scope_mode,
            accessible_hospital_ids=accessible_hospital_ids,
            can_access_all_hospitals=can_access_all_hospitals,
        ):
            return hospital_access_plan

        if hospital_scope_mode == "all" and not can_access_all_hospitals:
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale="当前账号不具备全部医院的数据权限，不能切换到全部医院模式。",
                suggestions=REFUSE_SUGGESTIONS,
                normalized_message=parsed.normalized_message,
            )

        if parsed.follow_up_resolution.mode == "none" and not self._is_domain_relevant(message):
            if "分析" in message:
                return AnalysisPlan(
                    product_scope=product_scope,
                    breakdown=parsed.breakdown,
                    time_grain=time_grain,
                    filters=filters,
                    answer_mode="clarify",
                    rationale="当前问题还不够明确，缺少可执行的主指标。",
                    clarification_question="请先明确你想看的指标，例如送检量、整倍体率、年龄分层、质控情况或结果分布。",
                    clarify_missing=["主指标"],
                    suggestions=CLARIFY_PROMPTS,
                    normalized_message=parsed.normalized_message,
                )
            rationale = (
                "当前助手只回答医院 PGT 数据回顾相关问题，暂不支持天气、闲聊或通用知识问答。"
            )
            return AnalysisPlan(
                product_scope=parsed.product_scope or "PGT-A",
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=rationale,
                suggestions=REFUSE_SUGGESTIONS,
                normalized_message=parsed.normalized_message,
            )

        if parsed.follow_up_resolution.needs_clarification:
            return AnalysisPlan(
                product_scope=parsed.product_scope or "PGT-A",
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="clarify",
                rationale=parsed.follow_up_resolution.summary or "当前追问还缺少足够的信息。",
                clarification_question=parsed.follow_up_resolution.clarification_question
                or "请补充这次想继续看的指标。",
                clarify_missing=["主指标"],
                suggestions=CLARIFY_PROMPTS,
                candidate_metric_ids=resolution.candidate_metric_ids,
                normalized_message=parsed.normalized_message,
            )

        if parsed.request_kind == "structured_business_request":
            return self._structured_business_request_plan(
                parsed=parsed,
                filters=filters,
                time_grain=time_grain,
            )

        if parsed.product_scope not in {"PGT-A", "PGT-SR", ""}:
            return AnalysisPlan(
                product_scope=parsed.product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale="当前快照模式已接入多产品文件，但真实执行主链路当前只支持 PGT-A 与 PGT-SR 第一阶段统计，不支持 PGT-M、PGT-AH 或全产品汇总执行。",
                suggestions=REFUSE_SUGGESTIONS,
                normalized_message=parsed.normalized_message,
            )

        if unsupported_topic_reason := self._unsupported_topic_reason(message, product_scope):
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=unsupported_topic_reason,
                suggestions=REFUSE_SUGGESTIONS,
                normalized_message=parsed.normalized_message,
            )

        if conflict_reason := self._detect_conflict(message):
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=conflict_reason,
                suggestions=REFUSE_SUGGESTIONS,
                normalized_message=parsed.normalized_message,
            )

        if object_clarify_plan := self._clarify_ambiguous_euploid_object(
            message=message,
            parsed=parsed,
            filters=filters,
            time_grain=time_grain,
            candidate_ids=resolution.candidate_metric_ids,
        ):
            return object_clarify_plan

        candidate_ids = resolution.candidate_metric_ids

        if len(set(candidate_ids)) > 1:
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="clarify",
                rationale="当前问题同时落到了多个可执行指标，请先明确你最想看的主指标。",
                clarification_question="你这次最想先看哪一类指标？",
                clarify_missing=["主指标"],
                suggestions=CLARIFY_PROMPTS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        metric_id = resolution.metric_id if resolution.metric_id else (candidate_ids[0] if candidate_ids else None)
        if metric_id is None:
            clarify_missing = ["主指标"]
            clarification_question = "请先明确你想看的指标，例如送检量、整倍体率、年龄分层、质控情况或结果分布。"
            rationale = resolution.reason or "当前问题还不够明确，缺少可执行的主指标。"
            if parsed.follow_up_resolution.mode != "none" and not parsed.has_explicit_time_range and not parsed.time_range:
                clarify_missing = ["时间范围"]
                clarification_question = "请补充你想延续的时间范围，例如 2025年7月、2025年Q3 或 2025年7月到10月。"
                rationale = "当前追问没有可安全继承的时间范围，需要先补充时间。"
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="clarify",
                rationale=rationale,
                clarification_question=clarification_question,
                clarify_missing=clarify_missing,
                suggestions=CLARIFY_PROMPTS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        metric = get_metric(metric_id)
        if metric is None:
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale="当前问题映射到了未登记的指标族，暂不执行。",
                suggestions=REFUSE_SUGGESTIONS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        if product_scope not in metric.supported_products:
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=f"当前第一版暂不支持“{metric.title}”在当前产品范围执行。",
                suggestions=REFUSE_SUGGESTIONS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        for filter_name in filters:
            if filter_name not in metric.supported_filters and filter_name not in {"breakdown", "focus", "hospital_scope_mode"}:
                return AnalysisPlan(
                    product_scope=product_scope,
                    breakdown=parsed.breakdown,
                    time_grain=time_grain,
                    filters=filters,
                    answer_mode="refuse",
                    rationale=f"当前第一版暂不支持“{metric.title}”使用“{self._filter_label(filter_name)}”筛选。",
                    suggestions=REFUSE_SUGGESTIONS,
                    candidate_metric_ids=candidate_ids,
                    normalized_message=parsed.normalized_message,
                )

        if parsed.breakdown not in metric.supported_breakdowns:
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=f"当前第一版暂不支持“{metric.title}”按“{self._breakdown_label(parsed.breakdown)}”维度分析。",
                suggestions=REFUSE_SUGGESTIONS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        if time_grain not in metric.supported_time_grains:
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=f"当前第一版暂不支持“{metric.title}”使用“{self._time_grain_label(time_grain)}”时间粒度。",
                suggestions=REFUSE_SUGGESTIONS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        if not set(metric.data_requirements).issubset(active_data_capabilities(product_scope)):
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=f"当前数据源还不能稳定支撑“{metric.title}”的业务语义。",
                suggestions=REFUSE_SUGGESTIONS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        if metric.unsupported_combinations and parsed.breakdown in metric.unsupported_combinations:
            return AnalysisPlan(
                product_scope=product_scope,
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=f"当前第一版暂不支持“{metric.title}”和“{self._breakdown_label(parsed.breakdown)}”的组合分析。",
                suggestions=REFUSE_SUGGESTIONS,
                candidate_metric_ids=candidate_ids,
                normalized_message=parsed.normalized_message,
            )

        return AnalysisPlan(
            product_scope=product_scope,
            metric_family=metric.metric_id,
            breakdown=parsed.breakdown,
            time_grain=time_grain,
            filters=filters,
            answer_mode="answer",
            rationale=f"问题已通过产品范围、数据支撑和组合有效性校验，可执行“{metric.title}”分析。",
            suggestions=self._follow_up_suggestions(metric.metric_id),
            candidate_metric_ids=candidate_ids,
            normalized_message=parsed.normalized_message,
        )

    def _structured_business_request_plan(
        self,
        *,
        parsed: ParsedIntent,
        filters: dict[str, str],
        time_grain: str,
    ) -> AnalysisPlan:
        missing_parts: list[str] = []
        if not parsed.has_explicit_product_scope:
            missing_parts.append("产品范围")
        if not parsed.has_explicit_time_range:
            missing_parts.append("时间范围")
        if not parsed.requested_metrics:
            missing_parts.append("指标集合")

        if missing_parts:
            return AnalysisPlan(
                product_scope=parsed.product_scope or "ALL",
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="clarify",
                rationale=f"当前请求属于结构化业务统计任务单，但还缺少关键范围信息：{'、'.join(missing_parts)}。",
                clarification_question="请补充你要统计的产品范围、时间范围，以及希望输出的指标集合。",
                clarify_missing=missing_parts,
                suggestions=[
                    "请统计 2026年1月1日到2026年5月31日，PGT-A 的周期数、胚胎数和整倍体率。",
                    "请统计 2026年1月1日到2026年5月31日，所有PGT项目的周期数、胚胎数和整倍体率。",
                ],
                warnings=[],
                normalized_message=parsed.normalized_message,
            )

        request = StructuredBusinessRequest(
            request_kind=parsed.request_kind,
            requested_products=parsed.requested_products,
            requested_metrics=parsed.requested_metrics,
            includes_marecs=parsed.includes_marecs,
        )
        matrix = business_request_service.build_capability_matrix(request)
        warnings = matrix.to_human_lines()
        requested_product_text = "、".join(parsed.requested_products) if parsed.requested_products else "当前识别的产品集合"
        requested_metric_text = "、".join(metric.label for metric in parsed.requested_metrics) if parsed.requested_metrics else "当前识别的指标集合"

        return AnalysisPlan(
            product_scope=parsed.product_scope or "ALL",
            breakdown=parsed.breakdown,
            time_grain=time_grain,
            filters=filters,
            answer_mode="refuse",
            rationale=(
                "当前请求属于结构化业务统计任务单，不是单一指标问答。"
                f"已识别产品：{requested_product_text}；已识别指标：{requested_metric_text}。"
                "当前 V0.2 快照模式已接入多产品文件，但真实执行主链路仍只支持 PGT-A 单指标，不支持跨产品、多指标汇总执行。"
            ),
            suggestions=[
                "看一下当前快照下的 PGT-A 送检量",
                "看一下当前快照下的 PGT-A 质控情况",
                "按月看一下 PGT-A 整倍体率变化",
            ],
            warnings=warnings,
            normalized_message=parsed.normalized_message,
        )

    def _is_domain_relevant(self, message: str) -> bool:
        normalized = message.lower()
        if any(term.lower() in normalized for term in SUPPORTED_DOMAIN_TERMS):
            return True
        return False

    def _unsupported_topic_reason(self, message: str, product_scope: str) -> str | None:
        if ("临床指征" in message and product_scope != "PGT-SR") or "流产" in message or "种植失败" in message:
            return "当前第一版暂不支持临床指征相关统计，因为这些字段口径还未完全确认。"
        if product_scope == "PGT-SR" and any(term in message for term in ("MaReCs", "marecs", "第二阶段", "二阶段")):
            return "当前第一阶段暂不支持 PGT-SR MaReCs 第二阶段相关统计。"
        return None

    def _clarify_ambiguous_euploid_object(
        self,
        *,
        message: str,
        parsed: ParsedIntent,
        filters: dict[str, str],
        time_grain: str,
        candidate_ids: list[str],
    ) -> AnalysisPlan | None:
        compact_message = "".join(message.split())
        has_cycle_signal = any(
            term in compact_message
            for term in ("周期无整倍体", "周期整倍体率", "周期整倍体结局", "周期结局", "周期层面", "从周期角度", "按周期看", "每周期")
        )
        has_embryo_signal = any(
            term in compact_message for term in ("胚胎整倍体率", "胚胎层面", "从胚胎角度", "按胚胎看", "每枚胚胎")
        )
        has_ambiguous_euploid_term = any(term in compact_message for term in AMBIGUOUS_EUPLOID_OBJECT_TERMS)

        if has_cycle_signal or has_embryo_signal or not has_ambiguous_euploid_term:
            return None

        object_metric_ids = {"pgta_euploid_rate", "pgta_cycle_indicator_overview"}
        if parsed.metric_id not in object_metric_ids and not set(candidate_ids).intersection(object_metric_ids):
            return None

        if candidate_ids and not set(candidate_ids).issubset(object_metric_ids):
            return None

        return AnalysisPlan(
            product_scope=parsed.product_scope or "PGT-A",
            breakdown=parsed.breakdown,
            time_grain=time_grain,
            filters=filters,
            answer_mode="clarify",
            rationale="当前问题已经进入整倍体相关主题，但还缺少“胚胎层面”还是“周期层面”的关键信息。",
            clarification_question="这次你想看胚胎层面的整倍体率，还是周期层面的整倍体结局？",
            clarify_missing=["统计对象"],
            suggestions=[
                "看一下 PGT-A 的胚胎整倍体率",
                "看一下 PGT-A 的周期无整倍体率",
                "看一下 PGT-A 的周期整倍体结局",
            ],
            candidate_metric_ids=["pgta_euploid_rate", "pgta_cycle_indicator_overview"],
            normalized_message=parsed.normalized_message,
        )

    def _detect_conflict(self, message: str) -> str | None:
        has_quality = "质控" in message or any(term in message.lower() for term in ("pass", "fail", "info"))
        has_euploid = "整倍体率" in message or "整倍体" in message
        has_result = any(term in message for term in ("嵌合", "异常结构", "结果分布", "结果结构"))

        if has_quality and has_euploid:
            return "当前第一版不支持按质控维度拆分整倍体率，请改问“质控情况”或单独问“整倍体率”。"
        if has_result and has_quality:
            return "当前第一版不支持把结果分布和质控分布做组合分析，请分别查询结果分布或质控情况。"
        return None

    def _infer_time_grain(self, time_range: str, breakdown: str) -> str:
        if breakdown == "age":
            return "overall"
        if breakdown == "sr_clinical_type":
            return "overall"
        if re.search(r"(20\d{2}年)?([1-9]|1[0-2])月([1-9]|[12]\d|3[01])[日号]", time_range) or re.search(
            r"(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])",
            time_range,
        ):
            return "day"
        if re.search(r"Q([1-4])|([1-4])季度", time_range, re.IGNORECASE):
            return "quarter"
        if re.search(r"([1-9]|1[0-2])月", time_range):
            return "month"
        return "overall"

    def _breakdown_label(self, breakdown: str) -> str:
        mapping = {
            "overall": "总体",
            "month": "按月",
            "quarter": "按季度",
            "day": "按天",
            "age": "按年龄",
            "result": "结果结构",
            "qc": "质控",
            "sr_clinical_type": "临床指征",
        }
        return mapping.get(breakdown, breakdown)

    def _time_grain_label(self, time_grain: str) -> str:
        mapping = {
            "overall": "总体",
            "month": "月",
            "quarter": "季度",
            "day": "日",
        }
        return mapping.get(time_grain, time_grain)

    def _filter_label(self, filter_name: str) -> str:
        mapping = {
            "hospital_id": "医院",
            "hospital_name": "医院",
            "time_range": "时间范围",
            "age_range": "年龄范围",
            "patient_age_range": "受检人年龄范围",
            "spouse_age_range": "配偶年龄范围",
            "sr_clinical_type": "临床指征",
        }
        return mapping.get(filter_name, filter_name)

    def _follow_up_suggestions(self, metric_id: str) -> list[str]:
        mapping = {
            "pgta_euploid_rate": [
                "按年龄分层看一下 PGT-A 整倍体率",
                "再看一下 PGT-A 的质控情况",
                "补充 PGT-A 的结果分布",
            ],
            "pgta_mosaic_abnormal": [
                "看一下 PGT-A 的周期整倍体结局",
                "补充 PGT-A 的特殊 CNV 提示情况",
                "再看一下 PGT-A 的质控情况",
            ],
            "pgtsr_total_volume": [
                "看一下 PGT-SR 质控情况",
                "看一下 PGT-SR 结果分布",
                "看一下 PGT-SR 是否进入下一步易位筛查",
            ],
            "pgtsr_result_overview": [
                "看一下 PGT-SR 周期结局",
                "看一下 PGT-SR 是否进入下一步易位筛查",
                "按临床指征看一下 PGT-SR 周期结局",
            ],
            "pgtsr_cycle_indicator_overview": [
                "按临床指征看一下 PGT-SR 周期结局",
                "看一下 PGT-SR 是否进入下一步易位筛查",
                "看一下 PGT-SR 结果分布",
            ],
        }
        return mapping.get(metric_id, CLARIFY_PROMPTS)

    def _evaluate_hospital_access(
        self,
        *,
        parsed: ParsedIntent,
        filters: dict[str, str],
        time_grain: str,
        host_hospital_id: str,
        host_hospital_name: str,
        hospital_scope_mode: str,
        accessible_hospital_ids: list[str] | None,
        can_access_all_hospitals: bool,
    ) -> AnalysisPlan | None:
        requested_hospital_id = parsed.requested_hospital_id
        if not requested_hospital_id:
            return None

        if parsed.product_scope == "PGT-SR":
            known_hospitals = {item["hospital_id"] for item in get_pgtsr_record_source().hospitals}
        else:
            known_hospitals = {item["hospital_id"] for item in get_pgta_record_source().hospitals}
        if requested_hospital_id not in known_hospitals:
            return AnalysisPlan(
                product_scope=parsed.product_scope or "PGT-A",
                breakdown=parsed.breakdown,
                time_grain=time_grain,
                filters=filters,
                answer_mode="refuse",
                rationale=f"当前可访问的数据集不包含“{requested_hospital_id}”，暂时无法查询该医院的数据。",
                suggestions=REFUSE_SUGGESTIONS,
                normalized_message=parsed.normalized_message,
            )

        if requested_hospital_id == host_hospital_id or can_access_all_hospitals:
            return None

        allowed_hospitals = set(accessible_hospital_ids or ([] if hospital_scope_mode == "all" else [host_hospital_id]))
        if requested_hospital_id in allowed_hospitals:
            return None

        return AnalysisPlan(
            product_scope=parsed.product_scope or "PGT-A",
            breakdown=parsed.breakdown,
            time_grain=time_grain,
            filters=filters,
            answer_mode="refuse",
            rationale=(
                f"当前会话只具备“{host_hospital_name}”的数据访问权限，不能查询“{requested_hospital_id}”的数据。"
                "请切换到有对应数据权限的医院账号，或由 IT 授权后再查询。"
            ),
            suggestions=REFUSE_SUGGESTIONS,
            normalized_message=parsed.normalized_message,
        )


answerability_policy = AnswerabilityPolicy()
