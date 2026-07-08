export type ResultCard =
  | {
      type: "summary";
      title: string;
      content?: string;
    }
  | {
      type: "table";
      title: string;
      table: {
        title: string;
        columns: string[];
        rows: Array<Array<string | number>>;
        preview_rows?: Array<Array<string | number>>;
        total_rows?: number;
        has_more_rows?: boolean;
      };
    }
  | {
      type: "chart";
      title: string;
      chart: {
        title: string;
        chart_type: "bar" | "line" | "pie";
        categories: string[];
        series: Array<{
          name: string;
          values: number[];
        }>;
      };
    };

export type ChatResponse = {
  assistant_text: string;
  structured_answer: {
    answer_mode: "answer" | "clarify" | "refuse";
    presentation_mode: "overview" | "trend" | "distribution" | "detail_heavy";
    evidence_density: "compact" | "dense";
    topic: string;
    rationale: string;
    applied_filters: Record<string, string>;
    metric_ids: string[];
    warnings: string[];
  };
  result_cards: ResultCard[];
  follow_up_suggestions: string[];
  clarify_payload?: {
    clarify_type?:
      | "missing_metric"
      | "multiple_metrics"
      | "missing_filter"
      | "ambiguous_object"
      | "unsafe_followup"
      | "unsupported_combination"
      | "general";
    title: string;
    question: string;
    missing_parts: string[];
    options: string[];
  } | null;
  snapshot_metadata?: {
    mode: "snapshot";
    data_source: string;
    product_scope: string;
    snapshot_start: string;
    snapshot_end: string;
    hospital_count: number;
    registered_products?: string[];
    source_summaries?: Array<{
      product_code: string;
      product_label: string;
      data_source: string;
      sheet_name: string;
      row_count: number;
      cycle_count: number;
      snapshot_start?: string | null;
      snapshot_end?: string | null;
      semantic_fields: string[];
      execution_status: "executable" | "metadata_only";
      notes: string[];
    }>;
    available_context: string[];
    limitations: string[];
  } | null;
  data_readiness?: {
    status: "ready" | "no_data" | "unsupported";
    summary: string;
    record_count: number;
    missing_fields: string[];
    limitations: string[];
  } | null;
  analysis_task?: {
    kind: "single_metric" | "structured_business_request";
    title: string;
    status: "completed" | "clarify" | "blocked";
    steps: Array<{
      title: string;
      status: "completed" | "clarify" | "blocked";
      detail?: string | null;
    }>;
    notes: string[];
  } | null;
  capability_report?: {
    title: string;
    summary: string;
    products: Array<{
      product_code: string;
      product_label: string;
      metrics: Array<{
        code: string;
        label: string;
        status: "supported" | "unsupported";
        reason: string;
      }>;
    }>;
  } | null;
  route_trace?: {
    raw_message: string;
    normalized_message: string;
    filters: Record<string, string>;
    candidate_metric_ids: string[];
    resolved_metric_id?: string | null;
    answer_mode: "answer" | "clarify" | "refuse";
    rationale: string;
  } | null;
  trace_id: string;
};

export type SessionRecord = {
  session_id: string;
  user_id: string;
  hospital_id: string;
  hospital_name?: string | null;
  hospital_scope_mode?: "single" | "all";
  can_access_all_hospitals?: boolean;
  accessible_hospital_ids?: string[] | null;
  overview?: {
    hospital_name: string;
    product_scope: string;
    hospital_scope_mode?: "single" | "all";
    snapshot_start: string;
    snapshot_end: string;
    embryo_count: number;
    cycle_count: number;
    summary: string;
  } | null;
};

export type DemoMetadata = {
  product_scope: string;
  data_source: string;
  snapshot_start: string;
  snapshot_end: string;
  hospital_count: number;
  can_access_all_hospitals: boolean;
  capability_overview: {
    supported_topics: string[];
    supported_dimensions: string[];
    available_context: string[];
    unsupported_topics: string[];
    guidance: string[];
    limitations: string[];
  };
  default_hospital: {
    hospital_id: string;
    hospital_name: string;
    sample_count: number;
  } | null;
  hospitals: Array<{
    hospital_id: string;
    hospital_name: string;
    sample_count: number;
  }>;
};

