from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

ModelId = Literal["claude", "chatgpt", "gemini", "deepseek", "qwen", "kimi", "kimi-k2.5", "kimi-k3", "grok", "llama"]


class ModelResponseRead(BaseModel):
    id: str
    session_id: str
    model_name: ModelId
    reasoning: str | None = None
    final_answer: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    latency: float = Field(ge=0)
    token_count: int | None = Field(default=None, ge=0)
    status: Literal["done", "error", "timeout"] = "done"
    error_message: str | None = None
    critique: str | None = None
    critique_score: float | None = Field(default=None, ge=0, le=10)
    raw_payload: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
