import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Float, Boolean, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CouncilSession(Base):
    __tablename__ = "council_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    selected_models: Mapped[list] = mapped_column(JSON, nullable=False)  # ["claude","chatgpt"] stored as JSON
    chairman_model: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="consensus", nullable=False)
    depth: Mapped[str] = mapped_column(String(20), default="detailed", nullable=False)
    show_reasoning: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    synthesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    agreements: Mapped[str | None] = mapped_column(Text, nullable=True)
    divergences: Mapped[str | None] = mapped_column(Text, nullable=True)
    unique_insights: Mapped[list | None] = mapped_column(JSON, nullable=True)
    deliberation_log: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_latency: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="sessions", lazy="joined")
    responses: Mapped[list["ModelResponse"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin", order_by="ModelResponse.model_name"
    )
