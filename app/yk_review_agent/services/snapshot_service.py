from __future__ import annotations

import re
from datetime import date

from yk_review_agent.models.chat import DataReadinessReport, SnapshotMetadata, SnapshotSourceSummary
from yk_review_agent.models.session import SessionOverview
from yk_review_agent.services.metric_catalog import active_data_capabilities, get_metric
from yk_review_agent.services.pgta_record_source import get_pgta_record_source
from yk_review_agent.services.product_snapshot_registry import get_snapshot_registry


SNAPSHOT_LIMITATIONS = [
    "当前仍依赖业务人工整合的 Excel 快照，不是正式接口直连。",
    "当前已接入 PGT-A、PGT-AH、PGT-SR、PGT-M 快照，但真实执行主链路仍只覆盖 PGT-A。",
    "跨产品执行仍处于能力矩阵阶段；PGT-A 的部分结果类指标已可执行，但扩增成功率口径仍待进一步对齐。",
]


class SnapshotService:
    def build_session_overview(self, hospital_id: str, hospital_name: str | None = None) -> SessionOverview:
        dataset = get_pgta_record_source()
        records = dataset.filter_records(hospital_id=hospital_id)
        cycle_count = len({item.cycle_id for item in records if item.cycle_id})
        embryo_count = len(records)
        snapshot_start, snapshot_end = self._session_snapshot_range(records, fallback=dataset.stat_month_range)
        resolved_hospital_name = hospital_name or hospital_id
        summary = (
            f"当前快照下，{resolved_hospital_name} 已接入 {embryo_count} 个可分析胚胎样本，"
            f"覆盖 {cycle_count} 个周期，时间范围 {snapshot_start} 至 {snapshot_end}。"
        )
        return SessionOverview(
            hospital_name=resolved_hospital_name,
            snapshot_start=snapshot_start,
            snapshot_end=snapshot_end,
            embryo_count=embryo_count,
            cycle_count=cycle_count,
            summary=summary,
        )

    def get_snapshot_metadata(self) -> SnapshotMetadata:
        dataset = get_pgta_record_source()
        start, end = dataset.stat_month_range
        registry = get_snapshot_registry()
        profiles = registry.list_profiles()
        return SnapshotMetadata(
            data_source="business_snapshot_bundle",
            product_scope="PGT-A（可执行） / PGT-AH、PGT-SR、PGT-M（快照已接入）",
            snapshot_start=start,
            snapshot_end=end,
            hospital_count=len(dataset.hospitals),
            registered_products=[profile.product_code for profile in profiles],
            source_summaries=[
                SnapshotSourceSummary(
                    product_code=profile.product_code,
                    product_label=profile.product_label,
                    data_source=profile.data_source,
                    sheet_name=profile.sheet_name,
                    row_count=profile.row_count,
                    cycle_count=profile.cycle_count,
                    snapshot_start=profile.snapshot_start,
                    snapshot_end=profile.snapshot_end,
                    semantic_fields=list(profile.semantic_fields),
                    execution_status=profile.execution_status,  # type: ignore[arg-type]
                    notes=list(profile.notes),
                )
                for profile in profiles
            ],
            available_context=[
                "医院",
                "时间",
                "周期",
                "胚胎",
                "年龄",
                "检测结果",
                "结果说明",
                "质控结果",
                "意外发现（人工处理）",
                "异倍体结果（人工处理）",
                "提示CNV",
            ],
            limitations=SNAPSHOT_LIMITATIONS,
        )

    def build_data_readiness(self, metric_id: str | None, filters: dict[str, str]) -> DataReadinessReport | None:
        if not metric_id:
            return None

        metric = get_metric(metric_id)
        if metric is None:
            return DataReadinessReport(
                status="unsupported",
                summary="当前指标未登记到可执行能力清单，不能直接执行。",
                limitations=["当前问题未映射到受控指标契约。"],
            )

        missing_fields = [field for field in metric.data_requirements if field not in active_data_capabilities("PGT-A")]
        if missing_fields:
            return DataReadinessReport(
                status="unsupported",
                summary=f"当前快照缺少执行“{metric.title}”所需的关键字段。",
                missing_fields=missing_fields,
                limitations=["需要补充字段或更换正式数据源后才能执行。"],
            )

        dataset = get_pgta_record_source()
        time_filter = self._parse_time_filter(filters.get("time_range", ""))
        records = dataset.filter_records(
            hospital_id=filters.get("hospital_id"),
            year=time_filter["year"],
            quarter=time_filter["quarter"],
            month=time_filter["month"],
            day=time_filter["day"],
            end_year=time_filter["end_year"],
            end_month=time_filter["end_month"],
            start_day=time_filter["start_day"],
            end_day=time_filter["end_day"],
            age_range=filters.get("age_range"),
        )
        if not records:
            return DataReadinessReport(
                status="no_data",
                summary="当前快照在所选医院和时间范围内没有可用于执行该统计的 PGT-A 数据。",
                record_count=0,
                limitations=["当前问题可执行，但本次筛选命中为空。"],
            )

        return DataReadinessReport(
            status="ready",
            summary=f"当前快照可执行“{metric.title}”，并已命中 {len(records)} 条有效胚胎记录。",
            record_count=len(records),
        )

    def _session_snapshot_range(self, records: list, fallback: tuple[str, str]) -> tuple[str, str]:
        if not records:
            return fallback
        buckets = [item.month_bucket for item in records if getattr(item, "month_bucket", "")]
        if buckets:
            return min(buckets), max(buckets)
        created_months = [item.created_at.strftime("%Y-%m") for item in records if getattr(item, "created_at", None)]
        if created_months:
            return min(created_months), max(created_months)
        return fallback

    def _parse_time_filter(self, text: str) -> dict[str, int | date | None]:
        result: dict[str, int | date | None] = {
            "year": None,
            "quarter": None,
            "month": None,
            "day": None,
            "end_year": None,
            "end_month": None,
            "start_day": None,
            "end_day": None,
        }
        if not text:
            return result
        month_range = re.search(
            r"(20\d{2})年([1-9]|1[0-2])月(?:到|至|-|~)(20\d{2})年([1-9]|1[0-2])月",
            text,
        )
        if month_range:
            result["year"] = int(month_range.group(1))
            result["month"] = int(month_range.group(2))
            result["end_year"] = int(month_range.group(3))
            result["end_month"] = int(month_range.group(4))
            return result
        iso_match = re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])", text)
        if iso_match:
            parsed = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            result["year"] = parsed.year
            result["month"] = parsed.month
            result["day"] = parsed.day
            result["start_day"] = parsed
            result["end_day"] = parsed
            return result
        short_iso_match = re.search(r"([2-3]\d)[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])", text)
        if short_iso_match:
            parsed = date(int(f"20{short_iso_match.group(1)}"), int(short_iso_match.group(2)), int(short_iso_match.group(3)))
            result["year"] = parsed.year
            result["month"] = parsed.month
            result["day"] = parsed.day
            result["start_day"] = parsed
            result["end_day"] = parsed
            return result
        full_date = re.search(r"(20\d{2})年(0?[1-9]|1[0-2])月(0?[1-9]|[12]\d|3[01])[日号]", text)
        if full_date:
            parsed = date(int(full_date.group(1)), int(full_date.group(2)), int(full_date.group(3)))
            result["year"] = parsed.year
            result["month"] = parsed.month
            result["day"] = parsed.day
            result["start_day"] = parsed
            result["end_day"] = parsed
            return result
        short_full_date = re.search(r"([2-3]\d)年(0?[1-9]|1[0-2])月(0?[1-9]|[12]\d|3[01])[日号]", text)
        if short_full_date:
            parsed = date(int(f"20{short_full_date.group(1)}"), int(short_full_date.group(2)), int(short_full_date.group(3)))
            result["year"] = parsed.year
            result["month"] = parsed.month
            result["day"] = parsed.day
            result["start_day"] = parsed
            result["end_day"] = parsed
            return result
        quarter_match = re.search(r"(20\d{2})年?([1-4])季度|Q([1-4])", text, re.IGNORECASE)
        if quarter_match:
            result["year"] = int(quarter_match.group(1)) if quarter_match.group(1) else None
            result["quarter"] = int(quarter_match.group(2) or quarter_match.group(3))
            return result
        short_quarter_match = re.search(r"([2-3]\d)年([1-4])季度", text, re.IGNORECASE)
        if short_quarter_match:
            result["year"] = int(f"20{short_quarter_match.group(1)}")
            result["quarter"] = int(short_quarter_match.group(2))
            return result
        month_match = re.search(r"(20\d{2})年?([1-9]|1[0-2])月", text)
        if month_match:
            result["year"] = int(month_match.group(1))
            result["month"] = int(month_match.group(2))
            return result
        short_month_match = re.search(r"([2-3]\d)年([1-9]|1[0-2])月", text)
        if short_month_match:
            result["year"] = int(f"20{short_month_match.group(1)}")
            result["month"] = int(short_month_match.group(2))
            return result
        year_match = re.search(r"(20\d{2})年", text)
        if year_match:
            result["year"] = int(year_match.group(1))
            return result
        short_year_match = re.search(r"([2-3]\d)年", text)
        if short_year_match:
            result["year"] = int(f"20{short_year_match.group(1)}")
            return result
        return result


snapshot_service = SnapshotService()
