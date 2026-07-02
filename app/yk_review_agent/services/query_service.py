from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from statistics import mean

from yk_review_agent.services.pgta_detail_dataset import DetailRecord, get_pgta_dataset


class QueryService:
    def run(self, metric_id: str, filters: dict[str, str]) -> dict:
        dataset = get_pgta_dataset()
        time_filter = _parse_time_filter(filters.get("time_range", ""))
        breakdown = filters.get("breakdown", "overall")
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
            return {
                "metric_id": metric_id,
                "filters": filters,
                "summary": "当前筛选条件下没有可用的 PGT-A 快照数据。",
                "evidence": {
                    "status": "no_data",
                    "record_count": 0,
                    "breakdown": breakdown,
                },
                "table": {
                    "title": "无数据",
                    "columns": ["筛选项", "值"],
                    "rows": [["time_range", filters.get("time_range", "当前快照全部时间")]],
                },
                "chart": None,
            }

        if metric_id == "pgta_euploid_rate":
            return self._pgta_euploid_rate(records, filters, breakdown)
        if metric_id == "pgta_age_distribution":
            return self._pgta_age_distribution(records, filters)
        if metric_id == "pgta_quality_overview":
            return self._pgta_quality_overview(records, filters, breakdown)
        if metric_id == "pgta_mosaic_abnormal":
            return self._pgta_mosaic_abnormal(records, filters, breakdown)
        if metric_id == "pgta_cycle_indicator_overview":
            return self._pgta_cycle_indicator_overview(records, filters, breakdown)
        if metric_id == "pgta_special_cnv_overview":
            return self._pgta_special_cnv_overview(records, filters, breakdown)
        return self._pgta_volume(records, filters, breakdown)

    def _pgta_volume(self, records: list[DetailRecord], filters: dict[str, str], breakdown: str) -> dict:
        cycle_count = len({item.cycle_id for item in records})
        embryo_count = len(records)
        avg_embryos = embryo_count / cycle_count if cycle_count else 0.0

        if breakdown == "overall":
            rows = [["总体", cycle_count, embryo_count, f"{avg_embryos:.2f}"]]
            chart = None
        else:
            rows = []
            categories: list[str] = []
            embryo_values: list[float] = []
            for key, bucket in _group_records(records, breakdown).items():
                bucket_cycles = len({item.cycle_id for item in bucket})
                bucket_embryos = len(bucket)
                bucket_avg = bucket_embryos / bucket_cycles if bucket_cycles else 0.0
                rows.append([key, bucket_cycles, bucket_embryos, f"{bucket_avg:.2f}"])
                categories.append(key)
                embryo_values.append(float(bucket_embryos))
            chart = {
                "title": self._volume_chart_title(breakdown),
                "chart_type": "bar",
                "categories": categories,
                "series": [{"name": "检测胚胎数", "values": embryo_values}],
            }

        return {
            "metric_id": "pgt_total_volume",
            "filters": filters,
            "summary": (
                f"当前快照下，PGT-A 共覆盖 {cycle_count} 个检测周期、{embryo_count} 个检测胚胎，"
                f"平均每周期 {avg_embryos:.2f} 个胚胎。"
            ),
            "evidence": {
                "status": "ready",
                "record_count": embryo_count,
                "cycle_count": cycle_count,
                "breakdown": breakdown,
            },
            "table": {
                "title": self._volume_table_title(breakdown),
                "columns": [self._breakdown_label(breakdown), "检测周期数", "检测胚胎数", "平均囊胚数"],
                "rows": rows,
            },
            "chart": chart,
        }

    def _pgta_euploid_rate(self, records: list[DetailRecord], filters: dict[str, str], breakdown: str) -> dict:
        if breakdown == "age":
            return self._pgta_age_distribution(records, filters)

        rows, categories, values = self._euploid_rate_rows(records, breakdown)
        total = len(records)
        euploid = sum(1 for item in records if item.is_euploid)
        rate = _pct(euploid, total)
        chart = None
        if categories:
            chart = {
                "title": self._rate_chart_title(breakdown),
                "chart_type": "bar",
                "categories": categories,
                "series": [{"name": "整倍体率", "values": values}],
            }

        return {
            "metric_id": "pgta_euploid_rate",
            "filters": filters,
            "summary": (
                f"当前快照下，PGT-A 共检测 {total} 个胚胎，其中整倍体 {euploid} 个，"
                f"整倍体率为 {rate}。"
            ),
            "evidence": {
                "status": "ready",
                "record_count": total,
                "euploid_count": euploid,
                "breakdown": breakdown,
            },
            "table": {
                "title": self._rate_table_title(breakdown),
                "columns": [self._breakdown_label(breakdown), "检测胚胎数", "整倍体数", "整倍体率"],
                "rows": rows,
            },
            "chart": chart,
        }

    def _pgta_age_distribution(self, records: list[DetailRecord], filters: dict[str, str]) -> dict:
        groups = {
            "<35": [],
            "35-37": [],
            "38-40": [],
            "41-43": [],
            ">=44": [],
            "未填写": [],
        }
        for item in records:
            if item.age is None:
                groups["未填写"].append(item)
            elif item.age < 35:
                groups["<35"].append(item)
            elif item.age <= 37:
                groups["35-37"].append(item)
            elif item.age <= 40:
                groups["38-40"].append(item)
            elif item.age <= 43:
                groups["41-43"].append(item)
            else:
                groups[">=44"].append(item)

        rows = []
        chart_categories: list[str] = []
        chart_values: list[float] = []
        for label, items in groups.items():
            if not items:
                continue
            cycles = len({item.cycle_id for item in items})
            embryos = len(items)
            euploid = sum(1 for item in items if item.is_euploid)
            rate = _pct_value(euploid, embryos)
            rows.append([label, cycles, embryos, euploid, f"{rate:.1f}%"])
            if label != "未填写":
                chart_categories.append(label)
                chart_values.append(round(rate, 1))

        return {
            "metric_id": "pgta_age_distribution",
            "filters": filters,
            "summary": "已按女方年龄对当前 PGT-A 快照做分层，可用于观察不同年龄段的周期量和整倍体率差异。",
            "evidence": {
                "status": "ready",
                "record_count": len(records),
                "group_count": len(rows),
                "breakdown": "age",
            },
            "table": {
                "title": "PGT-A 年龄分层整倍体率",
                "columns": ["年龄段", "检测周期数", "检测胚胎数", "整倍体数", "整倍体率"],
                "rows": rows,
            },
            "chart": {
                "title": "年龄分层整倍体率",
                "chart_type": "bar",
                "categories": chart_categories,
                "series": [{"name": "整倍体率", "values": chart_values}],
            },
        }

    def _pgta_quality_overview(self, records: list[DetailRecord], filters: dict[str, str], breakdown: str) -> dict:
        total = len(records)
        cycle_count = len({item.cycle_id for item in records})
        detection_success_count = sum(1 for item in records if item.has_main_cnv_result)
        na_count = sum(1 for item in records if item.is_qc_fail)
        detection_success_rate = _pct(detection_success_count, total)
        avg_blastocyst = cycle_count and (total / cycle_count) or 0.0
        pass_count = sum(1 for item in records if item.qc_conclusion == "PASS")
        info_count = sum(1 for item in records if item.qc_conclusion == "INFO")
        fail_count = sum(1 for item in records if item.qc_conclusion == "FAIL")
        avg_bincv = round(mean([item.bincv for item in records if item.bincv is not None]), 4) if any(
            item.bincv is not None for item in records
        ) else 0.0

        warnings = [
            "扩增成功率在当前快照中缺少稳定可回溯的原始阈值口径，本轮暂不在执行结果里给出正式数值。"
        ]

        if breakdown in {"month", "quarter", "day"}:
            rows = []
            categories: list[str] = []
            success_values: list[float] = []
            for key, bucket in _group_records(records, breakdown).items():
                bucket_cycles = len({item.cycle_id for item in bucket})
                bucket_total = len(bucket)
                bucket_success = sum(1 for item in bucket if item.has_main_cnv_result)
                bucket_na = sum(1 for item in bucket if item.is_qc_fail)
                bucket_avg = bucket_total / bucket_cycles if bucket_cycles else 0.0
                success_rate_value = _pct_value(bucket_success, bucket_total)
                rows.append([key, bucket_cycles, bucket_total, bucket_na, f"{success_rate_value:.1f}%", f"{bucket_avg:.2f}"])
                categories.append(key)
                success_values.append(round(success_rate_value, 1))
            chart = {
                "title": "PGT-A 分时间检测成功率",
                "chart_type": "bar",
                "categories": categories,
                "series": [{"name": "检测成功率", "values": success_values}],
            }
            table = {
                "title": "PGT-A 分时间检测与质控总览",
                "columns": [self._breakdown_label(breakdown), "检测周期数", "检测胚胎数", "NA胚胎数", "检测成功率", "平均囊胚数"],
                "rows": rows,
            }
        elif breakdown == "qc":
            rows = [
                ["PASS", pass_count, _pct(pass_count, total)],
                ["INFO", info_count, _pct(info_count, total)],
                ["FAIL", fail_count, _pct(fail_count, total)],
            ]
            chart = {
                "title": "PGT-A 质控结论分布",
                "chart_type": "bar",
                "categories": ["PASS", "INFO", "FAIL"],
                "series": [{"name": "样本数", "values": [float(pass_count), float(info_count), float(fail_count)]}],
            }
            table = {
                "title": "PGT-A 质控结论分布",
                "columns": ["质控结论", "样本数", "占比"],
                "rows": rows,
            }
        else:
            rows = [
                ["检测周期数", cycle_count],
                ["检测胚胎数", total],
                ["平均囊胚数", f"{avg_blastocyst:.2f}"],
                ["检测成功率", detection_success_rate],
                ["NA胚胎数", na_count],
                ["PASS样本数", pass_count],
                ["INFO样本数", info_count],
                ["FAIL样本数", fail_count],
                ["BinCV均值", avg_bincv],
                ["扩增成功率", "待确认"],
            ]
            chart = {
                "title": "PGT-A 质控结论分布",
                "chart_type": "bar",
                "categories": ["PASS", "INFO", "FAIL"],
                "series": [{"name": "样本数", "values": [float(pass_count), float(info_count), float(fail_count)]}],
            }
            table = {
                "title": "PGT-A 检测与质控总览",
                "columns": ["指标", "值"],
                "rows": rows,
            }

        return {
            "metric_id": "pgta_quality_overview",
            "filters": filters,
            "summary": (
                f"当前快照下，PGT-A 检测周期数为 {cycle_count}，检测胚胎数为 {total}，"
                f"检测成功率为 {detection_success_rate}，平均囊胚数为 {avg_blastocyst:.2f}。"
            ),
            "evidence": {
                "status": "ready",
                "record_count": total,
                "cycle_count": cycle_count,
                "na_count": na_count,
                "breakdown": breakdown,
                "warnings": warnings,
            },
            "table": table,
            "chart": chart,
        }

    def _pgta_mosaic_abnormal(self, records: list[DetailRecord], filters: dict[str, str], breakdown: str) -> dict:
        if breakdown == "result":
            total = len(records)
            rows = [
                ["未见异常", sum(1 for item in records if item.is_euploid), _pct(sum(1 for item in records if item.is_euploid), total)],
                ["嵌合异常", sum(1 for item in records if item.is_mosaic), _pct(sum(1 for item in records if item.is_mosaic), total)],
                ["异常", sum(1 for item in records if item.is_abnormal), _pct(sum(1 for item in records if item.is_abnormal), total)],
                ["质控不合格", sum(1 for item in records if item.is_qc_fail), _pct(sum(1 for item in records if item.is_qc_fail), total)],
            ]
            return {
                "metric_id": "pgta_mosaic_abnormal",
                "filters": filters,
                "summary": "已按主报告结果解释拆分当前 PGT-A 胚胎结果结构。",
                "evidence": {"status": "ready", "record_count": total, "breakdown": breakdown},
                "table": {
                    "title": "PGT-A 结果结构分布",
                    "columns": ["结果类型", "样本数", "占比"],
                    "rows": rows,
                },
                "chart": {
                    "title": "PGT-A 结果结构分布",
                    "chart_type": "bar",
                    "categories": [row[0] for row in rows],
                    "series": [{"name": "样本数", "values": [float(row[1]) for row in rows]}],
                },
            }

        total = len(records)
        euploid = sum(1 for item in records if item.is_euploid)
        mosaic = sum(1 for item in records if item.is_mosaic)
        abnormal = sum(1 for item in records if item.is_abnormal)
        aneuploid = sum(1 for item in records if _is_aneuploid_label(item.aneuploidy_label))
        incidental = sum(1 for item in records if item.incidental_label == "有")

        rows = [
            ["整倍体胚胎数", euploid, _pct(euploid, total)],
            ["仅嵌合胚胎数", mosaic, _pct(mosaic, total)],
            ["异常胚胎数", abnormal, _pct(abnormal, total)],
            ["异倍体胚胎数", aneuploid, _pct(aneuploid, total)],
            ["意外发现胚胎数", incidental, _pct(incidental, total)],
        ]
        chart = {
            "title": "PGT-A 结果指标总览",
            "chart_type": "bar",
            "categories": [row[0] for row in rows],
            "series": [{"name": "占比", "values": [_ratio_value(row[2]) for row in rows]}],
        }

        return {
            "metric_id": "pgta_mosaic_abnormal",
            "filters": filters,
            "summary": (
                f"当前快照下，PGT-A 整倍体率为 {_pct(euploid, total)}，仅嵌合率为 {_pct(mosaic, total)}，"
                f"异常率为 {_pct(abnormal, total)}，意外发现率为 {_pct(incidental, total)}。"
            ),
            "evidence": {
                "status": "ready",
                "record_count": total,
                "breakdown": breakdown,
            },
            "table": {
                "title": "PGT-A 结果指标总览",
                "columns": ["指标", "样本数", "占比"],
                "rows": rows,
            },
            "chart": chart,
        }

    def _pgta_cycle_indicator_overview(self, records: list[DetailRecord], filters: dict[str, str], breakdown: str) -> dict:
        grouped = _group_records(records, breakdown if breakdown in {"month", "quarter"} else "overall")
        rows = []
        chart_categories: list[str] = []
        chart_values: list[float] = []

        for key, bucket in grouped.items():
            cycle_stats = _cycle_stats(bucket)
            total_cycles = len(cycle_stats)
            euploid_cycles = sum(1 for stats in cycle_stats.values() if stats["euploid"] > 0)
            no_euploid_cycles = sum(1 for stats in cycle_stats.values() if stats["euploid"] == 0)
            no_euploid_with_mosaic_cycles = sum(
                1
                for stats in cycle_stats.values()
                if stats["euploid"] == 0 and stats["mosaic"] > 0
            )
            single_euploid_cycles = sum(1 for stats in cycle_stats.values() if stats["euploid"] == 1)
            multi_euploid_cycles = sum(1 for stats in cycle_stats.values() if stats["euploid"] >= 2)
            rows.append(
                [
                    key,
                    total_cycles,
                    _pct(euploid_cycles, total_cycles),
                    _pct(no_euploid_cycles, total_cycles),
                    _pct(no_euploid_with_mosaic_cycles, total_cycles),
                    _pct(single_euploid_cycles, total_cycles),
                    _pct(multi_euploid_cycles, total_cycles),
                ]
            )
            chart_categories.append(key)
            chart_values.append(round(_pct_value(euploid_cycles, total_cycles), 1))

        total_cycles = len({item.cycle_id for item in records})
        chart = None
        if len(chart_categories) > 1:
            chart = {
                "title": "PGT-A 周期整倍体率",
                "chart_type": "bar",
                "categories": chart_categories,
                "series": [{"name": "周期整倍体率", "values": chart_values}],
            }

        return {
            "metric_id": "pgta_cycle_indicator_overview",
            "filters": filters,
            "summary": f"当前快照下，PGT-A 共覆盖 {total_cycles} 个检测周期，已统计周期整倍体结局及无整倍体相关指标。",
            "evidence": {"status": "ready", "record_count": len(records), "cycle_count": total_cycles, "breakdown": breakdown},
            "table": {
                "title": "PGT-A 周期结局总览",
                "columns": [self._breakdown_label(breakdown), "检测周期数", "周期整倍体率", "周期无整倍体率", "无整倍体且含仅嵌合", "周期仅1个整倍体率", "周期≥2个整倍体率"],
                "rows": rows,
            },
            "chart": chart,
        }

    def _pgta_special_cnv_overview(self, records: list[DetailRecord], filters: dict[str, str], breakdown: str) -> dict:
        grouped = _group_records(records, breakdown if breakdown in {"month", "quarter"} else "overall")
        rows = []
        for key, bucket in grouped.items():
            one_to_four = sum(1 for item in bucket if _is_syndrome_micro_cnv(item, 1, 4))
            four_to_ten_mosaic = sum(1 for item in bucket if _is_mosaic_cnv(item, 4, 10, 50, 100, require_syndrome=True))
            ten_plus_low_mosaic = sum(1 for item in bucket if _is_mosaic_cnv(item, 10, None, 20, 30, require_syndrome=False))
            pseudoautosomal = sum(1 for item in bucket if _is_pseudoautosomal_deletion(item))
            rows.append([key, one_to_four, four_to_ten_mosaic, ten_plus_low_mosaic, pseudoautosomal])

        return {
            "metric_id": "pgta_special_cnv_overview",
            "filters": filters,
            "summary": "已按医学部确认的附加规则统计当前快照中的特殊 CNV 提示，包括综合征相关微缺失/重复、特定比例嵌合异常和拟常染色体区域异常。",
            "evidence": {"status": "ready", "record_count": len(records), "breakdown": breakdown},
            "table": {
                "title": "PGT-A 特殊 CNV 提示总览",
                "columns": [self._breakdown_label(breakdown), "1Mb~4Mb 综合征相关提示", "4Mb~10Mb 且≥50%嵌合", "≥10Mb 且20%~30%嵌合", "拟常染色体区域缺失"],
                "rows": rows,
            },
            "chart": None,
        }

    def _euploid_rate_rows(
        self,
        records: list[DetailRecord],
        breakdown: str,
    ) -> tuple[list[list[str | int | str]], list[str], list[float]]:
        grouped = _group_records(records, breakdown if breakdown in {"month", "quarter", "day"} else "overall")
        rows: list[list[str | int | str]] = []
        categories: list[str] = []
        values: list[float] = []
        for key, bucket in grouped.items():
            total = len(bucket)
            euploid = sum(1 for item in bucket if item.is_euploid)
            rate_value = _pct_value(euploid, total)
            rows.append([key, total, euploid, f"{rate_value:.1f}%"])
            if breakdown != "overall":
                categories.append(key)
                values.append(round(rate_value, 1))
        return rows, categories, values

    def _breakdown_label(self, breakdown: str) -> str:
        mapping = {
            "overall": "时间",
            "month": "月份",
            "quarter": "季度",
            "day": "日期",
            "age": "年龄段",
            "result": "结果类型",
            "qc": "质控类型",
        }
        return mapping.get(breakdown, "维度")

    def _volume_table_title(self, breakdown: str) -> str:
        mapping = {
            "quarter": "按季度统计的 PGT-A 送检量",
            "day": "按日期统计的 PGT-A 送检量",
            "month": "按月份统计的 PGT-A 送检量",
            "overall": "PGT-A 送检量总览",
        }
        return mapping.get(breakdown, "PGT-A 送检量总览")

    def _volume_chart_title(self, breakdown: str) -> str:
        mapping = {
            "quarter": "PGT-A 季度检测胚胎数",
            "day": "PGT-A 日期检测胚胎数",
            "month": "PGT-A 月度检测胚胎数",
        }
        return mapping.get(breakdown, "PGT-A 检测胚胎数")

    def _rate_table_title(self, breakdown: str) -> str:
        mapping = {
            "month": "PGT-A 分月份整倍体率",
            "quarter": "PGT-A 分季度整倍体率",
            "day": "PGT-A 分日期整倍体率",
            "overall": "PGT-A 整倍体率总览",
        }
        return mapping.get(breakdown, "PGT-A 整倍体率总览")

    def _rate_chart_title(self, breakdown: str) -> str:
        mapping = {
            "month": "PGT-A 分月份整倍体率",
            "quarter": "PGT-A 分季度整倍体率",
            "day": "PGT-A 分日期整倍体率",
        }
        return mapping.get(breakdown, "PGT-A 整倍体率")


