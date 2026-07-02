import { FormEvent, useEffect, useRef, useState } from "react";

import { ResultCards } from "./components/ResultCards";
import {
  createSession,
  fetchDemoMetadata,
  sendMessage,
  type ChatResponse,
  type DemoMetadata,
  type SessionRecord,
} from "./lib/api";

type ChatTurn = {
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
};

const promptGroups = [
  {
    title: "总量类",
    prompts: [
      "看一下当前快照下的 PGT-A 送检量",
      "山西省妇幼保健院 2025年7月到2025年10月 >35岁患者的送检量",
      "2025年 PGT-A 一共送了多少周期和胚胎",
    ],
  },
  {
    title: "率类与趋势类",
    prompts: [
      "按月看一下 PGT-A 整倍体率变化",
      "2025年 PGT-A 的整倍体率是多少",
      "看7月送检量，那整倍体率呢",
      "按季度看一下 PGT-A 整倍体率趋势",
    ],
  },
  {
    title: "年龄筛选类",
    prompts: [
      "按年龄分层看一下 PGT-A 的整倍体率",
      "35-37岁患者的 PGT-A 质控情况",
      "未填写年龄患者的 PGT-A 结果分布",
    ],
  },
  {
    title: "结果结构类",
    prompts: [
      "看一下 PGT-A 的结果分布",
      "看一下 PGT-A 的嵌合率、异常率和意外发现率",
      "看一下 PGT-A 的特殊 CNV 提示情况",
    ],
  },
  {
    title: "周期结局类",
    prompts: [
      "看一下 PGT-A 的周期无整倍体率",
      "看一下 PGT-A 的周期整倍体结局",
    ],
  },
];

