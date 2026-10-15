from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatLine(BaseModel):
    author: str = Field(default="Someone", max_length=60)
    text: str = Field(default="", max_length=1000)


class ChatContext(BaseModel):
    """Messages the user chose to share with LUNEX, e.g. 'Summarize this chat'."""
    messages: List[ChatLine] = Field(default_factory=list, max_length=250)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: List[Turn] = Field(default_factory=list, max_length=40)
    skill: Optional[Literal["auto", "chat", "research", "summarize", "faq", "translate", "calc", "time", "help"]] = None
    context: Optional[ChatContext] = None
    locale: Optional[str] = Field(default=None, max_length=12)
    tz: Optional[str] = Field(default=None, max_length=64)       # e.g. Africa/Johannesburg


class Source(BaseModel):
    title: str
    url: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    skill: str
    sources: List[Source] = Field(default_factory=list)
    remaining_today: int
