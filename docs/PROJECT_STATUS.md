# 项目现状

> 最后更新：2026-05-20

## 概述

FusionRAG Knowledge Base 实现完整的 Fusion RAG 管线：文档入库 → 混合检索 → Reranker → 带引用生成。提供 **CLI** 与 **Web UI（v0.2）** 两种使用方式。

Web 对话已支持 **多轮 RAG**（Query Rewrite + 历史截断）与 **乐观 UI**（发送即显示用户消息）；CLI `run_query` 仍为单轮问答。

## 实现状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 基础设施 | ✅ 可用 | Docker Compose：Milvus 2.5 + etcd + MinIO + PostgreSQL 15 |
| 文档入库 | ✅ 可用 | `scripts/run_ingest.py`，支持 PDF / MD / TXT |
| 混合检索 | ✅ 可用 | 稠密向量 + BM25 → RRF 融合 |
| Multi-Query | ✅ 可用 | SIMPLE / MODERATE / COMPLEX → 1 / 3 / 5 条子查询 |
| Query Rewrite（多轮） | ✅ 可用 | Web/API 对话：历史 → 独立检索问句 → 再走 Multi-Query |
| Reranker | ✅ 可用 | 问答与 Web 对话**始终**启用；评估默认关闭，`--with-reranker` 开启 |
| 答案生成 | ✅ 可用 | `scripts/run_query.py`（单次 / 交互，单轮） |
| 检索评估 | ✅ 可用 | `scripts/run_eval.py`，支持 JSON / JSONL，输出至 `reports/` |
| Mock 模式 | ✅ 可用 | `USE_MOCK=true`，无 API Key 本地开发 |
| 单元测试 | ✅ 可用 | `pytest`（9 个测试模块，含 `test_query_rewriter`） |
| HTTP API + Web UI | ✅ 可用 | FastAPI `:8000` + React `:5173`（见 [spec-web.md](./spec-web.md)） |
| Web 对话 UX | ✅ 可用 | 发送即清空输入、乐观显示用户气泡、加载态、Trace 展示改写查询 |
| CI/CD | ⚠️ 部分 | 仓库含 `.github/workflows/ci.yml`，本地以 Mock 测试为主 |

## 架构

```
入库:  DocumentParser → SemanticChunker → Embedding → Milvus + PostgreSQL

问答 (CLI):
  QueryProcessor → HybridSearcher → ChunkReranker → AnswerGenerator (LLM)

问答 (Web 多轮):
  会话历史 → QueryRewriter → standalone_query
           → QueryProcessor → HybridSearcher → ChunkReranker → AnswerGenerator
  （生成阶段仍使用用户「当前原句」；检索/Rerank 使用改写后的问句）

Web:   FastAPI → ChatService / DocumentService → 同上内核
评估:  QueryProcessor → HybridSearcher → [可选 ChunkReranker] → 文档级指标
```

### 双库存储分工

| 存储 | 职责 |
|------|------|
| **Milvus** | 稠密向量检索、BM25 稀疏检索、chunk 向量与稀疏字段 |
| **PostgreSQL** | 文档元数据（`documents`）、chunk 正文（`chunks`）、会话（`conversations` / `messages`） |

### 文档 ID 约定

Confluence 导出文件名为 `dsid_<hex32>__<slug>.md`。`parser.resolve_doc_id()` 从中提取稳定 `doc_id`，与评测集 `expected_doc_ids` 对齐。其他文件仍使用路径 MD5 前 16 位作为 `doc_id`。

## 代码结构

```
src/
├── ingestion/     parser.py, chunker.py, indexer.py, models.py
├── retrieval/     query_rewriter.py, query_processor.py, hybrid_search.py,
│                  rrf.py, reranker.py, generator.py, schemas.py
├── evaluation/    dataset.py, metrics.py, evaluator.py
├── api/           main.py, routers/, services/ (chat, document)
└── utils/         config.py, db.py, api_clients.py, logger.py

scripts/           init_db.py, run_ingest.py, run_query.py, run_eval.py, run_api.py
web/               React 前端（Chat + Documents）
config/            settings.yaml, prompts/ (multi_query, query_rewrite, generate)
```

共 **25+** 个 Python 源文件（`src/` 核心 + `src/api/`）。

## Web 功能摘要（v0.2）

| 能力 | 说明 |
|------|------|
| 对话 | 多轮会话持久化；Markdown 回答；引用折叠；Chunk 抽屉；Trace（含改写查询） |
| 多轮 RAG | `QueryRewriter` + 最近 N 轮历史（`chat.max_history_turns`） |
| 文档管理 | 统计、列表筛选、上传即入库、删除、预览 |
| 上传 | `POST /api/documents/upload` → 同步 `index_file()` |
| 非目标 | SSE 流式、鉴权、生成质量自动评测 |