export type DemoAccessMode = "single" | "all";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:18765/api/v1";

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isResultCard(value: unknown): value is ResultCard {
  if (!isObject(value) || typeof value.type !== "string" || typeof value.title !== "string") {
    return false;
  }

  if (value.type === "summary") {
    return value.content === undefined || typeof value.content === "string";
  }

  if (value.type === "table") {
    if (!isObject(value.table) || !Array.isArray(value.table.columns) || !Array.isArray(value.table.rows)) {
      return false;
    }
    if (typeof value.table.title !== "string") {
      return false;
    }
    if (value.table.preview_rows !== undefined && !Array.isArray(value.table.preview_rows)) {
      return false;
    }
    if (value.table.total_rows !== undefined && typeof value.table.total_rows !== "number") {
      return false;
    }
    if (value.table.has_more_rows !== undefined && typeof value.table.has_more_rows !== "boolean") {
      return false;
    }
    return true;
  }

  if (value.type === "chart") {
    if (
      !isObject(value.chart) ||
      typeof value.chart.title !== "string" ||
      !Array.isArray(value.chart.categories) ||
      !Array.isArray(value.chart.series)
    ) {
      return false;
    }
    return value.chart.chart_type === "bar" || value.chart.chart_type === "line" || value.chart.chart_type === "pie";
  }

  return false;
}

function isChatResponse(value: unknown): value is ChatResponse {
  if (!isObject(value)) {
    return false;
  }

  if (typeof value.assistant_text !== "string" || typeof value.trace_id !== "string") {
    return false;
  }

  if (!Array.isArray(value.result_cards) || !value.result_cards.every(isResultCard)) {
    return false;
  }

  if (!Array.isArray(value.follow_up_suggestions) || !value.follow_up_suggestions.every((item) => typeof item === "string")) {
    return false;
  }

  if (value.clarify_payload !== undefined && value.clarify_payload !== null) {
    if (
      !isObject(value.clarify_payload) ||
      (value.clarify_payload.clarify_type !== undefined &&
        value.clarify_payload.clarify_type !== "missing_metric" &&
        value.clarify_payload.clarify_type !== "multiple_metrics" &&
        value.clarify_payload.clarify_type !== "missing_filter" &&
        value.clarify_payload.clarify_type !== "ambiguous_object" &&
        value.clarify_payload.clarify_type !== "unsafe_followup" &&
        value.clarify_payload.clarify_type !== "unsupported_combination" &&
        value.clarify_payload.clarify_type !== "general") ||
      typeof value.clarify_payload.title !== "string" ||
      typeof value.clarify_payload.question !== "string" ||
      !Array.isArray(value.clarify_payload.missing_parts) ||
      !Array.isArray(value.clarify_payload.options)
    ) {
      return false;
    }
  }

  if (value.snapshot_metadata !== undefined && value.snapshot_metadata !== null) {
    if (
      !isObject(value.snapshot_metadata) ||
      value.snapshot_metadata.mode !== "snapshot" ||
      typeof value.snapshot_metadata.data_source !== "string" ||
      typeof value.snapshot_metadata.product_scope !== "string" ||
      typeof value.snapshot_metadata.snapshot_start !== "string" ||
      typeof value.snapshot_metadata.snapshot_end !== "string" ||
      typeof value.snapshot_metadata.hospital_count !== "number" ||
      (value.snapshot_metadata.registered_products !== undefined &&
        !Array.isArray(value.snapshot_metadata.registered_products)) ||
      (value.snapshot_metadata.source_summaries !== undefined &&
        !Array.isArray(value.snapshot_metadata.source_summaries)) ||
      !Array.isArray(value.snapshot_metadata.available_context) ||
      !Array.isArray(value.snapshot_metadata.limitations)
    ) {
      return false;
    }
  }

  if (value.data_readiness !== undefined && value.data_readiness !== null) {
    if (
      !isObject(value.data_readiness) ||
      (value.data_readiness.status !== "ready" &&
        value.data_readiness.status !== "no_data" &&
        value.data_readiness.status !== "unsupported") ||
      typeof value.data_readiness.summary !== "string" ||
      typeof value.data_readiness.record_count !== "number" ||
      !Array.isArray(value.data_readiness.missing_fields) ||
      !Array.isArray(value.data_readiness.limitations)
    ) {
      return false;
    }
  }

  if (value.analysis_task !== undefined && value.analysis_task !== null) {
    if (
      !isObject(value.analysis_task) ||
      (value.analysis_task.kind !== "single_metric" &&
        value.analysis_task.kind !== "structured_business_request") ||
      typeof value.analysis_task.title !== "string" ||
      (value.analysis_task.status !== "completed" &&
        value.analysis_task.status !== "clarify" &&
        value.analysis_task.status !== "blocked") ||
      !Array.isArray(value.analysis_task.steps) ||
      !Array.isArray(value.analysis_task.notes)
    ) {
      return false;
    }
  }

  if (value.route_trace !== undefined && value.route_trace !== null) {
    if (
      !isObject(value.route_trace) ||
      typeof value.route_trace.raw_message !== "string" ||
      typeof value.route_trace.normalized_message !== "string" ||
      !isObject(value.route_trace.filters) ||
      !Array.isArray(value.route_trace.candidate_metric_ids) ||
      !value.route_trace.candidate_metric_ids.every((item) => typeof item === "string") ||
      (value.route_trace.resolved_metric_id !== undefined &&
        value.route_trace.resolved_metric_id !== null &&
        typeof value.route_trace.resolved_metric_id !== "string") ||
      (value.route_trace.answer_mode !== "answer" &&
        value.route_trace.answer_mode !== "clarify" &&
        value.route_trace.answer_mode !== "refuse") ||
      typeof value.route_trace.rationale !== "string"
    ) {
      return false;
    }
  }

  if (value.capability_report !== undefined && value.capability_report !== null) {
    if (
      !isObject(value.capability_report) ||
      typeof value.capability_report.title !== "string" ||
      typeof value.capability_report.summary !== "string" ||
      !Array.isArray(value.capability_report.products)
    ) {
      return false;
    }
  }

  if (!isObject(value.structured_answer)) {
    return false;
  }

  const structuredAnswer = value.structured_answer;
  if (
    (structuredAnswer.answer_mode !== "answer" &&
      structuredAnswer.answer_mode !== "clarify" &&
      structuredAnswer.answer_mode !== "refuse") ||
    (structuredAnswer.presentation_mode !== "overview" &&
      structuredAnswer.presentation_mode !== "trend" &&
      structuredAnswer.presentation_mode !== "distribution" &&
      structuredAnswer.presentation_mode !== "detail_heavy") ||
    (structuredAnswer.evidence_density !== "compact" &&
      structuredAnswer.evidence_density !== "dense") ||
    typeof structuredAnswer.topic !== "string" ||
    typeof structuredAnswer.rationale !== "string" ||
    !isObject(structuredAnswer.applied_filters) ||
    !Array.isArray(structuredAnswer.metric_ids) ||
    !structuredAnswer.metric_ids.every((item) => typeof item === "string") ||
    !Array.isArray(structuredAnswer.warnings) ||
    !structuredAnswer.warnings.every((item) => typeof item === "string")
  ) {
    return false;
  }

  return true;
}