query_service = QueryService()


def _group_records(records: list[DetailRecord], breakdown: str) -> dict[str, list[DetailRecord]]:
    grouped: dict[str, list[DetailRecord]] = defaultdict(list)
    if breakdown == "overall":
        return {"总体": records}
    for item in records:
        grouped[_bucket_key(item, breakdown)].append(item)
    return dict(sorted(grouped.items(), key=lambda pair: pair[0]))


def _bucket_key(item: DetailRecord, breakdown: str) -> str:
    if breakdown == "quarter":
        year, month = _month_bucket_parts(item)
        return f"{year}Q{((month - 1) // 3 + 1)}"
    if breakdown == "day":
        return item.created_at.strftime("%Y-%m-%d")
    if breakdown == "month":
        year, month = _month_bucket_parts(item)
        return f"{year}-{month:02d}"
    return "总体"


def _month_bucket_parts(item: DetailRecord) -> tuple[int, int]:
    text = item.month_bucket.strip()
    for fmt in ("%Y-%m", "%Y/%m", "%Y年%m月"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.year, parsed.month
        except ValueError:
            continue
    return item.created_at.year, item.created_at.month


def _parse_time_filter(text: str) -> dict[str, int | date | None]:
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
    cn_day_match = re.search(r"(?:(20\d{2})年)?([1-9]|1[0-2])月([1-9]|[12]\d|3[01])[日号]", text)
    if cn_day_match:
        year = int(cn_day_match.group(1)) if cn_day_match.group(1) else None
        if year is not None:
            parsed = date(year, int(cn_day_match.group(2)), int(cn_day_match.group(3)))
            result["year"] = parsed.year
            result["month"] = parsed.month
            result["day"] = parsed.day
            result["start_day"] = parsed
            result["end_day"] = parsed
            return result
    short_cn_day_match = re.search(r"([2-3]\d)年([1-9]|1[0-2])月([1-9]|[12]\d|3[01])[日号]", text)
    if short_cn_day_match:
        parsed = date(int(f"20{short_cn_day_match.group(1)}"), int(short_cn_day_match.group(2)), int(short_cn_day_match.group(3)))
        result["year"] = parsed.year
        result["month"] = parsed.month
        result["day"] = parsed.day
        result["start_day"] = parsed
        result["end_day"] = parsed
        return result
    year_match = re.search(r"(20\d{2})", text)
    short_year_match = re.search(r"([2-3]\d)年", text)
    year = int(year_match.group(1)) if year_match else int(f"20{short_year_match.group(1)}") if short_year_match else None
    quarter_match = re.search(r"Q([1-4])|([1-4])季度", text, re.IGNORECASE)
    quarter = int(quarter_match.group(1) or quarter_match.group(2)) if quarter_match else None
    month_match = re.search(r"([1-9]|1[0-2])月", text)
    month = int(month_match.group(1)) if month_match else None
    result["year"] = year
    result["quarter"] = quarter
    result["month"] = month
    return result


def _cycle_stats(records: list[DetailRecord]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"euploid": 0, "mosaic": 0, "abnormal": 0})
    for item in records:
        stats[item.cycle_id]
        if item.is_euploid:
            stats[item.cycle_id]["euploid"] += 1
        if item.is_mosaic:
            stats[item.cycle_id]["mosaic"] += 1
        if item.is_abnormal:
            stats[item.cycle_id]["abnormal"] += 1
    return stats


