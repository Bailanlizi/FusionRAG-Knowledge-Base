# FusionRAG Knowledge Base

基于 Fusion RAG 架构的个人/企业知识库问答系统。融合 BM25 关键词检索与语义向量检索，支持自适应 Multi-Query、Qwen Reranker 重排序，以及 Docling 文档解析。

## 功能特性

- **Fusion RAG 检索**：稠密向量 + BM25 稀疏检索，RRF 融合 + Qwen Reranker 重排
- **自适应 Multi-Query**：按 SIMPLE / MODERATE / COMPLEX 动态生成 1–5 条子查询
- **企业级文档解析**：Docling 基础解析 + PaddleOCR 可选增强（CPU 默认关闭）
- **量化评估**：Recall@K、MRR、nDCG、Hit@K 自动化评估

## 环境要求

- Python 3.10+
- Docker Desktop（Milvus 2.5 + PostgreSQL 15）
- 阿里云百炼 DashScope API Key

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

将 PDF/Markdown 放入 `data/documents/`，然后：

```bash
python scripts/run_ingest.py --path data/documents --init-db
```

### 5. 问答查询

```bash
python scripts/run_query.py "FusionRAG 的核心检索策略是什么？"
python scripts/run_query.py --interactive
```

### 6. 检索评估

```bash
python scripts/run_eval.py --dataset data/eval_dataset/sample.json --k 1,5,10
```

## Mock 开发模式

无 API Key 时可在 `.env` 中设置：

```
USE_MOCK=true
```

Mock 模式使用确定性假向量与关键词重排，适合本地开发与单元测试。

## 项目结构

```
config/settings.yaml      # 应用配置
src/ingestion/            # 文档解析、切分、索引
src/retrieval/            # 检索、重排、生成
src/evaluation/           # 评估指标与流程
src/utils/                # 配置、DB、API 客户端
scripts/                  # CLI 入口
data/documents/           # 待索引文档
data/eval_dataset/        # 评估数据集
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `DASHSCOPE_API_KEY` | 百炼 API 密钥 | — |
| `MILVUS_HOST` | Milvus 地址 | localhost |
| `MILVUS_PORT` | Milvus 端口 | 19530 |
| `POSTGRES_URL` | PostgreSQL 连接串 | postgresql://fusion:fusion@localhost:5432/fusion_rag |
| `USE_MOCK` | Mock 模式 | false |

## OCR 说明（CPU 环境）

PaddleOCR 在 CPU 上较慢，默认在 `config/settings.yaml` 中 `ocr.enabled: false`。如需启用：

```yaml
ocr:
  enabled: true
  timeout_seconds: 120
```

## 运行测试

```bash
set USE_MOCK=true
pytest
```

## 技术栈

| 组件 | 选型 |
|------|------|
| Embedding | Qwen3-VL-Embedding (1024维) |
| Reranker | Qwen3-VL-Rerank |
| LLM | DeepSeek V4 Flash |
| 向量库 | Milvus 2.5 |
| 元数据库 | PostgreSQL 15 |
| 框架 | LlamaIndex + 自研检索管线 |

## 许可证

MIT
