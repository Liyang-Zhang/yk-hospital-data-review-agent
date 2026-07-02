# yk-hospital-data-review-agent

面向医院客户的定期数据回顾分析智能体骨架工程。

当前第一版开发收敛范围：

- 数据源切换为业务人工整合的快照文件：
  - `docs/PGTA数据统计输出-2025年.xlsx`
  - `docs/PGTAH数据统计输出-2025年-上传微盘.xlsx`
  - `docs/PGTSR数据统计输出-2025年.xlsx`
  - `docs/2025-PGTM类全年输出.xlsx`
- 当前真实执行范围固定为 `PGT-A`
- `PGT-AH / PGT-SR / PGT-M` 已接入快照元信息层，用于能力说明和后续扩展
- 时间筛选规则：
  - `年 / 月 / 季度` 优先基于业务统计月份字段
  - `按日` 基于审核时间字段
- LLM 提供层默认按 `Qwen / DashScope OpenAI-compatible` 接入

## 目录

- `docs/`：当前产品边界、指标计算说明、路由回归、人工测试、架构方案
- `app/`：后端服务
- `frontend/`：嵌入式聊天前端

当前保留的核心文档：

- `docs/当前产品边界速记.md`
- `docs/多线程开发规划.md`
- `docs/PGTA问法标准答案基线-20260702.md`
- `docs/PGTA指标计算说明-20260701.md`
- `docs/V0.2路由语料回归说明.md`
- `docs/人工测试说明.md`
- `docs/执行级技术架构方案.md`

## 环境管理建议

推荐双轨方案：

- 本地开发优先使用 `micromamba`
- Docker 交付继续使用 `python:3.11-slim`

原因：

- `micromamba` 适合开发环境隔离、统一 Python 与 Node 版本
- 当前项目依赖仍以纯 Python 为主，没有必要把 `conda` 强绑定到生产镜像
- IT 后续接手时，基于官方 Python 镜像的 Docker 更容易维护和排障

## 使用 micromamba 启动

```bash
micromamba create -f environment.yml
micromamba activate yk-review-agent
```

后端启动：

```bash
uvicorn yk_review_agent.main:app --reload --port 18765
```

如需启用正式 LLM 解析，请先配置 `.env`：

```bash
cp .env.example .env
```

然后填写：

- `LLM_MODEL=qwen-plus` 或其他 Qwen 系列模型
- `LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
- `LLM_API_KEY=你的 DashScope 兼容接口密钥`

前端启动：

```bash
cd frontend
npm install
export VITE_API_BASE=http://localhost:18765/api/v1
npm run dev
```

## 使用 venv 启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn yk_review_agent.main:app --reload --port 18765
```

## 前端启动

```bash
cd frontend
npm install
export VITE_API_BASE=http://localhost:18765/api/v1
npm run dev
```

## Docker

```bash
docker build -t yk-review-agent .
docker run --rm -p 18765:8000 yk-review-agent
```

## 说明

- `environment.yml` 用于本地开发环境
- `pyproject.toml` 仍是 Python 依赖的主定义
- Docker 当前不依赖 `micromamba`
- 未配置 `LLM_API_KEY` 时，后端会自动回退到本地规则解析
- 当前产品处于 `snapshot mode`：依赖业务高质量 Excel 快照，而不是正式接口