export function App() {
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [metadata, setMetadata] = useState<DemoMetadata | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState(promptGroups[0].prompts[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageColumnRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchDemoMetadata()
      .then((meta) => {
        setMetadata(meta);
        if (!meta.default_hospital) {
          throw new Error("No hospital found in current snapshot bundle");
        }
        return createSession(meta.default_hospital);
      })
      .then((record) => setSession(record))
      .catch(() => setError("无法创建会话，请检查后端服务是否已启动。"));
  }, []);

  useEffect(() => {
    if (!messageColumnRef.current) {
      return;
    }
    messageColumnRef.current.scrollTo({
      top: messageColumnRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, isSubmitting]);

  async function submitPrompt(prompt: string) {
    if (!session || !prompt.trim()) return;

    const normalizedPrompt = prompt.trim();
    setError(null);
    setIsSubmitting(true);
    setTurns((current) => [...current, { role: "user", text: normalizedPrompt }]);
    setInput("");

    try {
      const response = await sendMessage(session.session_id, normalizedPrompt, {
        hospital_id: session.hospital_id,
        hospital_name: session.hospital_name ?? "",
      });
      setTurns((current) => [
        ...current,
        {
          role: "assistant",
          text: response.assistant_text,
          response,
        },
      ]);
    } catch (caughtError) {
      const message =
        caughtError instanceof Error ? caughtError.message : "消息发送失败，请稍后重试。";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    await submitPrompt(input.trim());
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">YK</div>
          <div>
            <div className="brand-title">医院数据回顾智能体</div>
            <div className="brand-subtitle">Clinical analytics workspace</div>
          </div>
        </div>

          <section className="sidebar-panel">
            <div className="panel-title">当前场景</div>
            <p className="panel-copy">
            当前处于快照模式，已接入 PGT-A、PGT-AH、PGT-SR、PGT-M 业务数据文件；当前真实执行链路先聚焦 PGT-A 受控统计问答和结果卡片展示。
            </p>
          {metadata ? (
            <p className="panel-copy">
              当前默认医院：{metadata.default_hospital?.hospital_name ?? "无"}，数据时间快照：
              {metadata.snapshot_start.slice(0, 10)} 至 {metadata.snapshot_end.slice(0, 10)}。
            </p>
          ) : null}
        </section>

        {metadata ? (
          <>
            <section className="sidebar-panel">
              <div className="panel-title">当前可分析范围</div>
              <div className="capability-block">
                <div className="capability-label">支持主题</div>
                <div className="tag-list">
                  {metadata.capability_overview.supported_topics.map((item) => (
                    <span className="capability-tag" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
              <div className="capability-block">
                <div className="capability-label">可用维度</div>
                <div className="tag-list">
                  {metadata.capability_overview.supported_dimensions.map((item) => (
                    <span className="capability-tag capability-tag-soft" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
              <div className="capability-block">
                <div className="capability-label">当前已接入的数据能力</div>
                <div className="tag-list">
                  {metadata.capability_overview.available_context.map((item) => (
                    <span className="capability-tag capability-tag-muted" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
              <div className="capability-block">
                <div className="capability-label">推荐筛选方式</div>
                <div className="tag-list">
                  {["医院", "时间范围", "年龄范围"].map((item) => (
                    <span className="capability-tag capability-tag-soft" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </section>

            <section className="sidebar-panel">
              <div className="panel-title">暂不支持范围</div>
              <ul className="support-list support-list-warning">
                {metadata.capability_overview.unsupported_topics.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <ul className="support-list">
                {metadata.capability_overview.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          </>
        ) : null}

        <section className="sidebar-panel">
          <div className="panel-title">推荐问题</div>
          {promptGroups.map((group) => (
            <div className="prompt-group" key={group.title}>
              <div className="prompt-group-title">{group.title}</div>
              <div className="prompt-list">
                {group.prompts.map((prompt) => (
                  <button
                    className="prompt-chip"
                    disabled={isSubmitting || !session}
                    key={prompt}
                    onClick={() => void submitPrompt(prompt)}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <div className="workspace-kicker">EMBEDDED CHAT WORKSPACE</div>
            <h1>面向医院客户的 PGT 回顾分析助手</h1>
          </div>
          <div className="status-pill">
            {session ? `会话已连接 · ${session.hospital_name ?? session.hospital_id}` : "等待会话初始化"}
          </div>
        </header>

        <section className="workspace-body">
          <div className="chat-column">
            <div className="message-column" ref={messageColumnRef}>
              {turns.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-title">从一个业务问题开始</div>
                    <p className="empty-copy">
                      当前快照模式已接入 PGT-A、PGT-AH、PGT-SR、PGT-M 业务文件，当前可直接联调 PGT-A 的送检量、整倍体率、年龄分层、质控结果和异常结构。
                    </p>
                  {metadata ? (
                    <div className="empty-guidance">
                      <div className="empty-guidance-title">你可以这样提问</div>
                      <ul className="support-list">
                        {metadata.capability_overview.guidance.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {turns.map((turn, index) => (
                <article className={`message message-${turn.role}`} key={`${turn.role}-${index}`}>
                  <div className="message-role">{turn.role === "user" ? "用户问题" : "分析结果"}</div>
                  <div className="message-text">{turn.text}</div>
                  {(() => {
                    const answerMode = turn.response?.structured_answer?.answer_mode;
                    const rationale = turn.response?.structured_answer?.rationale;
                    if (!answerMode || answerMode === "answer" || !rationale) {
                      return null;
                    }
                    return (
                      <div className="state-banner">
                        {answerMode === "clarify" ? "需要澄清" : "当前不支持"}：{rationale}
                      </div>
                    );
                  })()}
                  {turn.response?.clarify_payload ? (
                    <div className="clarify-panel">
                      <div className="clarify-title">{turn.response.clarify_payload.title}</div>
                      <div className="clarify-question">{turn.response.clarify_payload.question}</div>
                      {turn.response.clarify_payload.missing_parts.length ? (
                        <div className="clarify-missing">
                          当前缺失：{turn.response.clarify_payload.missing_parts.join("、")}
                        </div>
                      ) : null}
                      {turn.response.clarify_payload.options.length ? (
                        <div className="clarify-options">
                          {turn.response.clarify_payload.options.map((item) => (
                            <button
                              className="followup-chip"
                              disabled={isSubmitting || !session}
                              key={item}
                              onClick={() => void submitPrompt(item)}
                              type="button"
                            >
                              {item}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  {turn.response ? <ResultCards response={turn.response} /> : null}
                  {turn.response?.follow_up_suggestions?.length ? (
                    <div className="followups">
                      {turn.response.follow_up_suggestions.map((item) => (
                        <button
                          className="followup-chip"
                          disabled={isSubmitting || !session}
                          key={item}
                          onClick={() => void submitPrompt(item)}
                          type="button"
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))}
            </div>

            <div className="composer-shell">
              <form className="composer" onSubmit={onSubmit}>
                <div className="composer-topline">
                  <label className="composer-label" htmlFor="message">
                    输入数据回顾问题
                  </label>
                  <div className="composer-meta">当前会话内可连续追问，输入区常驻底部</div>
                </div>
                <textarea
                  id="message"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="例如：2025 年 PGT-A 的整倍体率是多少？"
                  rows={3}
                />
                <div className="composer-footer">
                  <div className="composer-hint">当前只管理会话级上下文，不做长期记忆。</div>
                  <button className="submit-button" disabled={isSubmitting || !session} type="submit">
                    {isSubmitting ? "分析中..." : "发送问题"}
                  </button>
                </div>
              </form>
              {error ? <div className="error-banner">{error}</div> : null}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
