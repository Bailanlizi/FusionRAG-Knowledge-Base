# FusionRAG Web UI & API — Specification v0.2

> v0.1 CLI 规格见 [spec.md](./spec.md)。实现进度见 [PROJECT_STATUS.md](./PROJECT_STATUS.md)。

## 1. Objective

在现有 Fusion RAG 内核上提供 **Web 界面**：多轮对话（Markdown + 引用 + 诊断信息）与文档管理（统计、列表、上传、删除、预览）。v1 无用户鉴权，面向本地/内网单用户。

## 2. Non-Goals (v0.2)

- 流式 SSE 输出
- 多租户 / RBAC
- `gold_answer` 生成质量自动评测
- K8s / HTTPS 生产部署

## 3. Tech Stack

| 层 | 选型 |
|----|------|
| API | FastAPI + uvicorn |
| 前端 | React 18 + TypeScript + Vite + Tailwind |
| 数据请求 | TanStack Query v5 |
| 路由 | React Router |
| 持久化 | PostgreSQL（会话/消息/文档元数据）+ Milvus |

## 4. API Contract

Base URL: `http://localhost:8000`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/kb/stats` | document_count, chunk_count, last_updated_at |
| GET | `/api/documents` | List; query: q, source_type, sort, order, page, page_size |
| GET | `/api/documents/{doc_id}` | Document metadata |
| GET | `/api/documents/{doc_id}/chunks` | Chunk list for preview |
| POST | `/api/documents/upload` | multipart file upload → index |
| DELETE | `/api/documents/{doc_id}` | Delete PG + Milvus + file |
| GET | `/api/chunks/{chunk_id}` | Chunk detail for drawer |
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations/{id}` | Conversation + messages |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| POST | `/api/conversations/{id}/messages` | Send message or regenerate |

### POST `/api/conversations/{id}/messages`

Request:

```json
{
  "content": "user question",
  "regenerate": false,
  "target_message_id": null
}
```

When `regenerate: true`, re-run retrieval+generation for the last user turn; replace the target assistant message.

Response (assistant message):

```json
{
  "message_id": "uuid",
  "role": "assistant",
  "content": "markdown answer",
  "sources": [{ "index": 1, "chunk_id": "...", "doc_id": "...", "file_name": "...", "title_path": "...", "page": 1, "score": 0.87 }],
  "trace": {
    "complexity": "SIMPLE",
    "queries": ["..."],
    "retrieval_ms": 320,
    "rerank_ms": 180,
    "llm_ms": 2100,
    "chunk_count": 5
  }
}
```

## 5. Data Model

### Existing

- `documents`, `chunks` (unchanged semantics)

### New / Extended

- `documents.source_type`: `confluence` | `upload`
- `conversations(id, title, created_at, updated_at)`
- `messages(id, conversation_id, role, content, sources_json, trace_json, created_at)`

### source_type rules

- `confluence`: path contains `confluence_markdown` OR `doc_id` starts with `dsid_`
- `upload`: files under `data/documents/uploads/`
- Backfill on `init_tables()` for existing rows

## 6. UI Information Architecture

```
/  → redirect /chat
/chat     — SessionList | ChatArea | ChunkDrawer
/documents — StatsCards | Filters | Table | Upload | PreviewDrawer
```

## 7. Acceptance Criteria

- [ ] Swagger `/docs` accessible
- [ ] Documents: stats, upload PDF/MD, delete, preview, filter by source_type
- [ ] Chat: multi-turn, markdown, sources (collapse 3+), chunk drawer, copy, regenerate, trace panel
- [ ] `USE_MOCK=true` API tests pass; `npm run build` succeeds

## 8. Relation to CLI

CLI scripts (`run_ingest`, `run_query`, `run_eval`) remain; Web is additive via `run_api.py`.
