# FusionRAG Knowledge Base

基于 Fusion RAG 架构的个人/企业知识库问答系统。融合 BM25 关键词检索与语义向量检索，支持自适应 Multi-Query、Qwen Reranker 重排序，以及 Docling 文档解析。

> 项目现状与架构细节见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。Cursor Agent 请参阅 [AGENTS.md](AGENTS.md)。

## 功能特性

- **Fusion RAG 检索**：稠密向量 + BM25 稀疏检索，RRF 融合 + Qwen Reranker 重排
- **自适应 Multi-Query**：按 SIMPLE / MODERATE / COMPLEX 动态生成 1 / 3 / 5 条子查询
- **企业级文档解析**：Docling 基础解析 + PaddleOCR 可选增强（CPU 默认关闭）
- **量化评估**：Recall@K、MRR、nDCG、Hit@K；支持无/有 Reranker 对比
- **Confluence 基准集**：132 篇文档 + 64 条检索评测问答
- **Web UI（v0.2）**：多轮 RAG 对话（Query Rewrite）+ 文档管理（FastAPI + React）

## 环境要求

- Python 3.10+
- Node.js 18+（Web 前端）
- Docker Desktop（Milvus 2.5 + PostgreSQL 15）
- 阿里云百炼 DashScope API Key（或 `USE_MOCK=true` 本地开发）

## 快速开始

### 1. 克隆并安装依赖

```bash
cd FusionRAG-Knowledge-Base
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
copy .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY
```

### 3. 启动基础设施

```bash
docker compose up -d
python scripts/init_db.py
```

### 4. 文档入库

将 PDF/Markdown 放入 `data/documents/`，或使用内置 Confluence 基准集：

```bash
# Confluence 基准（推荐；doc_id 取自文件名 dsid_*）
python scripts/run_ingest.py \
  --path data/documents/confluence/confluence_markdown \
  --init-db

# 或任意目录
python scripts/run_ingest.py --path data/documents --init-db
```

### 5. Web 界面（推荐）

```bash
# 终端 1：API（:8000，Swagger 见 /docs）
python scripts/run_api.py

# 终端 2：前端（:5173）
cd web
npm install
npm run dev
```

浏览器打开 http://localhost:5173 — **对话** 与 **文档管理** 两个 Tab。

### 6. CLI 问答

```bash
python scripts/run_query.py "What is the default contractor access expiry period?"
python scripts/run_query.py --interactive
```

### 7. 检索评估

```bash
# Confluence 主基准（64 题）— 仅 RRF 混合检索
python scripts/run_eval.py \
  --dataset data/documents/confluence/confluence_questions.jsonl \
  --k 1,5,10

# 同上 + Reranker（与 run_query 检索链一致）
python scripts/run_eval.py \
  --dataset data/documents/confluence/confluence_questions.jsonl \
  --k 1,5,10 --with-reranker

# 快速 smoke test（3 题）
python scripts/run_eval.py --dataset data/eval_dataset/sample.json --k 1,5,10
```

报告输出至 `reports/`（`eval_*.json` 无 Reranker，`eval_rerank_*.json` 有 Reranker）。近期指标对比见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## Mock 开发模式

无 API Key 时可在 `.env` 中设置：

```
USE_MOCK=true
```

Mock 模式使用确定性假向量与关键词重排，适合本地开发与单元测试。

## 项目结构

```
config/
  settings.yaml              # 模型、切分、检索、OCR 等
  prompts/                   # Multi-Query、Query Rewrite、生成 Prompt
src/
  ingestion/                 # 解析、切分、索引（含 dsid doc_id 解析）
  retrieval/                 # Query Rewrite、Multi-Query、混合检索、重排、生成
  api/                       # FastAPI 路由与服务（对话、文档）
  evaluation/                # 数据集加载、指标、评估流程
  utils/                     # 配置、DB、API 客户端
scripts/                     # init_db, run_ingest, run_query, run_eval, run_api
web/                         # React + Vite 前端
data/
  documents/confluence/      # 基准文档 + 评测问答（见各目录 README）
  eval_dataset/              # sample.json smoke 集
docs/
  spec.md                    # 需求规格
  PROJECT_STATUS.md          # 项目现状（实现状态、评测结果）
reports/                     # 评估 JSON 输出（gitignore）
docker-compose.yml           # Milvus + PostgreSQL + 依赖
```

## 配置说明

### 环境变量

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `DASHSCOPE_API_KEY` | 百炼 API 密钥 | — |
| `MILVUS_HOST` | Milvus 地址 | localhost |
| `MILVUS_PORT` | Milvus 端口 | 19530 |
| `POSTGRES_URL` | PostgreSQL 连接串 | postgresql://fusion:fusion@localhost:5432/fusion_rag |
| `USE_MOCK` | Mock 模式 | false |

### 模型（`config/settings.yaml`）

| 组件 | 配置项 | 当前值 |
|------|--------|--------|
| Embedding | `models.embedding` | `text-embedding-v3`（1024 维） |
| Reranker | `models.rerank` | `qwen3-rerank` |
| LLM | `models.llm` | `deepseek-v4-flash` |

### 检索（`retrieval` 段）

| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| `dense_top_k` / `sparse_top_k` | 10 | 单路检索候选数 |
| `candidate_top_n` | 10 | RRF 融合后保留 chunk 数 |
| `rerank_top_m` | 5 | 问答与 Rerank 评估返回条数上限 |

### 多轮对话（`chat` 段，Web/API）

| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| `max_history_turns` | 6 | 参与改写的最近消息轮数 |
| `max_assistant_chars` | 400 | 历史中助手回复截断长度 |

## OCR 说明（CPU 环境）

PaddleOCR 在 CPU 上较慢，默认 `ocr.enabled: false`。如需启用：

```yaml
ocr:
  enabled: true
  timeout_seconds: 120
```

## 运行测试

```bash
set USE_MOCK=true
set DASHSCOPE_API_KEY=mock-key
pytest
```

- `USE_MOCK=true` 时自动 Mock Milvus（见 `tests/conftest.py`），无需启动 Milvus。
- `tests/test_api.py` 需要 PostgreSQL（与 `docker compose` 中库一致）；无库时会 skip。
- 本地调试 embedding 批大小：`python scripts/debug_embedding_batch.py [文件路径]`（非 pytest）。

## 技术栈

| 组件 | 选型 |
|------|------|
| Embedding | text-embedding-v3（百炼，1024 维） |
| Reranker | qwen3-rerank（百炼） |
| LLM | deepseek-v4-flash（百炼） |
| 向量库 | Milvus 2.5 |
| 元数据库 | PostgreSQL 15 |
| 框架 | LlamaIndex + 自研检索管线 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | 实现状态、架构、评测结果、已知缺口 |
| [docs/spec.md](docs/spec.md) | 需求规格与成功标准 |
| [docs/spec-web.md](docs/spec-web.md) | Web/API v0.2 规格 |
| [AGENTS.md](AGENTS.md) | Agent 修改指引 |
| [data/documents/confluence/README.md](data/documents/confluence/README.md) | Confluence 基准数据说明 |
| [data/eval_dataset/README.md](data/eval_dataset/README.md) | 评估数据集格式 |

## 许可证

MIT
