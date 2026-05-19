"""Infer document source_type from path and doc_id."""

from __future__ import annotations

from pathlib import Path


def infer_source_type(file_path: str, doc_id: str) -> str:
    path_lower = file_path.replace("\\", "/").lower()
    if "confluence_markdown" in path_lower or doc_id.startswith("dsid_"):
        return "confluence"
    if "/uploads/" in path_lower or "\\uploads\\" in path_lower:
        return "upload"
    return "upload"