def _hint_sizes(hint: str) -> list[float]:
    return [float(value) for value in re.findall(r"~([0-9]+(?:\.[0-9]+)?)Mb", hint or "", flags=re.IGNORECASE)]


def _hint_percentages(hint: str) -> list[int]:
    return [int(value) for value in re.findall(r"~(\d+)%", hint or "", flags=re.IGNORECASE)]


def _has_known_syndrome(detail: str) -> bool:
    text = detail or ""
    return "包含已知综合征" in text and "无已知综合征" not in text


def _is_syndrome_micro_cnv(item: DetailRecord, min_mb: float, max_mb: float) -> bool:
    hint = item.ldpgta_cnv_type or ""
    sizes = _hint_sizes(hint)
    return any(min_mb <= size < max_mb for size in sizes) and _has_known_syndrome(item.result_detail)


def _is_mosaic_cnv(
    item: DetailRecord,
    min_mb: float,
    max_mb: float | None,
    min_pct: int,
    max_pct: int,
    *,
    require_syndrome: bool,
) -> bool:
    if not item.is_mosaic:
        return False
    sizes = _hint_sizes(item.ldpgta_cnv_type)
    pcts = _hint_percentages(item.ldpgta_cnv_type)
    size_match = any(size >= min_mb and (max_mb is None or size < max_mb) for size in sizes)
    pct_match = any(min_pct <= pct <= max_pct for pct in pcts)
    if not (size_match and pct_match):
        return False
    return _has_known_syndrome(item.result_detail) if require_syndrome else True


def _is_pseudoautosomal_deletion(item: DetailRecord) -> bool:
    hint = (item.ldpgta_cnv_type or "").lower()
    detail = (item.result_detail or "").lower()
    return ("del(" in hint and "p22.33" in hint and "(x)" in hint) or ("x染色体p22.33" in detail and "缺失" in detail)


def _is_aneuploid_label(label: str) -> bool:
    text = label or ""
    return any(token in text for token in ("三倍体", "UPD", "ROH"))


def _pct_value(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator * 100


def _pct(numerator: int, denominator: int) -> str:
    return f"{_pct_value(numerator, denominator):.1f}%"


def _ratio_value(text: str) -> float:
    return float(text.rstrip("%")) if isinstance(text, str) and text.endswith("%") else 0.0
