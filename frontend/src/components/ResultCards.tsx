import { useState } from "react";

import type { ChatResponse, ResultCard } from "../lib/api";

type Props = {
  response: ChatResponse;
};

export function ResultCards({ response }: Props) {
  const cards = response.result_cards;
  const mode = response.structured_answer.presentation_mode;

  const summaryCard = cards.find((card) => card.type === "summary");
  const tableCard = cards.find((card) => card.type === "table");
  const chartCard = cards.find((card) => card.type === "chart");

  const content =
    mode === "trend" ? (
      <div className="answer-layout answer-layout-trend">
        {summaryCard ? <SummaryCard card={summaryCard} featured /> : null}
        {chartCard ? <ChartSection card={chartCard} featured /> : null}
        {tableCard ? <TableSection card={tableCard} collapsible /> : null}
      </div>
    ) : mode === "distribution" ? (
      <div className="answer-layout answer-layout-distribution">
        {summaryCard ? <SummaryCard card={summaryCard} featured /> : null}
        <div className="distribution-grid">
          {chartCard ? <ChartSection card={chartCard} /> : null}
          {tableCard ? <TableSection card={tableCard} collapsible={response.structured_answer.evidence_density === "dense"} /> : null}
        </div>
      </div>
    ) : mode === "detail_heavy" ? (
      <div className="answer-layout answer-layout-detail">
        {summaryCard ? <SummaryCard card={summaryCard} featured /> : null}
        {tableCard ? <TableSection card={tableCard} collapsible /> : null}
        {chartCard ? <ChartSection card={chartCard} /> : null}
      </div>
    ) : (
      <div className="answer-layout answer-layout-overview">
        {summaryCard ? <SummaryCard card={summaryCard} featured /> : null}
        <div className="overview-grid">
          {tableCard ? <TableSection card={tableCard} /> : null}
          {chartCard ? <ChartSection card={chartCard} /> : null}
        </div>
      </div>
    );

  return (
    <div className="answer-stack">
      {response.snapshot_metadata ? <SnapshotMetadataPanel response={response} /> : null}
      {response.data_readiness ? <DataReadinessPanel response={response} /> : null}
      {response.analysis_task ? <AnalysisTaskPanel response={response} /> : null}
      {response.capability_report ? <CapabilityReportPanel response={response} /> : null}
      {import.meta.env.DEV && response.route_trace ? <RouteTracePanel response={response} /> : null}
      {content}
    </div>
  );
}

function SnapshotMetadataPanel({ response }: Props) {
  const snapshot = response.snapshot_metadata;
  if (!snapshot) {
    return null;
  }

  return (
    <section className="result-card result-card-snapshot">
      <div className="result-card-label">当前快照上下文</div>
      <p className="result-card-content">
        数据源 {snapshot.data_source}，当前产品范围 {snapshot.product_scope}，时间快照 {snapshot.snapshot_start.slice(0, 10)} 至{" "}
        {snapshot.snapshot_end.slice(0, 10)}，覆盖 {snapshot.hospital_count} 家医院。
      </p>
    </section>
  );
}

function DataReadinessPanel({ response }: Props) {
  const readiness = response.data_readiness;
  if (!readiness) {
    return null;
  }

  return (
    <section className={`result-card result-card-readiness result-card-readiness-${readiness.status}`}>
      <div className="result-card-head">
        <div className="result-card-label">当前问题可执行性</div>
        <div className={`task-status-pill task-status-${readiness.status === "ready" ? "completed" : readiness.status === "no_data" ? "clarify" : "blocked"}`}>
          {readiness.status === "ready" ? "可执行" : readiness.status === "no_data" ? "无命中数据" : "受限"}
        </div>
      </div>
      <p className="result-card-content">{readiness.summary}</p>
      {readiness.missing_fields.length ? (
        <div className="readiness-detail">缺失字段：{readiness.missing_fields.join("、")}</div>
      ) : null}
      {readiness.limitations.length ? (
        <div className="readiness-detail">限制说明：{readiness.limitations.join("；")}</div>
      ) : null}
      {readiness.status !== "ready" ? (
        <div className="readiness-detail">建议补充更明确的指标、时间范围或筛选条件后再继续提问。</div>
      ) : null}
    </section>
  );
}

