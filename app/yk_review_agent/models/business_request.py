from typing import Literal

from pydantic import BaseModel, Field


MetricSupportStatus = Literal["supported", "unsupported"]


class RequestedBusinessMetric(BaseModel):
    code: str
    label: str


class MetricCapability(BaseModel):
    code: str
    label: str
    status: MetricSupportStatus
    reason: str


class ProductCapability(BaseModel):
    product_code: str
    product_label: str
    metrics: list[MetricCapability] = Field(default_factory=list)


class StructuredBusinessRequest(BaseModel):
    request_kind: Literal["single_metric", "structured_business_request"] = "single_metric"
    requested_products: list[str] = Field(default_factory=list)
    requested_metrics: list[RequestedBusinessMetric] = Field(default_factory=list)
    includes_marecs: bool = False


class CapabilityMatrix(BaseModel):
    request_kind: Literal["single_metric", "structured_business_request"] = "single_metric"
    products: list[ProductCapability] = Field(default_factory=list)

    def to_human_lines(self) -> list[str]:
        lines: list[str] = []
        for product in self.products:
            supported = [metric.label for metric in product.metrics if metric.status == "supported"]
            unsupported = [metric.label for metric in product.metrics if metric.status == "unsupported"]
            if supported:
                lines.append(f"{product.product_label} 当前可支撑：{', '.join(supported)}。")
            if unsupported:
                lines.append(f"{product.product_label} 当前不支撑：{', '.join(unsupported)}。")
        return lines
