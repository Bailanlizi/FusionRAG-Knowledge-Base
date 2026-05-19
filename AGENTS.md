# Agent 工作指引

本文件供 Cursor / 其他编码 Agent 在修改本仓库时快速建立上下文。

## 项目是什么

FusionRAG Knowledge Base：基于 **稠密向量 + BM25 + RRF + Reranker** 的企业知识库 RAG 系统，提供 CLI 与 Web（FastAPI + React），依赖 Milvus + PostgreSQL + 百炼 DashScope API。

详细现状见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## 关键路径

| 任务 | 入口 |
|------|------|
| 初始化 DB | `scripts/init_db.py` |
| 文档入库 | `scripts/run_ingest.py` → `src/ingestion/indexer.py` |
| 问答 | `scripts/run_query.py` → `src/retrieval/generator.py` |
| 检索评估 | `scripts/run_eval.py` → `src/evaluation/evaluator.py`（`--with-reranker` 可选） |
| Web API | `scripts/run_api.py` → `src/api/main.py` |
| Web 前端 | `web/`（`npm run dev`，代理 `/api` → :8000） |
| 配置 | `config/settings.yaml` + `.env` |
| Prompt | `config/prompts/multi_query.txt`, `query_rewrite.txt`, `generate.txt` |

## 修改时注意

1. **doc_id 约定**：Confluence 文件名为 `dsid_<hex32>__*.md`，解析逻辑在 `src/ingestion/parser.py` 的 `resolve_doc_id()`；评测集用 `expected_doc_ids` / `ground_truth_docs`。
2. **Mock 模式**：`USE_MOCK=true` 时走 `src/utils/api_clients.py` 中的 Mock 客户端，改检索逻辑时需兼顾单测。
3. **双写**：入库同时写 Milvus 与 PostgreSQL；改 schema 需同步 `src/utils/db.py`。
4. **范围克制**：优先小 diff；不要顺手重构无关模块。
5. **验证**：改完后在 Mock 下跑 `pytest`；涉及检索时可用 `run_eval.py` 对 `confluence_questions.jsonl` 抽样验证。
6. **评估模式**：默认仅 RRF；`--with-reranker` 与 `run_query` / Web 对话的 Rerank 链一致。报告：`eval_*.json` / `eval_rerank_*.json`。
7. **Web 多轮**：`ChatService` 传历史 → `QueryRewriter` → `AnswerGenerator`；`run_query` 无历史，单轮 only。

## 评测数据

- **主基准**：`data/documents/confluence/confluence_questions.jsonl`（64 题，132 篇文档）
- **Smoke**：`data/eval_dataset/sample.json`（3 题）
- **指标字段**：`expected_doc_ids` 或 `ground_truth_docs`（`src/evaluation/dataset.py`）

## Agent Skills

仓库内 `.cursor/rules/` 含分阶段工作流技能（spec、TDD、debug 等）。会话开始时可用 `using-agent-skills` 选择合适技能。

## 不要提交

- `.env`（含 API Key）
- `volumes/`、`logs/`、`reports/*.json`（报告目录仅保留 `.gitkeep`）
