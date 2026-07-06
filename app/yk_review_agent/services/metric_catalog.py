from dataclasses import dataclass

from yk_review_agent.services.product_snapshot_registry import get_snapshot_registry


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    title: str
    description: str
    supported_products: tuple[str, ...]
    supported_filters: tuple[str, ...]
    supported_breakdowns: tuple[str, ...]
    supported_time_grains: tuple[str, ...]
    business_terms: tuple[str, ...]
    data_requirements: tuple[str, ...]
    unsupported_combinations: tuple[str, ...]
    default_card_types: tuple[str, ...]
    example_questions: tuple[str, ...]
    default_chart_type: str | None
    chart_goal: str | None
    min_chart_points: int = 2
    route_priority: int = 100
    hard_terms: tuple[str, ...] = ()
    soft_terms: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    disambiguation_notes: tuple[str, ...] = ()


METRICS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        metric_id="pgt_total_volume",
        title="PGT-A 送检量",
        description="基于 PGT-A 业务快照统计周期数、胚胎数和平均胚胎数",
        supported_products=("PGT-A",),
        supported_filters=("hospital_id", "hospital_name", "time_range", "age_range"),
        supported_breakdowns=("overall", "month", "quarter", "day"),
        supported_time_grains=("overall", "month", "quarter", "day"),
        business_terms=("送检量", "周期数", "胚胎数", "周期量", "胚胎量", "送检情况", "趋势"),
        data_requirements=("cycle_id", "sample_id", "review_time", "hospital"),
        unsupported_combinations=(),
        default_card_types=("summary", "table", "chart"),
        default_chart_type="bar",
        chart_goal="trend",
        example_questions=("看一下当前快照下的 PGT-A 送检量", "按季度看一下 PGT-A 送检趋势"),
        route_priority=70,
        hard_terms=("送检量", "送检情况", "送检趋势", "多少周期", "多少胚胎", "周期量", "胚胎量"),
        soft_terms=("送检", "周期数", "胚胎数", "平均每周期胚胎数", "送了多少"),
        aliases=("volume",),
        disambiguation_notes=("当问题只提周期无整倍体或周期结局时，不应落到送检量。",),
    ),
    MetricDefinition(
        metric_id="pgta_euploid_rate",
        title="PGT-A 整倍体率",
        description="统计整倍体数和整倍体率",
        supported_products=("PGT-A",),
        supported_filters=("hospital_id", "hospital_name", "time_range", "age_range"),
        supported_breakdowns=("overall", "month", "quarter", "day", "age"),
        supported_time_grains=("overall", "month", "quarter", "day"),
        business_terms=("整倍体率", "整倍体", "euploid"),
        data_requirements=("result_label", "review_time", "hospital"),
        unsupported_combinations=("qc",),
        default_card_types=("summary", "table", "chart"),
        default_chart_type="bar",
        chart_goal="trend",
        example_questions=("按月看一下 PGT-A 整倍体率变化", "2025年 PGT-A 的整倍体率是多少"),
        route_priority=60,
        hard_terms=("整倍体率", "euploid"),
        soft_terms=("整倍体", "时间趋势", "变化趋势"),
        aliases=("euploid_rate",),
        disambiguation_notes=("年龄分层是 breakdown，不是独立指标。",),
    ),
    MetricDefinition(
        metric_id="pgta_quality_overview",
        title="PGT-A 检测与质控总览",
        description="统计检测周期数、检测胚胎数、平均囊胚数、检测成功率和质控分布",
        supported_products=("PGT-A",),
        supported_filters=("hospital_id", "hospital_name", "time_range", "age_range"),
        supported_breakdowns=("overall", "month", "quarter", "day", "qc"),
        supported_time_grains=("overall", "month", "quarter", "day"),
        business_terms=("质控", "检测成功率", "PASS", "FAIL", "INFO", "NA", "检测周期数", "检测胚胎数", "平均囊胚数"),
        data_requirements=("cycle_id", "sample_id", "qc_result", "result_label", "bin_cv", "stat_month"),
        unsupported_combinations=("age", "result"),
        default_card_types=("summary", "table", "chart"),
        default_chart_type="bar",
        chart_goal="distribution",
        example_questions=("看一下当前快照下的 PGT-A 质控情况", "2025年 PGT-A 的检测成功率和平均囊胚数"),
        route_priority=40,
        hard_terms=("质控", "检测成功率", "扩增成功率", "NA率", "NA数", "PASS", "FAIL", "INFO"),
        soft_terms=("检测周期数", "检测胚胎数", "平均囊胚数"),
        aliases=("quality", "qc"),
        disambiguation_notes=("整倍体率与质控同时出现时应触发组合冲突。",),
    ),
    MetricDefinition(
        metric_id="pgta_mosaic_abnormal",
        title="PGT-A 嵌合与异常结构",
        description="统计整倍体率、嵌合率、异常率、结果结构和主要附加发现指标",
        supported_products=("PGT-A",),
        supported_filters=("hospital_id", "hospital_name", "time_range", "age_range"),
        supported_breakdowns=("overall", "month", "quarter", "day", "result"),
        supported_time_grains=("overall", "month", "quarter", "day"),
        business_terms=("嵌合", "异常结构", "异常率", "结果分布", "结果结构", "嵌合率", "异倍体率", "意外发现率", "提示CNV"),
        data_requirements=("result_label", "result_detail", "cnv_hint", "review_time", "hospital", "incidental_label", "aneuploidy_label"),
        unsupported_combinations=("qc",),
        default_card_types=("summary", "table", "chart"),
        default_chart_type="bar",
        chart_goal="distribution",
        example_questions=("看一下 PGT-A 的结果分布", "看一下 PGT-A 的嵌合与异常结构", "看一下 PGT-A 的意外发现率和异倍体率"),
        route_priority=50,
        hard_terms=("嵌合", "异常结构", "结果分布", "结果结构", "嵌合率", "异常率", "异倍体率", "意外发现率", "意外发现"),
        soft_terms=("异倍体", "异常"),
        aliases=("mosaic", "abnormal"),
        disambiguation_notes=("CNV 特异提示应优先落到特殊 CNV 指标。",),
    ),
    MetricDefinition(
        metric_id="pgta_cycle_indicator_overview",
        title="PGT-A 周期结局总览",
        description="统计周期无整倍体率、周期整倍体率及整倍体数量分层",
        supported_products=("PGT-A",),
        supported_filters=("hospital_id", "hospital_name", "time_range", "age_range"),
        supported_breakdowns=("overall", "month", "quarter", "age"),
        supported_time_grains=("overall", "month", "quarter"),
        business_terms=("周期无整倍体", "周期整倍体率", "仅1个整倍体", ">=2个整倍体", "无整倍体且含有仅嵌合"),
        data_requirements=("cycle_id", "sample_id", "result_label", "stat_month"),
        unsupported_combinations=("day", "qc", "result"),
        default_card_types=("summary", "table", "chart"),
        default_chart_type="bar",
        chart_goal="comparison",
        example_questions=("看一下 PGT-A 的周期无整倍体率", "看一下 PGT-A 的周期整倍体结局"),
        route_priority=10,
        hard_terms=(
            "周期无整倍体",
            "周期整倍体率",
            "周期整倍体结局",
            "周期结局",
            "周期维度",
            "周期层面",
            "从周期角度",
            "按周期看",
            "每周期",
            "整体结局",
            "仅1个整倍体",
            "只有1个整倍体",
            ">=2个整倍体",
            "≥2个整倍体",
            "大于等于2个整倍体",
            "无整倍体且含有仅嵌合",
        ),
        soft_terms=("周期整倍体", "无整倍体胚胎率"),
        aliases=("cycle_outcome",),
        disambiguation_notes=("周期结局应始终高于整倍体率和送检量路由。",),
    ),
    MetricDefinition(
        metric_id="pgta_special_cnv_overview",
        title="PGT-A 特殊 CNV 提示总览",
        description="统计 1Mb~4Mb、4Mb~10Mb、>=10Mb 嵌合提示和拟常染色体区域异常",
        supported_products=("PGT-A",),
        supported_filters=("hospital_id", "hospital_name", "time_range", "age_range"),
        supported_breakdowns=("overall", "month", "quarter"),
        supported_time_grains=("overall", "month", "quarter"),
        business_terms=("1Mb", "4Mb", "10Mb", "提示CNV", "综合征", "拟常染色体", "p22.33"),
        data_requirements=("cnv_hint", "result_detail", "incidental_label", "sample_id", "stat_month"),
        unsupported_combinations=("day", "age", "qc", "result"),
        default_card_types=("summary", "table"),
        default_chart_type=None,
        chart_goal=None,
        example_questions=("看一下 PGT-A 的特殊 CNV 提示情况", "看一下 1Mb~4Mb 综合征相关提示和拟常染色体区域异常"),
        route_priority=20,
        hard_terms=("1Mb", "4Mb", "10Mb", "提示CNV", "CNV提示", "特殊 CNV", "特殊CNV", "综合征", "拟常染色体", "p22.33"),
        soft_terms=("CNV",),
        aliases=("special_cnv",),
        disambiguation_notes=("特殊 CNV 命中时不应落到普通结果结构指标。",),
    ),
    MetricDefinition(
        metric_id="pgtsr_stage2_noncarrier",
        title="PGT-SR 二阶段不携带率",
        description="统计二阶段进入情况和不携带率",
        supported_products=("PGT-SR",),
        supported_filters=("hospital_id", "hospital_name", "time_range"),
        supported_breakdowns=("overall",),
        supported_time_grains=("overall",),
        business_terms=("二阶段", "不携带率"),
        data_requirements=("stage2", "noncarrier"),
        unsupported_combinations=(),
        default_card_types=("summary", "table"),
        default_chart_type=None,
        chart_goal=None,
        example_questions=(),
    ),
    MetricDefinition(
        metric_id="pgtm_disease_distribution",
        title="PGT-M 病种分布",
        description="统计病种或基因 TopN 分布",
        supported_products=("PGT-M",),
        supported_filters=("hospital_id", "hospital_name", "time_range"),
        supported_breakdowns=("overall",),
        supported_time_grains=("overall",),
        business_terms=("病种", "基因"),
        data_requirements=("gene_name", "disease_name"),
        unsupported_combinations=(),
        default_card_types=("summary", "table"),
        default_chart_type=None,
        chart_goal=None,
        example_questions=(),
    ),
)


