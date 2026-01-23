from datetime import datetime
from sqlalchemy import ForeignKey, Text, Integer, func, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QuizValidation(Base, TimestampMixin):
    __tablename__ = "quiz_validations"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False, index=True)
    validation_status: Mapped[str] = mapped_column(nullable=False, index=True)  # 'pending', 'valid', 'invalid'
    validation_score: Mapped[int | None] = mapped_column(Integer, default=None)
    feedback: Mapped[str | None] = mapped_column(Text, default=None)
    issues: Mapped[list[str] | None] = mapped_column(JSONB, default=None)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="validations")
