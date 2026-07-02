from __future__ import annotations

from dataclasses import dataclass

from yk_review_agent.models.business_request import (
    CapabilityMatrix,
    MetricCapability,
    ProductCapability,
    RequestedBusinessMetric,
    StructuredBusinessRequest,
)
from yk_review_agent.services.product_snapshot_registry import get_snapshot_registry


@dataclass(frozen=True)
class BusinessMetricDefinition:
    code: str
    label: str
    aliases: tuple[str, ...]


BUSINESS_METRICS: tuple[BusinessMetricDefinition, ...] = (
    BusinessMetricDefinition("cycle_count", "周期数", ("周期数", "家系周期数")),
    BusinessMetricDefinition("embryo_count", "胚胎数", ("胚胎数",)),
    BusinessMetricDefinition("amplification_success_rate", "扩增成功率", ("扩增成功率",)),
    BusinessMetricDefinition("na_rate", "NA率", ("NA率", "na率", "NA 胎胚数", "NA胚胎数")),
    BusinessMetricDefinition("euploid_rate", "整倍体率", ("整倍体率",)),
    BusinessMetricDefinition("abnormal_rate", "异常率", ("异常率",)),
    BusinessMetricDefinition("mosaic_only_rate", "嵌合率（仅嵌合）", ("嵌合率", "仅嵌合", "嵌合率（仅嵌合）")),
    BusinessMetricDefinition("incidental_rate", "意外发现率", ("意外发现率", "意外发现")),
)

PRODUCT_ALIASES: dict[str, tuple[str, ...]] = {
    "PGT-A": ("PGT-A", "PGTA"),
    "PGT-AH": ("PGT-AH", "PGTAH"),
    "PGT-SR": ("PGT-SR", "PGTSR", "SR"),
    "PGT-M": ("PGT-M", "PGTM"),
}


class BusinessRequestService:
    def parse(self, message: str) -> StructuredBusinessRequest:
        requested_products = self._extract_products(message)
        requested_metrics = self._extract_metrics(message)
        includes_marecs = "marecs" in message.lower()
        is_structured = bool(requested_products or requested_metrics) and (
            "所有PGT项目" in message or len(requested_products) > 1 or len(requested_metrics) > 1
        )
        return StructuredBusinessRequest(
            request_kind="structured_business_request" if is_structured else "single_metric",
            requested_products=requested_products,
            requested_metrics=requested_metrics,
            includes_marecs=includes_marecs,
        )

    def build_capability_matrix(self, request: StructuredBusinessRequest) -> CapabilityMatrix:
        if request.request_kind != "structured_business_request":
            return CapabilityMatrix()

        products = request.requested_products or ["PGT-A", "PGT-SR", "PGT-M"]
        matrix_products: list[ProductCapability] = []
        for product in products:
            metrics: list[MetricCapability] = []
            for metric in request.requested_metrics:
                metrics.append(self._metric_capability_for(product, metric))
            matrix_products.append(
                ProductCapability(
                    product_code=product,
                    product_label=self._product_label(product, request.includes_marecs),
                    metrics=metrics,
                )
            )
        return CapabilityMatrix(
            request_kind="structured_business_request",
            products=matrix_products,
        )

    def _metric_capability_for(self, product: str, metric: RequestedBusinessMetric) -> MetricCapability:
        registry = get_snapshot_registry()
        profile = registry.get_profile(product)

        if product != "PGT-A":
            return MetricCapability(
                code=metric.code,
                label=metric.label,
                status="unsupported",
                reason=(
                    f"当前已接入 {profile.data_source if profile else product} 快照，"
                    "但该产品尚未接入真实统计执行函数层。"
                ),
            )

        supported_now = {
            "cycle_count",
            "embryo_count",
            "na_rate",
            "euploid_rate",
            "abnormal_rate",
            "mosaic_only_rate",
        }
        if metric.code in supported_now:
            return MetricCapability(
                code=metric.code,
                label=metric.label,
                status="supported",
                reason="当前 PGT-A 文件快照具备对应统计所需的核心业务字段。",
            )

        unsupported_reasons = {
            "amplification_success_rate": "当前已拿到快照字段，但尚未把扩增成功率沉淀成稳定的业务级原子指标函数。",
            "incidental_rate": "当前快照包含人工处理后的意外发现字段，但产品口径和执行函数层仍未收口。",
        }
        return MetricCapability(
            code=metric.code,
            label=metric.label,
            status="unsupported",
            reason=unsupported_reasons.get(metric.code, "当前第一版未对该指标建立稳定执行能力。"),
        )

    def _extract_products(self, message: str) -> list[str]:
        products: list[str] = []
        lowered = message.lower()
        if "所有pgt项目" in lowered or "所有PGT项目" in message or "全部pgt项目" in lowered:
            return ["PGT-A", "PGT-SR", "PGT-M"]

        for product_code, aliases in PRODUCT_ALIASES.items():
            if any(alias.lower() in lowered for alias in aliases):
                products.append(product_code)
        return products

    def has_explicit_product_scope(self, message: str) -> bool:
        lowered = message.lower()
        if "所有pgt项目" in lowered or "所有PGT项目" in message or "全部pgt项目" in lowered:
            return True
        return bool(self._extract_products(message))

    def _extract_metrics(self, message: str) -> list[RequestedBusinessMetric]:
        metrics: list[RequestedBusinessMetric] = []
        for definition in BUSINESS_METRICS:
            if any(alias in message for alias in definition.aliases):
                metrics.append(RequestedBusinessMetric(code=definition.code, label=definition.label))
        return metrics

    def _product_label(self, product: str, includes_marecs: bool) -> str:
        if product == "PGT-SR" and includes_marecs:
            return "PGT-SR（含 MARECS）"
        return product


business_request_service = BusinessRequestService()
