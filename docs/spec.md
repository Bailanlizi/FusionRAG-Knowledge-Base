# FusionRAG Knowledge Base — Specification v0.1.0

## 1. Objective

构建基于 Fusion RAG 架构的个人/企业知识库问答系统。从 Markdown、PDF（含扫描件、复杂表格）提取信息，通过自适应 Multi-Query 理解用户问题，生成带来源引用的准确答案。

## 2. Tech Stack

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| Embedding | Qwen3-VL-Embedding (百炼) | 1024 维向量 |
| Reranker | Qwen3-VL-Rerank (百炼) | 交叉编码器重排序 |
| LLM | DeepSeek V4 Flash (百炼) | 分类、Multi-Query、生成 |
| 向量库 | Milvus 2.5+ | 稠密 + BM25 混合检索 |
| 元数据库 | PostgreSQL 15+ | 文档元数据 |
| 框架 | LlamaIndex | RAG 编排 |
| 解析 | Docling + PaddleOCR (可选) | 分层解析 |

## 3. Modules

### 3.1 Ingestion
- Docling 基础解析 → 复杂度判断 → 可选 PaddleOCR 增强
- 结构化语义切分 (512-1024 tokens)
- Qwen Embedding → Milvus + PostgreSQL

### 3.2 Retrieval
- 自适应 Multi-Query (SIMPLE/MODERATE/COMPLEX → 1/2-3/3-5 查询)
- 稠密 + BM25 混合检索 → RRF 融合 → Qwen Rerank
- DeepSeek 生成答案 + 引用来源

### 3.3 Evaluation
- Recall@K, MRR, nDCG, Hit@K

## 4. Success Criteria

- [ ] Docker: Milvus + PostgreSQL 健康运行
- [ ] `run_ingest.py` 索引 PDF/MD
- [ ] `run_query.py` 返回答案 + 引用
- [ ] Multi-Query 按复杂度动态生成查询
- [ ] `run_eval.py` 输出检索指标
- [ ] `pytest` 全部通过 (mock 模式)
