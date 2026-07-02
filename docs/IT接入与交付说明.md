# IT 接入与交付说明

## 1. 当前交付内容

当前工程包含：

- Python 后端服务骨架
- 嵌入式聊天前端骨架
- Docker 构建文件
- Micromamba 开发环境描述文件
- 环境变量样例
- 技术架构文档

## 2. 推荐接入方式

推荐优先级：

1. `iframe`
2. 反向代理同域挂载
3. 前端静态资源独立托管

## 3. 宿主系统需提供的信息

- 当前登录用户唯一标识
- 当前医院唯一标识
- 当前医院名称，可选
- 宿主会话 ID，可选
- 鉴权 token 或签名，可选

## 4. 后端环境变量

- `DATABASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `HOST_ALLOWED_ORIGINS`
- `DEMO_MODE`

## 5. 开发与交付环境说明

- 开发侧推荐使用 `micromamba + environment.yml`
- 交付侧推荐使用 Docker 镜像
- 当前 Docker 运行时不依赖 conda 环境

## 6. 第一版接口

- `GET /api/v1/health`
- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/chat`

## 7. 后续联调重点

- 宿主系统如何把医院上下文透传给本应用
- 数据库是否提供只读视图或只读 schema
- 是否需要 PDF 导出
- 是否需要统一日志和链路追踪
