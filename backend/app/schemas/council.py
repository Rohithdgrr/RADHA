from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

ModelId = Literal["claude", "chatgpt", "gemini", "deepseek", "qwen", "kimi", "kimi-k2.5", "kimi-k3", "grok", "llama"]
CouncilMode = Literal["consensus", "debate", "specialist", "weighted"]
Depth = Literal["brief", "standard", "detailed"]


class CouncilQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    models: list[ModelId] = Field(min_length=2, max_length=8)
    mode: CouncilMode = "consensus"
    depth: Depth = "detailed"
    show_reasoning: bool = True
    chairman: ModelId = "claude"

    @field_validator("query")
    @classmethod
    def check_query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be empty/whitespace")
        return v.strip()

    @field_validator("models")
    @classmethod
    def unique_models(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("duplicate models")
        return v


class CouncilSessionRead(BaseModel):
    id: str
    user_id: str | None = None
    user_query: str
    selected_models: list[ModelId]
    chairman_model: ModelId
    mode: CouncilMode
    depth: Depth
    show_reasoning: bool = True
    synthesis: str | None = None
    agreements: str | None = None
    divergences: str | None = None
    unique_insights: list[str] | None = None
    deliberation_log: list[dict] | None = None
    total_latency: float | None = None
    status: Literal["running", "done", "error", "partial"] = "done"
    created_at: datetime
    updated_at: datetime | None = None
    responses: list["ModelResponseRead"] = []  # populated via join

    model_config = ConfigDict(from_attributes=True)


# forward ref
from app.schemas.model_response import ModelResponseRead  # noqa: E402
