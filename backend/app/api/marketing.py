from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from containers.marketing.chat_service import generate_consultant_reply, opening_message

router = APIRouter(prefix="/marketing", tags=["Marketing"])


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class MarketingChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=40)


class MarketingChatResponse(BaseModel):
    reply: str
    show_contact: bool
    user_turns: int


@router.get("/chat/opening")
async def get_opening_message():
    """Return the consultant's opening line for new sessions."""
    return {"message": opening_message()}


@router.post("/chat", response_model=MarketingChatResponse)
async def marketing_chat(request: MarketingChatRequest):
    """
    Stateless consultant chat for anonymous marketing leads.
    Client sends prior history; server returns the next consultant reply.
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    history = [{"role": m.role, "content": m.content.strip()} for m in request.history]
    history = [m for m in history if m["content"]]

    result = await generate_consultant_reply(history, user_message=message)
    return MarketingChatResponse(
        reply=result["reply"],
        show_contact=result["show_contact"],
        user_turns=result["user_turns"],
    )
