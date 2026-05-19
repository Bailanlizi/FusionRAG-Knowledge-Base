# FusionRAG Knowledge Base — Specification v0.1.0

> 实现进度与评测数据见 [PROJECT_STATUS.md](./PROJECT_STATUS.md)。

## 1. Objective

构建基于 Fusion RAG 架构的个人/企业知识库问答系统。从 Markdown、PDF（含扫描件、复杂表格）提取信息，通过自适应 Multi-Query 理解用户问题，生成带来源引用的准确答案。

## 2. Tech Stack

| 组件 | 技术选型 | 配置项（`settings.yaml`） |
|------|----------|---------------------------|
| Embedding | text-embedding-v3（百炼） | `models.embedding`，1024 维 |
| Reranker | qwen3-vl-rerank（百炼） | `models.rerank` |
| LLM | deepseek-v4-flash（百炼） | `models.llm` |
| 向量库 | Milvus 2.5+ | 稠密 + BM25 混合检索 |
| 元数据库 | PostgreSQL 15+ | 文档与 chunk 元数据 |
| 框架 | LlamaIndex | RAG 编排 |
| 解析 | Docling + PaddleOCR（可选） | `ocr.enabled` 默认 false |

## 3. Modules

### 3.1 Ingestion

- Docling 基础解析 → 复杂度判断 → 可选 PaddleOCR 增强
- 结构化语义切分（512–1024 tokens，见 `chunking.*`）
- Embedding → Milvus + PostgreSQL 双写
- Confluence 导出：`dsid_<hex32>__` 文件名 → 稳定 `doc_id`

### 3.2 Retrieval

- 自适应 Multi-Query（SIMPLE / MODERATE / COMPLEX → 1 / 3 / 5 查询）
- 稠密 + BM25 混合检索 → RRF 融合 → Qwen Rerank
- LLM 生成答案 + 引用来源

### 3.3 Evaluation

- Recall@K、Hit@K、nDCG@K、MRR
- 主基准：`data/documents/confluence/confluence_questions.jsonl`（64 题）

## 4. Success Criteria

- [x] Docker：Milvus + PostgreSQL 健康运行
- [x] `run_ingest.py` 索引 PDF/MD
- [x] `run_query.py` 返回答案 + 引用
- [x] Multi-Query 按复杂度动态生成查询
- [x] `run_eval.py` 输出检索指标
- [x] `pytest` 全部通过（mock 模式）
- [ ] HTTP API 层（未规划实现）
- [ ] CI/CD 自动化（未实现）

## 5. Out of Scope (v0.1)

- Web UI / REST API
- 生成质量自动评测（仅检索指标已落地）
- 多租户与权限体系
