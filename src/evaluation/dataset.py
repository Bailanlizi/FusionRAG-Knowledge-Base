"""Load evaluation datasets and resolve ground-truth document ids."""

from __future__ import annotations

import json
from pathlib import Path


def ground_truth_docs(item: dict) -> set[str]:
    """Merge ground_truth_docs and expected_doc_ids from eval items."""
    docs: list[str] = []
    docs.extend(item.get("ground_truth_docs") or [])
    docs.extend(item.get("expected_doc_ids") or [])
    return set(docs)


def load_json_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    return [data]


def load_jsonl_file(path: Path) -> list[dict]:
    items: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def load_dataset(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.is_dir():
        items: list[dict] = []
        for fp in sorted(path.glob("*.json")):
            items.extend(load_json_file(fp))
        for fp in sorted(path.glob("*.jsonl")):
            items.extend(load_jsonl_file(fp))
        return items
    if path.suffix.lower() == ".jsonl":
        return load_jsonl_file(path)
    return load_json_file(path)
