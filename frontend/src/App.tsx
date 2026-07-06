import { FormEvent, useEffect, useRef, useState } from "react";

import { ClarifyCard } from "./components/ClarifyCard";
import { ResultCards } from "./components/ResultCards";
import { UserResultCards } from "./components/UserResultCards";
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

type ViewMode = "user" | "debug";

const promptGroups = [
  {
    title: "看规模和趋势",
    description: "适合做月度、季度经营回顾",
    prompts: [
      "按季度看一下 2025 年 PGT-A 送检趋势",
      "看一下 2025 年 7 月到 10 月 PGT-A 送检量",
      "2025 年 PGT-A 每月整倍体率变化怎么样",
    ],
  },
  {
    title: "看结果和质量",
    description: "适合查看结果结构、质控和特殊提示",
    prompts: [
      "看一下 2025 年 PGT-A 质控情况",
      "看一下 PGT-A 结果分布和异常结构",
      "特殊 CNV 提示这块有多少",
    ],
  },
  {
    title: "看人群和周期",
    description: "适合按年龄或周期层面拆开看",
    prompts: [
      "按年龄分层看一下 PGT-A 整倍体率",
      "按年龄分层，从周期维度看整体结局",
      "看一下 PGT-A 的周期无整倍体率",
    ],
  },
];

const workflowHints = [
  {
    title: "可回答的问题",
    items: ["送检量", "胚胎整倍体率", "年龄分层", "质控", "结果结构", "周期结局", "特殊 CNV"],
  },
  {
    title: "可以使用的条件",
    items: ["医院", "时间范围", "年龄范围"],
  },
  {
    title: "当前不支持",
    items: ["PGT-SR / PGT-M / PGT-AH 真实执行", "全产品汇总", "复杂多指标联合执行", "临床指征类统计"],
  },
];

