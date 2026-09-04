import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Float, Integer, ForeignKey, func, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ModelResponse(Base):
    __tablename__ = "model_responses"
    __table_args__ = (
        UniqueConstraint("session_id", "model_name", name="ux_responses_session_model"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("council_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency: Mapped[float] = mapped_column(Float, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="done", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    critique: Mapped[str | None] = mapped_column(Text, nullable=True)
    critique_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped["CouncilSession"] = relationship(back_populates="responses", lazy="joined")
