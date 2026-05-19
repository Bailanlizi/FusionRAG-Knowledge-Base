# 项目现状

> 最后更新：2026-05-19

## 概述

FusionRAG Knowledge Base 是一套 **CLI 形态** 的知识库问答系统，实现完整的 Fusion RAG 管线：文档入库 → 混合检索 → 重排序 → 带引用生成。当前无 HTTP API 层。

## 实现状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 基础设施 | ✅ 可用 | Docker Compose：Milvus 2.5 + etcd + MinIO + PostgreSQL 15 |
| 文档入库 | ✅ 可用 | `scripts/run_ingest.py`，支持 PDF / MD / TXT |
| 混合检索 | ✅ 可用 | 稠密向量 + BM25 → RRF 融合 |
| Multi-Query | ✅ 可用 | SIMPLE / MODERATE / COMPLEX → 1 / 3 / 5 条子查询 |
| Reranker | ✅ 可用 | 问答与评估均可启用 |
| 答案生成 | ✅ 可用 | `scripts/run_query.py`（单次 / 交互） |
| 检索评估 | ✅ 可用 | `scripts/run_eval.py`，输出至 `reports/` |
| Mock 模式 | ✅ 可用 | `USE_MOCK=true`，无 API Key 本地开发 |
| 单元测试 | ✅ 可用 | `pytest`（8 个测试文件） |
| HTTP API | ❌ 未实现 | 仅 CLI 入口 |
| CI/CD | ❌ 未实现 | 无 GitHub Actions 等流水线 |

## 架构

```
入库:  DocumentParser → SemanticChunker → Embedding → Milvus + PostgreSQL
问答:  QueryProcessor → HybridSearcher → ChunkReranker → AnswerGenerator (LLM)
评估:  Evaluator（同上检索链 + Recall@K / Hit@K / nDCG@K / MRR）
```

### 双库存储分工

| 存储 | 职责 |
|------|------|
| **Milvus** | 稠密向量检索、BM25 稀疏检索、chunk 向量与稀疏字段 |
| **PostgreSQL** | 文档元数据（`documents`）、chunk 正文与元信息（`chunks`） |

Confluence 导出文档的文件名格式为 `dsid_<hex32>__<slug>.md`，`parser.resolve_doc_id()` 从中提取稳定 `doc_id`，与评测集 `expected_doc_ids` 对齐。

## 代码结构

```
src/
├── ingestion/     parser.py, chunker.py, indexer.py, models.py
├── retrieval/     query_processor.py, hybrid_search.py, rrf.py,
│                  reranker.py, generator.py, schemas.py
├── evaluation/    dataset.py, metrics.py, evaluator.py
└── utils/         config.py, db.py, api_clients.py, logger.py

scripts/           init_db.py, run_ingest.py, run_query.py, run_eval.py
config/            settings.yaml, prompts/
```

共 **22** 个 Python 源文件（`src/` 下）。

## 数据资产

### Confluence 基准集（主评测数据）

| 路径 | 规模 | 说明 |
|------|------|------|
| `data/documents/confluence/confluence_markdown/` | **104** 篇 MD | 企业运维 / 发布 / 事故复盘等文档 |
| `data/documents/confluence/confluence_questions.jsonl` | **64** 条 | 检索评测问答，含 `expected_doc_ids`、`gold_answer` |

入库命令：

```bash
python scripts/run_ingest.py --path data/documents/confluence/confluence_markdown --init-db
```

### 演示评估集

`data/eval_dataset/sample.json`：3 条占位题，用于快速 smoke test（需自行准备对应文档或 Mock）。

## 近期检索评估（Confluence，含 Reranker）

来源：`reports/eval_20260519_064503.json`（64 题，`--with-reranker`）

| 指标 | @1 | @5 | @10 |
|------|-----|-----|------|
| Recall | 0.70 | 0.92 | 0.95 |
| Hit | 0.91 | 1.00 | 1.00 |
| nDCG | 0.91 | 0.91 | 0.92 |
| MRR | — | — | **0.93** |

复现：

```bash
python scripts/run_eval.py \
  --dataset data/documents/confluence/confluence_questions.jsonl \
  --k 1,5,10 --with-reranker
```

## 配置与模型（`config/settings.yaml`）

| 角色 | 配置项 | 当前值 |
|------|--------|--------|
| Embedding | `models.embedding` | `text-embedding-v3`（1024 维） |
| Reranker | `models.rerank` | `qwen3-vl-rerank` |
| LLM | `models.llm` | `deepseek-v4-flash` |
| 检索 | `retrieval.*` | dense/sparse top_k=10，RRF k=60，rerank top_m=5 |
| Multi-Query | `multi_query.*` | SIMPLE=1，MODERATE=3，COMPLEX=5 |
| OCR | `ocr.enabled` | `false`（CPU 环境默认关闭） |

环境变量见 `.env.example`。

## 已知缺口与后续方向

1. **无对外 HTTP API** — 如需集成，可加 FastAPI 薄封装层。
2. **无 CI/CD** — 建议在 PR 上跑 `USE_MOCK=true pytest`。
3. **README 与 spec 需随配置同步** — 模型名以 `settings.yaml` 为准。
4. **`volumes/`、`logs/`** — 已在 `.gitignore` 中排除，勿提交运行时数据。

## 相关文档

- [spec.md](./spec.md) — 需求与成功标准
- [../README.md](../README.md) — 快速开始与使用说明
- [../AGENTS.md](../AGENTS.md) — Cursor Agent 工作指引
