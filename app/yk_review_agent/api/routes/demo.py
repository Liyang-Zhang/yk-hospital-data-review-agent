from fastapi import APIRouter

from yk_review_agent.services.pgta_record_source import get_pgta_record_source
from yk_review_agent.services.snapshot_service import snapshot_service

router = APIRouter()


@router.get("/demo/metadata")
def demo_metadata() -> dict:
    dataset = get_pgta_record_source()
    snapshot = snapshot_service.get_snapshot_metadata()
    hospitals = dataset.hospitals
    return {
        "product_scope": snapshot.product_scope,
        "data_source": snapshot.data_source,
        "snapshot_start": snapshot.snapshot_start,
        "snapshot_end": snapshot.snapshot_end,
        "hospital_count": snapshot.hospital_count,
        "capability_overview": {
            "supported_topics": [
                "送检量与周期规模",
                "整倍体率与时间趋势",
                "年龄分层整倍体率",
                "质控情况与检测成功率",
                "结果分布与嵌合异常结构",
            ],
            "supported_dimensions": [
                "按医院",
                "按月",
                "按季度",
                "按日期",
                "按年龄段",
                "按年龄范围筛选",
            ],
            "available_context": [
                "医院",
                "时间",
                "周期",
                "胚胎",
                "年龄",
                "检测结果",
                "质控结果",
            ],
            "unsupported_topics": [
                "意外发现",
                "临床指征",
                "流产/种植失败占比",
                "PGT-SR 二阶段",
                "PGT-M 病种分析",
            ],
            "guidance": [
                "优先直接描述你想看的指标，例如整倍体率、送检量、质控情况。",
                "可以加时间范围，例如 2025年7月、Q3、7月15号。",
                "可以说明分析方式，例如按月看趋势、按年龄分层、看结果分布。",
                "也可以加年龄范围，例如 >35岁、35-37岁、未填写年龄。",
            ],
            "limitations": snapshot.limitations,
        },
        "default_hospital": hospitals[0] if hospitals else None,
        "hospitals": hospitals[:20],
    }
