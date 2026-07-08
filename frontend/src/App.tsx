import { FormEvent, type CSSProperties, useEffect, useRef, useState } from "react";

import { ClarifyCard } from "./components/ClarifyCard";
import { ResultCards } from "./components/ResultCards";
import { UserResultCards } from "./components/UserResultCards";
import {
  createSession,
  type DemoAccessMode,
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
type ProductScope = "PGT-A" | "PGT-SR";
type HospitalScopeMode = "single" | "all";

const PRODUCT_OPTIONS: ProductScope[] = ["PGT-A", "PGT-SR"];

const PRODUCT_WORKSPACES: Record<
  ProductScope,
  {
    accent: string;
    businessTags: string[];
    icon: string;
    promptGroups: Array<{ title: string; description: string; prompts: string[] }>;
    workflowHints: Array<{ title: string; items: string[] }>;
    title: string;
    portalTitle: string;
    portalSubtitle: string;
    placeholder: string;
    objectChoices?: Array<{ kicker: string; title: string; description: string; prompt: string }>;
  }
> = {
  "PGT-A": {
    accent: "#27614f",
    businessTags: ["胚胎结果", "年龄分层", "周期结局"],
    icon: "A",
    title: "PGT-A 数据回顾",
    portalTitle: "PGT-A 回顾分析",
    portalSubtitle: "查看送检量、整倍体率、质控和周期结局",
    placeholder: "直接输入你想回顾的问题，例如：2025 年 PGT-A 的整倍体率怎么样？",
    promptGroups: [
      {
        title: "看规模和趋势",
        description: "适合做月度、季度经营回顾",
        prompts: ["按季度看一下 2025 年 PGT-A 送检趋势", "看一下 2025 年 7 月到 10 月 PGT-A 送检量", "2025 年 PGT-A 每月整倍体率变化怎么样"],
      },
      {
        title: "看结果和质量",
        description: "适合查看结果结构、质控和特殊提示",
        prompts: ["看一下 2025 年 PGT-A 质控情况", "看一下 PGT-A 结果分布和异常结构", "特殊 CNV 提示这块有多少"],
      },
      {
        title: "看人群和周期",
        description: "适合按年龄或周期层面拆开看",
        prompts: ["按年龄分层看一下 PGT-A 整倍体率", "按年龄分层，从周期维度看整体结局", "看一下 PGT-A 的周期无整倍体率"],
      },
    ],
    workflowHints: [
      { title: "可回答的问题", items: ["送检量", "胚胎整倍体率", "年龄分层", "质控", "结果结构", "周期结局", "特殊 CNV"] },
      { title: "可以使用的条件", items: ["医院", "时间范围", "年龄范围"] },
      { title: "当前不支持", items: ["PGT-SR / PGT-M / PGT-AH 真实执行", "全产品汇总", "复杂多指标联合执行", "临床指征类统计"] },
    ],
    objectChoices: [
      { kicker: "输出胚胎数和比例", title: "胚胎整倍体率", description: "适合判断检测胚胎中未见异常的占比。", prompt: "看一下 PGT-A 的胚胎整倍体率" },
      { kicker: "输出周期结局分布", title: "周期整倍体结局", description: "适合判断每个周期是否有可用整倍体胚胎。", prompt: "看一下 PGT-A 的周期整倍体结局" },
    ],
  },
  "PGT-SR": {
    accent: "#8a4f24",
    businessTags: ["临床指征", "易位相关", "周期结局"],
    icon: "SR",
    title: "PGT-SR 数据回顾",
    portalTitle: "PGT-SR 回顾分析",
    portalSubtitle: "按临床指征查看胚胎整倍体率和周期结局",
    placeholder: "直接输入你想回顾的问题，例如：按临床指征统计下 PGT-SR 胚胎整倍体率",
    promptGroups: [
      {
        title: "按临床指征看",
        description: "适合比较不同 SR 临床类型的胚胎和周期结局",
        prompts: ["按临床指征统计下 PGT-SR 胚胎整倍体率", "按临床指征看一下 PGT-SR 周期整倍体率情况", "按临床指征看一下 PGT-SR 周期结局"],
      },
      {
        title: "看具体 SR 类型",
        description: "适合查看罗氏易位、平衡易位、倒位等人群",
        prompts: ["PGT-SR 中罗氏易位患者的胚胎整倍体率情况", "罗氏易位、平衡易位患者的胚胎整倍体率", "按女性年龄分层统计胚胎整倍体率"],
      },
      {
        title: "看基础盘面",
        description: "适合查看规模、质控和结果结构",
        prompts: ["看一下 PGT-SR 送检量", "看一下 PGT-SR 结果分布", "看一下 PGT-SR 质控情况"],
      },
    ],
    workflowHints: [
      { title: "可回答的问题", items: ["送检量", "胚胎整倍体率", "结果分布", "周期结局", "下一步易位筛查", "按临床指征比较胚胎整倍体率或周期结局"] },
      { title: "可以使用的条件", items: ["医院", "时间范围", "受检人年龄", "配偶年龄", "临床指征"] },
      { title: "当前不支持", items: ["MaReCs 第二阶段", "核型精细解释", "全产品汇总", "复杂多指标联合执行"] },
    ],
  },
};

export function App() {
  const [viewMode, setViewMode] = useState<ViewMode>("user");
  const [selectedProduct, setSelectedProduct] = useState<ProductScope | null>(null);
  const [accessMode, setAccessMode] = useState<DemoAccessMode>("all");
  const [hospitalScopeMode, setHospitalScopeMode] = useState<HospitalScopeMode>("single");
  const [selectedHospitalId, setSelectedHospitalId] = useState<string>("");
  const [isSwitchingProduct, setIsSwitchingProduct] = useState(false);
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [metadata, setMetadata] = useState<DemoMetadata | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageColumnRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setTurns([]);
    setInput("");
    setSession(null);
    setMetadata(null);
    setError(null);
    setSelectedHospitalId("");
    setHospitalScopeMode("single");
    if (!selectedProduct) {
      setIsSwitchingProduct(false);
      return () => {
        cancelled = true;
      };
    }
    setIsSwitchingProduct(true);
    fetchDemoMetadata(selectedProduct, accessMode)
      .then((meta) => {
        if (cancelled) return;
        setMetadata(meta);
        if (!meta.default_hospital) {
          throw new Error("No hospital found in current snapshot bundle");
        }
        setSelectedHospitalId(meta.default_hospital.hospital_id);
      })
      .catch(() => {
        if (!cancelled) {
          setError("无法创建会话，请检查后端服务是否已启动。");
          setIsSwitchingProduct(false);
        }
      })
    return () => {
      cancelled = true;
    };
  }, [accessMode, selectedProduct]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedProduct || !metadata || !selectedHospitalId) {
      return () => {
        cancelled = true;
      };
    }
    const selectedHospital = metadata.hospitals.find((item) => item.hospital_id === selectedHospitalId);
    if (!selectedHospital) {
      return () => {
        cancelled = true;
      };
    }
    setIsSwitchingProduct(true);
    setSession(null);
    setTurns([]);
    createSession({
      hospital_id: hospitalScopeMode === "all" ? "__ALL_HOSPITALS__" : selectedHospital.hospital_id,
      hospital_name: hospitalScopeMode === "all" ? "全部医院" : selectedHospital.hospital_name,
      product_scope: selectedProduct,
      hospital_scope_mode: hospitalScopeMode,
      accessible_hospital_ids: metadata.hospitals.map((item) => item.hospital_id),
      can_access_all_hospitals: metadata.can_access_all_hospitals,
    })
      .then((record) => {
        if (!cancelled) {
          setSession(record);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("无法创建会话，请检查后端服务是否已启动。");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsSwitchingProduct(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [hospitalScopeMode, metadata, selectedHospitalId, selectedProduct]);

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
        hospital_scope_mode: session.hospital_scope_mode,
        accessible_hospital_ids: metadata?.hospitals.map((item) => item.hospital_id),
        can_access_all_hospitals: metadata?.can_access_all_hospitals,
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

  const currentWorkspace = selectedProduct ? PRODUCT_WORKSPACES[selectedProduct] : null;

  if (viewMode === "user") {
    return (
      <UserWorkspace
        error={error}
        input={input}
        isSubmitting={isSubmitting}
        metadata={metadata}
        onEnterProduct={setSelectedProduct}
        onInputChange={setInput}
        hospitalScopeMode={hospitalScopeMode}
        isSwitchingProduct={isSwitchingProduct}
        accessMode={accessMode}
        onAccessModeChange={setAccessMode}
        onHospitalChange={setSelectedHospitalId}
        onHospitalScopeModeChange={setHospitalScopeMode}
        onModeChange={setViewMode}
        onSubmit={onSubmit}
        productScope={selectedProduct}
        selectedHospitalId={selectedHospitalId}
        onProductChange={setSelectedProduct}
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
            当前处于快照模式，已接入 PGT-A、PGT-AH、PGT-SR、PGT-M 业务数据文件；当前真实执行链路支持 PGT-A 与 PGT-SR 第一阶段受控统计问答和结果卡片展示。
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
            {(currentWorkspace?.workflowHints ?? []).map((group) => (
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
          {!currentWorkspace ? (
            <div className="workflow-copy">
              先返回产品门户选择 PGT-A 或 PGT-SR，研发调试页才会加载对应的问法引导和会话上下文。
            </div>
          ) : null}
          {(currentWorkspace?.promptGroups ?? []).map((group) => (
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
                      当前快照模式已接入 PGT-A、PGT-AH、PGT-SR、PGT-M 业务文件；请选择产品后再进入对应的一阶段受控统计工作台。
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
                  placeholder={currentWorkspace?.placeholder ?? "请先返回产品门户选择产品，再进入研发调试提问。"}
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
  accessMode: DemoAccessMode;
  hospitalScopeMode: HospitalScopeMode;
  isSwitchingProduct: boolean;
  metadata: DemoMetadata | null;
  onEnterProduct: (product: ProductScope) => void;
  onAccessModeChange: (mode: DemoAccessMode) => void;
  onHospitalChange: (hospitalId: string) => void;
  onHospitalScopeModeChange: (mode: HospitalScopeMode) => void;
  onInputChange: (value: string) => void;
  onModeChange: (mode: ViewMode) => void;
  onProductChange: (product: ProductScope | null) => void;
  onSubmit: (event: FormEvent) => Promise<void>;
  productScope: ProductScope | null;
  selectedHospitalId: string;
  session: SessionRecord | null;
  submitPrompt: (prompt: string) => Promise<void>;
  turns: ChatTurn[];
};

function UserWorkspace({
  error,
  input,
  isSubmitting,
  accessMode,
  hospitalScopeMode,
  isSwitchingProduct,
  metadata,
  onEnterProduct,
  onAccessModeChange,
  onHospitalChange,
  onHospitalScopeModeChange,
  onInputChange,
  onModeChange,
  onProductChange,
  onSubmit,
  productScope,
  selectedHospitalId,
  session,
  submitPrompt,
  turns,
}: WorkspaceProps) {
  const workspace = productScope ? PRODUCT_WORKSPACES[productScope] : null;
  const hospitalName = session?.hospital_name ?? metadata?.default_hospital?.hospital_name ?? "当前医院";
  const overview = session?.overview ?? null;
  const snapshotRange = overview
    ? `${overview.snapshot_start} 至 ${overview.snapshot_end}`
    : metadata
      ? `${metadata.snapshot_start.slice(0, 10)} 至 ${metadata.snapshot_end.slice(0, 10)}`
      : "等待快照信息";
  const latestAssistant = [...turns].reverse().find((turn) => turn.role === "assistant" && turn.response);
  const sessionReady = Boolean(session);
  const isWorkspaceLocked = isSubmitting || isSwitchingProduct || !sessionReady;
  const sessionStatusText = isSwitchingProduct
    ? `正在切换到 ${productScope}`
    : session
      ? "会话已连接"
      : "连接中";
  const [expandedPromptGroups, setExpandedPromptGroups] = useState<Record<string, boolean>>({});
  const [showObjectChoices, setShowObjectChoices] = useState(false);

  useEffect(() => {
    setExpandedPromptGroups({});
    setShowObjectChoices(false);
  }, [productScope]);

  if (!productScope || !workspace) {
    return (
      <div className="user-shell">
        <header className="user-topbar">
          <div className="user-brand">
            <div className="user-brand-mark">YK</div>
            <div>
              <div className="user-brand-title">PGT 数据回顾</div>
              <div className="user-brand-subtitle">选择产品，开始分析</div>
            </div>
          </div>
          <div className="user-topbar-actions">
            <select
              className="mode-switch-button"
              disabled={isSwitchingProduct}
              value={accessMode}
              onChange={(event) => onAccessModeChange(event.target.value as DemoAccessMode)}
            >
              <option value="single">本院账号</option>
              <option value="all">内部账号</option>
            </select>
          </div>
        </header>

        <main className="user-main user-main-landing">
          <section className="user-command-panel user-command-panel-landing">
            <div className="user-context-row">
              <div>
                <div className="user-kicker">选产品</div>
                <h1>今天要看哪类 PGT 数据？</h1>
                <p className="user-context-lead">
                  先选产品，再进入分析。系统会按你选择的产品准备对应数据和推荐问题。
                </p>
              </div>
            </div>

            <div className="product-entry-grid">
              {PRODUCT_OPTIONS.map((product) => {
                const entry = PRODUCT_WORKSPACES[product];
                return (
                  <button
                    className="product-entry-card"
                    key={product}
                    style={{ "--product-accent": entry.accent } as CSSProperties}
                    onClick={() => onEnterProduct(product)}
                    type="button"
                  >
                    <span className="product-entry-icon" aria-hidden="true">{entry.icon}</span>
                    <span className="product-entry-kicker">进入分析</span>
                    <strong>{entry.portalTitle}</strong>
                    <span>{entry.portalSubtitle}</span>
                    <div className="product-entry-tags">
                      {entry.businessTags.map((item) => (
                        <span className="product-entry-tag" key={item}>
                          {item}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>

            {error ? <div className="error-banner">{error}</div> : null}
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="user-shell">
      <header className="user-topbar">
        <div className="user-brand">
          <div className="user-brand-mark">YK</div>
          <div>
            <div className="user-brand-title">PGT 数据回顾助手</div>
            <div className="user-brand-subtitle">受控统计问答</div>
          </div>
        </div>
        <div className="user-topbar-actions">
          <select
            className="mode-switch-button"
            disabled={isSwitchingProduct}
            value={accessMode}
            onChange={(event) => onAccessModeChange(event.target.value as DemoAccessMode)}
          >
            <option value="single">本院账号</option>
            <option value="all">内部账号</option>
          </select>
          <select
            className="mode-switch-button"
            disabled={isSwitchingProduct || !metadata?.can_access_all_hospitals}
            value={hospitalScopeMode}
            onChange={(event) => onHospitalScopeModeChange(event.target.value as HospitalScopeMode)}
          >
            <option value="single">当前医院</option>
            <option value="all">全部医院</option>
          </select>
          {hospitalScopeMode === "single" ? (
            <select
              className="mode-switch-button hospital-switch-select"
              disabled={isSwitchingProduct || !metadata || !metadata.can_access_all_hospitals}
              value={selectedHospitalId}
              onChange={(event) => onHospitalChange(event.target.value)}
            >
              {metadata?.hospitals.map((hospital) => (
                <option key={hospital.hospital_id} value={hospital.hospital_id}>
                  {hospital.hospital_name}
                </option>
              ))}
            </select>
          ) : null}
          <select
            className="mode-switch-button"
            disabled={isSwitchingProduct}
            value={productScope}
            onChange={(event) => onProductChange(event.target.value as ProductScope)}
          >
            <option value="PGT-A">PGT-A</option>
            <option value="PGT-SR">PGT-SR</option>
          </select>
          <button className="mode-switch-button" onClick={() => onProductChange(null)} type="button">
            返回产品选择
          </button>
          <div className={`user-session-pill${isSwitchingProduct ? " user-session-pill-loading" : ""}`}>{sessionStatusText}</div>
          <button className="mode-switch-button" onClick={() => onModeChange("debug")} type="button">
            研发调试
          </button>
        </div>
      </header>

      <main className="user-main">
        <section className="user-command-panel">
          <div className="user-context-row">
            <div>
              <div className="user-kicker">{hospitalScopeMode === "all" ? "全部医院范围" : hospitalName}</div>
              <h1>{workspace.title}</h1>
            </div>
          </div>

          {overview ? <SessionOverviewPanel overview={overview} /> : null}

          {isSwitchingProduct ? (
            <div className="user-switching-banner" role="status" aria-live="polite">
              <div className="user-switching-spinner" aria-hidden="true" />
              <div>
                <strong>正在切换到 {productScope}</strong>
                <span>正在重建默认医院、快照范围和当前会话上下文，完成前暂时不能直接提问。</span>
              </div>
            </div>
          ) : null}

          <form className="user-composer" onSubmit={onSubmit}>
            <textarea
              disabled={isWorkspaceLocked}
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              placeholder={workspace.placeholder}
              rows={3}
            />
            <div className="user-composer-footer">
              <div className="user-composer-hint">支持连续追问，会沿用当前医院和可继承的筛选条件。</div>
              <button className="user-submit-button" disabled={isWorkspaceLocked} type="submit">
                {isSubmitting ? "分析中..." : "开始分析"}
              </button>
            </div>
          </form>

          <div className="user-prompt-lanes">
            {workspace.promptGroups.map((group) => (
              <div className="user-prompt-lane" key={group.title}>
                <div className="user-lane-title">{group.title}</div>
                <p className="user-lane-copy">{group.description}</p>
                <div className="user-prompt-list">
                  {(expandedPromptGroups[group.title] ? group.prompts : group.prompts.slice(0, 2)).map((prompt) => (
                    <button
                      className="user-prompt-chip"
                      disabled={isWorkspaceLocked}
                      key={prompt}
                      onClick={() => void submitPrompt(prompt)}
                      type="button"
                    >
                      {prompt}
                    </button>
                  ))}
                  {group.prompts.length > 2 && !expandedPromptGroups[group.title] ? (
                    <button
                      className="user-prompt-more"
                      disabled={isWorkspaceLocked}
                      onClick={() =>
                        setExpandedPromptGroups((current) => ({
                          ...current,
                          [group.title]: true,
                        }))
                      }
                      type="button"
                    >
                      查看更多
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          {workspace.objectChoices ? <div className="user-object-choices">
            <div className="user-object-choices-head">
              <div className="user-lane-title">整倍体指标怎么选</div>
              <button
                className="user-prompt-more"
                disabled={isWorkspaceLocked}
                onClick={() => setShowObjectChoices((current) => !current)}
                type="button"
              >
                {showObjectChoices ? "收起说明" : "查看说明"}
              </button>
            </div>
            {showObjectChoices ? (
              <div className="user-object-choice-list">
                {workspace.objectChoices.map((choice) => (
                  <button
                    className="user-object-choice"
                    disabled={isWorkspaceLocked}
                    key={choice.prompt}
                    onClick={() => void submitPrompt(choice.prompt)}
                    type="button"
                  >
                    <span className="user-object-choice-kicker">{choice.kicker}</span>
                    <strong>{choice.title}</strong>
                    <span>{choice.description}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div> : null}
        </section>

        <aside className="user-capability-panel">
          <div className="user-panel-section user-panel-section-primary">
            <div className="user-panel-title">当前数据</div>
            <div className="user-scope-list">
              <div>
                <span>权限视角</span>
                <strong>{accessMode === "all" ? "内部账号" : "本院账号"}</strong>
              </div>
              <div>
                <span>当前范围</span>
                <strong>{hospitalName}</strong>
              </div>
              <div>
                <span>当前可分析</span>
                <strong>{productScope}</strong>
              </div>
              <div>
                <span>数据范围</span>
                <strong>{snapshotRange}</strong>
              </div>
            </div>
          </div>

          <div className="user-panel-divider" />

          <div className="user-panel-section">
            <div className="user-panel-title">能问什么</div>
            <ul className="user-capability-list">
              {workspace.workflowHints[0].items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="user-panel-section">
            <div className="user-panel-title">可以怎么限定</div>
            <ul className="user-capability-list user-capability-list-soft">
              {workspace.workflowHints[1].items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </aside>

        <section className="user-answer-panel">
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
                    disabled={isWorkspaceLocked}
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
                  disabled={isSwitchingProduct || !sessionReady}
                  onChange={(event) => onInputChange(event.target.value)}
                  placeholder="继续输入你的问题"
                  type="text"
                  value={input}
                />
                <button
                  className="user-followup-submit"
                  disabled={isSwitchingProduct || isSubmitting || !sessionReady || !input.trim()}
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
        <div className="session-overview-kicker">数据概览</div>
        <h2>{overview.hospital_scope_mode === "all" ? "全部医院当前数据概览" : "当前医院数据概览"}</h2>
      </div>

      <div className="session-overview-grid">
        <article className="session-overview-stat session-overview-stat-hero">
          <span className="session-overview-label">可分析胚胎</span>
          <strong>{overview.embryo_count.toLocaleString("zh-CN")}</strong>
        </article>

        <article className="session-overview-stat">
          <span className="session-overview-label">涉及周期</span>
          <strong>{overview.cycle_count.toLocaleString("zh-CN")}</strong>
        </article>

        <article className="session-overview-stat session-overview-stat-soft">
          <span className="session-overview-label">每周期平均胚胎</span>
          <strong>{avgEmbryosPerCycle}</strong>
        </article>
      </div>
    </section>
  );
}