export async function fetchDemoMetadata(
  productScope: string = "PGT-A",
  accessMode: DemoAccessMode = "all",
): Promise<DemoMetadata> {
  const response = await fetch(
    `${API_BASE}/demo/metadata?product_scope=${encodeURIComponent(productScope)}&access_mode=${encodeURIComponent(accessMode)}`,
  );
  if (!response.ok) {
    throw new Error("Failed to load demo metadata");
  }
  return response.json();
}

export async function createSession(hospital: {
  hospital_id: string;
  hospital_name: string;
  product_scope: string;
  hospital_scope_mode?: "single" | "all";
  accessible_hospital_ids?: string[];
  can_access_all_hospitals?: boolean;
}): Promise<SessionRecord> {
  const response = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: "demo-user",
      hospital_id: hospital.hospital_id,
      hospital_name: hospital.hospital_name,
      host_session_id: "demo-host-session",
      product_scope: hospital.product_scope,
      hospital_scope_mode: hospital.hospital_scope_mode ?? "single",
      accessible_hospital_ids: hospital.accessible_hospital_ids ?? [hospital.hospital_id],
      can_access_all_hospitals: hospital.can_access_all_hospitals ?? false,
    }),
  });
  if (!response.ok) {
    throw new Error("Failed to create session");
  }
  return response.json();
}

export async function sendMessage(
  sessionId: string,
  message: string,
  hospital: {
    hospital_id: string;
    hospital_name: string;
    hospital_scope_mode?: "single" | "all";
    accessible_hospital_ids?: string[];
    can_access_all_hospitals?: boolean;
  },
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      host_context: {
        user_id: "demo-user",
        hospital_id: hospital.hospital_id,
        hospital_name: hospital.hospital_name,
        hospital_scope_mode: hospital.hospital_scope_mode ?? "single",
        host_session_id: "demo-host-session",
        accessible_hospital_ids: hospital.accessible_hospital_ids ?? [hospital.hospital_id],
        can_access_all_hospitals: hospital.can_access_all_hospitals ?? false,
      },
    }),
  });
  if (!response.ok) {
    throw new Error("Failed to send message");
  }

  const payload: unknown = await response.json();
  if (!isChatResponse(payload)) {
    throw new Error("后端返回了不兼容的响应结构，请刷新前后端服务后重试。");
  }
  return payload;
}
