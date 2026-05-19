"""Configuration: merge settings.yaml with .env environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ModelsConfig(BaseSettings):
    embedding: str = "qwen3-vl-embedding"
    embedding_dim: int = 1024
    rerank: str = "qwen3-vl-rerank"
    llm: str = "deepseek-v4-flash"
    llm_temperature: float = 0.1


class ChunkingConfig(BaseSettings):
    min_tokens: int = 200
    target_min: int = 512
    target_max: int = 1024
    merge_short_chunks: bool = True


class RetrievalConfig(BaseSettings):
    dense_top_k: int = 20
    sparse_top_k: int = 20
    rrf_k: int = 60
    candidate_top_n: int = 20
    rerank_top_m: int = 5


class MultiQueryConfig(BaseSettings):
    simple: int = 1
    moderate: int = 3
    complex: int = 5


class ChatConfig(BaseSettings):
    max_history_turns: int = 6
    max_assistant_chars: int = 400


class OcrConfig(BaseSettings):
    enabled: bool = False
    timeout_seconds: int = 120
    complexity_threshold: float = 0.5


class IngestConfig(BaseSettings):
    batch_size: int = 16
    max_retries: int = 3


class MilvusConfig(BaseSettings):
    collection_name: str = "fusion_rag_chunks"
    index_type: str = "AUTOINDEX"
    metric_type: str = "COSINE"


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    file: str = "logs/fusion_rag.log"
    max_bytes: int = 10485760
    backup_count: int = 5


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dashscope_api_key: str = Field(default="", alias="DASHSCOPE_API_KEY")
    milvus_host: str = Field(default="localhost", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_collection: str = Field(default="fusion_rag_chunks", alias="MILVUS_COLLECTION")
    postgres_url: str = Field(
        default="postgresql://fusion:fusion@localhost:5432/fusion_rag",
        alias="POSTGRES_URL",
    )
    use_mock: bool = Field(default=False, alias="USE_MOCK")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


class Settings:
    """Merged application settings from YAML + environment."""

    def __init__(self) -> None:
        raw = _load_yaml()
        self.models = ModelsConfig(**raw.get("models", {}))
        self.chunking = ChunkingConfig(**raw.get("chunking", {}))
        self.retrieval = RetrievalConfig(**raw.get("retrieval", {}))
        self.multi_query = MultiQueryConfig(**raw.get("multi_query", {}))
        self.chat = ChatConfig(**raw.get("chat", {}))
        self.ocr = OcrConfig(**raw.get("ocr", {}))
        self.ingest = IngestConfig(**raw.get("ingest", {}))
        self.milvus = MilvusConfig(**raw.get("milvus", {}))
        self.logging = LoggingConfig(**raw.get("logging", {}))
        self.env = EnvSettings()

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()
