from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatSource(BaseModel):
    type: Literal["history", "nutrition_knowledge", "recommendation"]
    title: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
    in_scope: bool = True
