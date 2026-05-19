"""Conversation and messaging for the Web API."""

from __future__ import annotations

import json
import uuid

from fastapi import HTTPException

from src.api.schemas import (
    AssistantMessageResponse,
    ConversationDetail,
    ConversationSummary,
    MessageItem,
    SendMessageRequest,
    SourceItem,
    TraceInfo,
)
from src.retrieval.generator import AnswerGenerator
from src.utils.db import PostgresClient


class ChatService:
    def __init__(self) -> None:
        self.pg = PostgresClient()
        self.generator = AnswerGenerator()

    def list_conversations(self) -> list[ConversationSummary]:
        return [
            ConversationSummary(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in self.pg.list_conversations()
        ]

    def create_conversation(self, title: str | None = None) -> ConversationSummary:
        conv_id = str(uuid.uuid4())
        conv = self.pg.create_conversation(conv_id, title or "新对话")
        return ConversationSummary(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    def get_conversation(self, conv_id: str) -> ConversationDetail:
        conv = self.pg.get_conversation(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = [self._row_to_message(m) for m in self.pg.list_messages(conv_id)]
        return ConversationDetail(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages,
        )

    def delete_conversation(self, conv_id: str) -> None:
        if not self.pg.delete_conversation(conv_id):
            raise HTTPException(status_code=404, detail="Conversation not found")

    def send_message(
        self, conv_id: str, body: SendMessageRequest
    ) -> AssistantMessageResponse:
        conv = self.pg.get_conversation(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if body.regenerate:
            return self._regenerate(conv_id, body.target_message_id)

        if not body.content.strip():
            raise HTTPException(status_code=400, detail="Message content is required")

        user_msg_id = str(uuid.uuid4())
        self.pg.add_message(user_msg_id, conv_id, "user", body.content.strip())

        if conv.title == "新对话":
            title = body.content.strip()[:50] or "新对话"
            self.pg.touch_conversation(conv_id, title=title)
        else:
            self.pg.touch_conversation(conv_id)

        return self._generate_assistant(conv_id, body.content.strip(), user_msg_id)

    def _regenerate(
        self, conv_id: str, target_message_id: str | None
    ) -> AssistantMessageResponse:
        messages = self.pg.list_messages(conv_id)
        if not messages:
            raise HTTPException(status_code=400, detail="No messages to regenerate")

        assistant_msg = None
        if target_message_id:
            assistant_msg = self.pg.get_message(target_message_id)
        if not assistant_msg:
            for m in reversed(messages):
                if m.role == "assistant":
                    assistant_msg = m
                    break

        if not assistant_msg or assistant_msg.role != "assistant":
            raise HTTPException(status_code=400, detail="Assistant message not found")

        user_question = ""
        for m in messages:
            if m.id == assistant_msg.id:
                break
            if m.role == "user":
                user_question = m.content

        if not user_question:
            raise HTTPException(status_code=400, detail="User question not found")

        self.pg.delete_message(assistant_msg.id)
        return self._generate_assistant(conv_id, user_question, None)

    def _generate_assistant(
        self, conv_id: str, question: str, user_msg_id: str | None
    ) -> AssistantMessageResponse:
        detailed = self.generator.generate_detailed(question)
        sources = [SourceItem(**s) for s in detailed.sources]
        trace = TraceInfo(
            complexity=detailed.trace.complexity,
            queries=detailed.trace.queries,
            retrieval_ms=detailed.trace.retrieval_ms,
            rerank_ms=detailed.trace.rerank_ms,
            llm_ms=detailed.trace.llm_ms,
            chunk_count=detailed.trace.chunk_count,
        )

        msg_id = str(uuid.uuid4())
        self.pg.add_message(
            msg_id,
            conv_id,
            "assistant",
            detailed.answer,
            sources_json=json.dumps([s.model_dump() for s in sources], ensure_ascii=False),
            trace_json=trace.model_dump_json(),
        )
        self.pg.touch_conversation(conv_id)

        return AssistantMessageResponse(
            message_id=msg_id,
            content=detailed.answer,
            sources=sources,
            trace=trace,
            user_message_id=user_msg_id,
        )

    @staticmethod
    def _row_to_message(row) -> MessageItem:
        sources_raw = json.loads(row.sources_json or "[]")
        trace_raw = json.loads(row.trace_json or "{}")
        sources = [SourceItem(**s) for s in sources_raw] if sources_raw else []
        trace = TraceInfo(**trace_raw) if trace_raw else None
        return MessageItem(
            id=row.id,
            role=row.role,
            content=row.content,
            sources=sources,
            trace=trace,
            created_at=row.created_at,
        )