function AnalysisTaskPanel({ response }: Props) {
  const task = response.analysis_task;
  if (!task) {
    return null;
  }

  return (
    <section className="result-card result-card-task">
      <div className="result-card-head">
        <div className="result-card-label">{task.title}</div>
        <div className={`task-status-pill task-status-${task.status}`}>
          {task.status === "completed" ? "已完成" : task.status === "clarify" ? "待补充" : "受限"}
        </div>
      </div>
      <div className="task-step-list">
        {task.steps.map((step) => (
          <div className="task-step" key={`${task.title}-${step.title}`}>
            <div className="task-step-row">
              <span className={`task-step-dot task-step-dot-${step.status}`} />
              <span className="task-step-title">{step.title}</span>
            </div>
            {step.detail ? <div className="task-step-detail">{step.detail}</div> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function CapabilityReportPanel({ response }: Props) {
  const report = response.capability_report;
  if (!report) {
    return null;
  }

  return (
    <section className="result-card result-card-capability">
      <div className="result-card-label">{report.title}</div>
      <p className="result-card-content">{report.summary}</p>
      <div className="capability-report-products">
        {report.products.map((product) => (
          <div className="capability-report-product" key={product.product_code}>
            <div className="capability-report-product-title">{product.product_label}</div>
            <div className="capability-report-metrics">
              {product.metrics.map((metric) => (
                <div className="capability-report-metric" key={`${product.product_code}-${metric.code}`}>
                  <div className="capability-report-metric-head">
                    <span className="capability-report-metric-label">{metric.label}</span>
                    <span
                      className={
                        metric.status === "supported"
                          ? "capability-badge capability-badge-supported"
                          : "capability-badge capability-badge-unsupported"
                      }
                    >
                      {metric.status === "supported" ? "可支撑" : "未支撑"}
                    </span>
                  </div>
                  <div className="capability-report-metric-reason">{metric.reason}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RouteTracePanel({ response }: Props) {
  const trace = response.route_trace;
  if (!trace) {
    return null;
  }
  const statusClass =
    trace.answer_mode === "answer"
      ? "completed"
      : trace.answer_mode === "clarify"
        ? "clarify"
        : "blocked";

  return (
    <section className="result-card result-card-trace">
      <div className="result-card-head">
        <div className="result-card-label">开发调试路由 Trace</div>
        <div className={`task-status-pill task-status-${statusClass}`}>{trace.answer_mode}</div>
      </div>
      <div className="readiness-detail">原始问题：{trace.raw_message}</div>
      <div className="readiness-detail">规范化：{trace.normalized_message}</div>
      <div className="readiness-detail">Filters：{Object.entries(trace.filters).map(([key, value]) => `${key}=${value}`).join("；") || "无"}</div>
      <div className="readiness-detail">候选函数：{trace.candidate_metric_ids.join("、") || "无"}</div>
      <div className="readiness-detail">最终函数：{trace.resolved_metric_id ?? "无"}</div>
      <div className={`trace-rationale trace-rationale-${statusClass}`}>{trace.rationale}</div>
    </section>
  );
}

function SummaryCard({ card, featured = false }: { card: Extract<ResultCard, { type: "summary" }>; featured?: boolean }) {
  return (
    <section className={`result-card result-card-summary${featured ? " result-card-featured" : ""}`}>
      <div className="result-card-label">{card.title}</div>
      <p className="result-card-content">{card.content}</p>
    </section>
  );
}

function TableSection({
  card,
  collapsible = false,
}: {
  card: Extract<ResultCard, { type: "table" }>;
  collapsible?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const table = card.table;
  const visibleRows = collapsible && !expanded && table.preview_rows?.length ? table.preview_rows : table.rows;
  const canExpand = collapsible && Boolean(table.has_more_rows);

  return (
    <section className="result-card result-card-table">
      <div className="result-card-head">
        <div className="result-card-label">{card.title}</div>
        {typeof table.total_rows === "number" ? (
          <div className="result-card-meta">共 {table.total_rows} 行</div>
        ) : null}
      </div>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr key={`${card.title}-${rowIndex}`}>
                {row.map((value, valueIndex) => (
                  <td key={`${rowIndex}-${valueIndex}`}>{value}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {canExpand ? (
        <button
          className="table-toggle"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? "收起明细" : `查看全部明细（${table.total_rows} 行）`}
        </button>
      ) : null}
    </section>
  );
}

function ChartSection({
  card,
  featured = false,
}: {
  card: Extract<ResultCard, { type: "chart" }>;
  featured?: boolean;
}) {
  return (
    <section className={`result-card result-card-chart${featured ? " result-card-chart-hero" : ""}`}>
      <div className="result-card-label">{card.title}</div>
      <ChartCard card={card} featured={featured} />
    </section>
  );
}

function ChartCard({
  card,
  featured = false,
}: {
  card: Extract<ResultCard, { type: "chart" }>;
  featured?: boolean;
}) {
  const chart = card.chart;
  const series = chart.series[0];
  const values = series?.values ?? [];
  const categories = chart.categories;

  if (!series || !categories.length) {
    return <div className="chart-empty">当前图表没有可展示的数据点。</div>;
  }

  if (chart.chart_type === "line") {
    return <LineChart categories={categories} values={values} featured={featured} />;
  }

  if (chart.chart_type === "pie") {
    return <PieChart categories={categories} values={values} />;
  }

  return <BarChart categories={categories} values={values} featured={featured} />;
}

function BarChart({
  categories,
  values,
  featured = false,
}: {
  categories: string[];
  values: number[];
  featured?: boolean;
}) {
  const maxValue = Math.max(...values, 1);
  const step = featured ? 96 : 84;
  const chartWidth = Math.max(featured ? 720 : 360, categories.length * step);
  const chartHeight = featured ? 320 : 220;
  const innerHeight = featured ? 232 : 156;
  const barWidth = featured ? 34 : 28;
  const topOffset = featured ? 26 : 18;
  const labelStride = featured ? _labelStride(categories.length, 10) : _labelStride(categories.length, 6);

  return (
    <div className={`chart-shell${featured ? " chart-shell-featured" : ""}`}>
      <div className="chart-scroll">
        <svg
          aria-label="bar chart"
          className="chart-svg"
          role="img"
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        >
          <line className="chart-baseline" x1="24" x2={chartWidth - 24} y1={chartHeight - 40} y2={chartHeight - 40} />
          {categories.map((category, index) => {
            const value = values[index] ?? 0;
            const scaledHeight = Math.max(12, (value / maxValue) * innerHeight);
            const x = 42 + index * step;
            const y = chartHeight - 40 - scaledHeight;
            const showLabel = index % labelStride === 0 || index === categories.length - 1;
            return (
              <g key={category}>
                <text className="chart-number" textAnchor="middle" x={x + barWidth / 2} y={y - 8}>
                  {formatValue(value)}
                </text>
                <rect
                  className="chart-rect"
                  height={scaledHeight}
                  rx="10"
                  ry="10"
                  width={barWidth}
                  x={x}
                  y={y}
                />
                {showLabel ? (
                  <text className="chart-label" textAnchor="middle" x={x + barWidth / 2} y={chartHeight - topOffset}>
                    {shortLabel(category)}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

function LineChart({
  categories,
  values,
  featured = false,
}: {
  categories: string[];
  values: number[];
  featured?: boolean;
}) {
  const maxValue = Math.max(...values, 1);
  const chartWidth = Math.max(featured ? 720 : 360, categories.length * (featured ? 100 : 88));
  const chartHeight = featured ? 320 : 220;
  const baselineY = chartHeight - 40;
  const step = categories.length > 1 ? (chartWidth - 72) / (categories.length - 1) : 0;
  const labelStride = featured ? _labelStride(categories.length, 10) : _labelStride(categories.length, 6);

  const points = categories.map((category, index) => {
    const value = values[index] ?? 0;
    const x = 36 + index * step;
    const y = baselineY - (value / maxValue) * (featured ? 232 : 136);
    return { category, value, x, y };
  });

  const polylinePoints = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className={`chart-shell${featured ? " chart-shell-featured" : ""}`}>
      <div className="chart-scroll">
        <svg
          aria-label="line chart"
          className="chart-svg"
          role="img"
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        >
          <line className="chart-baseline" x1="24" x2={chartWidth - 24} y1={baselineY} y2={baselineY} />
          <polyline className="chart-line" fill="none" points={polylinePoints} />
          {points.map((point, index) => {
            const showLabel = index % labelStride === 0 || index === points.length - 1;
            return (
              <g key={point.category}>
                <circle className="chart-point" cx={point.x} cy={point.y} r="5" />
                <text className="chart-number" textAnchor="middle" x={point.x} y={point.y - 10}>
                  {formatValue(point.value)}
                </text>
                {showLabel ? (
                  <text className="chart-label" textAnchor="middle" x={point.x} y={chartHeight - 16}>
                    {shortLabel(point.category)}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

function PieChart({ categories, values }: { categories: string[]; values: number[] }) {
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    return <div className="chart-empty">当前图表没有可展示的数据点。</div>;
  }

  const radius = 72;
  const center = 96;
  const palette = ["#1f5c4b", "#3f7d67", "#7da28b", "#b4c7ba", "#d8e4dd"];
  let angleCursor = -Math.PI / 2;

  return (
    <div className="chart-shell chart-shell-pie">
      <svg aria-label="pie chart" className="chart-pie-svg" role="img" viewBox="0 0 192 192">
        {values.map((value, index) => {
          const angle = (value / total) * Math.PI * 2;
          const nextAngle = angleCursor + angle;
          const path = describeArc(center, center, radius, angleCursor, nextAngle);
          const fill = palette[index % palette.length];
          angleCursor = nextAngle;
          return <path d={path} fill={fill} key={`${categories[index]}-${value}`} />;
        })}
      </svg>
      <div className="pie-legend">
        {categories.map((category, index) => (
          <div className="pie-legend-item" key={category}>
            <span
              className="pie-legend-swatch"
              style={{ backgroundColor: palette[index % palette.length] }}
            />
            <span className="pie-legend-label">{category}</span>
            <span className="pie-legend-value">{formatValue(values[index] ?? 0)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= Math.PI ? "0" : "1";
  return [
    `M ${cx} ${cy}`,
    `L ${start.x} ${start.y}`,
    `A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`,
    "Z",
  ].join(" ");
}

function polarToCartesian(cx: number, cy: number, r: number, angle: number) {
  return {
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle),
  };
}

function formatValue(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function shortLabel(label: string) {
  if (label.length <= 10) {
    return label;
  }
  return `${label.slice(0, 10)}…`;
}

function _labelStride(count: number, targetVisible: number) {
  if (count <= targetVisible) {
    return 1;
  }
  return Math.ceil(count / targetVisible);
}
