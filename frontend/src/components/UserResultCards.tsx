import { useState } from "react";

import type { ChatResponse, ResultCard } from "../lib/api";

type Props = {
  response: ChatResponse;
};

export function UserResultCards({ response }: Props) {
  const summaryCard = response.result_cards.find((card) => card.type === "summary");
  const tableCards = response.result_cards.filter((card) => card.type === "table");
  const chartCard = response.result_cards.find((card) => card.type === "chart");

  if (!summaryCard && tableCards.length === 0 && !chartCard) {
    return null;
  }

  return (
    <div className="user-result-stack">
      {summaryCard ? <UserSummary card={summaryCard} /> : null}
      {chartCard ? <UserChartNote card={chartCard} /> : null}
      {tableCards.map((card) => (
        <UserTable card={card} key={card.title} />
      ))}
    </div>
  );
}

function UserSummary({ card }: { card: Extract<ResultCard, { type: "summary" }> }) {
  return (
    <section className="user-answer-card user-answer-summary">
      <div className="user-card-label">{card.title}</div>
      <p>{card.content}</p>
    </section>
  );
}

function UserChartNote({ card }: { card: Extract<ResultCard, { type: "chart" }> }) {
  const firstSeries = card.chart.series[0];
  const values = firstSeries?.values ?? [];
  const maxValue = Math.max(...values, 0);

  return (
    <section className="user-answer-card">
      <div className="user-card-head">
        <div>
          <div className="user-card-label">趋势概览</div>
          <h3>{card.chart.title}</h3>
        </div>
        <span className="user-card-meta">{firstSeries?.name ?? "当前指标"}</span>
      </div>
      <div className="user-mini-bars" aria-label={card.chart.title}>
        {card.chart.categories.map((category, index) => {
          const value = values[index] ?? 0;
          const height = maxValue > 0 ? Math.max(8, (value / maxValue) * 100) : 8;
          const valueInside = height >= 72;
          return (
            <div className="user-mini-bar-item" key={`${category}-${index}`}>
              <div className="user-mini-bar-track">
                <span className={`user-mini-bar-value${valueInside ? " user-mini-bar-value-inside" : ""}`}>
                  {formatMetricValue(value)}
                </span>
                <span className="user-mini-bar" style={{ height: `${height}%` }} />
              </div>
              <span className="user-mini-bar-label">{category}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function formatMetricValue(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function UserTable({ card }: { card: Extract<ResultCard, { type: "table" }> }) {
  const [expanded, setExpanded] = useState(false);
  const table = card.table;
  const isCollapsible =
    typeof table.total_rows === "number" &&
    table.preview_rows !== undefined &&
    table.preview_rows.length > 0 &&
    table.preview_rows.length < table.rows.length;
  const rows = isCollapsible && !expanded ? table.preview_rows ?? table.rows : table.rows;

  return (
    <section className="user-answer-card">
      <div className="user-card-head">
        <div>
          <div className="user-card-label">{card.title}</div>
          <h3>{table.title}</h3>
        </div>
        {typeof table.total_rows === "number" ? (
          <span className="user-card-meta">共 {table.total_rows} 行</span>
        ) : null}
      </div>
      <div className="user-table-shell">
        <table>
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`${card.title}-${rowIndex}`}>
                {row.map((value, valueIndex) => (
                  <td key={`${rowIndex}-${valueIndex}`}>{value}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {isCollapsible ? (
        <button
          className="user-table-toggle"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? "收起明细" : `查看全部明细（${table.total_rows} 行）`}
        </button>
      ) : null}
    </section>
  );
}