export function App() {
  const [viewMode, setViewMode] = useState<ViewMode>("user");
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [metadata, setMetadata] = useState<DemoMetadata | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
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

  if (viewMode === "user") {
    return (
      <UserWorkspace
        error={error}
        input={input}
        isSubmitting={isSubmitting}
        metadata={metadata}
        onInputChange={setInput}
        onModeChange={setViewMode}
        onSubmit={onSubmit}
        session={session}
        submitPrompt={submitPrompt}
        turns={turns}
      />
    );
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
          <div className="panel-title">问法引导</div>
          <div className="workflow-copy">
            先明确主指标，再补时间或年龄条件，系统会更稳定地进入受控统计分析。
          </div>
          <div className="workflow-grid">
            {workflowHints.map((group) => (
              <div className="workflow-block" key={group.title}>
                <div className="workflow-block-title">{group.title}</div>
                <div className="workflow-tag-list">
                  {group.items.map((item) => (
                    <span className={`workflow-tag${group.title === "当前不支持" ? " workflow-tag-warning" : ""}`} key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="sidebar-panel">
          <div className="panel-title">推荐问法</div>
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
          <div className="debug-header-actions">
            <button className="mode-switch-button" onClick={() => setViewMode("user")} type="button">
              用户工作台
            </button>
            <div className="status-pill">
              {session ? `会话已连接 · ${session.hospital_name ?? session.hospital_id}` : "等待会话初始化"}
            </div>
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
                    <ClarifyCard
                      payload={turn.response.clarify_payload}
                      isSubmitting={isSubmitting}
                      onSelectOption={(item) => void submitPrompt(item)}
                      sessionReady={Boolean(session)}
                    />
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

type WorkspaceProps = {
  error: string | null;
  input: string;
  isSubmitting: boolean;
  metadata: DemoMetadata | null;
  onInputChange: (value: string) => void;
  onModeChange: (mode: ViewMode) => void;
  onSubmit: (event: FormEvent) => Promise<void>;
  session: SessionRecord | null;
  submitPrompt: (prompt: string) => Promise<void>;
  turns: ChatTurn[];
};

function UserWorkspace({
  error,
  input,
  isSubmitting,
  metadata,
  onInputChange,
  onModeChange,
  onSubmit,
  session,
  submitPrompt,
  turns,
}: WorkspaceProps) {
  const hospitalName = metadata?.default_hospital?.hospital_name ?? session?.hospital_name ?? "当前医院";
  const overview = session?.overview ?? null;
  const snapshotRange = overview
    ? `${overview.snapshot_start} 至 ${overview.snapshot_end}`
    : metadata
      ? `${metadata.snapshot_start.slice(0, 10)} 至 ${metadata.snapshot_end.slice(0, 10)}`
      : "等待快照信息";
  const latestAssistant = [...turns].reverse().find((turn) => turn.role === "assistant" && turn.response);
  const sessionReady = Boolean(session);

  return (
    <div className="user-shell">
      <header className="user-topbar">
        <div className="user-brand">
          <div className="user-brand-mark">YK</div>
          <div>
            <div className="user-brand-title">PGT 数据回顾助手</div>
            <div className="user-brand-subtitle">{hospitalName}</div>
          </div>
        </div>
        <div className="user-topbar-actions">
          <div className="user-session-pill">{session ? "会话已连接" : "连接中"}</div>
          <button className="mode-switch-button" onClick={() => onModeChange("debug")} type="button">
            研发调试
          </button>
        </div>
      </header>

      <main className="user-main">
        <section className="user-command-panel">
          <div className="user-context-row">
            <div>
              <div className="user-kicker">当前医院</div>
              <h1>{hospitalName} PGT-A 数据回顾</h1>
            </div>
          </div>

          {overview ? <SessionOverviewPanel overview={overview} /> : null}

          <form className="user-composer" onSubmit={onSubmit}>
            <textarea
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              placeholder="直接输入你想回顾的问题，例如：2025 年 PGT-A 的整倍体率怎么样？"
              rows={4}
            />
            <div className="user-composer-footer">
              <div className="user-composer-hint">支持连续追问，会沿用当前医院和可继承的筛选条件。</div>
              <button className="user-submit-button" disabled={isSubmitting || !sessionReady} type="submit">
                {isSubmitting ? "分析中..." : "开始分析"}
              </button>
            </div>
          </form>

          <div className="user-prompt-lanes">
            {promptGroups.map((group) => (
              <div className="user-prompt-lane" key={group.title}>
                <div className="user-lane-title">{group.title}</div>
                <p className="user-lane-copy">{group.description}</p>
                <div className="user-prompt-list">
                  {group.prompts.map((prompt) => (
                    <button
                      className="user-prompt-chip"
                      disabled={isSubmitting || !sessionReady}
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
          </div>

          <div className="user-object-choices">
            <div className="user-lane-title">整倍体指标怎么选</div>
            <div className="user-object-choice-list">
              <button
                className="user-object-choice"
                disabled={isSubmitting || !sessionReady}
                onClick={() => void submitPrompt("看一下 PGT-A 的胚胎整倍体率")}
                type="button"
              >
                <span className="user-object-choice-kicker">输出胚胎数和比例</span>
                <strong>胚胎整倍体率</strong>
                <span>适合判断检测胚胎中未见异常的占比。</span>
              </button>
              <button
                className="user-object-choice"
                disabled={isSubmitting || !sessionReady}
                onClick={() => void submitPrompt("看一下 PGT-A 的周期整倍体结局")}
                type="button"
              >
                <span className="user-object-choice-kicker">输出周期结局分布</span>
                <strong>周期整倍体结局</strong>
                <span>适合判断每个周期是否有可用整倍体胚胎。</span>
              </button>
            </div>
          </div>
        </section>

        <aside className="user-capability-panel">
          <div className="user-panel-section user-panel-section-primary">
            <div className="user-panel-title">当前数据</div>
            <div className="user-scope-list">
              <div>
                <span>医院</span>
                <strong>{hospitalName}</strong>
              </div>
              <div>
                <span>数据时间</span>
                <strong>{snapshotRange}</strong>
              </div>
              <div>
                <span>当前可分析</span>
                <strong>PGT-A</strong>
              </div>
            </div>
          </div>

          <div className="user-panel-divider" />

          <div className="user-panel-section">
            <div className="user-panel-title">能问什么</div>
            <ul className="user-capability-list">
              {workflowHints[0].items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="user-panel-section">
            <div className="user-panel-title">可以怎么限定</div>
            <ul className="user-capability-list user-capability-list-soft">
              {workflowHints[1].items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </aside>

        <section className="user-answer-panel">
          {turns.length === 0 ? (
            <div className="user-empty-answer">
              <div className="user-empty-title">先问一个单指标问题</div>
              <p>例如送检量、整倍体率、质控情况、结果分布。问题不够明确时，我会给出补参选项。</p>
            </div>
          ) : null}

          <div className="user-thread">
            {turns.map((turn, index) => (
              <article className={`user-turn user-turn-${turn.role}`} key={`${turn.role}-${index}`}>
                <div className="user-turn-label">{turn.role === "user" ? "你的问题" : "分析结果"}</div>
                <div className="user-turn-text">{turn.text}</div>
                {turn.response?.structured_answer.answer_mode !== "answer" && turn.response?.structured_answer.rationale ? (
                  <div className={`user-state user-state-${turn.response.structured_answer.answer_mode}`}>
                    {turn.response.structured_answer.rationale}
                  </div>
                ) : null}
                {turn.response?.clarify_payload ? (
                  <ClarifyCard
                    payload={turn.response.clarify_payload}
                    isSubmitting={isSubmitting}
                    onSelectOption={(item) => void submitPrompt(item)}
                    sessionReady={sessionReady}
                  />
                ) : null}
                {turn.response ? <UserResultCards response={turn.response} /> : null}
              </article>
            ))}
          </div>

          {latestAssistant?.response?.follow_up_suggestions.length ? (
            <div className="user-followup-bar">
              <div className="user-followup-head">
                <div className="user-panel-title">继续追问</div>
              </div>
              <div className="user-followup-chip-list">
                {latestAssistant.response.follow_up_suggestions.map((item) => (
                  <button
                    className="user-followup-chip"
                    disabled={isSubmitting || !sessionReady}
                    key={item}
                    onClick={() => void submitPrompt(item)}
                    type="button"
                  >
                    {item}
                  </button>
                ))}
              </div>
              <form
                className="user-followup-composer"
                onSubmit={(event) => {
                  void onSubmit(event);
                }}
              >
                <input
                  className="user-followup-input"
                  disabled={!sessionReady}
                  onChange={(event) => onInputChange(event.target.value)}
                  placeholder="继续输入你的问题"
                  type="text"
                  value={input}
                />
                <button
                  className="user-followup-submit"
                  disabled={isSubmitting || !sessionReady || !input.trim()}
                  type="submit"
                >
                  {isSubmitting ? "发送中..." : "发送"}
                </button>
              </form>
            </div>
          ) : null}

          {error ? <div className="error-banner">{error}</div> : null}
        </section>
      </main>
    </div>
  );
}

function SessionOverviewPanel({ overview }: { overview: NonNullable<SessionRecord["overview"]> }) {
  const avgEmbryosPerCycle =
    overview.cycle_count > 0 ? (overview.embryo_count / overview.cycle_count).toFixed(2) : "0.00";

  return (
    <section className="session-overview-panel">
      <div className="session-overview-copy">
        <div className="session-overview-kicker">Current Snapshot View</div>
        <h2>会话已连接，先看当前医院的整体盘面</h2>
        <p>{overview.summary}</p>
      </div>

      <div className="session-overview-grid">
        <article className="session-overview-stat session-overview-stat-hero">
          <span className="session-overview-label">当前快照胚胎数</span>
          <strong>{overview.embryo_count.toLocaleString("zh-CN")}</strong>
          <span className="session-overview-footnote">可直接进入 PGT-A 受控统计分析的胚胎样本</span>
        </article>

        <article className="session-overview-stat">
          <span className="session-overview-label">覆盖周期数</span>
          <strong>{overview.cycle_count.toLocaleString("zh-CN")}</strong>
          <span className="session-overview-footnote">按送检单编号去重后的周期规模</span>
        </article>

        <article className="session-overview-stat session-overview-stat-soft">
          <span className="session-overview-label">平均每周期胚胎数</span>
          <strong>{avgEmbryosPerCycle}</strong>
          <span className="session-overview-footnote">帮助客户先建立当前盘面的规模感知</span>
        </article>

        <article className="session-overview-stat session-overview-stat-range">
          <span className="session-overview-label">数据覆盖月份</span>
          <strong>
            {overview.snapshot_start} <span>至</span> {overview.snapshot_end}
          </strong>
          <span className="session-overview-footnote">后续追问默认沿用当前医院，再叠加时间和年龄筛选</span>
        </article>
      </div>
    </section>
  );
}
