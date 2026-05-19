from fastapi import APIRouter

from src.api.schemas import (
    AssistantMessageResponse,
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    SendMessageRequest,
)
from src.api.services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["conversations"])
svc = ChatService()


@router.get("", response_model=list[ConversationSummary])
def list_conversations() -> list[ConversationSummary]:
    return svc.list_conversations()


@router.post("", response_model=ConversationSummary, status_code=201)
def create_conversation(body: ConversationCreate) -> ConversationSummary:
    return svc.create_conversation(body.title)


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: str) -> ConversationDetail:
    return svc.get_conversation(conv_id)


@router.delete("/{conv_id}", status_code=204)
def delete_conversation(conv_id: str) -> None:
    svc.delete_conversation(conv_id)


@router.post("/{conv_id}/messages", response_model=AssistantMessageResponse)
def send_message(conv_id: str, body: SendMessageRequest) -> AssistantMessageResponse:
    return svc.send_message(conv_id, body)
