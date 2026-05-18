"""Adaptive Multi-Query: classify question complexity and generate queries."""

from __future__ import annotations

from pathlib import Path

from src.utils.api_clients import get_llm_client, parse_json_from_llm
from src.utils.config import PROJECT_ROOT, get_settings
from src.utils.logger import logger

PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "multi_query.txt"


class QueryProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = get_llm_client()
        self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    def process(self, question: str) -> tuple[str, list[str]]:
        """
        Classify question and generate sub-queries.

        Returns:
            (complexity, list of queries)
        """
        prompt = self._prompt_template.format(question=question)
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            data = parse_json_from_llm(response)
            complexity = data.get("complexity", "SIMPLE").upper()
            queries = data.get("queries", [question])
        except Exception as e:
            logger.warning("Multi-query LLM failed, using original question: %s", e)
            complexity = "SIMPLE"
            queries = [question]

        max_queries = self._max_for_complexity(complexity)
        queries = queries[:max_queries] if queries else [question]

        if not queries:
            queries = [question]

        logger.info("Complexity=%s, generated %d queries", complexity, len(queries))
        return complexity, queries

    def _max_for_complexity(self, complexity: str) -> int:
        mq = self.settings.multi_query
        mapping = {
            "SIMPLE": mq.simple,
            "MODERATE": mq.moderate,
            "COMPLEX": mq.complex,
        }
        return mapping.get(complexity, mq.simple)
