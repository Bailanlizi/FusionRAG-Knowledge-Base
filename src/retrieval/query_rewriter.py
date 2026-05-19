"""Rewrite follow-up questions into standalone retrieval queries using chat history."""

from __future__ import annotations

from pathlib import Path

from src.retrieval.schemas import ChatTurn, QueryRewriteResult
from src.utils.api_clients import get_llm_client, parse_json_from_llm
from src.utils.config import PROJECT_ROOT, get_settings
from src.utils.logger import logger

PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "query_rewrite.txt"


class QueryRewriter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = get_llm_client()
        self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    def rewrite(self, question: str, history: list[ChatTurn]) -> QueryRewriteResult:
        trimmed = trim_history(
            history,
            max_turns=self.settings.chat.max_history_turns,
            max_assistant_chars=self.settings.chat.max_assistant_chars,
        )
        if not trimmed:
            return QueryRewriteResult(
                original_question=question,
                standalone_query=question,
                is_follow_up=False,
            )

        history_text = format_history(trimmed)
        prompt = self._prompt_template.format(history=history_text, question=question)
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            data = parse_json_from_llm(response)
            standalone = (data.get("standalone_query") or question).strip()
            is_follow_up = bool(data.get("is_follow_up", True))
        except Exception as e:
            logger.warning("Query rewrite failed, using original question: %s", e)
            standalone = question
            is_follow_up = len(trimmed) > 0

        if not standalone:
            standalone = question

        logger.info(
            "Query rewrite: follow_up=%s, original=%r -> standalone=%r",
            is_follow_up,
            question[:80],
            standalone[:80],
        )
        return QueryRewriteResult(
            original_question=question,
            standalone_query=standalone,
            is_follow_up=is_follow_up,
        )


def format_history(turns: list[ChatTurn]) -> str:
    lines: list[str] = []
    for turn in turns:
        label = "用户" if turn.role == "user" else "助手"
        lines.append(f"{label}：{turn.content}")
    return "\n".join(lines) if lines else "（无）"


def trim_history(
    turns: list[ChatTurn],
    *,
    max_turns: int,
    max_assistant_chars: int,
) -> list[ChatTurn]:
    """Keep the most recent turns; truncate long assistant messages."""
    if not turns or max_turns <= 0:
        return []

    recent = turns[-max_turns:]
    trimmed: list[ChatTurn] = []
    for turn in recent:
        content = turn.content
        if turn.role == "assistant" and len(content) > max_assistant_chars:
            content = content[:max_assistant_chars] + "…"
        trimmed.append(ChatTurn(role=turn.role, content=content))
    return trimmed
