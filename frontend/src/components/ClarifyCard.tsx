import type { ChatResponse } from "../lib/api";

type Props = {
  payload: NonNullable<ChatResponse["clarify_payload"]>;
  isSubmitting: boolean;
  sessionReady: boolean;
  onSelectOption: (option: string) => void;
};

const clarifyTypeLabels: Record<string, string> = {
  missing_metric: "需要先明确主指标",
  multiple_metrics: "当前问题包含多个主题",
  missing_filter: "还缺少筛选条件",
  ambiguous_object: "需要先明确统计对象",
  unsafe_followup: "追问信息还不够安全",
  unsupported_combination: "当前组合需要拆开问",
  general: "请补充关键信息",
};

const clarifyTypeHints: Record<string, string> = {
  missing_metric: "先选一个主指标，系统再继续沿着这个主题分析。",
  multiple_metrics: "当前版本一次只执行一个主指标，先确定最想看的那一个。",
  missing_filter: "补上时间、年龄或产品范围后，系统才能稳定进入受控统计。",
  ambiguous_object: "这次要先区分胚胎层面还是周期层面，系统再进入对应的统计函数。",
  unsafe_followup: "这轮追问还可能有多种理解，先补一句更明确的条件。",
  unsupported_combination: "当前组合容易答偏，拆成两步问会更稳定。",
  general: "补一条关键信息后，系统就能继续往下分析。",
};

export function ClarifyCard({ payload, isSubmitting, sessionReady, onSelectOption }: Props) {
  const clarifyType = payload.clarify_type ?? "general";
  const headline = clarifyTypeLabels[clarifyType] ?? clarifyTypeLabels.general;
  const hint = clarifyTypeHints[clarifyType] ?? clarifyTypeHints.general;

  return (
    <section className="clarify-panel">
      <div className="clarify-head">
        <div>
          <div className="clarify-title">{payload.title}</div>
          <div className="clarify-mode">{headline}</div>
        </div>
        <div className={`clarify-badge clarify-badge-${clarifyType}`}>待补充</div>
      </div>
      <div className="clarify-question">{payload.question}</div>
      <div className="clarify-hint">{hint}</div>
      {payload.missing_parts.length ? (
        <div className="clarify-missing">
          当前缺失：{payload.missing_parts.join("、")}
        </div>
      ) : null}
      {payload.options.length ? (
        <div className="clarify-options">
          {payload.options.map((item) => (
            <button
              className="clarify-option"
              disabled={isSubmitting || !sessionReady}
              key={item}
              onClick={() => onSelectOption(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </div>
      ) : (
        <div className="clarify-empty">请在输入框补充主指标或筛选条件后继续。</div>
      )}
    </section>
  );
}
