import type { ResultCard } from "./api";

type TableCard = Extract<ResultCard, { type: "table" }>;
type ChartCard = Extract<ResultCard, { type: "chart" }>;

const EXPORT_GREEN = "#1f5c4b";
const EXPORT_GRID = "#dde5de";
const EXPORT_TEXT = "#1f2220";
const EXPORT_MUTED = "#66736b";
const PIE_PALETTE = ["#1f5c4b", "#3f7d67", "#7da28b", "#b4c7ba", "#d8e4dd", "#b58c35", "#8d6f47"];
const MAX_EXPORT_POINTS = 30;

export function downloadTableCsv(card: TableCard) {
  const rows = [card.table.columns, ...card.table.rows];
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
  downloadBlob(blob, `${safeFileName(card.table.title || card.title)}.csv`);
}

export async function downloadChartPng(card: ChartCard) {
  const svg = chartToSvg(card);
  const svgBlob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(svgBlob);
  try {
    const image = await loadImage(url);
    const canvas = document.createElement("canvas");
    canvas.width = image.width;
    canvas.height = image.height;
    const context = canvas.getContext("2d");
    if (!context) {
      downloadBlob(svgBlob, `${safeFileName(card.chart.title || card.title)}.svg`);
      return;
    }
    context.fillStyle = "#fffdf8";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0);
    const pngBlob = await canvasToBlob(canvas);
    downloadBlob(pngBlob, `${safeFileName(card.chart.title || card.title)}.png`);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function chartToSvg(card: ChartCard) {
  const chart = card.chart;
  const series = chart.series[0];
  const exportData = topChartData(chart.categories, series?.values ?? []);
  const values = exportData.values;
  const categories = exportData.categories;
  const width = 1200;
  const height = chart.chart_type === "pie" ? 620 : chart.chart_type === "bar" ? barChartHeight(categories.length) : 560;
  const title = escapeXml(chart.title || card.title);
  const subtitle = escapeXml(
    `${series?.name ?? "当前指标"}${exportData.truncated ? `，展示 Top ${MAX_EXPORT_POINTS}，完整数据请导出表格` : ""}`,
  );
  const body =
    chart.chart_type === "pie"
      ? pieChartSvg(categories, values, width, height)
      : chart.chart_type === "line"
        ? lineChartSvg(categories, values, width, height)
        : barChartSvg(categories, values, width, height);

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    `<rect width="${width}" height="${height}" rx="24" fill="#fffdf8"/>`,
    `<text x="48" y="56" fill="${EXPORT_TEXT}" font-size="24" font-weight="700" font-family="Arial, 'Microsoft YaHei', sans-serif">${title}</text>`,
    `<text x="48" y="86" fill="${EXPORT_MUTED}" font-size="14" font-family="Arial, 'Microsoft YaHei', sans-serif">${subtitle}</text>`,
    body,
    "</svg>",
  ].join("");
}

function barChartSvg(categories: string[], values: number[], width: number, _height: number) {
  const left = 60;
  const top = 126;
  const columns = Math.min(10, Math.max(categories.length, 1));
  const rows = Math.ceil(categories.length / columns);
  const cellWidth = (width - left * 2) / columns;
  const cellHeight = 176;
  const chartAreaHeight = 96;
  const maxValue = Math.max(...values, 1);

  const bars = categories
    .map((category, index) => {
      const value = values[index] ?? 0;
      const row = Math.floor(index / columns);
      const column = index % columns;
      const cellX = left + column * cellWidth;
      const baselineY = top + row * cellHeight + chartAreaHeight;
      const barWidth = Math.min(44, cellWidth * 0.32);
      const x = cellX + (cellWidth - barWidth) / 2;
      const scaledHeight = Math.max(value > 0 ? 10 : 0, (value / maxValue) * chartAreaHeight);
      const y = baselineY - scaledHeight;
      const labelLines = wrapLabel(category, 8).slice(0, 2);
      return [
        `<line x1="${cellX + 12}" y1="${baselineY}" x2="${cellX + cellWidth - 12}" y2="${baselineY}" stroke="${EXPORT_GRID}" stroke-width="1"/>`,
        `<text x="${x + barWidth / 2}" y="${y - 12}" text-anchor="middle" fill="${EXPORT_TEXT}" font-size="14" font-weight="700" font-family="Arial, 'Microsoft YaHei', sans-serif">${formatValue(value)}</text>`,
        `<rect x="${x}" y="${y}" width="${barWidth}" height="${scaledHeight}" rx="8" fill="${EXPORT_GREEN}"/>`,
        labelLines
          .map(
            (line, lineIndex) =>
              `<text x="${cellX + cellWidth / 2}" y="${baselineY + 28 + lineIndex * 17}" text-anchor="middle" fill="${EXPORT_MUTED}" font-size="12" font-family="Arial, 'Microsoft YaHei', sans-serif">${escapeXml(line)}</text>`,
          )
          .join(""),
      ].join("");
    })
    .join("");

  return bars;
}

