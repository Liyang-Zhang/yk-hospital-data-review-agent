from __future__ import annotations

import re

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from yk_review_agent.core.config import settings
from yk_review_agent.models.intent import ParsedIntent, SUPPORTED_METRIC_IDS
from yk_review_agent.models.session import SessionContext
from yk_review_agent.services.business_request_service import business_request_service
from yk_review_agent.services.followup_resolver import follow_up_resolver
from yk_review_agent.services.function_resolver import function_resolver
from yk_review_agent.services.question_normalizer import question_normalizer


SUPPORTED_METRICS_TEXT = """
- pgt_total_volume: 送检量、周期数、胚胎数、平均每周期胚胎数
- pgta_euploid_rate: 整倍体率、按月/季度/日期看整倍体率
- pgta_quality_overview: 质控情况、检测周期数、检测胚胎数、平均囊胚数、检测成功率、PASS/INFO/FAIL、NA
- pgta_mosaic_abnormal: 嵌合、异常结构、异常率、异倍体率、意外发现率
- pgta_cycle_indicator_overview: 周期无整倍体率、周期整倍体率、仅1个整倍体、>=2个整倍体
- pgta_special_cnv_overview: 1Mb~4Mb、4Mb~10Mb、>=10Mb 特殊 CNV 提示、拟常染色体区域异常
- pgtsr_total_volume: PGT-SR 送检量、周期数、胚胎数、平均每周期胚胎数
- pgtsr_quality_overview: PGT-SR 质控情况、检测成功率、PASS/INFO/FAIL、NA
- pgtsr_result_overview: PGT-SR 结果分布、异常、嵌合异常
- pgtsr_cycle_indicator_overview: PGT-SR 周期结局、不同临床指征周期整倍体类比较
- pgtsr_next_step_overview: PGT-SR 是否进入下一步易位筛查
""".strip()