## 数据资产

### Confluence 基准集（主评测数据）

| 路径 | 规模 | 说明 |
|------|------|------|
| `data/documents/confluence/confluence_markdown/` | **132** 篇 MD | 企业运维 / 发布 / 事故复盘等文档 |
| `data/documents/confluence/confluence_questions.jsonl` | **64** 条 | 检索评测问答，含 `expected_doc_ids`、`gold_answer` |

入库（Confluence 文档使用 `dsid_*` 作为 `doc_id`，若曾用旧版 path-hash 入库需 `--force` 重索引）：

```bash
python scripts/run_ingest.py \
  --path data/documents/confluence/confluence_markdown \
  --init-db
```

### 演示评估集

`data/eval_dataset/sample.json`：3 条占位题，用于快速 smoke test。

## 检索评估结果（Confluence 64 题，K=1,5,10）

在同一套入库数据上对比两种评估模式（2026-05-19）：

| 指标 | 无 Reranker（RRF） | 有 Reranker | Δ |
|------|-------------------|-------------|-----|
| Hit@1 | 0.906 | **0.969** | +0.063 |
| Recall@1 | 0.704 | **0.753** | +0.049 |
| MRR | 0.931 | **0.992** | +0.061 |
| Hit@5 / @10 | 1.000 | 1.000 | — |
| Recall@10 | 0.947 | 0.952 | +0.005 |

| 报告文件 | 模式 |
|----------|------|
| `reports/eval_20260519_064503.json` | `use_reranker: false`（默认） |
| `reports/eval_rerank_20260519_142835.json` | `use_reranker: true` |

复现：

```bash
python scripts/run_eval.py \
  --dataset data/documents/confluence/confluence_questions.jsonl \
  --k 1,5,10

python scripts/run_eval.py \
  --dataset data/documents/confluence/confluence_questions.jsonl \
  --k 1,5,10 --with-reranker
```

评估说明：

- 指标在 **文档级** `doc_id` 上计算（同一文档多个 chunk 去重）。
- `ground_truth_docs` 与 `expected_doc_ids` 均支持（见 `src/evaluation/dataset.py`）。
- 带 Reranker 时每题调用百炼 Rerank API，耗时与 token 消耗显著高于无 Reranker 模式。
- **多轮 Query Rewrite 未纳入检索评估**（评测仍为单轮问句）。

## 配置与模型（`config/settings.yaml`）

| 角色 | 配置项 | 当前值 |
|------|--------|--------|
| Embedding | `models.embedding` | `text-embedding-v3`（1024 维） |
| Reranker | `models.rerank` | `qwen3-rerank` |
| LLM | `models.llm` | `deepseek-v4-flash` |
| 检索 | `retrieval.*` | dense/sparse top_k=10，candidate_top_n=10，RRF k=60，rerank_top_m=5 |
| Multi-Query | `multi_query.*` | SIMPLE=1，MODERATE=3，COMPLEX=5 |
| 多轮对话 | `chat.*` | max_history_turns=6，max_assistant_chars=400 |
| OCR | `ocr.enabled` | `false`（CPU 环境默认关闭） |

环境变量见 `.env.example`。

## 已知缺口与后续方向

1. **生成质量评测** — 当前仅检索指标；`gold_answer` 尚未用于答案准确率评估。
2. **生成阶段未带对话历史** — 改写仅用于检索；复杂指代在生成 prompt 中仍可能不足（可扩展 `generate.txt`）。
3. **评估 MRR 重复检索** — 每题检索执行两次，大基准集上可优化耗时。
4. **Web 流式输出** — 当前为同步生成，未实现 SSE。
5. **大文件上传** — Web 上传为同步 `index_file`，大 PDF 可能长时间阻塞请求。
6. **`volumes/`、`logs/`、`reports/*.json`** — 已在 `.gitignore` 中排除，勿提交运行时数据。

## Web 启动

```bash
docker compose up -d
python scripts/init_db.py
python scripts/run_api.py          # http://localhost:8000/docs
cd web && npm install && npm run dev   # http://localhost:5173
```

## 相关文档

- [spec.md](./spec.md) — 需求与成功标准
- [spec-web.md](./spec-web.md) — Web/API v0.2 规格
- [../README.md](../README.md) — 快速开始与使用说明
- [../AGENTS.md](../AGENTS.md) — Cursor Agent 工作指引
- [../data/documents/confluence/README.md](../data/documents/confluence/README.md) — Confluence 基准说明
