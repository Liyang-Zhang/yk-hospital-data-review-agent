# DataWowsight 对照分析

## 分析对象

- 仓库：`wdkwdkwdk/DataWowsight`
- 本地拉取位置：`/tmp/DataWowsight`

本次分析依据：

- [README.md](/tmp/DataWowsight/README.md)
- [package.json](/tmp/DataWowsight/package.json)
- [lib/analysis/orchestrator.ts](/tmp/DataWowsight/lib/analysis/orchestrator.ts)
- [lib/sql-safety.ts](/tmp/DataWowsight/lib/sql-safety.ts)
- [lib/analysis/schema-intelligence.ts](/tmp/DataWowsight/lib/analysis/schema-intelligence.ts)
- [lib/types.ts](/tmp/DataWowsight/lib/types.ts)
- [app/page.tsx](/tmp/DataWowsight/app/page.tsx)
- [app/api/analysis/query/route.ts](/tmp/DataWowsight/app/api/analysis/query/route.ts)
- [app/api/analysis/runs/[id]/stream/route.ts](/tmp/DataWowsight/app/api/analysis/runs/[id]/stream/route.ts)

## 一句话判断

DataWowsight 对我们最大的指导意义不在“chat to SQL”，而在：

- 透明执行链路
- 运行态和任务态设计
- 只读安全层
- 结果证据链和流式回传

它对我们指导有限的部分是：

- 医疗统计口径
- 指标语义层
- 受控问答边界
- 多源数据事实层

## 项目画像

DataWowsight 是一个：

- 单仓 Next.js 全栈项目
- 面向通用数据库分析的轻量 analytics agent
- 强调 `planning -> SQL -> evidence -> answer`
- 强调 run lifecycle、SQL trace、SSE 更新和只读安全

它本质上是：

- 通用 analytics agent

而我们项目本质上是：

- 医院 PGT 数据回顾的受控统计助手

这两者不是同一类产品。

## 可借鉴 / 不该借 / 未来再借

| 模块/思路 | DataWowsight 做法 | 对我们建议 | 原因 | 对应到我们项目 |
|---|---|---|---|---|
| 执行链路透明化 | `planning -> SQL -> evidence -> answer`，并保留 run events 与 traces | 可借鉴 | 对复杂统计请求很重要，能提升可解释性和调试性 | 我们可以做 `request parse -> capability matrix -> analysis plan -> atomic metric functions -> answer` |
| 只读安全层 | `lib/sql-safety.ts` 用 parser + keyword guard 限制只读 SQL | 可借鉴 | 安全理念对，尤其是未来接真实库时 | 但我们更适合做“业务原子函数安全层”，不直接让 LLM 产 SQL |
| SSE + 可恢复 run | `app/api/analysis/runs/[id]/stream/route.ts` 支持流式事件和 resume | 可借鉴 | 对未来长任务、多子任务、复杂统计请求非常有用 | 未来支持结构化业务统计请求时可复用这个思想 |
| 对话 + run + audit log 分层 | `types.ts` 里有 conversation / run / sql audit / debug logs | 可借鉴 | 任务态和消息态分离很清晰 | 我们未来应补 `analysis task`、`subtask`、`capability report` 等对象 |
| 图表从结果数据生成 | 图表基于 SQL 结果集，不是模型硬编 | 可借鉴 | 这和我们当前“图表是受控展示协议”方向一致 | 可继续坚持后端决定图表 payload，前端只渲染 |
| Schema intelligence | `schema-intelligence.ts` 通过 introspection + heuristic enrich 表结构 | 未来再借 | 未来接正式数据库时会有价值 | 但我们当前优先级更高的是指标语义层，不是通用 schema 描述 |
| 可配置 LLM runtime | 支持 openrouter / openai-compatible，多 scope 配置 | 可借鉴 | 工程化做法不错 | 我们已有 Qwen/OpenAI-compatible 方向，可学习它的 runtime 配置分层 |
| 单仓 Next.js 全栈 | 前后端都在 Next.js API routes 内 | 不该借 | 我们主后端明确是 Python，后续还要接企业系统和受控数据层 | 当前不应为参考项目改变主栈 |
| LLM 直接驱动 SQL 写作 | planner 决定 action，SQL writer 生成 SQL，再执行 | 不该借 | 对我们项目风险过高，尤其医疗统计口径和合规场景 | 我们应坚持“LLM 只做理解和计划，执行层只调业务原子函数” |
| 通用数据库分析定位 | 输入任意数据库问题，走 agent loop | 不该借 | 会削弱我们的产品边界，重新滑向通用 chat-to-SQL | 我们必须坚持 `product scope + database support` 双重判断 |
| SQL trace 直接面向最终用户 | 前端大面积展示 SQL / debug / run traces | 未来再借 | 对内部调试有用，但医院老师未必适合直接看 | 可作为内部调试视图或专家模式，不作为默认用户界面 |
| 明文存 API key | README 直接写了 plaintext 存储是当前阶段方案 | 不该借 | 这是工程权宜之计，不适合复制 | 我们后续应走更稳妥配置/密钥管理方式 |
| 结果回答是通用 report | `InsightReport` 支持 summary / chart / resultTable / sqlTraces | 可借鉴 | 结果对象建模思路值得学 | 我们可以扩成 `structured statistical answer package` |
| Clarification flow | `ClarifyRequest` 类型存在，但当前实现里直接 disabled | 未来再借 | 它识别到澄清的重要性，但还没做完整闭环 | 我们当前已经在做 clarify/refuse，反而这块比它更产品化 |