class IntentParserService:
    def __init__(self) -> None:
        self._llm_agent = self._build_llm_agent()

    def parse(
        self,
        *,
        message: str,
        context: SessionContext,
        hospital_id: str,
        hospital_name: str | None,
    ) -> ParsedIntent:
        normalized = question_normalizer.normalize(message)
        fallback = self._rule_parse(message=normalized.normalized_message, context=context)
        fallback = self._apply_rule_resolution(message=normalized.normalized_message, parsed=fallback)
        fallback = follow_up_resolver.resolve(message=normalized.normalized_message, parsed=fallback, context=context)
        fallback = self._apply_rule_resolution(message=normalized.normalized_message, parsed=fallback)
        if self._llm_agent is None or self._should_skip_llm(fallback):
            return self._apply_defaults(
                parsed=fallback,
                fallback_time_range=fallback.time_range,
                hospital_id=hospital_id,
                hospital_name=hospital_name,
                normalized_message=normalized.normalized_message,
            )

        try:
            result = self._llm_agent.run_sync(
                self._build_prompt(
                    normalized_message=normalized.normalized_message,
                    context=context,
                    hospital_id=hospital_id,
                    hospital_name=hospital_name,
                )
            )
            parsed = result.output
        except Exception:
            parsed = fallback

        parsed = follow_up_resolver.resolve(message=normalized.normalized_message, parsed=parsed, context=context)
        parsed = self._apply_rule_resolution(message=normalized.normalized_message, parsed=parsed)
        return self._apply_defaults(
            parsed=parsed,
            fallback_time_range=fallback.time_range,
            hospital_id=hospital_id,
            hospital_name=hospital_name,
            normalized_message=normalized.normalized_message,
        )

    def _build_llm_agent(self) -> Agent[None, ParsedIntent] | None:
        if not settings.llm_api_key:
            return None

        model = OpenAIChatModel(
            settings.llm_model,
            provider=OpenAIProvider(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
            ),
        )
        return Agent(
            model,
            output_type=ParsedIntent,
            instructions=(
                "你是医院客户数据回顾助手的意图识别器。"
                "当前系统使用业务快照文件作为数据源，真实执行主链路当前支持 PGT-A 和 PGT-SR 第一阶段统计问题。"
                f"可支持的 metric_id 只有以下几个：\n{SUPPORTED_METRICS_TEXT}\n"
                "如果问题涉及 PGT-M、全产品汇总、MaReCs 第二阶段、临床精细解释、流产、种植失败，"
                "必须返回 unsupported_reason，且 metric_id 置空。"
                "如果用户问题和医院PGT数据分析无关，例如天气、闲聊、通用知识，也必须拒答。"
                "time_range 要尽量保留用户原话中的时间表达；如果原话没有时间，就使用当前会话时间范围或当前快照全部时间。"
                "breakdown 只能从 overall/month/quarter/day/age/result/qc/sr_clinical_type 中选择。"
                "focus 只能表达 summary/trend/rate/distribution。"
                "不要发散分析，不要补充不存在的产品范围。"
            ),
        )

    def _build_prompt(
        self,
        *,
        normalized_message: str,
        context: SessionContext,
        hospital_id: str,
        hospital_name: str | None,
    ) -> str:
        current_time = context.time_range or "当前快照全部时间"
        last_analysis = context.last_analysis
        last_metric = last_analysis.metric_id if last_analysis else "无"
        last_breakdown = last_analysis.breakdown if last_analysis else "无"
        last_age_range = last_analysis.age_range if last_analysis and last_analysis.age_range else "无"
        return f"""
当前医院：
- hospital_id: {hospital_id}
- hospital_name: {hospital_name or "未提供"}

当前会话上下文：
- current_time_range: {current_time}
- last_metric_id: {last_metric}
- last_breakdown: {last_breakdown}
- last_age_range: {last_age_range}

用户问题：
规范化：{normalized_message}

请输出结构化意图，不要输出解释性文字。
""".strip()

    def _apply_defaults(
        self,
        *,
        parsed: ParsedIntent,
        fallback_time_range: str,
        hospital_id: str,
        hospital_name: str | None,
        normalized_message: str,
    ) -> ParsedIntent:
        time_range = parsed.time_range or fallback_time_range or "当前快照全部时间"
        breakdown = parsed.breakdown or "overall"
        focus = parsed.focus or "summary"
        metric_id = parsed.metric_id if parsed.metric_id in SUPPORTED_METRIC_IDS else ""

        return ParsedIntent(
            request_kind=parsed.request_kind or "single_metric",
            topic=parsed.topic or "未识别问题",
            metric_id=metric_id,
            time_range=time_range,
            product_scope=parsed.product_scope or "PGT-A",
            breakdown=breakdown,
            focus=focus,
            candidate_metric_ids=parsed.candidate_metric_ids,
            requested_products=parsed.requested_products,
            requested_metrics=parsed.requested_metrics,
            includes_marecs=parsed.includes_marecs,
            has_explicit_time_range=parsed.has_explicit_time_range,
            has_explicit_product_scope=parsed.has_explicit_product_scope,
            age_range=parsed.age_range,
            age_scope=parsed.age_scope,
            sr_clinical_type=parsed.sr_clinical_type,
            has_explicit_age_range=parsed.has_explicit_age_range,
            has_explicit_hospital_scope=parsed.has_explicit_hospital_scope,
            requested_hospital_id=parsed.requested_hospital_id,
            normalized_message=normalized_message,
            follow_up_resolution=parsed.follow_up_resolution,
            applied_filters={
                "time_range": time_range,
                "hospital_id": hospital_id,
                "hospital_name": hospital_name or hospital_id,
                "breakdown": breakdown,
                "focus": focus,
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
            },
            unsupported_reason=parsed.unsupported_reason,
        )

    def _rule_parse(self, *, message: str, context: SessionContext) -> ParsedIntent:
        business_request = business_request_service.parse(message)
        explicit_time_range = self._extract_time_range(message)
        age_range = self._extract_age_range(message)
        age_scope = self._extract_age_scope(message)
        sr_clinical_type = self._extract_sr_clinical_type(message)
        requested_hospital_id = question_normalizer.extract_explicit_hospital(message)
        time_range = explicit_time_range or context.time_range or "当前快照全部时间"
        breakdown = self._infer_breakdown(message, age_range, sr_clinical_type)
        focus = self._infer_focus(message)
        topic = "结构化业务统计请求" if business_request.request_kind == "structured_business_request" else self._topic_for("", breakdown, focus)

        return ParsedIntent(
            request_kind=business_request.request_kind,
            topic=topic,
            metric_id="",
            time_range=time_range,
            product_scope=self._infer_product_scope(message, context.product_scope),
            breakdown=breakdown,
            focus=focus,
            candidate_metric_ids=[],
            requested_products=business_request.requested_products,
            requested_metrics=business_request.requested_metrics,
            includes_marecs=business_request.includes_marecs,
            has_explicit_time_range=bool(explicit_time_range),
            has_explicit_product_scope=business_request_service.has_explicit_product_scope(message),
            age_range=age_range,
            age_scope=age_scope,
            sr_clinical_type=sr_clinical_type,
            has_explicit_age_range=age_range is not None,
            has_explicit_hospital_scope=requested_hospital_id is not None,
            requested_hospital_id=requested_hospital_id,
            normalized_message=message,
        )

    def _apply_rule_resolution(self, *, message: str, parsed: ParsedIntent) -> ParsedIntent:
        resolution = function_resolver.resolve(message=message, parsed=parsed)
        updated = parsed.model_copy(deep=True)
        updated.candidate_metric_ids = resolution.candidate_metric_ids
        if resolution.metric_id and resolution.metric_id in SUPPORTED_METRIC_IDS:
            updated.metric_id = resolution.metric_id
            updated.topic = self._topic_for(resolution.metric_id, updated.breakdown, updated.focus)
        return updated

    def _should_skip_llm(self, parsed: ParsedIntent) -> bool:
        if parsed.request_kind == "structured_business_request":
            return True
        if parsed.follow_up_resolution.needs_clarification:
            return True
        if parsed.metric_id in SUPPORTED_METRIC_IDS:
            return True
        if len(parsed.candidate_metric_ids) > 1:
            return True
        if parsed.unsupported_reason:
            return True
        return False

    def _extract_time_range(self, message: str) -> str | None:
        if month_range := re.search(
            r"(20\d{2})\s*年\s*([1-9]|1[0-2])\s*月\s*(?:到|至|-|~)\s*(20\d{2})\s*年\s*([1-9]|1[0-2])\s*月",
            message,
        ):
            return re.sub(r"\s+", "", month_range.group(0))
        if same_year_month_range := re.search(
            r"(20\d{2})\s*年\s*([1-9]|1[0-2])\s*月\s*(?:到|至|-|~)\s*([1-9]|1[0-2])\s*月",
            message,
        ):
            year = same_year_month_range.group(1)
            start_month = same_year_month_range.group(2)
            end_month = same_year_month_range.group(3)
            return f"{year}年{start_month}月到{year}年{end_month}月"
        if full_date := re.search(r"(20\d{2}\s*年\s*)?([1-9]|1[0-2])\s*月\s*([1-9]|[12]\d|3[01])\s*[日号]", message):
            return full_date.group(0)
        if iso_date := re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])", message):
            return iso_date.group(0)
        if short_year_date := re.search(r"([2-3]\d)\s*年\s*([1-9]|1[0-2])\s*月\s*([1-9]|[12]\d|3[01])\s*[日号]", message):
            return f"20{short_year_date.group(1)}年{short_year_date.group(2)}月{short_year_date.group(3)}日"
        if month_or_quarter := re.search(
            r"(20\d{2}\s*年\s*)?([1-4]\s*季度|Q[1-4]|[1-9]\s*月|1[0-2]\s*月)",
            message,
            re.IGNORECASE,
        ):
            return re.sub(r"\s+", "", month_or_quarter.group(0))
        if short_year_month_or_quarter := re.search(
            r"([2-3]\d)\s*年\s*([1-4]\s*季度|Q[1-4]|[1-9]\s*月|1[0-2]\s*月)",
            message,
            re.IGNORECASE,
        ):
            value = re.sub(r"\s+", "", short_year_month_or_quarter.group(2))
            return f"20{short_year_month_or_quarter.group(1)}年{value}"
        if year_only := re.search(r"(20\d{2})\s*年", message):
            return year_only.group(0)
        if short_year_only := re.search(r"([2-3]\d)\s*年", message):
            return f"20{short_year_only.group(1)}年"
        return None

    def _infer_breakdown(self, message: str, age_range: str | None, sr_clinical_type: str | None) -> str:
        if any(keyword in message.lower() for keyword in ("按临床指征", "不同sr患者", "不同患者")):
            return "sr_clinical_type"
        if sum(1 for term in ("罗氏易位", "平衡易位", "倒位", "微缺微重", "正常/嵌合/多态", "两种适应症", "插入") if term in message) >= 2:
            return "sr_clinical_type"
        if sr_clinical_type and any(keyword in message for keyword in ("罗氏易位", "平衡易位", "倒位")):
            return "sr_clinical_type"
        if "年龄分层" in message or ("按年龄" in message and age_range is None):
            return "age"
        if re.search(r"(20\d{2}年)?([1-9]|1[0-2])月([1-9]|[12]\d|3[01])[日号]", message):
            return "day"
        if re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])", message):
            return "day"
        if any(keyword in message for keyword in ("按天", "每天", "每日")):
            return "day"
        if any(keyword in message for keyword in ("按月", "每月", "月度")):
            return "month"
        if any(keyword in message for keyword in ("按季度", "分季度", "季度")):
            return "quarter"
        if any(keyword in message for keyword in ("趋势", "变化", "波动")):
            return "month"
        if any(
            keyword in message
            for keyword in (
                "1Mb",
                "4Mb",
                "10Mb",
                "提示CNV",
                "CNV提示",
                "CNV 提示",
                "特殊 CNV",
                "特殊CNV",
                "综合征",
                "拟常染色体",
                "p22.33",
                "P22.33",
            )
        ):
            return "overall"
        if any(keyword in message for keyword in ("嵌合", "异常结构", "结果分布", "结果结构")):
            return "result"
        if any(keyword in message.lower() for keyword in ("pass", "fail", "info")) or "质控" in message:
            return "qc"
        return "overall"

    def _infer_focus(self, message: str) -> str:
        if any(keyword in message for keyword in ("趋势", "变化", "波动", "分布", "结构")):
            return "trend" if any(term in message for term in ("趋势", "变化", "波动")) else "distribution"
        if "率" in message:
            return "rate"
        return "summary"

    def _infer_product_scope(self, message: str, fallback_product_scope: str | None = None) -> str:
        if any(keyword in message for keyword in ("PGT-SR", "PGTSR")) or re.search(r"\bSR\b", message, re.IGNORECASE):
            return "PGT-SR"
        if any(keyword in message for keyword in ("PGT-M", "PGTM")):
            return "PGT-M"
        if any(keyword in message for keyword in ("PGT-AH", "PGTAH")):
            return "PGT-AH"
        if any(keyword in message for keyword in ("全产品", "总体")):
            return "ALL"
        return fallback_product_scope or "PGT-A"

    def _extract_age_range(self, message: str) -> str | None:
        if "未填写年龄" in message:
            return "missing"
        between = re.search(r"(\d{2})\s*-\s*(\d{2})\s*岁", message)
        if between:
            return f"between:{between.group(1)},{between.group(2)}"
        gte = re.search(r">=\s*(\d{2})\s*岁", message)
        if gte:
            return f"gte:{gte.group(1)}"
        gt = re.search(r">\s*(\d{2})\s*岁", message)
        if gt:
            return f"gt:{gt.group(1)}"
        lte = re.search(r"<=\s*(\d{2})\s*岁", message)
        if lte:
            return f"lte:{lte.group(1)}"
        lt = re.search(r"<\s*(\d{2})\s*岁", message)
        if lt:
            return f"lt:{lt.group(1)}"
        return None

    def _extract_age_scope(self, message: str) -> str | None:
        if any(term in message for term in ("配偶年龄", "男方年龄", "女方配偶年龄")):
            return "spouse"
        if any(term in message for term in ("受检人年龄", "患者年龄", "女方年龄")):
            return "patient"
        return None

    def _extract_sr_clinical_type(self, message: str) -> str | None:
        candidates = (
            "平衡易位",
            "罗氏易位",
            "倒位",
            "微缺微重",
            "正常/嵌合/多态",
            "两种适应症",
            "插入",
        )
        matched = [candidate for candidate in candidates if candidate in message]
        if len(matched) == 1:
            return matched[0]
        return None

    def _topic_for(self, metric_id: str, breakdown: str, focus: str) -> str:
        mapping = {
            "pgt_total_volume": "PGT-A 送检量",
            "pgta_euploid_rate": "PGT-A 整倍体率",
            "pgta_quality_overview": "PGT-A 检测与质控总览",
            "pgta_mosaic_abnormal": "PGT-A 嵌合与异常结构",
            "pgta_cycle_indicator_overview": "PGT-A 周期结局总览",
            "pgta_special_cnv_overview": "PGT-A 特殊 CNV 提示总览",
            "pgtsr_total_volume": "PGT-SR 送检量",
            "pgtsr_quality_overview": "PGT-SR 检测与质控总览",
            "pgtsr_result_overview": "PGT-SR 结果分布",
            "pgtsr_cycle_indicator_overview": "PGT-SR 周期结局总览",
            "pgtsr_next_step_overview": "PGT-SR 下一步易位筛查总览",
        }
        if metric_id:
            return mapping.get(metric_id, "未识别问题")
        if breakdown == "sr_clinical_type":
            return "PGT-SR 临床指征分组分析"
        if breakdown == "age":
            return "PGT-A 年龄分层分析"
        if breakdown == "qc":
            return "PGT-A 质控分析"
        if breakdown == "result":
            return "PGT-A 结果结构分析"
        if focus == "trend":
            return "PGT-A 趋势分析"
        return "未识别问题"


intent_parser_service = IntentParserService()
