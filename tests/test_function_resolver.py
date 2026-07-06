from yk_review_agent.models.intent import ParsedIntent
from yk_review_agent.services.function_resolver import function_resolver


def _parsed(*, breakdown: str = "overall", focus: str = "summary") -> ParsedIntent:
    return ParsedIntent(
        topic="测试",
        time_range="2025年",
        product_scope="PGT-A",
        breakdown=breakdown,
        focus=focus,
        normalized_message="",
    )


def test_cycle_outcome_has_priority_over_euploid_rate() -> None:
    resolution = function_resolver.resolve(
        message="看一下周期无整倍体率和周期整倍体结局",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_cycle_indicator_overview"
    assert resolution.candidate_metric_ids == ["pgta_cycle_indicator_overview"]


def test_special_cnv_has_priority_over_result_overview() -> None:
    resolution = function_resolver.resolve(
        message="看一下提示CNV和特殊 CNV 提示情况",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_special_cnv_overview"


def test_oral_special_cnv_question_routes_to_special_cnv_overview() -> None:
    resolution = function_resolver.resolve(
        message="想看一下意外发现里面那些1Mb到4Mb综合征相关提示多不多",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_special_cnv_overview"


def test_pseudoautosomal_question_routes_to_special_cnv_overview() -> None:
    resolution = function_resolver.resolve(
        message="拟常染色体区域缺失这块有多少个胚胎",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_special_cnv_overview"


def test_multi_topic_question_returns_multiple_candidates() -> None:
    resolution = function_resolver.resolve(
        message="看一下送检量和整倍体率",
        parsed=_parsed(),
    )

    assert resolution.metric_id is None
    assert resolution.candidate_metric_ids == ["pgt_total_volume", "pgta_euploid_rate"]


def test_age_breakdown_routes_to_euploid_rate_when_metric_is_euploid() -> None:
    resolution = function_resolver.resolve(
        message="按年龄分层看整倍体率",
        parsed=_parsed(breakdown="age"),
    )

    assert resolution.metric_id == "pgta_euploid_rate"
    assert resolution.candidate_metric_ids == ["pgta_euploid_rate"]


def test_cycle_dimension_overrides_age_breakdown_metric() -> None:
    resolution = function_resolver.resolve(
        message="按年龄分层，从周期维度去看下整体结局",
        parsed=_parsed(breakdown="age"),
    )

    assert resolution.metric_id == "pgta_cycle_indicator_overview"
    assert resolution.candidate_metric_ids == ["pgta_cycle_indicator_overview"]


def test_oral_volume_terms_route_to_total_volume() -> None:
    resolution = function_resolver.resolve(
        message="山西省妇幼保健院 2025年7月到2025年10月 35岁以上患者送检情况怎么样",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgt_total_volume"


def test_volume_trend_routes_to_total_volume() -> None:
    resolution = function_resolver.resolve(
        message="按季度看一下 PGT-A 的送检趋势",
        parsed=_parsed(breakdown="quarter", focus="trend"),
    )

    assert resolution.metric_id == "pgt_total_volume"
    assert resolution.candidate_metric_ids == ["pgt_total_volume"]


def test_avg_blastocyst_routes_to_quality_overview() -> None:
    resolution = function_resolver.resolve(
        message="25年PGT-A的平均囊胚数",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_quality_overview"
    assert resolution.candidate_metric_ids == ["pgta_quality_overview"]


def test_detection_success_rate_routes_to_quality_overview() -> None:
    resolution = function_resolver.resolve(
        message="2025年PGTA检测成功率是多少",
        parsed=_parsed(focus="rate"),
    )

    assert resolution.metric_id == "pgta_quality_overview"
    assert resolution.candidate_metric_ids == ["pgta_quality_overview"]


def test_avg_embryos_per_cycle_routes_to_total_volume() -> None:
    resolution = function_resolver.resolve(
        message="2025年PGT-A平均每周期胚胎数是多少",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgt_total_volume"
    assert resolution.candidate_metric_ids == ["pgt_total_volume"]


def test_multi_metric_oral_question_keeps_both_candidates() -> None:
    resolution = function_resolver.resolve(
        message="山西妇幼在25年7月到10月年龄大于35岁的患者送了多少周期，整倍体率如何",
        parsed=_parsed(),
    )

    assert resolution.metric_id is None
    assert resolution.candidate_metric_ids == ["pgt_total_volume", "pgta_euploid_rate"]


def test_cycle_angle_phrase_routes_to_cycle_indicator_overview() -> None:
    resolution = function_resolver.resolve(
        message="从周期角度分析无整倍体胚胎率",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_cycle_indicator_overview"
    assert resolution.candidate_metric_ids == ["pgta_cycle_indicator_overview"]


def test_explicit_cycle_euploid_outcome_phrase_routes_to_cycle_indicator_overview() -> None:
    resolution = function_resolver.resolve(
        message="看一下 PGT-A 的周期整倍体结局",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_cycle_indicator_overview"
    assert resolution.candidate_metric_ids == ["pgta_cycle_indicator_overview"]


def test_embryo_level_phrase_routes_to_embryo_euploid_rate() -> None:
    resolution = function_resolver.resolve(
        message="从胚胎层面看整倍体率",
        parsed=_parsed(),
    )

    assert resolution.metric_id == "pgta_euploid_rate"
    assert resolution.candidate_metric_ids == ["pgta_euploid_rate"]