function lineChartSvg(categories: string[], values: number[], width: number, height: number) {
  const left = 58;
  const right = 48;
  const top = 126;
  const bottom = 78;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const maxValue = Math.max(...values, 1);
  const baselineY = top + chartHeight;
  const step = categories.length > 1 ? chartWidth / (categories.length - 1) : chartWidth;
  const labelStride = labelStrideFor(categories.length);
  const points = categories.map((category, index) => {
    const value = values[index] ?? 0;
    return {
      category,
      value,
      x: left + index * step,
      y: baselineY - (value / maxValue) * chartHeight,
    };
  });
  const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");

  return [
    `<line x1="${left}" y1="${baselineY}" x2="${width - right}" y2="${baselineY}" stroke="${EXPORT_GRID}" stroke-width="1"/>`,
    `<polyline fill="none" points="${polyline}" stroke="${EXPORT_GREEN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`,
    points
      .map((point, index) => {
        const showLabel = index % labelStride === 0 || index === points.length - 1;
        return [
          `<circle cx="${point.x}" cy="${point.y}" r="6" fill="#fffdf8" stroke="${EXPORT_GREEN}" stroke-width="4"/>`,
          `<text x="${point.x}" y="${point.y - 14}" text-anchor="middle" fill="${EXPORT_MUTED}" font-size="12" font-family="Arial, 'Microsoft YaHei', sans-serif">${formatValue(point.value)}</text>`,
          showLabel
            ? `<text x="${point.x}" y="${baselineY + 30}" text-anchor="middle" fill="${EXPORT_MUTED}" font-size="11" font-family="Arial, 'Microsoft YaHei', sans-serif">${escapeXml(shortLabel(point.category, 12))}</text>`
            : "",
        ].join("");
      })
      .join(""),
  ].join("");
}

function pieChartSvg(categories: string[], values: number[], width: number, height: number) {
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    return `<text x="48" y="160" fill="${EXPORT_MUTED}" font-size="16" font-family="Arial, 'Microsoft YaHei', sans-serif">当前图表没有可展示的数据点。</text>`;
  }
  const centerX = 236;
  const centerY = 300;
  const radius = 140;
  let angleCursor = -Math.PI / 2;
  const paths = values
    .map((value, index) => {
      const angle = (value / total) * Math.PI * 2;
      const nextAngle = angleCursor + angle;
      const path = describeArc(centerX, centerY, radius, angleCursor, nextAngle);
      angleCursor = nextAngle;
      return `<path d="${path}" fill="${PIE_PALETTE[index % PIE_PALETTE.length]}"/>`;
    })
    .join("");
  const legend = categories
    .map((category, index) => {
      const y = 178 + index * 34;
      return [
        `<rect x="470" y="${y - 13}" width="14" height="14" rx="3" fill="${PIE_PALETTE[index % PIE_PALETTE.length]}"/>`,
        `<text x="494" y="${y}" fill="${EXPORT_TEXT}" font-size="14" font-family="Arial, 'Microsoft YaHei', sans-serif">${escapeXml(shortLabel(category, 24))}</text>`,
        `<text x="${width - 58}" y="${y}" text-anchor="end" fill="${EXPORT_MUTED}" font-size="14" font-family="Arial, 'Microsoft YaHei', sans-serif">${formatValue(values[index] ?? 0)}</text>`,
      ].join("");
    })
    .join("");

  return `${paths}${legend}`;
}

function topChartData(categories: string[], values: number[]) {
  if (categories.length <= MAX_EXPORT_POINTS) {
    return { categories, values, truncated: false };
  }
  const paired = categories
    .map((category, index) => ({ category, value: values[index] ?? 0 }))
    .sort((left, right) => right.value - left.value);
  const top = paired.slice(0, MAX_EXPORT_POINTS);
  return {
    categories: top.map((item) => item.category),
    values: top.map((item) => item.value),
    truncated: true,
  };
}

function barChartHeight(count: number) {
  const rows = Math.ceil(Math.max(count, 1) / 10);
  return 166 + rows * 176;
}

function csvCell(value: string | number) {
  const text = String(value ?? "");
  if (/[",\r\n]/.test(text)) {
    return `"${text.replaceAll('"', '""')}"`;
  }
  return text;
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function safeFileName(text: string) {
  const compact = text.trim().replace(/[\\/:*?"<>|]+/g, "-").replace(/\s+/g, "-");
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, "");
  return `${compact || "export"}-${stamp}`;
}

function loadImage(url: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = url;
  });
}

function canvasToBlob(canvas: HTMLCanvasElement) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error("无法生成图片文件"));
      }
    }, "image/png");
  });
}

function escapeXml(text: string) {
  return text.replace(/[<>&"']/g, (char) => {
    switch (char) {
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case "&":
        return "&amp;";
      case '"':
        return "&quot;";
      default:
        return "&apos;";
    }
  });
}

function formatValue(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function shortLabel(label: string, limit: number) {
  if (label.length <= limit) {
    return label;
  }
  return `${label.slice(0, limit)}...`;
}

function wrapLabel(label: string, limit: number) {
  const compact = label.trim();
  if (!compact) {
    return [""];
  }
  const chunks: string[] = [];
  for (let index = 0; index < compact.length; index += limit) {
    chunks.push(compact.slice(index, index + limit));
  }
  return chunks;
}

function labelStrideFor(count: number) {
  if (count <= 12) {
    return 1;
  }
  return Math.ceil(count / 12);
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= Math.PI ? "0" : "1";
  return [`M ${cx} ${cy}`, `L ${start.x} ${start.y}`, `A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`, "Z"].join(" ");
}

function polarToCartesian(cx: number, cy: number, r: number, angle: number) {
  return {
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle),
  };
}