## 对我们最有价值的 5 点

### 1. 把“分析过程”变成显式对象

DataWowsight 明确有：

- run
- run events
- sql audit
- debug log
- report

这提醒我们：

- 复杂统计请求不应只留下最终回答
- 应该留下任务对象、子任务对象、执行日志对象

### 2. 长任务必须有任务态，不只是同步接口

它用：

- `POST /api/analysis/query`
- `GET /api/analysis/runs/:id`
- `GET /api/analysis/runs/:id/stream`

说明它把分析看成一个“run”，不是一次普通请求。

这对我们未来处理：

- 多产品
- 多指标
- 部分支持
- 分步完成

非常重要。

### 3. SQL 安全是单独一层，不应散落在执行代码里

`lib/sql-safety.ts` 独立存在，这一点值得直接借鉴。

即使我们未来不直接执行 LLM 产出的 SQL，也应该有：

- query guard
- read-only contract
- row limit / timeout / cost guard

### 4. 前端要承认“分析不是一次性返回”的事实

DataWowsight 前端里有：

- run status
- status message
- message list
- log viewer
- trace export

说明它没有把分析当成普通聊天泡泡，而是“聊天 + 任务执行”的混合体验。

这对我们未来的结构化业务统计请求很有指导意义。

### 5. 结果对象要同时容纳 summary / chart / table / trace

它的 `InsightReport` 结构比较实用：

- summary
- keyEvidence
- analysisMethod
- chart
- resultTable
- sqlTraces
- debugLogs

我们当前已经有 `summary/table/chart`，未来可以补：

- key evidence
- analysis method
- capability gaps
- subtask traces

## 对我们最不该照搬的 4 点

### 1. 不要把模型放到数据库前面自由写 SQL

这是它产品定位的一部分，但对我们是高风险方向。

我们这里必须坚持：

- LLM 负责理解
- planner 负责拆解
- executor 只调业务函数

### 2. 不要把“通用数据库分析 agent”当成目标

我们不是做一个“问数据库任何问题”的产品。

我们做的是：

- 医院客户
- PGT 数据回顾
- 受控统计问答

### 3. 不要把 schema intelligence 当成当前最优先事项

它的 introspection 很适合通用数据库探索。

但我们当前更紧要的是：

- 指标口径
- 业务语义层
- 多系统字段来源确认

### 4. 不要照搬它的 UI 复杂度

它的 run 面板、trace viewer、export、connection 管理都比较重。

对我们当前 V0.1 来说：

- 可借鉴任务态概念
- 但不应一开始就复制整套复杂运维式界面

## 未来再借的部分

这些内容不该现在做，但未来值得吸收：

1. `run stream / resume`
2. `analysis task + event log`
3. `internal trace viewer`
4. `datasource introspection assistant`
5. `structured export`

## 对我们当前架构的直接启发

结合我们现在的代码主干，最值得追加的不是“SQL 生成”，而是这三层：

### A. AnalysisTask 层

当前我们已经有：

- `ParsedIntent`
- `AnalysisPlan`

后续应补：

- `AnalysisTask`
- `Subtask`
- `TaskStatus`
- `CapabilityReport`

### B. Atomic Metric Function 层

DataWowsight 的执行单元是 SQL。

我们的执行单元应该是：

- `count_cycles`
- `count_embryos`
- `calc_euploid_rate`
- `calc_na_rate`
- `calc_mosaic_only_rate`

### C. Partial Support 输出层

DataWowsight 偏向“能不能跑 SQL”。

我们更需要：

- 哪些产品支持
- 哪些指标支持
- 哪些字段缺失
- 哪些口径未确认

这类 capability-first 的输出。

## 最终结论

DataWowsight 对我们有明显指导意义，但它指导的是：

- agent runtime
- traceability
- safe execution
- long-task interaction

不是：

- 医疗统计口径
- 产品边界设计
- 业务语义层

所以正确姿势不是“照着做”，而是：

- 当前阶段保留我们的受控问答主干
- 未来逐步吸收它的任务态和执行态设计

最适合我们的落地结论是：

### 现在就借

- 执行链路透明化
- 分析任务对象化
- 只读安全层思想

### 现在不要借

- LLM 直写 SQL
- 通用数据库分析定位
- 重 JS 全栈迁移

### 未来可以借

- run stream / resume
- trace viewer
- schema intelligence
- richer export workflow
