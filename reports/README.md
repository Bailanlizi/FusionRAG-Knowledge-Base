# 评估报告目录

`run_eval.py` 生成的 JSON 报告保存在此目录（已加入 `.gitignore`，不提交具体报告文件）。

## 文件命名

| 前缀 | 含义 |
|------|------|
| `eval_YYYYMMDD_HHMMSS.json` | 仅 RRF 混合检索（默认） |
| `eval_rerank_YYYYMMDD_HHMMSS.json` | RRF + ChunkReranker |

报告内 `use_reranker` 字段与文件名一致。

## 主要字段

- `summary` — 聚合指标（Recall@K、Hit@K、nDCG@K、MRR）
- `per_query` — 每题明细（检索到的 `doc_id`、ground truth、单题指标）
- `total` — 题目数量

## 参考结果

Confluence 64 题对比见 [docs/PROJECT_STATUS.md](../docs/PROJECT_STATUS.md)。