def list_metric_ids() -> list[str]:
    return [item.metric_id for item in METRICS]


def get_metric(metric_id: str) -> MetricDefinition | None:
    for item in METRICS:
        if item.metric_id == metric_id:
            return item
    return None


SUPPORTED_DOMAIN_TERMS: tuple[str, ...] = (
    "PGT",
    "PGT-A",
    "整倍体",
    "胚胎",
    "周期",
    "送检",
    "质控",
    "检测",
    "嵌合",
    "异常",
    "年龄",
    "医院",
    "结果分布",
    "CNV",
    "意外发现",
    "综合征",
    "拟常染色体",
    "p22.33",
)

def active_data_capabilities(product_code: str = "PGT-A") -> frozenset[str]:
    return get_snapshot_registry().active_capabilities(product_code)

CLARIFY_PROMPTS: list[str] = [
    "看一下当前快照下的 PGT-A 送检量",
    "按月看一下 PGT-A 整倍体率变化",
    "按年龄分层看一下 PGT-A 的整倍体率",
    "看一下当前快照下的 PGT-A 质控情况",
    "看一下 PGT-A 的结果分布",
    "看一下 PGT-A 的周期整倍体结局",
]

REFUSE_SUGGESTIONS: list[str] = [
    "看一下当前快照下的 PGT-A 送检量",
    "按月看一下 PGT-A 整倍体率变化",
    "按年龄分层看一下 PGT-A 的整倍体率",
]

ROUTABLE_METRICS: tuple[MetricDefinition, ...] = tuple(
    sorted(
        (
            metric
            for metric in METRICS
            if metric.metric_id
            in {
                "pgt_total_volume",
                "pgta_euploid_rate",
                "pgta_quality_overview",
                "pgta_mosaic_abnormal",
                "pgta_cycle_indicator_overview",
                "pgta_special_cnv_overview",
            }
        ),
        key=lambda metric: metric.route_priority,
    )
)
