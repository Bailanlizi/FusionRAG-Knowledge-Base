# 评估数据集

## 文件说明

| 文件 | 用途 |
|------|------|
| `sample.json` | **Smoke test**：3 条演示题，字段为 `question` + `ground_truth_docs`，适合快速验证评估管线是否跑通 |
| （推荐）`../documents/confluence/confluence_questions.jsonl` | **主基准**：64 条 Confluence 问答，含 `expected_doc_ids`、`gold_answer`、`answer_facts` |

## JSON 格式（`sample.json`）

```json
{
  "question": "问题文本",
  "ground_truth_docs": ["doc_id_1"],
  "answer": "可选：参考答案摘要"
}
```

## JSONL 格式（Confluence）

每行一条 JSON，关键字段：

- `question` — 评测问题
- `expected_doc_ids` — 相关文档 ID 列表（与入库时的 `doc_id` 一致）
- `gold_answer` — 标准答案（评估检索时不使用，可用于后续生成质量评测）

`load_dataset()` 同时支持 `ground_truth_docs` 与 `expected_doc_ids`（见 `src/evaluation/dataset.py`）。

## 运行评估

```bash
# Smoke（需已入库对应文档或使用 Mock）
python scripts/run_eval.py --dataset data/eval_dataset/sample.json --k 1,5,10

# Confluence 主基准 — 仅 RRF
python scripts/run_eval.py \
  --dataset data/documents/confluence/confluence_questions.jsonl \
  --k 1,5,10

# Confluence 主基准 — RRF + Reranker
python scripts/run_eval.py \
  --dataset data/documents/confluence/confluence_questions.jsonl \
  --k 1,5,10 --with-reranker
```

报告输出至 `reports/`（`eval_*.json` 无 Reranker，`eval_rerank_*.json` 有 Reranker）。
