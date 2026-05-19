"""API clients for DashScope: Embedding, Rerank, LLM + Mock implementations."""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.config import get_settings
from src.utils.logger import logger

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/api/v1"


def _stable_vector(text: str, dim: int = 1024) -> list[float]:
  """Deterministic mock embedding from text hash."""
  h = hashlib.sha256(text.encode()).digest()
  rng = np.random.default_rng(int.from_bytes(h[:8], "big"))
  vec = rng.standard_normal(dim).astype(np.float32)
  vec /= np.linalg.norm(vec) + 1e-8
  return vec.tolist()


class BaseEmbeddingClient(ABC):
  @abstractmethod
  def embed(self, texts: list[str]) -> list[list[float]]:
    ...


class BaseRerankClient(ABC):
  @abstractmethod
  def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
    ...


class BaseLLMClient(ABC):
  @abstractmethod
  def chat(self, messages: list[dict[str, str]], temperature: float | None = None) -> str:
    ...


class MockEmbeddingClient(BaseEmbeddingClient):
  def embed(self, texts: list[str]) -> list[list[float]]:
    dim = get_settings().models.embedding_dim
    return [_stable_vector(t, dim) for t in texts]


class MockRerankClient(BaseRerankClient):
  def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
    scores = []
    for i, doc in enumerate(documents):
      overlap = len(set(query.lower().split()) & set(doc.lower().split()))
      scores.append((i, float(overlap)))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_n]


class MockLLMClient(BaseLLMClient):
  def chat(self, messages: list[dict[str, str]], temperature: float | None = None) -> str:
    last = messages[-1].get("content", "") if messages else ""
    if "对话查询改写" in last or "standalone_query" in last:
      question = last
      if "用户最后一句话：" in last:
        question = last.split("用户最后一句话：", 1)[-1].strip()
      has_history = "对话历史" in last and "（无）" not in last
      standalone = f"结合上文：{question}" if has_history else question
      return json.dumps(
        {"standalone_query": standalone, "is_follow_up": has_history}
      )
    if "检索查询优化" in last or "complexity" in last.lower():
      question = last
      if "用户问题：" in last:
        question = last.split("用户问题：", 1)[-1].strip()
      return json.dumps({"complexity": "SIMPLE", "queries": [question]})
    return f"[Mock answer] Based on context for: {last[:100]}"


class QwenEmbeddingClient(BaseEmbeddingClient):
  def __init__(self) -> None:
    self.settings = get_settings()
    self.api_key = self.settings.env.dashscope_api_key
    self.model = self.settings.models.embedding
    self.dim = self.settings.models.embedding_dim

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
  def embed(self, texts: list[str]) -> list[list[float]]:
    import dashscope
    from dashscope import TextEmbedding

    dashscope.api_key = self.api_key
    results: list[list[float]] = []
    batch_size = self.settings.ingest.batch_size

    for i in range(0, len(texts), batch_size):
      batch = texts[i : i + batch_size]
      resp = TextEmbedding.call(
        model=self.model,
        input=batch,
        dimension=self.dim,
      )
      if resp.status_code != 200:
        raise RuntimeError(f"Embedding API error: {resp.code} {resp.message}")
      for item in resp.output["embeddings"]:
        results.append(item["embedding"])
    return results


class QwenRerankClient(BaseRerankClient):
  def __init__(self) -> None:
    self.settings = get_settings()
    self.api_key = self.settings.env.dashscope_api_key
    self.model = self.settings.models.rerank

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
  def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
    url = f"{DASHSCOPE_BASE}/services/rerank/text-rerank/text-rerank"
    payload = {
      "model": self.model,
      "input": {"query": query, "documents": documents},
      "parameters": {"top_n": top_n, "return_documents": False},
    }
    headers = {
      "Authorization": f"Bearer {self.api_key}",
      "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60.0) as client:
      resp = client.post(url, json=payload, headers=headers)
      resp.raise_for_status()
      data = resp.json()

    results = data.get("output", {}).get("results", [])
    return [(r["index"], r["relevance_score"]) for r in results]


class DeepSeekLLMClient(BaseLLMClient):
  def __init__(self) -> None:
    self.settings = get_settings()
    self.api_key = self.settings.env.dashscope_api_key
    self.model = self.settings.models.llm
    self.default_temp = self.settings.models.llm_temperature

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
  def chat(self, messages: list[dict[str, str]], temperature: float | None = None) -> str:
    import dashscope
    from dashscope import Generation

    dashscope.api_key = self.api_key
    resp = Generation.call(
      model=self.model,
      messages=messages,
      result_format="message",
      temperature=temperature if temperature is not None else self.default_temp,
    )
    if resp.status_code != 200:
      raise RuntimeError(f"LLM API error: {resp.code} {resp.message}")
    return resp.output.choices[0].message.content


def get_embedding_client() -> BaseEmbeddingClient:
  if get_settings().env.use_mock:
    return MockEmbeddingClient()
  return QwenEmbeddingClient()


def get_rerank_client() -> BaseRerankClient:
  if get_settings().env.use_mock:
    return MockRerankClient()
  return QwenRerankClient()


def get_llm_client() -> BaseLLMClient:
  if get_settings().env.use_mock:
    return MockLLMClient()
  return DeepSeekLLMClient()


def parse_json_from_llm(text: str) -> dict[str, Any]:
  """Extract JSON object from LLM response."""
  text = text.strip()
  if text.startswith("```"):
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
  try:
    return json.loads(text)
  except json.JSONDecodeError:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
      return json.loads(match.group())
    raise
